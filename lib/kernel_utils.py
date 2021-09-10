import re
import socket
import fcntl
import struct
import os
import platform
import subprocess


def _run_cmd_with_output(cmds):

    output = []
    shell_cmd = ' '.join(cmds)
    proc = subprocess.Popen(
        shell_cmd,
        shell=True,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,)
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        output.append(line.strip())
        proc.wait()
    return output


def get_macos_interfaces():
    bashCmd = '''networksetup -listallhardwareports| grep Device: |sed -e "s#Device: ##"'''
    return _run_cmd_with_output([bashCmd])


def get_linux_interfaces():
    return os.listdir('/sys/class/net/')


def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    inet = fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', ifname[:15]))
    ret = socket.inet_ntoa(inet[20:24])
    return ret


def get_all_interfaces():
    os = platform.uname()
    if not len(os):
        return []
    if os[0] == 'Darwin':
        return get_macos_interfaces()
    elif os[0] == 'Linux':
        return get_linux_interfaces()
    return []


def get_all_ips():
    ips = []
    for interface in get_all_interfaces():
        try:
            ip = get_ip_address(interface)
            ips.append(ip)
        except Exception:
            pass
    return ips


def is_local_ip(ip):
    return ip in get_all_ips()


def is_yunion_kernel():
    kernel_str = platform.platform()
    pattern = re.compile(r'\.yn[\d]{8}\.')
    return pattern.search(kernel_str) is not None

def is_centos():
    # we only provide x86 centos kernel which need reboot
    try:
        if not (platform.uname()[-2] == 'x86_64' and platform.system() == 'Linux'):
            return False
    except IndexError:
        pass
    return os.system('grep -qi centos /etc/os-release 2>/dev/null') == 0
