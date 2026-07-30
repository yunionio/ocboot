# encoding: utf-8
from __future__ import unicode_literals

import ipaddress
import unittest

from lib.fabric_setup import (
    build_fabric_nodes,
    fabric_mac_from_ip,
    parse_node_spec,
    vip_from_index,
)


FABRIC_CIDR = '198.19.240.0/19'
MAC_PREFIX = '00:74'


def fabric_network():
    return ipaddress.ip_network(FABRIC_CIDR, strict=False)


class TestParseNodeSpec(unittest.TestCase):

    def test_node_ip_only(self):
        self.assertEqual(
            parse_node_spec('10.166.20.182'),
            ('10.166.20.182', None, None))

    def test_node_ip_with_index(self):
        self.assertEqual(
            parse_node_spec('10.166.20.182:1'),
            ('10.166.20.182', 1, None))
        self.assertEqual(
            parse_node_spec('10.166.20.182:10'),
            ('10.166.20.182', 10, None))

    def test_node_ip_with_vip(self):
        self.assertEqual(
            parse_node_spec('10.166.20.182:198.19.240.1'),
            ('10.166.20.182', None, '198.19.240.1'))

    def test_strips_whitespace(self):
        self.assertEqual(
            parse_node_spec('  10.166.20.182 : 2  '),
            ('10.166.20.182', 2, None))

    def test_empty_spec(self):
        with self.assertRaises(ValueError):
            parse_node_spec('')

    def test_invalid_suffix(self):
        with self.assertRaises(ValueError) as ctx:
            parse_node_spec('10.166.20.182:abc')
        self.assertIn('suffix must be index or VIP', str(ctx.exception))


class TestVipFromIndex(unittest.TestCase):

    def test_index_one(self):
        net = fabric_network()
        # normalized network is 198.19.224.0/19
        self.assertEqual(vip_from_index(net, 1), '198.19.224.1')

    def test_index_must_be_positive(self):
        with self.assertRaises(ValueError) as ctx:
            vip_from_index(fabric_network(), 0)
        self.assertIn('must be > 0', str(ctx.exception))

    def test_index_out_of_range(self):
        # /30 has only 4 addresses; index 3 is broadcast after base+3 on tiny net
        net = ipaddress.ip_network('10.0.0.0/30', strict=False)
        with self.assertRaises(ValueError):
            vip_from_index(net, 100)


class TestFabricMacFromIp(unittest.TestCase):

    def test_mac_from_vip(self):
        self.assertEqual(
            fabric_mac_from_ip('198.19.240.1', MAC_PREFIX),
            '00:74:c6:13:f0:01')
        self.assertEqual(
            fabric_mac_from_ip('198.19.224.1', MAC_PREFIX),
            '00:74:c6:13:e0:01')

    def test_prefix_trailing_colon(self):
        self.assertEqual(
            fabric_mac_from_ip('198.19.240.10', '00:74:'),
            '00:74:c6:13:f0:0a')

    def test_ipv6_rejected(self):
        with self.assertRaises(ValueError):
            fabric_mac_from_ip('fd85::1', MAC_PREFIX)


class TestBuildFabricNodes(unittest.TestCase):

    def test_auto_index_by_position(self):
        nodes, peers = build_fabric_nodes(
            ['10.166.20.182', '10.166.20.183'],
            fabric_network(),
            MAC_PREFIX)
        self.assertEqual(peers, ['10.166.20.182', '10.166.20.183'])
        self.assertEqual(nodes['10.166.20.182']['fabric_node_ip_addr'], '198.19.224.1')
        self.assertEqual(nodes['10.166.20.183']['fabric_node_ip_addr'], '198.19.224.2')
        self.assertEqual(
            nodes['10.166.20.182']['fabric_node_mac_addr'],
            '00:74:c6:13:e0:01')
        self.assertEqual(
            nodes['10.166.20.183']['fabric_node_mac_addr'],
            '00:74:c6:13:e0:02')

    def test_explicit_index(self):
        nodes, peers = build_fabric_nodes(
            ['10.166.20.182:5', '10.166.20.183:10'],
            fabric_network(),
            MAC_PREFIX)
        self.assertEqual(peers, ['10.166.20.182', '10.166.20.183'])
        self.assertEqual(nodes['10.166.20.182']['fabric_node_ip_addr'], '198.19.224.5')
        self.assertEqual(nodes['10.166.20.183']['fabric_node_ip_addr'], '198.19.224.10')
        self.assertEqual(
            nodes['10.166.20.183']['fabric_node_mac_addr'],
            '00:74:c6:13:e0:0a')

    def test_explicit_vip(self):
        nodes, peers = build_fabric_nodes(
            ['10.166.20.182:198.19.240.1'],
            fabric_network(),
            MAC_PREFIX)
        self.assertEqual(peers, ['10.166.20.182'])
        self.assertEqual(nodes['10.166.20.182']['fabric_node_ip_addr'], '198.19.240.1')
        self.assertEqual(
            nodes['10.166.20.182']['fabric_node_mac_addr'],
            '00:74:c6:13:f0:01')

    def test_mixed_modes(self):
        nodes, peers = build_fabric_nodes(
            [
                '10.166.20.182',                 # auto index 1 -> 198.19.224.1
                '10.166.20.183:3',               # index 3 -> 198.19.224.3
                '10.166.20.184:198.19.240.10',   # explicit VIP
            ],
            fabric_network(),
            MAC_PREFIX)
        self.assertEqual(peers, [
            '10.166.20.182',
            '10.166.20.183',
            '10.166.20.184',
        ])
        self.assertEqual(nodes['10.166.20.182']['fabric_node_ip_addr'], '198.19.224.1')
        self.assertEqual(nodes['10.166.20.183']['fabric_node_ip_addr'], '198.19.224.3')
        self.assertEqual(nodes['10.166.20.184']['fabric_node_ip_addr'], '198.19.240.10')
        for node_ip in peers:
            self.assertEqual(nodes[node_ip]['node_ip'], node_ip)
            self.assertIn('fabric_node_mac_addr', nodes[node_ip])

    def test_duplicate_node_ip(self):
        with self.assertRaises(ValueError) as ctx:
            build_fabric_nodes(
                ['10.166.20.182', '10.166.20.182:2'],
                fabric_network(),
                MAC_PREFIX)
        self.assertIn('duplicate node IP', str(ctx.exception))

    def test_vip_collision(self):
        with self.assertRaises(ValueError) as ctx:
            build_fabric_nodes(
                ['10.166.20.182', '10.166.20.183:1'],
                fabric_network(),
                MAC_PREFIX)
        self.assertIn('fabric VIP collision', str(ctx.exception))

    def test_explicit_vip_out_of_range(self):
        with self.assertRaises(ValueError) as ctx:
            build_fabric_nodes(
                ['10.166.20.182:198.19.200.1'],
                fabric_network(),
                MAC_PREFIX)
        self.assertIn('outside fabric cidr', str(ctx.exception))

    def test_explicit_vip_network_address_rejected(self):
        net = fabric_network()
        with self.assertRaises(ValueError) as ctx:
            build_fabric_nodes(
                ['10.166.20.182:%s' % net.network_address],
                net,
                MAC_PREFIX)
        self.assertIn('network or broadcast', str(ctx.exception))

    def test_explicit_vip_broadcast_rejected(self):
        net = fabric_network()
        with self.assertRaises(ValueError) as ctx:
            build_fabric_nodes(
                ['10.166.20.182:%s' % net.broadcast_address],
                net,
                MAC_PREFIX)
        self.assertIn('network or broadcast', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
