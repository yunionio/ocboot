# encoding: utf-8
from __future__ import unicode_literals

import os
import base64

from lib import k3s

from . import ansible
from . import utils
from . import consts
from .color import RB as Red
from .k3s import is_using_k3s

GROUP_MARIADB_NODE = "mariadb_node"
GROUP_MARIADB_HA_NODES = "mariadb_ha_nodes"
GROUP_CLICKHOUSE_NODE = "clickhouse_node"
GROUP_REGISTRY_NODE = "registry_node"
GROUP_PRIMARY_MASTER_NODE = "primary_master_node"
GROUP_MASTER_NODES = "master_nodes"
GROUP_WORKER_NODES = "worker_nodes"
GROUP_NODES = "nodes"

KEY_HOSTNAME = 'hostname'
KEY_ONECLOUD_VERSION = 'onecloud_version'
KEY_OPERATOR_VERSION = 'operator_version'
KEY_ONECLOUD_MAJOR_VERSION = 'onecloud_major_version'
KEY_PRODUCT_VERSION = 'product_version'
KEY_AS_HOST = 'as_host'
KEY_AS_HOST_ON_VM = 'as_host_on_vm'
KEY_EXTRA_PACKAGES = 'extra_packages'

KEY_K8S_OR_K3S = 'env_k8s_or_k3s'
KEY_K3S_API_ENDPOINT = "api_endpoint"
KEY_K3S_API_PORT = "api_port"
KEY_K3S_AIRGAP_DIR = "airgap_dir"
KEY_K3S_VERSION = "k3s_version"
VAL_K3S_VERSION = k3s.VERSION_V1_28_5_K3S_1
KEY_K3S_TOKEN = "token"
VAL_K3S_TOKEN = "mytoken@yunionio"

KEY_STACK_FULLSTACK = 'FullStack'
KEY_STACK_EDGE = 'Edge'
KEY_STACK_CMP = 'CMP'
KEY_STACK_LIST = [KEY_STACK_FULLSTACK, KEY_STACK_EDGE, KEY_STACK_CMP]

KEY_USER_DNS = 'user_dns'


def load_config(config_file):
    import yaml
    with open(config_file) as f:
        config = Config(yaml.safe_load(f))
        return OcbootConfig(config)


def get_ansible_global_vars(version):
    _is_using_k3s = is_using_k3s()
    major_version = utils.get_major_version(version)
    vars = {
        KEY_ONECLOUD_VERSION: version,
        KEY_ONECLOUD_MAJOR_VERSION: major_version,
        KEY_EXTRA_PACKAGES: [],
        KEY_K3S_VERSION: VAL_K3S_VERSION,
        KEY_K3S_AIRGAP_DIR: k3s.GET_AIRGAP_DIR(),
        KEY_K3S_TOKEN: VAL_K3S_TOKEN,
        KEY_K8S_OR_K3S: 'k3s' if _is_using_k3s else 'k8s',      # for path, eg: utils/k8s/kubelet or utils/k3s/kubelet,
    }

    # set yunion_qemu_package for pre released version
    yunion_qemu_package = 'yunion-qemu-4.2.0'
    extra_packages = []
    if utils.is_below_v3_9(version):
        yunion_qemu_package = 'yunion-qemu-2.12.1'
    if yunion_qemu_package:
        vars['yunion_qemu_package'] = yunion_qemu_package
    vars[KEY_EXTRA_PACKAGES] = extra_packages
    return vars


