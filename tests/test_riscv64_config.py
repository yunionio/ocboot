import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock

try:
    import yaml
except ImportError:
    yaml = None
try:
    from jinja2 import Environment, StrictUndefined
except ImportError:
    Environment = None
    StrictUndefined = None

from lib import ocboot
from lib import service


def valid_riscv64_config():
    return {
        'k3s': {
            'url_prefix': 'https://artifacts.example.test/k3s',
            'binary_sha256': '1' * 64,
            'airgap_images_sha256': '2' * 64,
        },
        'cni': 'flannel',
        'rpm': {
            'baseurl': 'https://artifacts.example.test/rpm/',
            'gpgcheck': False,
            'repo_gpgcheck': False,
        },
        'images': {
            key: 'registry.example.test/%s:test' % key
            for key in ocboot.RISCV64_IMAGE_KEYS
        },
        'cloudpods': {
            key: 'test'
            for key in ocboot.RISCV64_CLOUDPODS_KEYS
        },
    }


class FakeGroup(object):

    onecloud_version = 'v4.0.3-test'
    target_architecture = 'riscv64'

    def get_nodes(self):
        return []


class FakeCluster(object):

    def __init__(self, using_k3s=True):
        self.k8s_nodes = []
        self.using_k3s = using_k3s

    def find_node_by_ip_or_hostname(self, _target):
        return None

    def get_current_version(self):
        return 'v4.0.3-test'

    def get_cluster_controlplane_host(self):
        return '192.0.2.10'

    def get_primary_master_node_ip(self):
        return '192.0.2.10'

    def get_repository(self):
        return 'registry.example.test/cloudpods', False

    def get_image_repository(self):
        return 'registry.example.test/cloudpods'

    def is_using_k3s(self):
        return self.using_k3s


class FakeSSHClient(object):

    def __init__(self, host, _user, _key_file, _port):
        self.host = host

    def get_hostname(self):
        return 'compute-%s' % self.host.rsplit('.', 1)[-1]

    def exec_command(self, command):
        if command == 'uname -m':
            return 'riscv64\n'
        raise AssertionError('unexpected command: %s' % command)


