#!/usr/bin/env bash
set -ex
export PS4='+(${BASH_SOURCE}:${LINENO}): ${FUNCNAME[0]:+${FUNCNAME[0]}(): }'

[[ -n "${ITEM_KEY}" ]] && [[ -n "${ITEM_VALUE}" ]] && [[ -n "$SECOND_IMAGE_PATH" ]]
[[ -d "$OFFLINE_DATA_PATH" ]]
versions_registry="${VERSIONS_REGISTRY:-}"
[[ -n "$versions_registry" ]]
insecure_registry="${INSECURE_REGISTRY:-}"
[[ -n "$insecure_registry" ]]

img="${ITEM_KEY}:${ITEM_VALUE}"
img_base="$ITEM_KEY-$ITEM_VALUE.tar.xz"
img_fn="$OFFLINE_DATA_PATH/images/$img_base"
img_other_arch_fn=$SECOND_IMAGE_PATH/$img_base

img_registry="registry.cn-beijing.aliyuncs.com/$versions_registry"
img_url=$img_registry/$img

bi_failed_counter=0

img_name=$insecure_registry/$versions_registry/$img
docker manifest inspect "${img_name}" | grep -wq amd64 &&
    docker manifest inspect "${img_name}" | grep -wq arm64 || bi_failed_counter=$((bi_failed_counter + 1))

[[ "$bi_failed_counter" -eq 0 ]] && exit 0

[ -f "$img_fn" ] && [ -f "$img_other_arch_fn" ] && ls -lah "$img_fn" "$img_other_arch_fn"
docker load -i "$img_fn"
arch=$(docker inspect "$img_url" | grep -w Architecture | awk '{print $2}' | sed -e 's#[",]##g')
[[ "$arch" == "amd64" ]] || [[ "$arch" == "arm64" ]] || exit 1

docker tag "$img_url" "$insecure_registry/$versions_registry/$img-$arch"
docker push "$insecure_registry/$versions_registry/$img-$arch"
old_arch="$arch"
docker load -i "$img_other_arch_fn"
arch=$(docker inspect "$img_url" | grep -w Architecture | awk '{print $2}' | sed -e 's#[",]##g')
[[ "$arch" == "amd64" ]] || [[ "$arch" == "arm64" ]] || exit 1
[[ "$arch" != "$old_arch" ]] || exit 1

docker tag "$img_url" "$insecure_registry/$versions_registry/$img-$arch"
docker push "$insecure_registry/$versions_registry/$img-$arch"
img_name="$insecure_registry/$versions_registry/$img"
docker manifest create --amend --insecure "$img_name" \
    "$img_name-amd64" \
    "$img_name-arm64"
docker manifest annotate "$img_name" --arch amd64 --os linux "$img_name-amd64"
docker manifest annotate "$img_name" --arch arm64 --os linux "$img_name-arm64"

docker manifest inspect "${img_name}" | grep -wq amd64
docker manifest inspect "${img_name}" | grep -wq arm64
docker manifest push --insecure "$img_name"
