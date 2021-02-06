# encoding: utf-8
from __future__ import unicode_literals


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


class AnsibleBastionHost(object):

    def __init__(self, host, user='root'):
        self.host = host
        self.user = user

    def to_option(self):
        val = '-o "ProxyCommand ssh -o StrictHostKeyChecking=no' \
            ' -o UserKnownHostsFile=/dev/null' \
            ' -W %h:%p -q {}@{}"'.format(self.user, self.host)
        return val
