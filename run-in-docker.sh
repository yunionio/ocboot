#!/bin/bash

REGISTRY=${REGISTRY:-registry.cn-beijing.aliyuncs.com/yunionio}
VERSION=${VERSION:-latest}
OCBOOT_IMAGE="$REGISTRY/ocboot:$VERSION"

if ! docker ps > /dev/null 2>&1; then
    echo "Error: Docker unavailable, Please resolve the problem and try again"
    exit 3
fi

run_cmd="docker run --rm -t --network host -v $HOME/.ssh/id_rsa:/root/.ssh/id_rsa"

if [ $# -ge 2 ]; then
    echo 'copy config file to "ocboot" directory'
    for i in $@ ; do
        if [ -f $i ]; then
            CONF=$i
        fi
    done
    $run_cmd -v `pwd`/$CONF:/opt/ocboot/$CONF $OCBOOT_IMAGE $@
elif [ $# -eq 1 ]; then
    config_dir="$(pwd)/_config"
    mkdir "$config_dir"
    $run_cmd -v "$config_dir":/opt/ocboot/_config \
        --env OCBOOT_CONFIG_DIR=/opt/ocboot/_config \
        --entrypoint /opt/ocboot/run.py $OCBOOT_IMAGE $@
else
    $run_cmd -v `pwd`/$CONF:/opt/ocboot/$CONF $OCBOOT_IMAGE -h
    exit 1
fi
