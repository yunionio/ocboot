#!/bin/bash

set -e

REGISTRY=${REGISTRY:-registry.cn-beijing.aliyuncs.com/yunionio}
VERSION=${VERSION:-v4-k3s.4}
OCBOOT_IMAGE="$REGISTRY/ocboot:$VERSION"

CUR_DIR="$(pwd)"
CONTAINER_NAME="buildah-ocboot"

buildah_from_image() {
    if buildah ps | grep $CONTAINER_NAME; then
        buildah rm $CONTAINER_NAME
    fi
    local img="$1"
    echo "Using buildah pull $img"
    buildah from --name $CONTAINER_NAME "$img"
}

buildah_from_image "$OCBOOT_IMAGE"

mkdir -p "$HOME/.ssh"

CMD=""

is_ocboot_subcmd() {
    local subcmds="install upgrade add-node add-lbagent backup restore"
    for subcmd in $subcmds; do
        if [[ "$1" == "$subcmd" ]]; then
            return 0
        fi
    done
    return 1
}

if is_ocboot_subcmd $1; then
    CMD="ocboot.py"
fi

buildah run -t \
    --net=host \
    -v "$HOME/.ssh:/root/.ssh" \
    -v "$(pwd):/ocboot" \
    -v "$(pwd)/airgap_assets/k3s-install.sh:/airgap_assets/k3s-install.sh:ro" \
    "$CONTAINER_NAME" $CMD $@
