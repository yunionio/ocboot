#!/usr/bin/env python3
# encoding: utf-8

from __future__ import unicode_literals

from .ocboot import KEY_DISK_PATHS, KEY_ENABLE_CONTAINERD, KEY_HOST_NETWORKS, KEY_IMAGE_REPOSITORY, KEY_K8S_CONTROLPLANE_HOST, ClickhouseConfig, NodeConfig, Config, get_ansible_global_vars_by_cluster, KEY_PRIMARY_MASTER_NODE_IP
from .cmd import run_ansible_playbook
from .ansible import get_inventory_config
from .parser import help_d, inject_add_hostagent_options, inject_primary_node_options, inject_ssh_options
from .parser import inject_add_nodes_options
from .parser import inject_auto_backup_options
from .parser import inject_ssh_hosts_options
from . import utils
from . import ansible
from .cluster import construct_cluster
from .ocboot import WorkerConfig, Config
from .ocboot import get_ansible_global_vars
from .ocboot import KEY_ONECLOUD_VERSION
from .ssh import SSHClient
from .color import RB as Red


class BaseService(object):

    def __init__(self, subparsers, action, help_text):
        self.action = action
        parser = subparsers.add_parser(
            action, help=help_text)
        self.inject_options(parser)
        self._set_parser_defaults(parser)

    def inject_options(self, parser):
        pass

    def _set_parser_defaults(self, parser):
        parser.set_defaults(func=self.do_action)

    def do_action(self, args):
        pass


class Service(BaseService):

    def __init__(self, subparsers, action):
        super(Service, self).__init__(subparsers,
                                      action, "%s services of hosts" % action)

    def inject_options(self, parser):
        inject_ssh_hosts_options(parser)

    def do_action(self, args):
        config = NodesConfig(args.target_node_hosts,
                             args.ssh_user,
                             args.ssh_private_file,
                             args.ssh_port)
        config.run(self.action)


class NodesConfig(object):

    def __init__(self, target_nodes, ssh_user, ssh_private_file, ssh_port):
        target_nodes = list(set(target_nodes))
        conf = [{'hostname': target_node, 'user': ssh_user, 'port': ssh_port}
                for target_node in target_nodes]
        conf_dict = {
            'hosts': conf,
        }
        self.nodes_config = NodeConfig(Config(conf_dict))

    def run(self, action, vars=None):
        inventory_content = get_inventory_config(self.nodes_config)
        yaml_content = utils.to_yaml(inventory_content)
        filepath = '/tmp/cluster_%s_node_services_inventory.yml' % action
        with open(filepath, 'w') as f:
            f.write(yaml_content)
        # start run upgrade playbook
        run_ansible_playbook(
            filepath,
            './onecloud/%s-services.yml' % action,
            vars=vars,
        )


class PrimaryMasterService(BaseService):

    def __init__(self, subparsers, action):
        super().__init__(subparsers, action, f"{action} service of primary_master_host")

    def inject_options(self, parser):
        inject_primary_node_options(parser)
        inject_ssh_options(parser)

    def get_ansible_vars(self, args, cluster, primary_master_host):
        vars = get_ansible_global_vars(
            cluster.get_current_version(),
            cluster.is_using_k3s())
        vars[KEY_K8S_CONTROLPLANE_HOST] = primary_master_host
        return vars


    def do_action(self, args):
        cluster = construct_cluster(
            args.primary_master_host,
            args.ssh_user,
            args.ssh_private_file,
            args.ssh_port)
        vars = self.get_ansible_vars(args, cluster, args.primary_master_host)
        config = NodesConfig(
            [args.primary_master_host],
            args.ssh_user,
            args.ssh_private_file,
            args.ssh_port,
        )
        config.run(self.action, vars=vars)


class AddNodeBaseService(BaseService):

    def __init__(self, subparsers, action, help_text):
        super(AddNodeBaseService, self).__init__(subparsers, action, help_text)

    def inject_options(self, parser):
        inject_add_nodes_options(parser)


class AddNodeService(AddNodeBaseService):

    def __init__(self, subparsers, action, help_text):
        super(AddNodeService, self).__init__(subparsers, action, help_text)

    def inject_options(self, parser):
        super(AddNodeService, self).inject_options(parser)
        inject_add_hostagent_options(parser)

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
                                args.enable_host_on_vm)
        config.run()


