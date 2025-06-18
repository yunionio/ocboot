#!/usr/bin/env python3

import array
import fcntl
import socket
import struct
import sys


def format_ip(addr):
    return str(addr[0]) + '.' + \
        str(addr[1]) + '.' + \
        str(addr[2]) + '.' + \
        str(addr[3])


def all_interfaces():
    max_possible = 128  # arbitrary. raise if needed.
    bytes = max_possible * 32
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    names = array.array('B', b'\0' * bytes)
    outbytes = struct.unpack('iL', fcntl.ioctl(
        s.fileno(),
        0x8912,  # SIOCGIFCONF
        struct.pack('iL', bytes, names.buffer_info()[0])
    ))[0]
    if hasattr(names, 'tobytes'):
        namestr = names.tobytes()
    elif hasattr(names, 'tostring'):
        namestr = names.tostring()
    else:
        raise Exception("can not convert names to string")

    lst = []
    for i in range(0, outbytes, 40):
        name = namestr[i:i+16].split(b'\0', 1)[0].decode('utf-8')
        ip = format_ip(struct.unpack('BBBB', namestr[i+20:i+24]))
        lst.append((name, ip))

    # 读取 /proc/net/if_inet6 获取 IPv6 地址
    try:
        with open('/proc/net/if_inet6', 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) != 6:
                    continue
                raw_addr, idx, plen, scope, flags, ifname = parts
                # 格式化 IPv6 地址
                ipv6_addr = ':'.join([raw_addr[i:i+4] for i in range(0, 32, 4)])
                ipv6_addr = socket.inet_ntop(socket.AF_INET6, bytearray.fromhex(raw_addr))
                # 过滤掉 ::1 和 fe80::/10
                if ipv6_addr == '::1' or ipv6_addr.startswith('fe80'):
                    continue
                lst.append((ifname, ipv6_addr))
    except Exception as e:
        print(f"get ipv6error: {e}")
        pass
    return lst


ifs = all_interfaces()

def get_interface_by_ip(ip):
    if not ip:
        raise Exception("[get_interface_by_ip] empty ip")
    for i in ifs:
        if ip == i[1]:
            return i[0]
    raise Exception("Not found interface name for ip <%s>" % ip)


def main():
    ip = sys.argv[1]
    print(get_interface_by_ip(ip))


if __name__ == "__main__":
    main()
