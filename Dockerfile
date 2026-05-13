FROM alpine:3.22.2

ENV TZ="UTC"
RUN sed -i 's!https://dl-cdn.alpinelinux.org/!https://mirrors.ustc.edu.cn/!g' /etc/apk/repositories && \
    CARGO_NET_GIT_FETCH_WITH_CLI=1 && \
    apk --no-cache add \
        sudo \
        python3\
        py3-pip \
        openssl \
        ca-certificates \
        sshpass \
        openssh-client \
        rsync \
        git \
        py3-paramiko \
        jq \
        zstd \
        tar \
        skopeo \
	curl \
	mariadb-client && \
    apk --no-cache add --virtual build-dependencies \
        libffi-dev \
	openssl-dev \
	python3-dev \
	build-base \
	py-setuptools \
	rust \
	cargo \
	mariadb-dev && \
    pip3 install -U pip wheel --break-system-packages && \
    pip3 install mysqlclient pywinrm 'ansible<=9.0.0' --break-system-packages && \
    apk del build-dependencies && \
    rm -rf /var/cache/apk/* && \
    rm -rf /root/.cache/pip && \
    rm -rf /root/.cargo

RUN mkdir -p /airgap_assets 
RUN	curl -L https://github.com/k3s-io/k3s/releases/download/v1.28.5%2Bk3s1/k3s -o /airgap_assets/k3s 
RUN	curl -L https://github.com/k3s-io/k3s/releases/download/v1.28.5%2Bk3s1/k3s-arm64 -o /airgap_assets/k3s-arm64 
RUN	curl -L https://github.com/k3s-io/k3s/releases/download/v1.28.5%2Bk3s1/k3s-airgap-images-amd64.tar.zst -o /airgap_assets/k3s-airgap-images-amd64.tar.zst 
RUN	curl -L https://github.com/k3s-io/k3s/releases/download/v1.28.5%2Bk3s1/k3s-airgap-images-arm64.tar.zst -o /airgap_assets/k3s-airgap-images-arm64.tar.zst 
RUN curl -L https://github.com/CARV-ICS-FORTH/k3s/releases/download/20241024/k3s-riscv64.gz.aa -o /tmp/k3s-riscv64.gz.aa 
RUN curl -L https://github.com/CARV-ICS-FORTH/k3s/releases/download/20241024/k3s-riscv64.gz.ab -o /tmp/k3s-riscv64.gz.ab 
RUN curl -L https://github.com/CARV-ICS-FORTH/k3s/releases/download/20241024/k3s-riscv64.gz.ac -o /tmp/k3s-riscv64.gz.ac 
RUN cat /tmp/k3s-riscv64.gz.* | gunzip > /airgap_assets/k3s-riscv64 && chmod a+x /airgap_assets/k3s-riscv64


ARG TARGET_IMAGES="docker.io/carvicsforth/klipper-helm:v0.9.3-build20241008 docker.io/carvicsforth/metrics-server:v0.7.2 docker.io/coredns/coredns:1.11.3 docker.io/rancher/local-path-provisioner:v0.0.29 docker.io/rancher/mirrored-library-traefik:2.11.30 docker.io/riscv64/busybox:1.36.1"
ARG OUTPUT_TAR_ZST="/airgap_assets/k3s-airgap-images-riscv64.tar.zst"

RUN set -e; \
    # 1. 创建临时目录存储单镜像 docker-archive tar
    mkdir -p /tmp/single-images; \
    rm -rf /tmp/single-images/*; \
    \
    # 2. 循环拉取每个镜像，保存为单独的 docker-archive tar
    for img in $TARGET_IMAGES; do \
        img_filename=$(echo "$img" | sed 's/[\/:]/_/g').tar; \
        img_path="/tmp/single-images/$img_filename"; \
        echo "=== 拉取镜像：$img -> $img_path ==="; \
        # skopeo 拉取镜像并保存为 Docker 归档（支持私有仓库认证）
        # 注意：docker-archive 目标格式需要显式给出 reference，否则有些情况下归档不会按预期生成。
        skopeo copy --override-arch riscv64 --override-os linux $REGISTRY_CREDS docker://$img docker-archive:$img_path:$img; \
    done; \
    \
    # 3. 将多个单镜像 docker-archive tar 合成为“多镜像 docker save 兼容 tar”
    #    关键点：不能简单 tar-of-tars；需要合并 manifest.json / repositories 并保留层/配置文件。
    rm -rf /tmp/merged-docker-archive; \
    mkdir -p /tmp/merged-docker-archive; \
    # 用 jq 合并各单镜像 tar 的 manifest.json/repositories，避免使用 python。
    rm -rf /tmp/all-manifests /tmp/all-repositories; \
    mkdir -p /tmp/all-manifests /tmp/all-repositories; \
    i=0; \
    for p in /tmp/single-images/*.tar; do \
        [ -f "$p" ] || continue; \
        (tar -xOf "$p" manifest.json || tar -xOf "$p" ./manifest.json) > /tmp/all-manifests/$i.json; \
        (tar -xOf "$p" repositories || tar -xOf "$p" ./repositories) > /tmp/all-repositories/$i.json; \
        tar -xf "$p" -C /tmp/merged-docker-archive; \
        i=$((i+1)); \
    done; \
    if [ "$i" -eq 0 ]; then \
        echo "[ERROR] no single-image tar generated under /tmp/single-images" >&2; \
        exit 1; \
    fi; \
    # tar 解包出来的 manifest/repositories 有时会带只读权限；
    # 在覆盖前强制赋写权限并删除旧文件，避免 permission denied。
    chmod -R u+rwX /tmp/merged-docker-archive || true; \
    rm -f /tmp/merged-docker-archive/manifest.json /tmp/merged-docker-archive/repositories; \
    # manifest.json 通常是数组；把多个数组拼接起来即可。
    jq -s 'add' /tmp/all-manifests/*.json > /tmp/merged-docker-archive/manifest.json; \
    # repositories 是对象；按层级合并即可（tag 冲突取后者）。
    jq -s 'reduce .[] as $item ({}; . * $item)' /tmp/all-repositories/*.json > /tmp/merged-docker-archive/repositories

RUN set -e; \
    echo "=== 合并并压缩所有镜像到 $OUTPUT_TAR_ZST ==="; \
    tar -cf - -C /tmp/merged-docker-archive . | zstd --long=25 -19 -o $OUTPUT_TAR_ZST; \
    zstd --test $OUTPUT_TAR_ZST && echo "=== 打包成功！ ===";

ENV K3S_AIRGAP_DIR="/airgap_assets"
ENV PATH="$PATH:/ocboot"
WORKDIR /ocboot