class TestRiscv64Config(unittest.TestCase):

    def test_normalizes_external_artifact_configuration(self):
        normalized = ocboot.normalize_riscv64_config(
            valid_riscv64_config())
        self.assertEqual(normalized['cni'], 'flannel')
        self.assertEqual(
            normalized['rpm']['baseurl'],
            'https://artifacts.example.test/rpm')
        self.assertFalse(normalized['cloudpods']['monitor_disable'])

    def test_signed_repository_requires_key(self):
        config = valid_riscv64_config()
        del config['rpm']['gpgcheck']
        del config['rpm']['repo_gpgcheck']
        with self.assertRaisesRegex(ValueError, 'gpgkey'):
            ocboot.normalize_riscv64_config(config)

    def test_rejects_incomplete_image_set(self):
        config = valid_riscv64_config()
        del config['images']['pause']
        with self.assertRaisesRegex(ValueError, 'pause'):
            ocboot.normalize_riscv64_config(config)

    @unittest.skipIf(yaml is None, 'PyYAML is not installed')
    def test_loads_wrapped_configuration_file(self):
        with tempfile.NamedTemporaryFile(
                mode='w', suffix='.yml', encoding='utf-8') as stream:
            yaml.safe_dump({'riscv64': valid_riscv64_config()}, stream)
            stream.flush()
            loaded = ocboot.load_riscv64_config_file(stream.name)
        self.assertEqual(loaded['cni'], 'flannel')

    def test_node_normalizes_declared_architecture(self):
        node = ocboot.Node(ocboot.Config({
            'hostname': '192.0.2.10',
            'target_architecture': 'RISCV64',
        }))
        self.assertEqual(node.target_architecture, 'riscv64')
        self.assertEqual(
            node.ansible_host_vars()['target_architecture'], 'riscv64')

    def test_global_vars_include_riscv64_only_when_requested(self):
        config = ocboot.OcbootConfig.__new__(ocboot.OcbootConfig)
        config.config = ocboot.Config({
            'riscv64': valid_riscv64_config(),
        })
        config.primary_master_config = FakeGroup()
        config.master_config = None
        config.worker_config = None
        config.mariadb_config = None
        config.mariadb_ha_config = None
        config.clickhouse_config = None
        config.registry_config = None

        variables = config.ansible_global_vars()

        self.assertEqual(variables['target_architectures'], ['riscv64'])
        self.assertEqual(variables['cluster_cni'], 'flannel')
        self.assertIn('riscv64', variables)

    @unittest.skipIf(yaml is None, 'PyYAML is not installed')
    @mock.patch('lib.service.resolve_ssh_private_file', return_value='/key')
    @mock.patch('lib.service.SSHClient', FakeSSHClient)
    def test_add_node_detects_riscv64_and_forwards_config(self, _resolve_key):
        with tempfile.NamedTemporaryFile(
                mode='w', suffix='.yml', encoding='utf-8') as stream:
            yaml.safe_dump({'riscv64': valid_riscv64_config()}, stream)
            stream.flush()
            with mock.patch.dict(
                    os.environ, {'IGNORE_ALL_CHECKS': 'true'}):
                config = service.AddNodesConfig(
                    FakeCluster(), ['192.0.2.11'], 'root', '/key', 22, 22,
                    runtime='qemu', riscv64_config_file=stream.name)

        self.assertEqual(config.target_architectures, ['riscv64'])
        variables = config.get_vars()
        self.assertEqual(variables['cluster_cni'], 'flannel')
        host = config.worker_config.get_nodes()[0]
        self.assertEqual(host.target_architecture, 'riscv64')

    @mock.patch('lib.service.resolve_ssh_private_file', return_value='/key')
    @mock.patch('lib.service.SSHClient', FakeSSHClient)
    def test_add_riscv64_node_requires_artifact_config(self, _resolve_key):
        with mock.patch.dict(os.environ, {'IGNORE_ALL_CHECKS': 'true'}):
            with self.assertRaisesRegex(ValueError, '--riscv64-config'):
                service.AddNodesConfig(
                    FakeCluster(), ['192.0.2.11'], 'root', '/key', 22, 22,
                    runtime='qemu')

    @mock.patch('lib.service.resolve_ssh_private_file', return_value='/key')
    @mock.patch('lib.service.SSHClient', FakeSSHClient)
    def test_add_riscv64_node_rejects_native_kubernetes(self, _resolve_key):
        with mock.patch.dict(os.environ, {'IGNORE_ALL_CHECKS': 'true'}):
            with self.assertRaisesRegex(ValueError, 'native Kubernetes'):
                service.AddNodesConfig(
                    FakeCluster(using_k3s=False), ['192.0.2.11'], 'root',
                    '/key', 22, 22, runtime='qemu')

    @unittest.skipIf(
        yaml is None or Environment is None,
        'PyYAML and Jinja2 are required',
    )
    def test_k3s_template_preserves_defaults_and_selects_riscv64_images(self):
        template_path = (
            Path(__file__).parents[1] /
            'onecloud/roles/k3s/config/templates/config.yaml.j2')
        environment = Environment(
            undefined=StrictUndefined, keep_trailing_newline=True)
        environment.filters['regex_search'] = (
            lambda value, pattern: re.search(pattern, value or ''))
        template = environment.from_string(
            template_path.read_text(encoding='utf-8'))
        variables = {
            'ip_type': 'ipv4',
            'node_ip': '192.0.2.10',
            'image_repository': 'registry.example.test/cloudpods',
            'is_k3s_server': True,
            'pod_network_cidr': '10.40.0.0/16',
            'service_cidr': '10.96.0.0/12',
            'service_dns_domain': 'cluster.local',
            'join_as_host': True,
            'enable_lbagent': False,
        }

        default_config = yaml.safe_load(template.render(
            ansible_architecture='x86_64', **variables))
        self.assertEqual(
            default_config['pause-image'],
            'registry.example.test/cloudpods/pause:3.1')
        self.assertEqual(default_config['flannel-backend'], 'none')
        self.assertTrue(default_config['disable-network-policy'])
        self.assertNotIn('helm-job-image', default_config)

        riscv64_config = yaml.safe_load(template.render(
            ansible_architecture='riscv64',
            cluster_cni='flannel',
            k3s_pause_image='registry.example.test/pause:riscv64',
            k3s_helm_job_image='registry.example.test/helm:riscv64',
            **variables))
        self.assertEqual(
            riscv64_config['pause-image'],
            'registry.example.test/pause:riscv64')
        self.assertEqual(
            riscv64_config['helm-job-image'],
            'registry.example.test/helm:riscv64')
        self.assertEqual(riscv64_config['flannel-backend'], 'vxlan')
        self.assertFalse(riscv64_config['disable-network-policy'])


if __name__ == '__main__':
    unittest.main()
