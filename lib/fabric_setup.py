# encoding: utf-8
from __future__ import unicode_literals

import ipaddress

from .service import BaseService, NodesConfig
from .parser import inject_ssh_hosts_options, help_d
from .utils import pr_green, pr_red


def parse_node_spec(spec):
    """Parse node_ip | node_ip:index | node_ip:vip.

    Returns (node_ip, node_index_or_None, vip_or_None).
    """
    spec = spec.strip()
    if not spec:
        raise ValueError('empty node spec')

    if ':' not in spec:
        return spec, None, None

    host, suffix = spec.rsplit(':', 1)
    host = host.strip()
    suffix = suffix.strip()
    if not host:
        raise ValueError('invalid node spec %r: missing node IP' % spec)

    if suffix.isdigit():
        return host, int(suffix), None

    try:
        vip = ipaddress.ip_address(suffix)
    except ValueError:
        raise ValueError(
            'invalid node spec %r: suffix must be index or VIP, got %r' % (spec, suffix))
    return host, None, str(vip)


def fabric_mac_from_ip(fabric_ip, mac_prefix):
    ip = ipaddress.ip_address(fabric_ip)
    if ip.version != 4:
        raise ValueError('fabric overlay currently supports IPv4 only, got %s' % fabric_ip)
    ip_hex = ':'.join('%02x' % b for b in ip.packed)
    prefix = mac_prefix.strip().rstrip(':').lower()
    return '%s:%s' % (prefix, ip_hex)


def fabric_cidr_base(fabric_cidr):
    """Base address from cidr literal, e.g. 198.19.240.0/19 -> 198.19.240.0."""
    return ipaddress.ip_address(str(ipaddress.ip_interface(fabric_cidr).ip))


def vip_from_index(network, index):
    """VIP = address-part-of(fabric_cidr) + index."""
    base = fabric_cidr_base(network)
    if index <= 0:
        raise ValueError('node index must be > 0 (exclude network address), got %s' % index)
    vip = base + index
    if vip not in network:
        raise ValueError(
            'VIP %s (cidr %s + index %s) is outside fabric cidr %s' % (
                vip, base, index, network))
    if vip == network.network_address or vip == network.broadcast_address:
        raise ValueError('VIP %s cannot be network or broadcast address of %s' % (vip, network))
    return str(vip)


def build_fabric_nodes(node_specs, network, mac_prefix):
    """Pre-compute underlay node_ip, overlay VIP and MAC for each node.

    Input modes per spec:
      - node_ip            -> index = position+1, VIP = fabric_cidr_base + index
      - node_ip:index      -> VIP = fabric_cidr_base + index
      - node_ip:vip        -> VIP as given (must be inside fabric_cidr)
    """
    fabric_nodes = {}
    peer_node_ips = []
    used_vips = {}

    for pos, spec in enumerate(node_specs):
        node_ip, node_index, explicit_vip = parse_node_spec(spec)

        if node_ip in fabric_nodes:
            raise ValueError('duplicate node IP %s in specs %s' % (node_ip, node_specs))

        if explicit_vip is not None:
            vip = ipaddress.ip_address(explicit_vip)
            if vip not in network:
                raise ValueError('VIP %s for node %s is outside fabric cidr %s' % (
                    vip, node_ip, network))
            if vip == network.network_address or vip == network.broadcast_address:
                raise ValueError(
                    'VIP %s for node %s cannot be network or broadcast of %s' % (
                        vip, node_ip, network))
            fabric_ip = str(vip)
        else:
            if node_index is None:
                node_index = pos + 1
            fabric_ip = vip_from_index(network, node_index)

        if fabric_ip in used_vips:
            raise ValueError(
                'fabric VIP collision: %s used by both %s and %s' % (
                    fabric_ip, used_vips[fabric_ip], node_ip))

        used_vips[fabric_ip] = node_ip
        fabric_mac = fabric_mac_from_ip(fabric_ip, mac_prefix)
        fabric_nodes[node_ip] = {
            'node_ip': node_ip,
            'fabric_node_ip_addr': fabric_ip,
            'fabric_node_mac_addr': fabric_mac,
        }
        peer_node_ips.append(node_ip)

    return fabric_nodes, peer_node_ips


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
                            default='198.19.240.0/20',
                            help=help_d('fabric network CIDR'))
        parser.add_argument('--fabric-mac-prefix',
                            dest='fabric_mac_prefix',
                            default='00:74',
                            help=help_d('fabric MAC address prefix (2 octets)'))

    def do_action(self, args):
        node_specs = list(args.target_node_hosts)
        if not node_specs:
            raise Exception('at least one node IP is required '
                            '(node_ip | node_ip:index | node_ip:vip)')

        network = ipaddress.ip_network(args.fabric_cidr, strict=False)
        if network.version != 4:
            raise ValueError('fabric overlay currently supports IPv4 only: %s' % args.fabric_cidr)
        if network.num_addresses <= 2:
            raise ValueError('fabric cidr too small: %s' % args.fabric_cidr)
        try:
            fabric_nodes, peer_node_ips = build_fabric_nodes(
                node_specs, network, args.fabric_mac_prefix)
        except ValueError as e:
            pr_red(str(e))
            return 1

        pr_green('Fabric plan (cidr=%s, vni=%s, mac_prefix=%s):' % (
            args.fabric_cidr, args.vxlan_vni, args.fabric_mac_prefix))
        for node_ip in peer_node_ips:
            info = fabric_nodes[node_ip]
            pr_green('  %s -> vip=%s mac=%s' % (
                node_ip,
                info['fabric_node_ip_addr'],
                info['fabric_node_mac_addr']))

        config = NodesConfig(peer_node_ips,
                             args.ssh_user,
                             args.ssh_private_file,
                             args.ssh_port)
        vars = {
            'vxlan_vni': args.vxlan_vni,
            'fabric_cidr': args.fabric_cidr,
            'fabric_cidr_prefix_length': network.prefixlen,
            'fabric_mac_prefix': args.fabric_mac_prefix,
            'fabric_peer_node_ips': peer_node_ips,
            'fabric_nodes': fabric_nodes,
        }
        return config.run(self.action, vars=vars)


def add_command(subparsers):
    FabricSetupService(subparsers)