class AddLBAgentService(AddNodeBaseService):

    def __init__(self, subparsers, action, help_text):
        super(AddLBAgentService, self).__init__(subparsers, action, help_text)

    def inject_options(self, parser):
        super(AddLBAgentService, self).inject_options(parser)

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
                                False, True)
        config.run()


class AddNodesConfig(object):

    def __init__(self, cluster, target_nodes, ssh_user, ssh_private_file,
                 controlplane_ssh_port, ssh_port,
                 enable_host_on_vm=False,
                 enable_lbagent=False,
                 **kwargs):
        target_nodes = list(set(target_nodes))
        target_hostnames = [node.get_hostname() for node in cluster.k8s_nodes]
        self.enable_containerd = kwargs.get('runtime') == 'containerd'

        for target_node in target_nodes:
            # check IP:
            node = cluster.find_node_by_ip_or_hostname(target_node)
            if node is not None:
                raise Exception(Red("Node %s(%s) already exists in cluster (By IP Check). " % (
                    node.get_hostname(), node.get_ip())))

            # check Hostname:
            cli = SSHClient(
                target_node,
                ssh_user,
                ssh_private_file,
                ssh_port
            )
            target_hostname = cli.get_hostname()
            if target_hostname in target_hostnames:
                raise Exception(Red(f"Node {target_hostname}[{target_node}] already exists in cluster (By Hostname Check). "))

        self.current_version = cluster.get_current_version()
        controlplane_host = cluster.get_cluster_controlplane_host()
        primary_master_node_ip = cluster.get_primary_master_node_ip()
        nodes_conf = [{'hostname': target_node, 'user': ssh_user,
                       'port': ssh_port} for target_node in target_nodes]
        as_host = True
        if enable_lbagent:
            # can't enable lbagent and host at same time
            as_host = False
        woker_config_dict = {
            KEY_ONECLOUD_VERSION: self.current_version,
            'hosts': nodes_conf,
            'controlplane_host': controlplane_host,
            'as_controller': False,
            'as_host': as_host,
            'as_host_on_vm': enable_host_on_vm,
            'controlplane_ssh_port': controlplane_ssh_port,
            'enable_lbagent': enable_lbagent,
            KEY_ENABLE_CONTAINERD: self.enable_containerd,
            KEY_HOST_NETWORKS: kwargs.get(KEY_HOST_NETWORKS, None),
            KEY_DISK_PATHS: kwargs.get(KEY_DISK_PATHS, None),
            KEY_PRIMARY_MASTER_NODE_IP: primary_master_node_ip,
        }
        (repo, is_insecure) = cluster.get_repository()
        if is_insecure:
            woker_config_dict['insecure_registries'] = [repo]
        self.worker_config = WorkerConfig(Config(woker_config_dict))

        self.image_repository = cluster.get_image_repository()
        self.is_using_k3s = cluster.is_using_k3s()

        self.offline_data_path = kwargs.get('offline_data_path', None)
        self.ip_type = kwargs.get('ip_type', None)
        
        utils.pr_green(f"Get current cluster: {controlplane_host}, primary_master_node_ip: {primary_master_node_ip}, version: {self.current_version}, is_using_k3s: {self.is_using_k3s}")

    def run(self):
        inventory_content = ansible.get_inventory_config(self.worker_config)
        yaml_content = utils.to_yaml(inventory_content)
        filepath = './cluster_add_node_inventory.yml'
        with open(filepath, 'w') as f:
            f.write(yaml_content)
        # start run upgrade playbook
        return_code = run_ansible_playbook(
            filepath,
            './onecloud/add-node.yml',
            vars=self.get_vars(),
        )

    def get_vars(self):
        vars = get_ansible_global_vars(self.current_version, self.is_using_k3s)
        vars[KEY_IMAGE_REPOSITORY] = self.image_repository

        if self.offline_data_path:
            vars['offline_data_path'] = self.offline_data_path
            vars['iso_install_mode'] = True
            vars['docker_insecure_registries'] = ['private-registry.onecloud:5000']
            vars[KEY_IMAGE_REPOSITORY] = 'private-registry.onecloud:5000/yunion'
        if self.ip_type:
            vars['ip_type'] = self.ip_type
        return vars


