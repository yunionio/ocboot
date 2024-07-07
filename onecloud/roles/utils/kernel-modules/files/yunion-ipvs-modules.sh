#!/bin/bash

ipvs_modules="ip_vs ip_vs_lc ip_vs_wlc ip_vs_rr ip_vs_wrr ip_vs_lblc ip_vs_lblcr ip_vs_dh ip_vs_sh ip_vs_fo ip_vs_nq ip_vs_sed ip_vs_ftp nf_conntrack_ipv4"
for kernel_module in ${ipvs_modules}; do
    /sbin/modinfo -F filename ${kernel_module} >/dev/null 2>&1 || :
    /sbin/modprobe ${kernel_module} || :
done

tcp_be_liberal=$(sysctl net.netfilter.nf_conntrack_tcp_be_liberal | awk '{print $NF}')

if [[ $tcp_be_liberal -ne 1 ]]; then
    echo "net.netfilter.nf_conntrack_tcp_be_liberal is not enabled. Updating sysctl.conf ..."
    echo "net.netfilter.nf_conntrack_tcp_be_liberal = 1" >>/etc/sysctl.conf
    sysctl -p || :
fi

tcp_mtu_probing=$(sysctl net.ipv4.tcp_mtu_probing | awk '{print $NF}')

if [[ $tcp_mtu_probing -ne 2 ]]; then
    echo "net.ipv4.tcp_mtu_probing is not enabled. Updating sysctl.conf ..."
    echo "net.ipv4.tcp_mtu_probing = 2" >>/etc/sysctl.conf
    sysctl -p || :
fi