class OcbootConfig(object):

    def __init__(self, config):
        self.config = config

        self.bastion_host = self.load_bastion_host(config)

        self.mariadb_config = self._fetch_conf(MariadbConfig)
        self.mariadb_ha_config = self._fetch_conf(MariadbHAConfig)
        self.clickhouse_config = self._fetch_conf(ClickhouseConfig)
        self.registry_config = self._fetch_conf(RegistryConfig)
        self.primary_master_config = self._fetch_conf(PrimaryMasterConfig)
        self.master_config = self._fetch_conf(MasterConfig)
        if self.master_config:
            self.master_config.set_primary_master_config(self.primary_master_config)
        self.worker_config = self._fetch_conf(WorkerConfig)
        if self.mariadb_config and self.mariadb_ha_config:
            raise Exception("mariadb_node and mariadb_ha_nodes can't coexist in config")

    def load_bastion_host(self, config):
        bastion_config = config.get('bastion_host', None)
        if not bastion_config:
            return None
        bastion_config = Config(bastion_config)
        host = bastion_config.ensure_get('host', 'hostname')
        user = bastion_config.get('user', 'root')
        return ansible.AnsibleBastionHost(host, user)

    def is_iso_join_mode(self):
        worker_nodes = self.config.get('worker_nodes', None)
        master_nodes = self.config.get('master_nodes', None)

        if worker_nodes and worker_nodes.get('join_token', None):
            return True
        if master_nodes and master_nodes.get('join_token', None):
            return True
        return False

    def get_primary_master_ssh_port(self):
        if self.is_iso_join_mode():
            return
        return self.primary_master_config.node.port

    def _fetch_conf(self, config_cls):
        group = config_cls.get_group()
        group_config = self.config.get(group, None)
        if not group_config:
            return None
        if group in [GROUP_MASTER_NODES, GROUP_WORKER_NODES]:
            if not group_config.get('controlplane_ssh_port', None):
                group_config['controlplane_ssh_port'] = self.get_primary_master_ssh_port()
        return config_cls(Config(group_config), self.bastion_host)

    def get_onecloud_version(self):
        for node in [self.mariadb_config, self.mariadb_ha_config, self.clickhouse_config, self.registry_config, self.primary_master_config, self.master_config, self.worker_config]:
            if not node:
                continue
            version = getattr(node, KEY_ONECLOUD_VERSION, None)
            if version:
                return version
        raise Exception("get attr onecloud_version error")

    def ansible_global_vars(self):
        return get_ansible_global_vars(self.get_onecloud_version())

    def get_ansible_inventory(self):
        return ansible.get_inventory_config(
            self.mariadb_config,
            self.mariadb_ha_config,
            self.clickhouse_config,
            self.registry_config,
            self.primary_master_config,
            self.master_config,
            self.worker_config)

    def generate_inventory_file(self):
        content = self.get_ansible_inventory()
        yaml_content = utils.to_yaml(content)
        filepath = '/tmp/host_inventory.yml'
        with open(filepath, 'w') as f:
            f.write(yaml_content)
        return filepath

    def get_login_info(self):
        if self.primary_master_config is None:
            return None
        p_master_config = self.primary_master_config
        frontend_ip = p_master_config.controlplane_host
        user = p_master_config.onecloud_user
        password = p_master_config.onecloud_user_password
        if frontend_ip is None:
            raise Exception("Not found controlplane_host in config")
        if user is None:
            raise Exception("Not found onecloud_user in config")
        if password is None:
            raise Exception("Not found onecloud_user_password in config")
        return (frontend_ip, user, password)

    def is_using_ee(self):
        return self.primary_master_config.use_ee


class ConfigNotFoundException(Exception):

    def __init__(self, config, what):
        self.config = config
        self.what = what

    def __str__(self):
        return "not found '%s' in config %s" % (self.what, self.config)


class Config(object):

    def __init__(self, config):
        self.config = config

    def get_config(self, group):
        config = self.ensure_get(group)
        return Config(config)

    def get(self, key, default):
        return self.config.get(key, default)

    def ensure_get(self, key, alter_key=None):
        val = self.get(key, None)
        if val:
            return val
        if alter_key:
            val = self.get(alter_key, None)
        if not val:
            what = key
            if alter_key:
                what = '%s or %s' % (key, alter_key)
            raise ConfigNotFoundException(self.config, what)
        return val


class Node(object):

    def __init__(self, config):
        self.use_local = config.get('use_local', False)
        self.host = '127.0.0.1' if self.use_local else config.ensure_get('host', 'hostname')
        self.user = config.get('user', 'root')
        self.port = config.get('port', 22)
        self.host_networks = config.get('host_networks', None)
        self.enable_hugepage = config.get('enable_hugepage', True)
        self.node_ip = config.get('node_ip', None)
        if not self.node_ip:
            self.node_ip = self.host
        self.bastion_host = None
        self.vrrp_priority = config.get('vrrp_priority', 0)
        self.vrrp_interface = config.get('vrrp_interface', None)
        self.vrrp_vip = config.get('vrrp_vip', None)
        self.vrrp_router_id = config.get('vrrp_router_id', None)

    def get_host(self):
        return self.host

    def with_bastion(self, bastion_host):
        self.bastion_host = bastion_host
        return self

    def ansible_host_vars(self):
        vars = {
            'ansible_host': self.host,
            'ansible_user': self.user,
            'ansible_port': self.port,
        }
        if self.bastion_host:
            vars['ansible_ssh_common_args'] = self.bastion_host.to_option()
        if self.host != "127.0.0.1":
            vars['node_ip'] = self.node_ip
        if self.use_local:
            vars['ansible_connection'] = 'local'
        if self.host_networks:
            vars['host_networks'] = self.host_networks
        if self.enable_hugepage:
            vars['enable_hugepage'] = self.enable_hugepage
        if self.vrrp_interface or self.vrrp_vip:
            vars['vrrp_vip'] = self.vrrp_vip
            vars['vrrp_interface'] = self.vrrp_interface
            vars['vrrp_priority'] = self.vrrp_priority
            vars['vrrp_router_id'] = self.vrrp_router_id
        return vars

    def __str__(self):
        ret = self.host
        if self.host != "127.0.0.1":
            ret = "%s node_ip=%s" % (ret, self.node_ip)
        if self.use_local:
            ret = "%s ansible_connection=local" % ret
        if self.user is not None:
            ret = "%s ansible_user=%s" % (ret, self.user)
        if self.host_networks is not None:
            ret = "%s host_networks=%s" % (ret, self.host_networks)
        return ret


