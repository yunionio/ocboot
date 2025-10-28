#!/bin/bash

# Version configuration (can be overridden by environment variables)
TARGET_REGISTRY=${TARGET_REGISTRY:-"registry.cn-beijing.aliyuncs.com/yunion"}
CALICO_VERSION=${CALICO_VERSION:-"v3.27.5"}

# skopeo login --username $USERNAME $TARGET_REGISTRY

SKOPEO_COPY_CMD='skopeo copy --override-os linux --multi-arch all'

# Function: Copy image from source to target registry
copy_image() {
    local source_image=$1
    local target_name=$2
    local target_image="${TARGET_REGISTRY}/${target_name}"
    
    echo "Copying ${source_image} to ${target_image}..."
    $SKOPEO_COPY_CMD docker://${source_image} docker://${target_image}
}

# Function: Add calico images to the copy list
add_calico_images() {
    local version=$1
    IMAGES["calico-cni:${version}"]="docker.io/calico/cni:${version}"
    IMAGES["calico-node:${version}"]="docker.io/calico/node:${version}"
    IMAGES["calico-kube-controllers:${version}"]="docker.io/calico/kube-controllers:${version}"
}

# Define images to be copied
declare -A IMAGES=()

# Add calico images
add_calico_images "${CALICO_VERSION}"

# Add other images
IMAGES["traefik:2.10.5"]="docker.io/rancher/mirrored-library-traefik:2.10.5"
IMAGES["coredns:1.10.1"]="docker.io/rancher/mirrored-coredns-coredns:1.10.1"

# Copy all images
for target_name in "${!IMAGES[@]}"; do
    copy_image "${IMAGES[$target_name]}" "${target_name}"
done
