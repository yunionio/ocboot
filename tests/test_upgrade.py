import unittest
import inspect

from lib import upgrade
from lib.ansible import PRIMARY_MASTER_NODE, MASTER_NODES, WORKER_NODES


class fakeAnsibleHost(object):

    def __init__(self, hostname, ip, role):
        self.hostname = hostname
        self.ip = ip
        self.role = role

    def get_hostname(self):
        return self.hostname

    def get_ip(self):
        return self.ip

    def get_role(self):
        return self.role

    def get_content(self):
        return '%s ansible_host=%s' % (
            self.hostname,
            self.ip)

class TestAnsibleInventory(unittest.TestCase):

    def new_primary_master_node(self, hostname, ip):
        return fakeAnsibleHost(hostname, ip, PRIMARY_MASTER_NODE)

    def new_master_node(self, hostname, ip):
        return fakeAnsibleHost(hostname, ip, MASTER_NODES)

    def new_worker_node(self, hostname, ip):
        return fakeAnsibleHost(hostname, ip, WORKER_NODES)

    def test_generate_content(self):
        p_m_host = self.new_primary_master_node('p1', '192.168.0.1')
        m_host1 = self.new_master_node('m1', '192.168.0.2')
        m_host2 = self.new_master_node('m2', '192.168.0.3')
        w_host1 = self.new_worker_node('w1', '192.168.0.4')
        w_host2 = self.new_worker_node('w2', '192.168.0.5')

        inventory = upgrade.AnsibleInventory()
        inventory.add(p_m_host, m_host1, m_host2, w_host1, w_host2)

        content = inventory.generate_content()
        self.assertEqual(content, inspect.cleandoc("""[all]
        p1 ansible_host=192.168.0.1
        m1 ansible_host=192.168.0.2
        m2 ansible_host=192.168.0.3
        w1 ansible_host=192.168.0.4
        w2 ansible_host=192.168.0.5
        [primary_master_node]
        p1
        [master_nodes]
        m1
        m2
        [worker_nodes]
        w1
        w2"""))
