#!/usr/bin/env bash

set -ex
export PS4='+(${BASH_SOURCE}:${LINENO}): ${FUNCNAME[0]:+${FUNCNAME[0]}(): }'

offline_data_path=${OFFLINE_DATA_PATH:-}
insecure_registry=${INSECURE_REGISTRY:-}

if [[ -z "$offline_data_path" ]]; then
    echo "offline_data_path empty ! "
    exit 1
fi
if [ -z "$insecure_registry" ]; then
    echo "empty insecure_registry ! "
    exit 1
fi

export version_file="$offline_data_path/versions.json"

if ! [ -s "$version_file" ]; then
    echo "[ERROR] version file $version_file is empty! "
    exit 1
fi

imgs=($(cat "$version_file" | jq '.dockers |to_entries[] |.key +":"+ .value' | tr -d '"'))
echo imgs "${imgs[@]}"

export registry
registry="$(cat $version_file | jq .registry | xargs)"

if [ -z "$registry" ]; then
    echo "[ERROR] registry is empty!"
    exit 1
fi

push_and_tag() {
    local img_name_version=$1
    docker tag "registry.cn-beijing.aliyuncs.com/$registry/$img_name_version" \
        "$insecure_registry/$registry/$img_name_version" &&
        docker push "$insecure_registry/$registry/$img_name_version"
}
export -f push_and_tag
insecure_registry=$insecure_registry parallel --retries 3 --jobs 4 --halt-on-error 2 --will-cite --verbose --bar push_and_tag ::: "${imgs[@]}"
