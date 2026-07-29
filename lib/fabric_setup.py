# encoding: utf-8
from __future__ import unicode_literals

import hashlib
import ipaddress

from .service import BaseService, NodesConfig
from .parser import inject_ssh_hosts_options, help_d


def build_fabric_nodes(node_ips, fabric_cidr, mac_prefix):
    fabric_nodes = {}
    for node_ip in node_ips:
        fabric_nodes[node_ip] = {
            'node_ip': node_ip,
        }
    return fabric_nodes


class FabricSetupService(BaseService):

    def __init__(self, subparsers):
        super(FabricSetupService, self).__init__(
            subparsers,
            'fabric-setup',
            'setup full-mesh VXLAN fabric overlay on target nodes')

    def inject_options(self, parser):
        inject_ssh_hosts_options(parser)
        parser.add_argument('--vxlan-vni',
                            dest='vxlan_vni',
                            type=int,
                            default=1342,
                            help=help_d('VXLAN VNI for fabric network'))
        parser.add_argument('--fabric-cidr',
                            dest='fabric_cidr',
                            default='198.19.240.0/19',
                            help=help_d('fabric network CIDR'))
        parser.add_argument('--fabric-mac-prefix',
                            dest='fabric_mac_prefix',
                            default='00:74',
                            help=help_d('fabric MAC address prefix (2 octets)'))

    def do_action(self, args):
        # Keep stable unique order for peer list.
        node_ips = list(dict.fromkeys(args.target_node_hosts))
        if not node_ips:
            raise Exception('at least one node IP is required')

        network = ipaddress.ip_network(args.fabric_cidr, strict=False)
        fabric_nodes = build_fabric_nodes(
            node_ips, args.fabric_cidr, args.fabric_mac_prefix)

        config = NodesConfig(node_ips,
                             args.ssh_user,
                             args.ssh_private_file,
                             args.ssh_port)
        vars = {
            'vxlan_vni': args.vxlan_vni,
            'fabric_cidr': args.fabric_cidr,
            'fabric_cidr_prefix_length': network.prefixlen,
            'fabric_mac_prefix': args.fabric_mac_prefix,
            'fabric_peer_node_ips': node_ips,
            'fabric_nodes': fabric_nodes,
        }
        return config.run(self.action, vars=vars)


def add_command(subparsers):
    FabricSetupService(subparsers)
