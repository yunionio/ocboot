#!/usr/bin/env bash

offline_data_path=/opt/yunion/upgrade
export loaded_path=${offline_data_path}/images/loaded

enable_parallel=${enable_parallel:-false}

if k3s --version > /dev/null 2>&1; then
    enable_parallel=false
fi

load_and_mv(){
    local img=$1
    if [ ! -d $loaded_path ]; then
        mkdir -p $loaded_path
    fi
    MAX_RETRY=50
    RETRY=0
    while [ $RETRY -lt $MAX_RETRY ]; do
        if k3s --version > /dev/null 2>&1; then
            xzcat $img | k3s ctr images import -
        else
            docker load -i $img
        fi
        if [ $? -eq 0 ]; then
            break
        fi
        RETRY=$((RETRY+1))
        sleep $RETRY
    done
    if [ $RETRY -eq $MAX_RETRY ]; then
        echo "[ERROR] load image $img failed after $MAX_RETRY retries"
        exit 1
    fi
    mv $img $loaded_path
}

export -f load_and_mv

if [ ! -d $offline_data_path/images ]; then
    echo "no images path found under the offline data path. "
    exit 0
fi

count=$(find $offline_data_path/images -maxdepth 1 -type f -name '*tar.xz' |wc -l)
if [ "$count" -eq 0 ]; then
    echo "no images to load. "
    exit 0
fi

if [ -x /usr/bin/parallel ] && [ "$enable_parallel" -eq "true" ]; then
    parallel --will-cite load_and_mv ::: $offline_data_path/images/*.tar.xz
else
    for i in $offline_data_path/images/*.tar.xz
    do
        load_and_mv $i
    done
fi

version_file=${offline_data_path}/versions.json
if ! [ -f "$version_file" ]; then
    echo "[ERROR] version file $version_file is empty! "
    exit 1
fi

imgs=( $(cat $version_file |jq  '.dockers |to_entries[] |.key +":"+ .value' | xargs) )
echo imgs ${imgs[@]}

registry=$(cat $version_file | jq .registry |xargs)
if [ -z "$registry" ]; then
    echo "[ERROR] registry is empty!"
    exit 1
fi
echo registry $registry

tag_image(){
    local img_name_version=$1
    local insecure_registry="private-registry.onecloud:5000"
    MAX_RETRY=50
    RETRY=0
    while [ $RETRY -lt $MAX_RETRY ]; do
        if k3s --version > /dev/null 2>&1; then
            k3s ctr images ls | grep -w "$insecure_registry/$registry/$img_name_version"
            if [ $? -ne 0 ]; then
                k3s ctr images tag registry.cn-beijing.aliyuncs.com/$registry/$img_name_version \
                $insecure_registry/$registry/$img_name_version
            fi
        else
            docker tag registry.cn-beijing.aliyuncs.com/$registry/$img_name_version \
                $insecure_registry/$registry/$img_name_version
        fi
        if [ $? -eq 0 ]; then
            break
        fi
        RETRY=$((RETRY+1))
        sleep $RETRY
    done
    if [ $RETRY -eq $MAX_RETRY ]; then
        echo "[ERROR] tag image $img_name_version failed after $MAX_RETRY retries"
        exit 1
    fi
}
export -f tag_image

for img in "${imgs[@]}"
do
    registry=$registry tag_image $img
done

# rm -fv /tmp/load-images.sh
