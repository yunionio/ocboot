# encoding: utf-8
from __future__ import unicode_literals

import yaml

from . import ansible
from . import utils


GROUP_MARIADB_NODE = "mariadb_node"
GROUP_REGISTRY_NODE="registry_node"
GROUP_PRIMARY_MASTER_NODE = "primary_master_node"
GROUP_MASTER_NODES = "master_nodes"
GROUP_WORKER_NODES = "worker_nodes"
GROUP_LONGHORN_NODES = "longhorn_nodes"
GROUP_REBOOT_NODES = "reboot_nodes"


def load_config(config_file):
    with open(config_file) as f:
        config = Config(yaml.load(f))
        return OcbootConfig(config)


class OcbootConfig(object):

    def __init__(self, config):
        self.config = config

        self.bastion_host = self.load_bastion_host(config)

        self.mariadb_config = self._fetch_conf(MariadbConfig)
        self.registry_config = self._fetch_conf(RegistryConfig)
        self.primary_master_config = self._fetch_conf(PrimaryMasterConfig)
        self.master_config = self._fetch_conf(MasterConfig)
        self.worker_config = self._fetch_conf(WorkerConfig)
        self.longhorn_config = self._fetch_conf(LonghornConfig)
        self.reboot_config = self._fetch_conf(RebootConfig)

    def load_bastion_host(self, config):
        bastion_config = config.get('bastion_host', None)
        if not bastion_config:
            return None
        bastion_config = Config(bastion_config)
        host = bastion_config.ensure_get('host', 'hostname')
        user = bastion_config.get('user', 'root')
        return ansible.AnsibleBastionHost(host, user)

    def _fetch_conf(self, config_cls):
        group = config_cls.get_group()
        group_config = self.config.get(group, None)
        if not group_config:
            return None
        return config_cls(Config(group_config), self.bastion_host)

    def get_onecloud_version(self):
        return self.primary_master_config.onecloud_version

    def ansible_global_vars(self):
        return {
            "onecloud_major_version": utils.get_major_version(
                self.get_onecloud_version()),
        }

    def get_ansible_inventory(self):
        return ansible.get_inventory_config(
            self.mariadb_config,
            self.registry_config,
            self.primary_master_config,
            self.master_config,
            self.worker_config,
            self.longhorn_config,
            self.reboot_config)

    def generate_inventory_file(self):
        content = self.get_ansible_inventory()
        yaml_content = utils.to_yaml(content)
        filepath = '/tmp/host_inventory.yml'
        with open(filepath, 'w') as f:
            f.write(yaml_content)
        return filepath

    def get_login_info(self):
	    # TODO 验证接口、参数是否 OK
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
        self.host = config.ensure_get('host', 'hostname')
        self.use_local = config.get('user_local', False)
        self.user = config.get('user', 'root')
        self.port = config.get('port', 22)
        self.host_networks = config.get('host_networks', None)
        self.node_ip = config.get('node_ip', None)
        if not self.node_ip:
            self.node_ip = self.host
        self.bastion_host = None

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
        }


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

        self.registry_mirrors = config.get('registry_mirrors', [])
        self.insecure_registries = config.get('insecure_registries', [])
        self.skip_docker_config = config.get('skip_docker_config', False)

        self.high_availability = config.get('high_availability', False)
        self.high_availability_vip = None
        if self.high_availability:
            self.high_availability_vip = self.controlplane_host

        self.keepalived_version_tag = config.get('keepalived_version_tag', None)

    def ansible_vars(self):
        vars = {
            'docker_registry_mirrors': self.registry_mirrors,
            'docker_insecure_registries': self.insecure_registries,
            'k8s_controlplane_host': self.controlplane_host,
            'k8s_controlplane_port': self.controlplane_port,
            'k8s_node_as_oc_host': self.as_host,
        }
        if self.high_availability_vip:
            vars['high_availability_vip'] = self.high_availability_vip
        if self.keepalived_version_tag:
            vars['keepalived_version_tag'] = self.keepalived_version_tag
        return vars


