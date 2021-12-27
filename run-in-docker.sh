#!/bin/bash

: ${OCBOOT_IMAGE="registry.cn-beijing.aliyuncs.com/yunionio/ocboot:latest"}

if ! docker ps > /dev/null 2>&1; then
  echo "Error: Docker unavailable, Please resolve the problem and try again"
  exit 3
fi

if [ $# -ge 2 ]; then
  echo 'copy config file to "ocboot" directory'
  for i in $@ ; do
    if [ -f $i ]; then
      CONF=$i
    fi
  done
  docker run -t --network host -v ~/.ssh/id_rsa:/root/.ssh/id_rsa -v `pwd`/$CONF:/opt/ocboot/$CONF $OCBOOT_IMAGE $@
elif [ $# -eq 1 ]; then
  docker run -t --network host -v ~/.ssh/id_rsa:/root/.ssh/id_rsa --entrypoint /opt/ocboot/run.py $OCBOOT_IMAGE $@
else
  echo "Error: no argument"
  exit 1
fi

if [ $? -eq 0 ];then
  echo "Script running complete"
else
  echo "Script running failure!!!"
fi