class AutoBackupConfig(NodesConfig):

    def __init__(self, target_nodes, ssh_user, ssh_private_file, ssh_port,
                 backup_path,
                 light_backup,
                 max_backups,
                 max_disck_percentage):
        target_nodes = list(set(target_nodes))
        conf = [{'hostname': target_node, 'user': ssh_user, 'port': ssh_port}
                for target_node in target_nodes]
        conf_dict = {
            'hosts': conf,
        }
        self.vars = {
            'backup_path': backup_path,
            'light_backup': 'true' if light_backup else 'false',
            'max_backups': max_backups,
            'max_disck_percentage': max_disck_percentage,
        }
        self.nodes_config = NodeConfig(Config(conf_dict))

    def run(self, action):
        inventory_content = get_inventory_config(self.nodes_config)
        yaml_content = utils.to_yaml(inventory_content)
        filepath = '/tmp/cluster_%s_node_services_inventory.yml' % action
        with open(filepath, 'w') as f:
            f.write(yaml_content)
        # start run upgrade playbook
        run_ansible_playbook(
            filepath,
            './onecloud/%s-services.yml' % action,
            vars=self.vars,
        )


class AutoBackupService(Service):

    def __init__(self, subparsers, action):
        super(AutoBackupService, self).__init__(subparsers, action)

    def inject_options(self, parser):
        super(AutoBackupService, self).inject_options(parser)
        inject_auto_backup_options(parser)

    def do_action(self, args):
        config = AutoBackupConfig(args.target_node_hosts,
                                  args.ssh_user,
                                  args.ssh_private_file,
                                  args.ssh_port,
                                  args.backup_path,
                                  args.light,
                                  args.max_backups,
                                  args.max_disk_percentage,
                                  )
        config.run(self.action)


class ClickhouseServiceConfig(object):

    def __init__(self, cluster, primary_host,
                 ch_pwd, ch_port, offline_data_path,
                 ssh_user='root', ssh_port=22):
        cfg = {
            'host': primary_host,
            'user': ssh_user,
            'port': ssh_port,
            'ch_password': ch_pwd,
            'ch_port': ch_port,
        }
        self.cluster = cluster
        self.primary_host = primary_host
        self.ch_config = ClickhouseConfig(Config(cfg))
        self.offline_data_path = offline_data_path

    def run(self):
        inventory_content = ansible.get_inventory_config(self.ch_config)
        yaml_content = utils.to_yaml(inventory_content)
        filepath = './cluster_clickhouse_inventory.yml'
        with open(filepath, 'w') as f:
            f.write(yaml_content)
        # start run upgrade playbook
        return_code = run_ansible_playbook(
            filepath,
            './onecloud/clickhouse-services.yml',
            vars=self.get_vars(),
        )

    def get_vars(self):
        vars = self.ch_config.ansible_vars()
        vars['offline_data_path'] = self.offline_data_path
        vars[KEY_K8S_CONTROLPLANE_HOST] = self.primary_host
        global_vars = get_ansible_global_vars_by_cluster(self.cluster)
        vars.update(global_vars)
        return vars


class ClickhouseService(BaseService):

    def __init__(self, subparsers, action):
        super().__init__(subparsers, action, 'deploy clickhouse')

    def inject_options(self, parser):
        inject_primary_node_options(parser)
        inject_ssh_options(parser)
        parser.add_argument("offline_data_path",
                            metavar='OFFLINE_DATA_PATH',
                            help="offline ISO mount point, e.g., /mnt")
        parser.add_argument("--ch-password", dest="ch_password",
                            default="your-clickhouse-password",
                            help=help_d("clickhouse password"))
        parser.add_argument("--ch-port", dest="ch_port",
                            default=9000, type=int,
                            help=help_d("clickhouse port"))

    def do_action(self, args):
        # config = 
        cluster = construct_cluster(
            args.primary_master_host,
            args.ssh_user,
            args.ssh_private_file,
            args.ssh_port)
        print(f'found cluster {cluster.get_current_version()}')
        config = ClickhouseServiceConfig(cluster,
            args.primary_master_host, args.ch_password, args.ch_port, args.offline_data_path, args.ssh_user, args.ssh_port)
        config.run()
