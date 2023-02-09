# encoding: utf-8
from __future__ import unicode_literals

import os

from .cluster import construct_cluster
from .ocboot import WorkerConfig, Config
from .ocboot import get_ansible_global_vars
from .cmd import run_ansible_playbook
from . import ansible
from . import utils


def add_command(subparsers):
    parser = subparsers.add_parser(
        "add-node", help="add new node into cluster")

    parser.add_argument("primary_master_host",
                        metavar="FIRST_MASTER_HOST",
                        help="onecloud cluster primary master host, \
                              e.g., 10.1.2.56")

    parser.add_argument("target_node_hosts",
                        nargs='+',
                        default=[],
                        metavar="TARGET_NODE_HOSTS",
                        help="target nodes ip added into cluster")

    # optional options
    help_d = lambda help: help + " (default: %(default)s)"

    parser.add_argument("--user", "-u",
                        dest="ssh_user",
                        default="root",
                        help=help_d("primary master host ssh user"))

    parser.add_argument("--key-file", "-k",
                        dest="ssh_private_file",
                        default=os.path.expanduser("~/.ssh/id_rsa"),
                        help=help_d("primary master ssh private key file"))

    parser.add_argument("--port", "-p",
                        dest="ssh_port",
                        type=int,
                        default="22",
                        help=help_d("primary master host ssh port"))

    parser.add_argument("--node-port", "-n",
                        dest="ssh_node_port",
                        type=int,
                        default="22",
                        help=help_d("worker node host ssh port"))

    parser.add_argument("--enable-host-on-vm",
                        dest="enable_host_on_vm",
                        action="store_true", default=False)

    parser.set_defaults(func=do_add_node)


def do_add_node(args):
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
                           args.enable_host_on_vm)
    config.run()


class AddNodesConfig(object):

    def __init__(self, cluster, target_nodes, ssh_user, ssh_private_file,
            controlplane_ssh_port, ssh_port, enable_host_on_vm=False):
        target_nodes = list(set(target_nodes))
        for target_node in target_nodes:
            node = cluster.find_node_by_ip_or_hostname(target_node)
            if node is not None:
                raise Exception("Node %s(%s) already exists in cluster" % (
                    node.get_hostname(), node.get_ip()))
        self.current_version = cluster.get_current_version()
        controlplane_host = cluster.get_primary_master_node_ip()
        nodes_conf = [{'hostname': target_node, 'user': ssh_user, 'port': ssh_port} for target_node in target_nodes]
        woker_config_dict = {
            'hosts': nodes_conf,
            'controlplane_host': controlplane_host,
            'ad_controller': False,
            'as_host': True,
            'as_host_on_vm': enable_host_on_vm,
            'controlplane_ssh_port': controlplane_ssh_port,
        }
        self.worker_config = WorkerConfig(Config(woker_config_dict))
        print("Get current cluster %s version: %s" % (controlplane_host, self.current_version))

    def run(self):
        inventory_content = ansible.get_inventory_config(self.worker_config)
        yaml_content = utils.to_yaml(inventory_content)
        filepath = '/tmp/cluster_add_node_inventory.yml'
        with open(filepath, 'w') as f:
            f.write(yaml_content)
        # start run upgrade playbook
        return_code = run_ansible_playbook(
            filepath,
            './onecloud/add-node.yml',
            vars=self.get_vars(),
        )

    def get_vars(self):
        return get_ansible_global_vars(self.current_version)
