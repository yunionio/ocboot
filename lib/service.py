# encoding: utf-8
from __future__ import unicode_literals

from .ocboot import NodeConfig, Config
from .cmd import run_ansible_playbook
from .ansible import get_inventory_config
from .parser import inject_add_hostagent_options, inject_ssh_hosts_options, inject_add_nodes_options
from . import utils
from . import ansible
from .cluster import construct_cluster
from .ocboot import WorkerConfig, Config
from .ocboot import get_ansible_global_vars


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
        super(Service, self).__init__(subparsers, action, "%s services of hosts" % action)

    def inject_options(self, parser):
        inject_ssh_hosts_options(parser)

    def do_action(self, args):
        config = NodesConfig(args.target_node_hosts,
                             args.ssh_user,
                             args.ssh_private_file,
                             args.ssh_port)
        config.run(self.action)


class RoutineInspectionService(Service):
    def __init__(self, subparsers, action, *args):
        super(Service, self).__init__(subparsers, action, "%s services of hosts" % action)

    def inject_options(self, parser):
        pass # inject_ssh_hosts_options(parser)

    def do_action(self, args):
        pass
        # import os
        # os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
        # config = NodesConfig(['10.127.100.212'], 'root', '/root/.ssh/id_rsa.pub', 22)
        # config.run(self.action)

class NodesConfig(object):

    def __init__(self, target_nodes, ssh_user, ssh_private_file, ssh_port):
        target_nodes = list(set(target_nodes))
        conf = [{'hostname': target_node, 'user': ssh_user, 'port': ssh_port} for target_node in target_nodes]
        conf_dict = {
            'hosts': conf,
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
        )


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
                 enable_lbagent=False):
        target_nodes = list(set(target_nodes))
        for target_node in target_nodes:
            node = cluster.find_node_by_ip_or_hostname(target_node)
            if node is not None:
                raise Exception("Node %s(%s) already exists in cluster" % (
                    node.get_hostname(), node.get_ip()))
        self.current_version = cluster.get_current_version()
        controlplane_host = cluster.get_primary_master_node_ip()
        nodes_conf = [{'hostname': target_node, 'user': ssh_user, 'port': ssh_port} for target_node in target_nodes]
        as_host = True
        if enable_lbagent:
            # can't enable lbagent and host at same time
            as_host = False
        woker_config_dict = {
            'hosts': nodes_conf,
            'controlplane_host': controlplane_host,
            'as_controller': False,
            'as_host': as_host,
            'as_host_on_vm': enable_host_on_vm,
            'controlplane_ssh_port': controlplane_ssh_port,
            'enable_lbagent': enable_lbagent
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
