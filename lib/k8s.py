from .utils import parse_k8s_time


L_K8S_ARCH = 'kubernetes.io/arch'
L_K8S_MASTER = 'node-role.kubernetes.io/master'
L_ONECLOUD_CONTROLLER = 'onecloud.yunion.io/controller'
L_ONECLOUD_HOST = 'onecloud.yunion.io/host'


class Resource(object):

    def __init__(self, obj):
        self.obj = obj

    def get(self, *keys):
        obj = self.obj
        for key in keys:
            obj = obj.get(key, None)
            if not obj:
                return None
        return obj

    def get_spec(self):
        return self.get('spec')

    def get_metadata(self):
        return self.get('metadata')

    def get_status(self):
        return self.get('status')

    def get_name(self):
        return self.get('metadata', 'name')

    def get_labels(self):
        return self.get('metadata', 'labels')

    def get_annotations(self):
        return self.get('metadata', 'annotations')

    def get_label(self, key):
        return self.get_labels().get(key, None)

    def creationTimestamp(self):
        create_str = self.get('metadata', 'creationTimestamp')
        return parse_k8s_time(create_str)


class Node(object):

    def __init__(self, obj):
        self.node = Resource(obj)

    def get_addresses(self):
        addrs = self.node.get('status', 'addresses')
        return addrs

    def get_address(self, a_type):
        addrs = self.get_addresses()
        for addr in addrs:
            if addr.get('type') == a_type:
                return addr.get('address')
        return None

    def get_ip(self):
        return self.get_address('InternalIP')

    def get_hostname(self):
        return self.get_address('Hostname')

    def is_master(self):
        return L_K8S_MASTER in self.node.get_labels()

    def is_onecloud_role(self, role):
        val = self.node.get_label(role)
        if val == 'enable':
            return True
        return False

    def is_onecloud_controller(self):
        return self.is_onecloud_role(L_ONECLOUD_CONTROLLER)

    def is_onecloud_host(self):
        return self.is_onecloud_role(L_ONECLOUD_HOST)

    def creationTimestamp(self):
        return self.node.creationTimestamp()
