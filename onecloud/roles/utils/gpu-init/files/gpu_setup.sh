#!/bin/bash

set -o errexit

pushd $(dirname $(readlink -f "$BASH_SOURCE")) > /dev/null
CUR_DIR=$(pwd)
ROOT_DIR=$(cd .. && pwd)
popd > /dev/null

export LC_CTYPE="en_US.UTF-8"
################################################

. $CUR_DIR/functions

is_intel_cpu() {
    grep -m 1 'model name' /proc/cpuinfo | grep -qi intel
    return $?
}

PCIIDS_FILE=${PCIIDS_FILE:-$CUR_DIR/pci.ids}
VFIO_PCI_OVERRIDE_TOOL=/usr/bin/vfio-pci-override.sh

declare -A NEW_KERNEL_PARAMS=(
    [crashkernel]=auto
    [iommu]=pt
    [vfio_iommu_type1.allow_unsafe_interrupts]=1
    [rdblacklist]=nouveau
    [nouveau.modeset]=0
    [mgag200.modeset]=0
)

if is_intel_cpu; then
    info "enable intel_iommu=on"
    NEW_KERNEL_PARAMS[intel_iommu]=on
fi

OLD_KERNEL_PARAMS_FILE="/tmp/ocboot_gpusetup_old_kernel_params_file.txt"

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

# refresh_pciids() {
#     info "Refresh PCI ids..."
#     local args=""
#     if [ -z "$PCIIDS_FILE" ]; then
#         info "pci.ids file not provided, fetch from upstream..."
#     elif [ ! -e "$PCIIDS_FILE" ]; then
#         error "pciids file $PCIIDS_FILE not exists, fetch from upstream"
#     else
#         args="-s $PCIIDS_FILE"
#     fi
#     $CUR_DIR/update_pciids.sh $args
# }

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
    elif [[ "${distro}" == "debian" ]]; then
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
    # 删掉 rd.lvm.lv(含)之后，空格之前的所有字符
    # 以便解决重启后因未加载 lvm 驱动而卡住的问题
    sed -i -e 's#rd.lvm.lv=[^ ]*##gi' $grub_cfg

    # 替换成带有 yn 后缀的内核，只对 centos
    if [[ "${distro}" != "centos" ]]; then
        mk_grub ${distro}
        return
    fi

    for i in {1..3}; do
        idx=$(awk -F\' '$1=="menuentry " {print i++ " : " $2}' $(find /etc/ -name 'grub2*cfg' -exec test -e {} \; -print |head -1 ) |grep -P '\.yn\d{8}\.'|awk '{print $1}' |head -1)
        if [ "$idx" -gt "0" ]; then
            break
        fi
        mk_grub ${distro}
    done
    if grep -q '^GRUB_DEFAULT' $grub_cfg; then
        sudo sed -i -e "s#^GRUB_DEFAULT=.*#GRUB_DEFAULT=$idx#" $grub_cfg
    else
        local tmp_conf=$(mktemp)
        cp -fv $conf $tmp_conf
        echo "GRUB_DEFAULT=$idx" >> $tmp_conf
        sudo mv $tmp_conf $grub_cfg
    fi
    mk_grub ${distro}
}

vfio_override_script_setup() {
    local vfio_override_file="/usr/bin/vfio-pci-override.sh"

    info "Add script: ${UCYAN}$vfio_override_file"

    cat <<EOF >"$vfio_override_file"
#!/bin/sh

CODE_VGA=0x030000
CODE_3D=0x030200

for i in \$(/usr/bin/find /sys/devices/pci* -name class); do
    CLS_CODE=\$(cat "\$i")
    if [ \$CLS_CODE == \$CODE_VGA ] || [ \$CLS_CODE == \$CODE_3D ]; then
        GPU="\${i%/class}"
        BOOT_VGA="\$GPU/boot_vga"
        if [ -f "\$BOOT_VGA" ]; then
            if [ \$(cat "\$BOOT_VGA") -eq 1 ]; then
                continue
            fi
        fi
        AUDIO="\$(echo "\$GPU" | sed -e "s/0$/1/")"
        echo "vfio-pci" > "\$GPU/driver_override"
        if [ -d "\$AUDIO" ]; then
            echo "vfio-pci" > "\$AUDIO/driver_override"
        fi
    fi
done

modprobe -i vfio-pci
EOF

    chmod a+x "$vfio_override_file"
}

modules_setup() {
    info "Configure kernel modules..."

    local vfio_load_file="/etc/modules-load.d/vfio.conf"
    local vfio_conf_file="/etc/modprobe.d/vfio.conf"
    local mod_blacklist_file="/etc/modprobe.d/blacklist-gpu.conf"
    local kvm_conf_file="/etc/modprobe.d/kvm.conf"

    cat <<EOF >"$vfio_load_file"
vfio
vfio_iommu_type1
vfio_pci
EOF

	cat <<EOF >"$vfio_conf_file"
install vfio-pci $VFIO_PCI_OVERRIDE_TOOL
EOF

	cat <<EOF >"$mod_blacklist_file"
blacklist nouveau
blacklist nvidia
blacklist nvidia_drm
EOF

    local kvm_options="options kvm ignore_msrs=1"
    if grep -xq "$kvm_options" "$kvm_conf_file"; then
        return
    else
        cat <<EOF >>"$kvm_conf_file"
options kvm ignore_msrs=1
EOF
    fi

    modprobe vfio
    modprobe vfio_pci
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
    if [[ $EUID -ne 0 ]]; then
        error_exit "You need sudo or root to run this script."
    fi

    local supported_distros=("centos" "debian" "openeuler")
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

dracut_ramfs() {
    info "Use dracut rebuild initramfs..."
    local yn_kernel=$(ls /boot/vmlinuz-* | grep yn | sort -r | head -n 1)
    if [ -z "$yn_kernel" ]; then
        warn "Dracut ramfs not found cloud customize kernel, skip it"
        return
    fi

    local dracut_vfio_file="/etc/dracut.conf.d/vfio.conf"
    cat <<EOF >"$dracut_vfio_file"
add_drivers+=" vfio vfio_iommu_type1 vfio_pci"
EOF
    local kernel_release=$(basename $yn_kernel | sed 's/vmlinuz-//g')
    dracut -f --kver $kernel_release --install find --install $VFIO_PCI_OVERRIDE_TOOL
}

main() {
    distro=$(env_check)
    grub_setup ${distro}
    vfio_override_script_setup
    modules_setup
#    refresh_pciids # has been replaced by "Update pciids" task in playbook.
    dracut_ramfs
    info "All done, ${UCYAN}REBOOT to make it work"
}

main

