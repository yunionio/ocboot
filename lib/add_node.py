# encoding: utf-8
from __future__ import unicode_literals

import socket

from . import consts
from .service import AddNodeService, AddNodesConfig
from .cluster import construct_cluster
from .parser import inject_add_nodes_runtime_options


def is_ipv4(addr):
    try:
        socket.inet_pton(socket.AF_INET, addr)
        return True
    except (OSError, AttributeError, socket.error):
        return False


def is_ipv6(addr):
    try:
        socket.inet_pton(socket.AF_INET6, addr)
        return True
    except (OSError, AttributeError, socket.error):
        return False


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

        config = AddNodesConfig(cluster,
                                args.target_node_hosts,
                                args.ssh_user,
                                args.ssh_private_file,
                                args.ssh_port,
                                args.ssh_node_port,
                                enable_host_on_vm=True,
                                runtime=args.runtime,
                                host_networks=args.host_networks,
                                disk_paths=args.disk_paths,
                                ip_dual_conf=getattr(args, 'ip_dual_conf', None),
                                ip_type=args.ip_type,
                                offline_data_path=args.offline_data_path,
                                )
        config.run()


def add_command(subparsers):
    AddWorkerNodeService(subparsers, "add-node", "add new node into cluster")
