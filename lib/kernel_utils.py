import re
import socket
import fcntl
import struct
import os
import platform


def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    inet = fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', ifname[:15]))
    ret = socket.inet_ntoa(inet[20:24])
    return ret


def get_all_ips():
    ips = []
    for interface in os.listdir('/sys/class/net/'):
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