class PrimaryMasterConfig(OnecloudConfig):

    def __init__(self, config, bastion_host=None):
        super(PrimaryMasterConfig, self).__init__(config)

        self.node = Node(config).with_bastion(bastion_host)

        self.db_user = config.get('db_user', 'root')
        self.db_host = config.ensure_get('db_host')
        self.db_password = config.ensure_get('db_password')
        self.onecloud_version = config.ensure_get('onecloud_version')
        self.operator_version = config.get('operator_version', self.onecloud_version)

        # set calico ip_autodetection_method only in primary master
        self.ip_autodetection_method = config.get('ip_autodetection_method', None)
        if not self.ip_autodetection_method:
            self.ip_autodetection_method = "'can-reach=%s'" % self.node.node_ip

        self.onecloud_user = config.get('onecloud_user', 'admin')
        self.onecloud_user_password = config.get('onecloud_user_password', 'admin@123')
        self.use_ee = config.get('use_ee', False)
        self.image_repository = config.get('image_repository', 'registry.cn-beijing.aliyuncs.com/yunionio')

    @classmethod
    def get_group(cls):
        return GROUP_PRIMARY_MASTER_NODE

    def ansible_vars(self):
        vars = super(PrimaryMasterConfig, self).ansible_vars()

        vars['db_host'] = self.db_host
        vars['db_user'] = self.db_user
        vars['db_password'] = self.db_password
        vars['onecloud_version'] = self.onecloud_version
        vars['operator_version'] = self.operator_version
        vars['onecloud_user'] = self.onecloud_user
        vars['onecloud_user_password'] = self.onecloud_user_password
        vars['use_ee'] = self.use_ee
        vars['apiserver_advertise_address'] = self.node.node_ip
        vars['ip_autodetection_method'] = self.ip_autodetection_method
        vars['image_repository'] = self.image_repository

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

    def ansible_vars(self):
        vars = super(OnecloudJointConfig, self).ansible_vars()

        vars['k8s_node_as_oc_controller'] = self.as_controller
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
        self.nodes = get_nodes(config, bastion_host)

    @classmethod
    def get_group(cls):
        return GROUP_WORKER_NODES

    def get_nodes(self):
        return self.nodes


class LonghornConfig(object):

    def __init__(self, config, bastion_host=None):
        self.nodes = get_nodes(config, bastion_host)
        self.k8s_host_node_ips = config.get('k8s_host_node_ips', None)
        self.longhorn_image_repository = config.get('longhorn_image_repository', None)
        self.longhorn_data_path = config.get('longhorn_data_path', None)
        self.longhorn_over_provisioning_percentage = config.get('longhorn_over_provisioning_percentage', None)
        self.high_availability_controlplane_as_host = config.get('high_availability_controlplane_as_host', None)

    @classmethod
    def get_group(cls):
        return GROUP_LONGHORN_NODES

    def ansible_vars(self):
        vars = {}
        if self.k8s_host_node_ips:
            vars['k8s_host_node_ips'] = self.k8s_host_node_ips
        if self.longhorn_image_repository:
            vars['longhorn_image_repository'] = self.longhorn_image_repository
        if self.longhorn_data_path:
            vars['longhorn_data_path'] = self.longhorn_data_path
        if self.longhorn_over_provisioning_percentage:
            vars['longhorn_over_provisioning_percentage'] = self.longhorn_over_provisioning_percentage
        if self.high_availability_controlplane_as_host:
            vars['high_availability_controlplane_as_host'] = self.high_availability_controlplane_as_host

    def get_nodes(self):
        return self.nodes


class RebootConfig(object):

    def __init__(self, config, bastion_host=None):
        self.nodes = get_nodes(config, bastion_host)
        self.availability_controlplane_as_host = config.get('availability_controlplane_as_host', None)

    @classmethod
    def get_group(cls):
        return GROUP_REBOOT_NODES

    def ansible_vars(self):
        vars = {}
        if self.availability_controlplane_as_host:
            vars['availability_controlplane_as_host'] = self.availability_controlplane_as_host
        return vars

    def get_nodes(self):
        return self.nodes
