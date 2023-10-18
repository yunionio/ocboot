# encoding: utf-8
from __future__ import unicode_literals

from .service import AddNodeService, AddNodesConfig
from .cluster import construct_cluster


class AddWorkerNodeService(AddNodeService):

    def inject_options(self, parser):
        super(AddNodeService, self).inject_options(parser)

    def do_action(self, args):
        cluster = construct_cluster(
            args.primary_master_host,
            args.ssh_user,
            args.ssh_private_file,
            args.ssh_port)

        config = AddNodesConfig(cluster,
                                args.target_node_hosts,
                                args.ssh_user,
                                args.ssh_private_file,
                                args.ssh_port,
                                args.ssh_node_port,
                                enable_host_on_vm=True)
        config.run()


def add_command(subparsers):
    AddWorkerNodeService(subparsers, "add-node", "add new node into cluster")
