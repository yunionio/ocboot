FROM alpine:3.17

ENV TZ UTC
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
    pip3 install -U pip wheel && \
    pip3 install mysqlclient pywinrm 'ansible<=9.0.0' && \
    apk del build-dependencies && \
    rm -rf /var/cache/apk/* && \
    rm -rf /root/.cache/pip && \
    rm -rf /root/.cargo

ENV PATH $PATH:/ocboot
