FROM registry.cn-beijing.aliyuncs.com/yunionio/ansibleserver-base:v1.1.2
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN mkdir -p /opt/ocboot
ADD . /opt/ocboot
WORKDIR /opt/ocboot
ENTRYPOINT [ "/opt/ocboot/ocboot.py" ]
