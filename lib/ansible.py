#!/usr/bin/env python3
# encoding: utf-8

from __future__ import unicode_literals

import yaml


def get_inventory_config(*configs):
    children = {}
    for config in configs:
        if not config:
            continue
        group = config.get_group()
        children[group] = get_inventory_child_config(config)
    return {
        'all': {
            'children': children,
        }
    }


def get_inventory_child_config(config):
    ret = {
        'hosts': {},
        'vars': config.ansible_vars(),
    }

    nodes = config.get_nodes()
    for n in nodes:
        hosts = ret['hosts']
        hosts[n.get_host()] = n.ansible_host_vars()
    return ret


def parse_inventory_config(inventory_file: str):
    with open(inventory_file, 'r') as f:
        inventory_config = yaml.load(f, Loader=yaml.FullLoader)
    if 'all' not in inventory_config:
        raise ValueError("Invalid inventory config, missing all")
    if 'children' not in inventory_config['all']:
        raise ValueError("Invalid inventory config, missing all.children")
    if 'primary_master_node' not in inventory_config['all']['children']:
        raise ValueError("Invalid inventory config, missing all.children.primary_master_node")
    return inventory_config['all']['children']


def get_primary_master_node(inventory_config):
    from .ocboot import Config
    config = Config(inventory_config['primary_master_node']['vars'])
    print(config)
    return config


class AnsibleBastionHost(object):

    def __init__(self, host, user='root'):
        self.host = host
        self.user = user

    def to_option(self):
        val = '-o "ProxyCommand ssh -o StrictHostKeyChecking=no' \
            ' -o UserKnownHostsFile=/dev/null' \
            ' -W %h:%p -q {}@{}"'.format(self.user, self.host)
        return val
