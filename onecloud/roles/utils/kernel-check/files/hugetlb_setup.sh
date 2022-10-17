#!/bin/bash

set -o errexit

pushd $(dirname $(readlink -f "$BASH_SOURCE")) > /dev/null
CUR_DIR=$(pwd)
ROOT_DIR=$(cd .. && pwd)
popd > /dev/null

export LC_CTYPE="en_US.UTF-8"
################################################

ensure_file_exist() {
    local file="$1"

    if [ ! -e "$file" ]; then
        error_exit "$file not exists"
    fi
}

ensure_file_writable() {
    local file="$1"

    ensure_file_exist "$file"

    if [ ! -w "$file" ]; then
        error_exit "$file not writable"
    fi
}

ensure_file_readable() {
    local file="$1"

    ensure_file_exist "$file"

    if [ ! -r "$file" ]; then
        error_exit "$file not readable"
    fi
}

GREEN="\033[1;32m"
RED="\033[1;31m"
YELLOW="\033[1;33m"
UCYAN="\033[4;36m"
NOCOLOR="\033[0m"
REVERSECOLOR="\e[7m"

function error_exit() {
    error "$@"
    exit 1
}

function info() {
    echo
    echo -e "${GREEN}$@${NOCOLOR}"
    echo
}

function warn() {
    echo
    echo -e "${YELLOW}$@${NOCOLOR}"
    echo
}

function error() {
    echo
    echo -e "${RED}$@${NOCOLOR}"
    echo
}

declare -A NEW_KERNEL_PARAMS=(
    [default_hugepagesz]=1G
    [hugepagesz]=1G
)

declare -A OLD_KERNEL_PARAMS

_fill_old_kernel_params() {
    local cmdline_param=$*
    for param in $cmdline_param; do
        local key
        local val
        key=${param%=*}
        val=${param#*=}
        if [[ "$key" == "$val" ]]; then
            OLD_KERNEL_PARAMS["$key"]=''
        else
            OLD_KERNEL_PARAMS["$key"]="$val"
        fi
    done
}

_merge_new_kernel_params() {
    local new_tmp_val
    local old_tmp_val
    for key in "${!NEW_KERNEL_PARAMS[@]}"; do
        new_tmp_val="${NEW_KERNEL_PARAMS[$key]}"
        old_tmp_val="${OLD_KERNEL_PARAMS[$key]}"
        if [ "$new_tmp_val" != "$old_tmp_val" ]; then
            OLD_KERNEL_PARAMS[$key]="$new_tmp_val"
        fi
    done
}

_generate_kernel_cmdline() {
    local cmdline=""
    local val=""
    for key in "${!OLD_KERNEL_PARAMS[@]}"; do
        val="${OLD_KERNEL_PARAMS[$key]}"
        if [ -z "$val" ]; then
            cmdline="$cmdline $key"
        else
            cmdline="$cmdline $key=$val"
        fi
    done
    echo "$cmdline" | cut -c2-
}

mk_grub() {
    if [ -d /sys/firmware/efi ]; then
        mkdir -p /boot/efi/EFI/centos
        grub2-mkconfig -o /boot/efi/EFI/centos/grub.cfg
    else
        grub2-mkconfig -o /boot/grub2/grub.cfg
    fi
}

grub_setup() {
    info "Configure grub option..."
    local grub_cfg="/etc/default/grub"
    local cmdline_param
    local idx

    ensure_file_writable "$grub_cfg"

    cmdline_param=$(grep GRUB_CMDLINE_LINUX $grub_cfg | cut -d'"' -f2)
    _fill_old_kernel_params $cmdline_param
    _merge_new_kernel_params
    cmdline_param=$(_generate_kernel_cmdline)
    sed -i "s|GRUB_CMDLINE_LINUX=.*|GRUB_CMDLINE_LINUX=\"$cmdline_param\"|g" $grub_cfg
    mk_grub
}

if [ "$(uname -m)" != "x86_64" ]; then
    echo "is not x86 machine"
    exit 0
fi

grub_setup
systemctl enable oc-hugetlb-gigantic-pages




