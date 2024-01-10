#!/bin/bash

TARGET_REGISTRY=registry.cn-beijing.aliyuncs.com/yunion

# skopeo login --username $USERNAME $TARGET_REGISTRY

SKOPEO_COPY_CMD='skopeo copy --override-os linux --multi-arch all'

# calico
$SKOPEO_COPY_CMD docker://docker.io/calico/cni:v3.27.0 docker://$TARGET_REGISTRY/calico-cni:v3.27.0
$SKOPEO_COPY_CMD docker://docker.io/calico/node:v3.27.0 docker://$TARGET_REGISTRY/calico-node:v3.27.0
$SKOPEO_COPY_CMD docker://docker.io/calico/kube-controllers:v3.27.0 docker://$TARGET_REGISTRY/calico-kube-controllers:v3.27.0

### k3s ###
$SKOPEO_COPY_CMD docker://docker.io/rancher/mirrored-library-traefik:2.10.5 docker://$TARGET_REGISTRY/traefik:2.10.5
$SKOPEO_COPY_CMD docker://docker.io/rancher/mirrored-coredns-coredns:1.10.1 docker://$TARGET_REGISTRY/coredns:1.10.1
