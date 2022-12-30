# encoding: utf-8
from __future__ import unicode_literals

from .ocboot import NodeConfig, Config
from .cmd import run_ansible_playbook
from .ansible import get_inventory_config
from .parser import inject_ssh_hosts_options
from . import utils


class Service(object):

    def __init__(self, subparsers, action):
        self.action = action

        parser = subparsers.add_parser(
            action, help="%s services of hosts" % action)

        inject_ssh_hosts_options(parser)
        parser.set_defaults(func=self.do_action_services)


    def do_action_services(self, args):
        config = NodesConfig(args.target_node_hosts,
                             args.ssh_user,
                             args.ssh_private_file,
                             args.ssh_port)
        config.run(self.action)


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

