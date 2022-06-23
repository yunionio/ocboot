# encoding: utf-8
import unittest
import inspect

from lib import cluster
from lib.ocboot import \
    GROUP_PRIMARY_MASTER_NODE, GROUP_MASTER_NODES, GROUP_WORKER_NODES


class fakeNode(object):

    def __init__(self, hostname, ip):
        self.hostname = hostname
        self.ip = ip

    def get_hostname(self):
        return self.hostname

    def get_ip(self):
        return self.ip


class TestAnsibleInventory(unittest.TestCase):

    def new_primary_master_node(self, hostname, ip, port=22):
        return cluster.AnsiblePrimaryMasterHost(fakeNode(hostname, ip), port=port)

    def new_master_node(self, hostname, ip, port=22):
        return cluster.AnsibleMasterHost(fakeNode(hostname, ip), port=port)

    def new_worker_node(self, hostname, ip, port=22):
        return cluster.AnsibleWorkerHost(fakeNode(hostname, ip), port=port)

    def test_generate_content(self):
        p_m_host = self.new_primary_master_node('p1', '192.168.0.1', port=34)
        m_host1 = self.new_master_node('m1', '192.168.0.2', port=34)
        m_host2 = self.new_master_node('m2', '192.168.0.3', port=34)
        w_host1 = self.new_worker_node('w1', '192.168.0.4', port=36)
        w_host2 = self.new_worker_node('w2', '192.168.0.5', port=36)

        inventory = cluster.AnsibleInventory()
        inventory.add(p_m_host, m_host1, m_host2, w_host1, w_host2)

        content = inventory.generate_content()
        self.maxDiff = None
        self.assertEqual(content, inspect.cleandoc("""[all]
        p1 ansible_ssh_host=192.168.0.1 ansible_host=192.168.0.1 ansible_ssh_user=root ansible_user=root ansible_ssh_port=34 ansible_port=34
        m1 ansible_ssh_host=192.168.0.2 ansible_host=192.168.0.2 ansible_ssh_user=root ansible_user=root ansible_ssh_port=34 ansible_port=34
        m2 ansible_ssh_host=192.168.0.3 ansible_host=192.168.0.3 ansible_ssh_user=root ansible_user=root ansible_ssh_port=34 ansible_port=34
        w1 ansible_ssh_host=192.168.0.4 ansible_host=192.168.0.4 ansible_ssh_user=root ansible_user=root ansible_ssh_port=36 ansible_port=36
        w2 ansible_ssh_host=192.168.0.5 ansible_host=192.168.0.5 ansible_ssh_user=root ansible_user=root ansible_ssh_port=36 ansible_port=36
        [primary_master_node]
        p1
        [master_nodes]
        m1
        m2
        [worker_nodes]
        w1
        w2"""))
