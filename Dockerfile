FROM python:3.9-alpine3.13
ARG ANSIBLE_VERSION=2.9.25
ENV TZ UTC
RUN sed -i 's!https://dl-cdn.alpinelinux.org/!https://mirrors.ustc.edu.cn/!g' /etc/apk/repositories && apk update
RUN apk add --no-cache openssh openssl curl rsync
RUN apk add --no-cache --virtual .build-dependencies \
    libffi-dev openssl-dev python3-dev build-base py-setuptools rust cargo git && \
    pip install --no-cache-dir https://releases.ansible.com/ansible/ansible-${ANSIBLE_VERSION}.tar.gz && \
    pip install paramiko && \
    apk del --no-network .build-dependencies && \
    rm -rf /root/.cache /root/.cargo
RUN mkdir -p /opt/ocboot
ADD . /opt/ocboot
WORKDIR /opt/ocboot
ENTRYPOINT [ "/opt/ocboot/ocboot.py" ]