class MariadbConfig(object):

    def __init__(self, config, bastion_host=None):
        self.node = Node(config).with_bastion(bastion_host)

        self.db_user = config.get('db_user', 'root')
        self.db_password = config.ensure_get('db_password')
        self.db_port = config.get('db_port', 3306)

    @classmethod
    def get_group(cls):
        return GROUP_MARIADB_NODE

    def get_nodes(self):
        return [self.node]

    def ansible_vars(self):
        return {
            "db_user": self.db_user,
            "db_password": self.db_password,
            "db_port": self.db_port,
            "db_host": self.node.host,
        }


class MariadbHAConfig(object):

    def __init__(self, config, bastion_host=None):
        self.nodes = get_nodes(config, bastion_host)

        self.db_user = config.get('db_user', 'root')
        self.db_password = config.ensure_get('db_password')
        self.db_port = config.get('db_port', 3306)
        self.db_vip = config.get('db_vip', None)
        self.db_nic = config.get('db_nic', None)

    @classmethod
    def get_group(cls):
        return GROUP_MARIADB_HA_NODES

    def get_nodes(self):
        return self.nodes

    def ansible_vars(self):
        vars = {
            "db_user": self.db_user,
            "db_password": self.db_password,
            "db_port": self.db_port,
        }
        if self.db_vip:
            vars['db_vip'] = self.db_vip
            vars['db_nic'] = self.db_nic
        return vars


class ClickhouseConfig(object):

    def __init__(self, config, bastion_host=None):
        self.node = Node(config).with_bastion(bastion_host)
        self.ch_password = config.ensure_get('ch_password')
        self.ch_port = config.get('ch_port', 9000)

    @classmethod
    def get_group(cls):
        return GROUP_CLICKHOUSE_NODE

    def get_nodes(self):
        return [self.node]

    def ansible_vars(self):
        vars = {
            "ch_password": self.ch_password,
            "ch_port": self.ch_port,
        }
        return vars


class RegistryConfig(object):

    def __init__(self, config, bastion_host=None):
        self.node = Node(config).with_bastion(bastion_host)

        self.port = config.get('port', '5000')
        self.root_dir = config.get('root_dir', '/opt/registry')

    @classmethod
    def get_group(cls):
        return GROUP_REGISTRY_NODE

    def get_nodes(self):
        return [self.node]

    def ansible_vars(self):
        return {
            "listen_port": self.port,
            "root_dir": self.root_dir,
        }


