#!/bin/sh

set -o errexit

reserve_pages()
{
    echo $1 > $hugepage_path/nr_hugepages
}

if [ `grep hugepages_option /etc/yunion/host.conf | awk '{print $2}'` != "native" ]; then
    echo "host agent hugepage not enabled"
    exit 0
fi

hugepage_path=/sys/kernel/mm/hugepages/hugepages-1048576kB
if [ ! -d $hugepage_path ]; then
    echo "ERROR: $hugepage_path does not exist"
    exit 1
fi

reserved=${RESERVED_MEM:--1}
total=`free -g | grep Mem | awk '{ print $2 }'`

if [ "$reserved" -gt "0" ]; then
    total=$((total-reserved))
    reserve_pages $total
    exit 0
fi


if [ "$total" -lt "10" ]; then
    reserved=1
else
    reserved=$((total/10))
    if [ "$reserved" -gt "20" ]; then
        reserved=20
    fi
fi

total=$((total-reserved))

reserve_pages $total
