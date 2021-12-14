#!/bin/bash

if [ $# -eq 0 ]; then
  echo "Error: no argument"
  exit 1
fi

if [ `grep -c ID=ubuntu /etc/os-release` -ne '0' ];then
  pkg_manager=apt-get
elif [ `grep -c 'ID="centos"' /etc/os-release` -ne '0' ];then
  pkg_manager=yum
else
  echo "Error: OS unsupported"
  exit 2
fi

if ! git version > /dev/null 2>&1; then
  echo "Git not installed, trying to install"
  sudo $pkg_manager -y install git
fi

if [ ! -d "./ocboot" ];then
  echo "Clone ocboot"
  git clone https://github.com/yunionio/ocboot.git > /dev/null 2>&1
fi

if ! docker ps > /dev/null 2>&1; then
  echo "Error: Docker unavailable, Please resolve the problem and try again"
  exit 3
fi
if [ $# -gt 1 ]; then
  docker run -v ~/.ssh/id_rsa:/root/.ssh/id_rsa -v `pwd`/ocboot:/opt/ocboot/ -t ocboot:v0.1 $@
else
  docker run -v ~/.ssh/id_rsa:/root/.ssh/id_rsa -v `pwd`/ocboot:/opt/ocboot/ --entrypoint /opt/ocboot/run.py -t ocboot:v0.1 $@
fi

echo "Script running complete"