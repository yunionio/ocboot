# encoding: utf-8
from __future__ import unicode_literals

import socket

from . import consts
from .service import AddNodeService, AddNodesConfig
from .cluster import construct_cluster
from .parser import inject_add_nodes_runtime_options
from .utils import is_ipv4, is_ipv6


class AddWorkerNodeService(AddNodeService):

    def inject_options(self, parser):
        super(AddWorkerNodeService, self).inject_options(parser)
        inject_add_nodes_runtime_options(parser)

    def do_action(self, args):
        cluster = construct_cluster(
            args.primary_master_host,
            args.ssh_user,
            args.ssh_private_file,
            args.ssh_port)

        if args.ip_type == '':
            if is_ipv4(args.primary_master_host):
                args.ip_type = consts.IP_TYPE_IPV4
            elif is_ipv6(args.primary_master_host):
                args.ip_type = consts.IP_TYPE_IPV6
            else:
                raise ValueError("ip type is not set and cannot be determined from primary master host")

        # 处理双栈配置
        kwargs = {
            'runtime': args.runtime,
            'host_networks': args.host_networks,
            'disk_paths': args.disk_paths,
            'ip_dual_conf': getattr(args, 'ip_dual_conf', None),
            'ip_type': args.ip_type,
            'offline_data_path': args.offline_data_path,
        }

        # 如果是双栈配置，需要处理IPv4和IPv6地址
        if args.ip_type == consts.IP_TYPE_DUAL_STACK and hasattr(args, 'ip_dual_conf') and args.ip_dual_conf:
            # 确定哪个是IPv4，哪个是IPv6
            if is_ipv4(args.target_node_hosts[0]):
                # 主IP是IPv4，ip_dual_conf是IPv6
                kwargs['node_ip_v4'] = args.target_node_hosts[0]
                kwargs['node_ip_v6'] = args.ip_dual_conf
            else:
                # 主IP是IPv6，ip_dual_conf是IPv4
                kwargs['node_ip_v4'] = args.ip_dual_conf
                kwargs['node_ip_v6'] = args.target_node_hosts[0]

        config = AddNodesConfig(cluster,
                                args.target_node_hosts,
                                args.ssh_user,
                                args.ssh_private_file,
                                args.ssh_port,
                                args.ssh_node_port,
                                enable_host_on_vm=True,
                                **kwargs)
        return config.run()


def add_command(subparsers):
    AddWorkerNodeService(subparsers, "add-node", "add new node into cluster")
