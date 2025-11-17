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

    

ENV K3S_AIRGAP_DIR /airgap_assets
ENV PATH $PATH:/ocboot
WORKDIR /ocboot
