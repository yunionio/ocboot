FROM python:3.9-alpine3.13
ARG ANSIBLE_VERSION=2.9.25
RUN apk add --no-cache openssh openssl curl rsync
RUN apk add --no-cache --virtual .build-dependencies \
    libffi-dev openssl-dev python3-dev build-base py-setuptools rust cargo git && \
    pip install --no-cache-dir https://releases.ansible.com/ansible/ansible-${ANSIBLE_VERSION}.tar.gz && \
    pip install paramiko && \
    git clone https://github.com/yunionio/ocboot.git /opt/ocboot && \
    apk del --no-network .build-dependencies && \
    rm -rf /root/.cache /root/.cargo
WORKDIR /opt/ocboot
ENTRYPOINT [ "/opt/ocboot/ocboot.py" ]
