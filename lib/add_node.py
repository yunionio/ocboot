# encoding: utf-8
from __future__ import unicode_literals

import socket

from .service import AddNodeService, AddNodesConfig
from .cluster import construct_cluster
from .parser import inject_add_nodes_runtime_options
from .ansible import parse_inventory_config


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

        master_inventory = None
        if args.master_inventory:
            master_inventory = parse_inventory_config(args.master_inventory)

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
                                master_inventory=master_inventory,
                                offline_data_path=args.offline_data_path,
                                )
        config.run()


def add_command(subparsers):
    AddWorkerNodeService(subparsers, "add-node", "add new node into cluster")
