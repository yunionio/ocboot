FROM registry.cn-beijing.aliyuncs.com/yunionio/ansibleserver-base:v1.1.1
RUN apk add --no-cache openssh openssl curl rsync pv mariadb-client
RUN apk add --no-cache --virtual .build-dependencies \
    libffi-dev openssl-dev python3-dev build-base py-setuptools rust cargo mariadb-dev && \
    pip3 install paramiko mysqlclient && \
    apk del --no-network .build-dependencies && \
    rm -rf /root/.cache /root/.cargo
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN mkdir -p /opt/ocboot
ADD . /opt/ocboot
WORKDIR /opt/ocboot
ENTRYPOINT [ "/opt/ocboot/ocboot.py" ]