class OnecloudConfig(object):

    def __init__(self, config):
        self.controlplane_host = config.ensure_get('controlplane_host')
        self.controlplane_port = config.get('controlplane_port', '6443')
        self.as_host = config.get('as_host', None)
        self.as_host_on_vm = config.get('as_host_on_vm', None)

        self.registry_mirrors = config.get('registry_mirrors', [])
        self.insecure_registries = config.get('insecure_registries', [])
        self.skip_docker_config = config.get('skip_docker_config', False)

        self.node_ip = config.get('node_ip', None)
        self.onecloud_version = config.get(KEY_ONECLOUD_VERSION, None)
        self.high_availability = config.get('high_availability', False)
        self.high_availability_vip = None
        self.keepalived_version_tag = None
        self.keepalived_password = None
        default_keepalived_version_tag = 'v2.0.28' if is_using_k3s() else 'v2.0.25'
        if self.high_availability:
            self.high_availability_vip = self.controlplane_host
            self.keepalived_password = base64.b64encode(self.high_availability_vip.encode('ascii'))[0:8].decode()
            self.keepalived_router_id = int(self.high_availability_vip.replace('.', '')) % 255
            self.keepalived_version_tag = config.get('keepalived_version_tag', default_keepalived_version_tag)
        self.iso_install_mode = config.get('iso_install_mode', False)
        self.enable_eip_man = config.get('enable_eip_man', False)
        self.offline_deploy = config.get('offline_deploy', False) or os.environ.get('OFFLINE_DEPLOY') == 'true'
        self.enable_lbagent = config.get('enable_lbagent', False)

    def ansible_vars(self):
        vars = {
            'docker_registry_mirrors': self.registry_mirrors,
            'docker_insecure_registries': self.insecure_registries,
            'k8s_controlplane_host': self.controlplane_host,
            KEY_K3S_API_ENDPOINT: self.controlplane_host,
            'k8s_controlplane_port': self.controlplane_port,
            KEY_K3S_API_PORT: self.controlplane_port,
            'k8s_node_as_oc_host': self.as_host,
            'k8s_node_as_oc_host_on_vm': self.as_host_on_vm,
            'enable_eip_man': self.enable_eip_man,
            'offline_deploy': self.offline_deploy,
            'enable_lbagent': self.enable_lbagent,
        }
        if self.high_availability_vip:
            vars['high_availability_vip'] = self.high_availability_vip
            vars['keepalived_version_tag'] = self.keepalived_version_tag
            vars['keepalived_password'] = self.keepalived_password
            vars['keepalived_router_id'] = self.keepalived_router_id
        if self.onecloud_version:
            vars[KEY_ONECLOUD_VERSION] = self.onecloud_version
        if self.node_ip:
            vars['node_ip'] = self.node_ip
        if self.iso_install_mode:
            vars['iso_install_mode'] = True
        return vars


class PrimaryMasterConfig(OnecloudConfig):

    # All kinds of products
    PRODUCT_VERSION_FULL_STACK = "FullStack"
    # Cloud Management Platform product
    PRODUCT_VERSION_CMP = "CMP"
    # Private Cloud Edge on-premise product
    PRODUCT_VERSION_Edge = "Edge"

    PRODUCT_VERSIONS = [
        PRODUCT_VERSION_FULL_STACK,
        PRODUCT_VERSION_CMP,
        PRODUCT_VERSION_Edge,
    ]

    def __init__(self, config, bastion_host=None):
        super(PrimaryMasterConfig, self).__init__(config)

        self.node = Node(config).with_bastion(bastion_host)

        self.db_user = config.get('db_user', 'root')
        self.db_host = config.ensure_get('db_host')
        self.db_port = config.get('db_port', 3306)
        self.db_password = config.ensure_get('db_password')
        self.onecloud_version = config.ensure_get(KEY_ONECLOUD_VERSION)
        self.operator_version = config.get(KEY_OPERATOR_VERSION, self.onecloud_version)
        self.restore_mode = config.get('restore_mode', False)

        # set calico ip_autodetection_method only in primary master
        self.ip_autodetection_method = config.get('ip_autodetection_method', None)
        if not self.ip_autodetection_method:
            self.ip_autodetection_method = "'can-reach=%s'" % self.node.node_ip

        self.onecloud_user = config.get('onecloud_user', 'admin')
        self.onecloud_user_password = config.get('onecloud_user_password', 'admin@123')
        self.use_ee = config.get('use_ee', False)
        self.image_repository = config.get('image_repository', consts.REGISTRY_ALI_YUNION)
        if utils.is_below_v3_9(self.onecloud_version):
            self.image_repository = consts.REGISTRY_ALI_YUNIONIO
        self.enable_minio = config.get('enable_minio', False)
        self.offline_nodes = config.get('offline_nodes', '')
        self.pod_network_cidr = config.get('pod_network_cidr', '10.40.0.0/16')
        self.service_cidr = config.get('service_cidr', '10.96.0.0/12')
        self.service_dns_domain = config.get('service_dns_domain', 'cluster.local')
        self.product_version = self.get_product_version(config)
        self.user_dns = config.get(KEY_USER_DNS, [])

    def get_product_version(self, config):
        pv = config.get('product_version', self.PRODUCT_VERSION_FULL_STACK)
        if pv in self.PRODUCT_VERSIONS:
            return pv
        raise Exception("Unsupported product_version: %s" % pv)

    @classmethod
    def get_group(cls):
        return GROUP_PRIMARY_MASTER_NODE

    def ansible_vars(self):
        vars = super(PrimaryMasterConfig, self).ansible_vars()

        vars['db_host'] = self.db_host
        vars['db_port'] = self.db_port
        vars['db_user'] = self.db_user
        vars['db_password'] = self.db_password
        vars[KEY_ONECLOUD_VERSION] = self.onecloud_version
        vars[KEY_OPERATOR_VERSION] = self.operator_version
        vars['onecloud_user'] = self.onecloud_user
        vars['onecloud_user_password'] = self.onecloud_user_password
        vars['use_ee'] = self.use_ee
        vars['apiserver_advertise_address'] = self.node.node_ip
        vars[KEY_K3S_API_ENDPOINT] = self.node.node_ip
        vars['ip_autodetection_method'] = self.ip_autodetection_method
        vars['image_repository'] = self.image_repository
        vars['enable_minio'] = self.enable_minio
        vars['restore_mode'] = self.restore_mode
        vars['pod_network_cidr'] = self.pod_network_cidr
        vars['service_cidr'] = self.service_cidr
        vars['service_dns_domain'] = self.service_dns_domain
        if len(self.offline_nodes) > 0:
            vars['offline_nodes'] = ' '.join(self.offline_nodes)
        vars['product_version'] = self.product_version
        if self.user_dns:
            vars[KEY_USER_DNS] = self.user_dns
        return vars

    def get_nodes(self):
        return [self.node]


