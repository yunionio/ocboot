import unittest

from lib import utils


class TestUtils(unittest.TestCase):

    def test_parse_k8s_time(self):
        time = utils.parse_k8s_time("2021-02-03T11:33:05Z")
        self.assertEqual(time.timestamp(), 1612351985.0)
        time2 = utils.parse_k8s_time("2021-02-03T11:34:05Z")
        self.assertGreater(time2, time)

    def test_is_below_v3_9(self):
        self.assertTrue(utils.is_below_v3_9('v3.8.11'))
        self.assertTrue(utils.is_below_v3_9('v3.7.11'))
        self.assertTrue(utils.is_below_v3_9('v3.6.11'))
        self.assertTrue(utils.is_below_v3_9('v2.6.11'))
        self.assertFalse(utils.is_below_v3_9('v3.9.0'))
        self.assertFalse(utils.is_below_v3_9('master-test'))

    def test_parse_ip(self):
        self.assertIsNotNone(utils.parse_ip('10.0.0.1'))
        self.assertIsNotNone(utils.parse_ip('fd85:ee78:d8a6:8607::1'))
        self.assertIsNone(utils.parse_ip('127.0.0.1'))
        self.assertIsNone(utils.parse_ip('my-hostname'))
        self.assertIsNone(utils.parse_ip(None))

    def test_ip_in_cidr_ipv4(self):
        self.assertTrue(utils.ip_in_cidr('10.40.0.5', '10.40.0.0/16'))
        self.assertFalse(utils.ip_in_cidr('10.0.0.5', '10.40.0.0/16'))
        self.assertFalse(utils.ip_in_cidr('10.40.0.5', 'fd85:ee78:d8a6:8607::/56'))

    def test_ip_in_cidr_ipv6(self):
        self.assertTrue(utils.ip_in_cidr(
            'fd85:ee78:d8a6:8607::1', 'fd85:ee78:d8a6:8607::/56'))
        self.assertFalse(utils.ip_in_cidr(
            '2001:db8::1', 'fd85:ee78:d8a6:8607::/56'))

    def test_check_ips_against_cidrs_conflict(self):
        ips = [('primary_master_node', '10.40.0.5')]
        cidrs = [
            ('pod_network_cidr', '10.40.0.0/16'),
            ('service_cidr', '10.96.0.0/12'),
        ]
        errors = utils.check_ips_against_cidrs(ips, cidrs)
        self.assertEqual(len(errors), 1)
        self.assertIn('10.40.0.5', errors[0])
        self.assertIn('pod_network_cidr', errors[0])

    def test_check_ips_against_cidrs_no_conflict(self):
        ips = [('primary_master_node', '10.0.0.5')]
        cidrs = [
            ('pod_network_cidr', '10.40.0.0/16'),
            ('service_cidr', '10.96.0.0/12'),
        ]
        errors = utils.check_ips_against_cidrs(ips, cidrs)
        self.assertEqual(errors, [])

    def test_check_ips_against_cidrs_dual_stack(self):
        ips = [
            ('worker_node', '10.0.0.5'),
            ('worker_node', 'fd85:ee78:d8a6:8607::1'),
        ]
        cidrs = [
            ('pod_network_cidr', 'fd85:ee78:d8a6:8607::/56'),
            ('service_cidr', 'fd85:ee78:d8a6:8608::/112'),
            ('pod_network_cidr_v4', '10.40.0.0/16'),
            ('service_cidr_v4', '10.96.0.0/12'),
        ]
        errors = utils.check_ips_against_cidrs(ips, cidrs)
        self.assertEqual(len(errors), 1)
        self.assertIn('fd85:ee78:d8a6:8607::1', errors[0])

    def test_check_ips_against_cidrs_skips_hostname(self):
        ips = [('worker_node', 'my-hostname')]
        cidrs = [('pod_network_cidr', '10.40.0.0/16')]
        errors = utils.check_ips_against_cidrs(ips, cidrs)
        self.assertEqual(errors, [])

    def test_check_ips_against_cidrs_invalid_cidr(self):
        with self.assertRaises(Exception) as ctx:
            utils.check_ips_against_cidrs(
                [('node', '10.0.0.1')], [('pod_network_cidr', 'invalid')])
        self.assertIn('Invalid CIDR format', str(ctx.exception))

    def test_parse_k3s_network_cidrs(self):
        config_yaml = """
cluster-cidr: 10.40.0.0/16
service-cidr: 10.96.0.0/12
"""
        cidrs = utils.parse_k3s_network_cidrs(config_yaml)
        self.assertEqual(cidrs, [
            ('pod_network_cidr', '10.40.0.0/16'),
            ('service_cidr', '10.96.0.0/12'),
        ])

    def test_parse_k3s_network_cidrs_dual_stack(self):
        config_yaml = """
cluster-cidr: fd85:ee78:d8a6:8607::/56,10.40.0.0/16
service-cidr: fd85:ee78:d8a6:8608::/112,10.96.0.0/12
"""
        cidrs = utils.parse_k3s_network_cidrs(config_yaml)
        self.assertEqual(len(cidrs), 4)
        self.assertIn(('pod_network_cidr', '10.40.0.0/16'), cidrs)
        self.assertIn(('service_cidr', '10.96.0.0/12'), cidrs)

    def test_validate_cidr_valid(self):
        self.assertEqual(utils.validate_cidr('10.40.0.0/16', 'pod'), '10.40.0.0/16')
        self.assertEqual(
            utils.validate_cidr('fd85:ee78:d8a6:8607::/56', 'pod', version=6),
            'fd85:ee78:d8a6:8600::/56')

    def test_validate_cidr_invalid(self):
        with self.assertRaises(Exception) as ctx:
            utils.validate_cidr('invalid', 'pod_network_cidr')
        self.assertIn('Invalid', str(ctx.exception))

    def test_validate_cidr_wrong_version(self):
        with self.assertRaises(Exception) as ctx:
            utils.validate_cidr('10.40.0.0/16', 'pod_network_cidr', version=6)
        self.assertIn('IPv6', str(ctx.exception))

    def test_apply_cidr_to_config_dict_ipv4_single_stack(self):
        config = {}
        utils.apply_cidr_to_config_dict(
            config,
            ip_type='ipv4',
            pod_network_cidr_v4='10.50.0.0/16',
            service_cidr_v4='10.100.0.0/16',
        )
        self.assertEqual(config['pod_network_cidr_v4'], '10.50.0.0/16')
        self.assertEqual(config['pod_network_cidr'], '10.50.0.0/16')
        self.assertEqual(config['service_cidr'], '10.100.0.0/16')

    def test_apply_cidr_to_config_dict_dual_stack(self):
        config = {}
        utils.apply_cidr_to_config_dict(
            config,
            ip_type='dual-stack',
            pod_network_cidr='fd85:ee78:d8a6:8607::/56',
            service_cidr='fd85:ee78:d8a6:8608::/112',
            pod_network_cidr_v4='10.50.0.0/16',
            service_cidr_v4='10.100.0.0/16',
        )
        self.assertEqual(config['pod_network_cidr'], 'fd85:ee78:d8a6:8607::/56')
        self.assertEqual(config['pod_network_cidr_v4'], '10.50.0.0/16')
        self.assertNotEqual(config.get('pod_network_cidr'), '10.50.0.0/16')
