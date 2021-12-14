FROM python:3.9-alpine3.13
ARG ANSIBLE_VERSION=2.9.25
# install tools
RUN apk add --no-cache openssh openssl
# install build_dependencies
RUN apk add --no-cache --virtual .build-dependencies \
    libffi-dev openssl-dev python3-dev build-base py-setuptools rust cargo && \
    pip install --no-cache-dir https://releases.ansible.com/ansible/ansible-${ANSIBLE_VERSION}.tar.gz && \
    pip install paramiko && \
    apk del --no-network .build-dependencies && \
    rm -rf /root/.cache /root/.cargo
WORKDIR /opt/ocboot
ENTRYPOINT [ "/opt/ocboot/ocboot.py" ]