class OnecloudJointConfig(OnecloudConfig):

    def __init__(self, config):
        super(OnecloudJointConfig, self).__init__(config)

        self.as_controller = config.get('as_controller', None)
        self.join_token = config.get('join_token', None)
        self.join_cert_key = config.get('join_certificate_key', None)
        self.ntpd_server = config.get('ntpd_server', None)
        self.controlplane_ssh_port = config.get('controlplane_ssh_port', 22)

    def ansible_vars(self):
        vars = super(OnecloudJointConfig, self).ansible_vars()

        vars['k8s_node_as_oc_controller'] = self.as_controller
        vars['k8s_controlplane_ssh_port'] = self.controlplane_ssh_port
        if self.join_token:
            vars['k8s_join_token'] = self.join_token
        if self.join_cert_key:
            vars['k8s_join_certificate_key'] = self.join_cert_key
        # TODO: ntpd_server should define in all nodes config?
        if self.ntpd_server:
            vars['ntpd_server'] = self.ntpd_server
        return vars


def get_nodes(config, bastion_host=None):
    host_configs = config.ensure_get('hosts')
    nodes = []
    for host_config in host_configs:
        node = Node(Config(host_config)).with_bastion(bastion_host)
        nodes.append(node)
    return nodes


class MasterConfig(OnecloudJointConfig):

    def __init__(self, config, bastion_host=None):
        super(MasterConfig, self).__init__(config)
        if self.as_controller is None:
            self.as_controller = True
        self.nodes = get_nodes(config, bastion_host)
        self.primary_master_config = None

    def set_primary_master_config(self, primary_master_config):
        self.primary_master_config = primary_master_config

    def ansible_vars(self):
        vars = super(MasterConfig, self).ansible_vars()
        pc = self.primary_master_config
        vars['pod_network_cidr'] = pc.pod_network_cidr
        vars['service_cidr'] = pc.service_cidr
        vars['service_dns_domain'] = pc.service_dns_domain
        vars['image_repository'] = pc.image_repository
        return vars

    @classmethod
    def get_group(cls):
        return GROUP_MASTER_NODES

    def get_nodes(self):
        return self.nodes


class WorkerConfig(OnecloudJointConfig):

    def __init__(self, config, bastion_host=None):
        super(WorkerConfig, self).__init__(config)
        if self.as_host is None:
            self.as_host = True
        if self.as_host_on_vm is None:
            self.as_host_on_vm = False
        self.nodes = get_nodes(config, bastion_host)

    @classmethod
    def get_group(cls):
        return GROUP_WORKER_NODES

    def get_nodes(self):
        return self.nodes


class NodeConfig(object):

    def __init__(self, config, bastion_host=None):
        self.nodes = get_nodes(config, bastion_host)

    @classmethod
    def get_group(cls):
        return GROUP_NODES

    def get_nodes(self):
        return self.nodes

    def ansible_vars(self):
        return {}
