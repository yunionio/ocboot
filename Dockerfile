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

RUN mkdir -p /airgap_assets && \
	curl -L https://github.com/k3s-io/k3s/releases/download/v1.28.5%2Bk3s1/k3s -o /airgap_assets/k3s && \
	curl -L https://github.com/k3s-io/k3s/releases/download/v1.28.5%2Bk3s1/k3s-arm64 -o /airgap_assets/k3s-arm64 && \
	curl -L https://github.com/k3s-io/k3s/releases/download/v1.28.5%2Bk3s1/k3s-airgap-images-amd64.tar.zst -o /airgap_assets/k3s-airgap-images-amd64.tar.zst && \
	curl -L https://github.com/k3s-io/k3s/releases/download/v1.28.5%2Bk3s1/k3s-airgap-images-arm64.tar.zst -o /airgap_assets/k3s-airgap-images-arm64.tar.zst && \
    curl -L https://github.com/CARV-ICS-FORTH/k3s/releases/download/20241024/k3s-riscv64.gz.aa -o /tmp/k3s-riscv64.gz.aa && \
    curl -L https://github.com/CARV-ICS-FORTH/k3s/releases/download/20241024/k3s-riscv64.gz.ab -o /tmp/k3s-riscv64.gz.ab && \
    curl -L https://github.com/CARV-ICS-FORTH/k3s/releases/download/20241024/k3s-riscv64.gz.ac -o /tmp/k3s-riscv64.gz.ac && \
    cat /tmp/k3s-riscv64.gz.* | gunzip > /airgap_assets/k3s-riscv64 && chmod a+x /airgap_assets/k3s-riscv64


ARG TARGET_IMAGES="docker.io/carvicsforth/klipper-helm:v0.9.3-build20241008 docker.io/carvicsforth/metrics-server:v0.7.2 docker.io/carvicsforth/pause:v3.10-v1.31.1 docker.io/coredns/coredns:1.11.3 docker.io/rancher/local-path-provisioner:v0.0.29 docker.io/rancher/mirrored-library-traefik:2.11.30 ghcr.io/flannel-io/flannel-cni-plugin:v1.8.0-flannel1 ghcr.io/flannel-io/flannel:v0.27.4"
ARG OUTPUT_TAR_ZST="/airgap_assets/k3s-airgap-images-riscv64.tar.zst"

RUN set -e; \
    # 1. 创建临时目录存储单个镜像归档
    mkdir -p /tmp/single-images; \
    # 2. 循环拉取每个镜像，保存为单独的 tar 归档
    for img in $TARGET_IMAGES; do \
        # 提取镜像名+标签作为文件名（替换特殊字符为下划线）
        img_filename=$(echo "$img" | sed 's/[\/:]/_/g').tar; \
        img_path="/tmp/single-images/$img_filename"; \
        echo "=== 拉取镜像：$img -> $img_path ==="; \
        # skopeo 拉取镜像并保存为 Docker 归档（支持私有仓库认证）
        skopeo copy --override-arch riscv64 $REGISTRY_CREDS docker://$img docker-archive:$img_path; \
    done; \
    # 3. 合并所有单个镜像归档为一个 tar，再用 zstd 压缩（高压缩比）
    echo "=== 合并并压缩所有镜像到 $OUTPUT_TAR_ZST ==="; \
    tar -cf - -C /tmp/single-images . | zstd -z -19 -o $OUTPUT_TAR_ZST; \
    # 4. 验证压缩包（可选，确保文件有效）
    zstd --test $OUTPUT_TAR_ZST && echo "=== 打包成功！ ===";

ENV K3S_AIRGAP_DIR="/airgap_assets"
ENV PATH="$PATH:/ocboot"
WORKDIR /ocboot
