#!/bin/bash

shopt -s expand_aliases

set -e

DEFAULT_REPO=registry.cn-beijing.aliyuncs.com/yunionio
IMAGE_REPOSITORY=${IMAGE_REPOSITORY:-$DEFAULT_REPO}
VERSION=${VERSION:-v4-k3s.6}
OCBOOT_IMAGE="$IMAGE_REPOSITORY/ocboot:$VERSION"

CUR_DIR="$(pwd)"
CONTAINER_NAME="buildah-ocboot"

alias buildah="sudo buildah"

ensure_buildah() {
    if ! [ -x "$(command -v buildah)" ]; then
        echo "Installing buildah ..."
        ./scripts/install-buildah.sh
    fi
}

buildah_from_image() {
    if buildah ps | grep $CONTAINER_NAME; then
        buildah rm $CONTAINER_NAME
    fi
    local img="$1"
    echo "Using buildah pull $img"
    buildah pull --policy missing "$img"
    buildah from --pull=false --name $CONTAINER_NAME "$img"
}

ensure_buildah

buildah_from_image "$OCBOOT_IMAGE"

mkdir -p "$HOME/.ssh"

ROOT_DIR='/ocboot'

CMD=""

is_ocboot_subcmd() {
    local subcmds="install upgrade add-node add-lbagent backup restore setup-container-env switch-edition clickhouse setup-ai-env start stop set-calico-version fabric-setup"
    for subcmd in $subcmds; do
        if [[ "$1" == "$subcmd" ]]; then
            return 0
        fi
    done
    return 1
}

if is_ocboot_subcmd "$1"; then
    CMD="$ROOT_DIR/ocboot.py"
fi

buildah_version=$(buildah --version | awk '{print $3}')
buildah_version_major=$(echo "$buildah_version" | awk -F. '{print $1}')
buildah_version_minor=$(echo "$buildah_version" | awk -F. '{print $2}')

buildah_extra_args=()

# buildah accepts --env since 1.23
echo "buildah version: $buildah_version"
# Pass ANSIBLE_VERBOSITY with env(1) so it reaches ansible on every buildah version.
ansible_verbosity="${ANSIBLE_VERBOSITY:-0}"
echo "ansible verbosity: $ansible_verbosity"
if [[ $buildah_version_major -eq 1 ]] && [[ "$buildah_version_minor" -gt 23 ]]; then
    buildah_extra_args+=(-e HOME="$HOME")
fi

cmd_extra_args=""
origin_args=()

normalize_installer_path() {
    local path="$1"
    if [[ "$path" == /* ]]; then
        if [[ "$path" == "$(pwd)"/* ]] || [[ "$path" == "$(pwd)" ]]; then
            if [[ "$path" == "$(pwd)" ]]; then
                echo "$ROOT_DIR"
            else
                echo "$ROOT_DIR/${path#$(pwd)/}"
            fi
        else
            echo "$path"
        fi
    else
        path="${path#./}"
        echo "$ROOT_DIR/$path"
    fi
}

prev_arg=""
for arg in "$@"; do
    case "$prev_arg" in
        --nvidia-driver-installer-path|--cuda-installer-path|--riscv64-config)
            origin_args+=("$(normalize_installer_path "$arg")")
            ;;
        *)
            origin_args+=("$arg")
            ;;
    esac
    prev_arg="$arg"
done

if [[ "${origin_args[0]:-}" == "run.py" ]]; then
    if [[ "$IMAGE_REPOSITORY" != "$DEFAULT_REPO" ]]; then
        cmd_extra_args="$cmd_extra_args -i $IMAGE_REPOSITORY"
    fi
    origin_args[0]="$ROOT_DIR/run.py"
fi

mkdir -p "$HOME/.kube"

# Bind input files outside $(pwd) so they remain accessible in the container.
extra_installer_volumes=()
prev_arg=""
declare -A mounted_installer_dirs
for arg in "$@"; do
    case "$prev_arg" in
        --nvidia-driver-installer-path|--cuda-installer-path|--riscv64-config)
            # Only handle absolute paths that are not already under $(pwd)
            if [[ "$arg" == /* ]] && [[ "${arg#$(pwd)/}" == "$arg" ]] && [[ "$arg" != "$(pwd)" ]]; then
                _dir="$(dirname "$arg")"
                if [[ -z "${mounted_installer_dirs[$_dir]+x}" ]]; then
                    extra_installer_volumes+=(-v "$_dir:$_dir:ro")
                    mounted_installer_dirs[$_dir]=1
                fi
            fi
            ;;
    esac
    prev_arg="$arg"
done

# Bind the config file after extra_installer_volumes is initialized.
if [[ "${origin_args[0]:-}" == "$ROOT_DIR/run.py" ]]; then
    if [ -n "${origin_args[2]}" ] && [ -f "${origin_args[2]}" ]; then
        config_file_fullpath=$(readlink -f "${origin_args[2]}")
        config_file_name=$(basename "$config_file_fullpath")
        echo "Using config file: $config_file_fullpath -> /$config_file_name"
        extra_installer_volumes+=(-v "$config_file_fullpath:/$config_file_name:ro")
        origin_args[2]="/$config_file_name"
        echo "extra_installer_volumes: ${extra_installer_volumes[@]}"
    fi
fi

buildah run --isolation chroot --user $(id -u):$(id -g) \
    -t "${buildah_extra_args[@]}" \
    --net=host \
    -v "$(mktemp -d):$HOME/.ansible" \
    -v "$HOME/.ssh:$HOME/.ssh" \
    -v "$HOME/.kube:$HOME/.kube" \
    -v "/etc/passwd:/etc/passwd:ro" \
    -v "/etc/group:/etc/group:ro" \
    -v "$(pwd):$ROOT_DIR" \
    -v "$(pwd)/airgap_assets/k3s-install.sh:/airgap_assets/k3s-install.sh:ro" \
    "${extra_installer_volumes[@]}" \
    "$CONTAINER_NAME" env "ANSIBLE_VERBOSITY=${ansible_verbosity}" $CMD "${origin_args[@]}" $cmd_extra_args
