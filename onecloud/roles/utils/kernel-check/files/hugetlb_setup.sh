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

function info_exit() {
    info "$@"
    exit 0
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

OLD_KERNEL_PARAMS_FILE="/tmp/ocboot_hugetbl_old_kernel_params_file.txt"

_fill_old_kernel_params() {
    rm -rf $OLD_KERNEL_PARAMS_FILE && touch $OLD_KERNEL_PARAMS_FILE
    local cmdline_param=$*
    for param in $cmdline_param; do
        local key
        local val
        key=${param%=*}
        val=${param#*=}
        if [[ "$key" == "$val" ]]; then
            echo "$key" >> $OLD_KERNEL_PARAMS_FILE
        else
            echo "$key=$val" >> $OLD_KERNEL_PARAMS_FILE
        fi
    done
}

_merge_new_kernel_params() {
    local new_tmp_val
    for key in "${!NEW_KERNEL_PARAMS[@]}"; do
        new_tmp_val="${NEW_KERNEL_PARAMS[$key]}"
        if grep -q "^$key=" $OLD_KERNEL_PARAMS_FILE; then
            sed -i "s|^$key=.*|$key=$new_tmp_val|g" $OLD_KERNEL_PARAMS_FILE
        else
            echo "$key=$new_tmp_val" >> $OLD_KERNEL_PARAMS_FILE
        fi
    done
}

_generate_kernel_cmdline() {
    cat $OLD_KERNEL_PARAMS_FILE | tr '\n' ' '
}


get_distro() {
    distro=($(awk '/^ID=/' /etc/*-release | awk -F'=' '{ print tolower($2) }' | tr -d \"))
    echo "${distro[@]}"
}

function findStringInArray() {
    local search="$1"
    shift

    for element in "$@"; do
        if [[ "$element" == "$search" ]]; then
            return 0
        fi
    done
    return 1
}

env_check() {
    if [[ "$(uname -m)" != "x86_64" ]]; then
        info_exit "is not x86 machine"
    fi

    if [[ $EUID -ne 0 ]]; then
        error_exit "You need sudo or root to run this script."
    fi

    local supported_distros=("centos" "debian" "openeuler" "ubuntu")
    local distros=($(get_distro))

    local found_supported_distro=false
    local unsupported_distros=()

    for distro in "${distros[@]}"; do
        if findStringInArray "${distro}" "${supported_distros[@]}"; then
            found_supported_distro=true
            echo "${distro}"
            break
        else
            unsupported_distros+=("${distro}")
        fi
    done

    if [[ $found_supported_distro == false ]]; then
        error_exit "The following Linux distributions are not supported: ${unsupported_distros[*]}, only support ${supported_distros[*]}"
    fi
}

mk_grub2(){
    if [ -d /sys/firmware/efi ]; then
        mkdir -p /boot/efi/EFI/centos
        grub2-mkconfig -o /boot/efi/EFI/centos/grub.cfg
    else
        grub2-mkconfig -o /boot/grub2/grub.cfg
    fi
}


mk_grub2_openeuler(){
    if [ -d /sys/firmware/efi ]; then
        mkdir -p /boot/efi/EFI/openEuler
        grub2-mkconfig -o /boot/efi/EFI/openEuler/grub.cfg
    else
        grub2-mkconfig -o /boot/grub2/grub.cfg
    fi
}


mk_grub_legacy(){
    update-grub
}

mk_grub(){
    local distro=${1}
    if [[ "${distro}" == "centos" ]]; then
        mk_grub2
    elif [[ "${distro}" == "debian" ]] || [[ "${distro}" == "ubuntu" ]]; then
        mk_grub_legacy
    elif [[ "${distro}" == "openeuler" ]]; then
        mk_grub2_openeuler
    else
        error_exit "unsupport distro ${distro}!"
    fi
}

grub_setup() {
    info "Configure grub option..."
    local grub_cfg="/etc/default/grub"
    local cmdline_param
    local idx
    local distro=${1}

    ensure_file_writable "$grub_cfg"

    cmdline_param=$(grep GRUB_CMDLINE_LINUX $grub_cfg | cut -d'"' -f2)
    _fill_old_kernel_params $cmdline_param
    _merge_new_kernel_params
    cmdline_param=$(_generate_kernel_cmdline)
    sed -i "s|GRUB_CMDLINE_LINUX=.*|GRUB_CMDLINE_LINUX=\"$cmdline_param\"|g" $grub_cfg
    mk_grub ${distro}
}

main() {
    distro=$(env_check)
    grub_setup ${distro}
    systemctl enable oc-hugetlb-gigantic-pages
    info "All done, ${UCYAN}REBOOT to make it work"
}

main

