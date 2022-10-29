#!/usr/bin/env bash

offline_data_path=/opt/yunion/upgrade
export loaded_path=/opt/yunion/upgrade/images/loaded

load_and_mv(){
    local img=$1
    if [ ! -d $loaded_path ]; then
        mkdir -p $loaded_path
    fi
    docker load -i $img && mv $img $loaded_path
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

if [ -x /usr/bin/parallel ]; then
    parallel --will-cite load_and_mv ::: $offline_data_path/images/*.tar.xz
else
    for i in $offline_data_path/images/*.tar.xz
    do
        load_and_mv $i
    done
fi

rm -fv /tmp/load-images.sh
