FROM alpine:3.22.2

ENV TZ="UTC"
RUN sed -i 's!https://dl-cdn.alpinelinux.org/!https://mirrors.ustc.edu.cn/!g' /etc/apk/repositories && \
    apk --no-cache add \
        sudo \
        python3 \
        py3-pip \
        openssl \
        ca-certificates \
        sshpass \
        openssh-client \
        rsync \
        git \
        curl \
        mariadb-client \
        ansible \
        py3-mysqlclient && \
    rm -rf /var/cache/apk/* && \
    rm -rf /root/.cache/pip

RUN mkdir -p /airgap_assets

RUN	curl -L https://github.com/k3s-io/k3s/releases/download/v1.28.5%2Bk3s1/k3s -o /airgap_assets/k3s
RUN	curl -L https://github.com/k3s-io/k3s/releases/download/v1.28.5%2Bk3s1/k3s-arm64 -o /airgap_assets/k3s-arm64
RUN	curl -L https://github.com/yunionio/k3s/releases/download/v1.28.5%2Bk3s1/k3s-riscv64 -o /airgap_assets/k3s-riscv64
RUN	curl -L https://github.com/k3s-io/k3s/releases/download/v1.28.5%2Bk3s1/k3s-airgap-images-amd64.tar.zst -o /airgap_assets/k3s-airgap-images-amd64.tar.zst
RUN	curl -L https://github.com/k3s-io/k3s/releases/download/v1.28.5%2Bk3s1/k3s-airgap-images-arm64.tar.zst -o /airgap_assets/k3s-airgap-images-arm64.tar.zst
RUN	curl -L https://github.com/yunionio/k3s/releases/download/v1.28.5%2Bk3s1/k3s-airgap-images-riscv64.tar.zst -o /airgap_assets/k3s-airgap-images-riscv64.tar.zst

ENV K3S_AIRGAP_DIR="/airgap_assets"
ENV PATH="$PATH:/ocboot"
WORKDIR /ocboot
