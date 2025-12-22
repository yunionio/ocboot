#!/bin/bash

export os_string=

get_name_version() {
    local fn=/etc/os-release
    local arch
    arch="$(uname -m)"
    if ! [ -f "$fn" ]; then
        return
    fi
    local name=$(cat $fn | grep '^NAME=.*' | awk -F= '{print $2}' | xargs)
    local version="$(cat $fn | grep '^VERSION=.*' | awk -F= '{print $2}' | xargs)"
    echo "$name $version $arch" | sed -e 's#(.*)##' -e 's#  # #g'
}

supported_os=(
    "AlmaLinux 8.* x86_64"
    "AlmaLinux 8.* aarch64"
    "AlmaLinux 9.* x86_64"
    "AlmaLinux 9.* aarch64"
    "AlmaLinux 10.* x86_64"
    "AlmaLinux 10.* aarch64"
    "Anolis OS 8.* x86_64"
    "Anolis OS 8.* aarch64"
    "CentOS Linux 7 x86_64"
    "CentOS Linux 7 aarch64"
    "CentOS Stream 8 x86_64"
    "CentOS Stream 8 aarch64"
    "CentOS Stream 9 x86_64"
    "CentOS Stream 9 aarch64"
    "CentOS Stream 9 x86_64"
    "CentOS Stream 10 aarch64"
    "CentOS Stream 10 x86_64"
    "Debian GNU/Linux 11 x86_64"
    "Debian GNU/Linux 11 aarch64"
    "Debian GNU/Linux 12 x86_64"
    "Debian GNU/Linux 12 aarch64"
    "Debian GNU/Linux 13 x86_64"
    "Debian GNU/Linux 13 aarch64"
    "openEuler 22.03 x86_64"
    "openEuler 22.03 aarch64"
    "openEuler 24.03 x86_64"
    "openEuler 24.03 aarch64"
    "OpenCloudOS 8.* x86_64"
    "OpenCloudOS 8.* aarch64"
    "OpenCloudOS 9.* x86_64"
    "OpenCloudOS 9.* aarch64"
    "Rocky Linux 8.* x86_64"
    "Rocky Linux 8.* aarch64"
    "Rocky Linux 9.* x86_64"
    "Rocky Linux 9.* aarch64"
    "Rocky Linux 10.* x86_64"
    "Rocky Linux 10.* aarch64"
    "Ubuntu 20.04.* LTS x86_64"
    "Ubuntu 20.04.* LTS aarch64"
    "Ubuntu 22.04.* LTS x86_64"
    "Ubuntu 22.04.* LTS aarch64"
    "Ubuntu 22.04 LTS x86_64"
    "Ubuntu 22.04 LTS aarch64"
    "Ubuntu 24.04.* LTS x86_64"
    "Ubuntu 24.04.* LTS aarch64"
    "Ubuntu 25.04 x86_64"
    "Ubuntu 25.04 aarch64"
    "Ubuntu 25.04.* x86_64"
    "Ubuntu 25.04.* aarch64"
    "Ubuntu 24.04.* riscv64"
    "ctyunos 2.*.* x86_64"
    "Arch Linux x86_64"
    "Arch Linux aarch64"
)

ubuntu_20_os=(
    "Ubuntu 20.04.* LTS x86_64"
    "Ubuntu 20.04.* LTS aarch64"
)

centos_obsolete_os=(
    "CentOS Linux 7 x86_64"
    "CentOS Linux 7 aarch64"
    "CentOS Stream 8 x86_64"
    "CentOS Stream 8 aarch64"
)

is_supported() {
    local s
    s="$(get_name_version)"
    for i in "${supported_os[@]}"; do
        if echo "$s" | grep "$i"; then
            return 0
        fi
    done
    return 1
}

is_openeuler() {
    grep -qw 'openEuler' /etc/os-release
}

is_ubuntu_20() {
    local s
    s="$(get_name_version)"
    for i in "${ubuntu_20_os[@]}"; do
        if echo "$s" | grep "$i"; then
            return 0
        fi
    done
    return 1
}

is_centos_obsolete() {
    local s
    s="$(get_name_version)"
    for i in "${centos_obsolete_os[@]}"; do
        if echo "$s" | grep "$i"; then
            return 0
        fi
    done
    return 1
}

ensure_buildah_on_openeuler() {
    local arch
    local url
    arch="$(uname -m)"
    case $arch in
    x86_64)
        url=https://iso.yunion.cn/openeuler/22.03/base/x86_64/Packages/buildah-1.34.1-4.x86_64.rpm
        ;;
    aarch64)
        url=https://iso.yunion.cn/openeuler/22.03/base/aarch64/Packages/buildah-1.34.1-4.aarch64.rpm
        ;;
    *)
        exit 1
        ;;
    esac
    if hash buildah &>/dev/null; then
        return
    fi
    dnf localinstall -y "$url"
}

ensure_buildah() {
    local installer
    hash yum &>/dev/null && installer=yum
    hash dnf &>/dev/null && installer=dnf
    hash apt &>/dev/null && installer=apt
    hash pacman &>/dev/null && installer=pacman
    #hash git &>/dev/null || $installer install -y git

	if is_ubuntu_20; then
		./scripts/install-buildah-ubuntu20.sh
		return
	fi

    if is_openeuler; then
        ensure_buildah_on_openeuler
        return
    fi

	if is_centos_obsolete; then
        sed -i 's/^mirrorlist/#mirrorlist/g' /etc/yum.repos.d/CentOS-*
        sed -i 's/^#baseurl/baseurl/g' /etc/yum.repos.d/CentOS-*
        sed -i 's/mirror.centos.org/vault.centos.org/g' /etc/yum.repos.d/CentOS-*
	fi

    if hash buildah &>/dev/null; then
        return
    fi
    if [[ "$installer" == "apt" ]]; then
        apt update -y
        $installer install -y buildah
    elif [[ "$installer" == "pacman" ]]; then
        pacman -Sy --noconfirm buildah
    else
        $installer install -y buildah
    fi
}

main() {
    local os_string="$(get_name_version)"

    if ! is_supported; then
        echo "Not supported OS [$os_string]!"
        exit 1
    fi
    # 禁用selinux，否则安装配置文件 config-allinone-current.yml 会写入失败
    hash setenforce &>/dev/null && setenforce 0

    ensure_buildah

    echo "[$os_string] $(buildah --version)"
}

main
