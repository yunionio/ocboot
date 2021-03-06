# encoding: utf-8
from __future__ import unicode_literals

import yaml


MARIADB_NODE = "mariadb_node"
REGISTRY_NODE="registry_node"
PRIMARY_MASTER_NODE = "primary_master_node"
MASTER_NODES = "master_nodes"
WORKER_NODES = "worker_nodes"
LONGHORN_NODES = "longhorn_nodes"
REBOOT_NODES = "reboot_nodes"

def inventory_content_by_group(nodes, group):
    if nodes is None:
        return None
    ret = ["[%s]" % group]
    if not isinstance(nodes, list):
        ret.append("%s" % nodes)
    else:
        for n in nodes:
            ret.append("%s" % n)
    return '\n'.join(ret)


class Node(object):

    def __init__(self, host, use_local=False, user=None, host_networks=None):
        self.host = host
        self.use_local = use_local
        self.user = user
        self.host_networks = host_networks

    def __str__(self):
        ret = self.host
        if self.host != "127.0.0.1":
            ret = "%s node_ip=%s ip_autodetection_method='can-reach=%s' " % (ret, ret, ret)
        if self.use_local:
            ret = "%s ansible_connection=local" % ret
        if self.user is not None:
            ret = "%s ansible_user=%s" % (ret, self.user)
        if self.host_networks is not None:
            ret = "%s host_networks=%s" % (ret, self.host_networks)
        return ret

def new_inventory_content(db_node=None, reg_node=None, primary_master_node=None, master_nodes=None, worker_nodes=None, longhorn_nodes=None, reboot_nodes=None):
    ret = []
    groups = [
        (MARIADB_NODE, db_node),
        (REGISTRY_NODE, reg_node),
        (PRIMARY_MASTER_NODE, primary_master_node),
        (MASTER_NODES, master_nodes),
        (WORKER_NODES, worker_nodes),
        (LONGHORN_NODES, longhorn_nodes),
        (REBOOT_NODES, reboot_nodes),
    ]
    for k, v in groups:
        g_ret = inventory_content_by_group(v, k)
        if g_ret is None:
            continue
        ret.append(inventory_content_by_group(v, k))
    return "\n".join(ret)


def new_site_item(hosts, role, vars={}):
    data = {
        "hosts": hosts,
        "vars": vars,
        "roles": [role],
    }
    return data


def new_site_item_db(user, passwd, port=3306):
    vars = {
        "db_user": user,
        "db_password": passwd,
    }
    if port:
        vars["db_port"] = port
    return new_site_item(
        MARIADB_NODE,
        "mariadb",
        vars)


def new_site_item_registry(port="5000", root_dir="/opt/registry"):
    return new_site_item(
        REGISTRY_NODE,
        "registry",
        {
            "listen_port": port,
            "root_dir": root_dir,
         })


def new_site_item_primary_master(
    db_host, db_user, db_password,
    controlplane_host,
    controlplane_port="6443",
    as_host=True,
    registry_mirrors=[],
    insecure_regs=[],
    image_repository=None,
    onecloud_version=None,  # instead of 'latest' for clarity
    operator_version=None,  # instead of 'latest' for clarity
    skip_docker_config=False,
    onecloud_user="admin",
    onecloud_user_password="admin@123",
	apiserver_advertise_address="",
    node_ip="",
    host_networks="",
    ip_autodetection_method="",
    db_port="",
    high_availability_vip="",
    keepalived_version_tag="",
    use_ee=False,
):
    vars = {
        "db_host": db_host,
        "db_user": db_user,
        "db_password": db_password,
        "docker_registry_mirrors": registry_mirrors,
        "docker_insecure_registries": insecure_regs,
        "k8s_controlplane_host": controlplane_host,
        "k8s_controlplane_port": controlplane_port,
        "k8s_node_as_oc_host": as_host,
        "onecloud_user": onecloud_user,
        "onecloud_user_password": onecloud_user_password,
		"apiserver_advertise_address": apiserver_advertise_address,
        "node_ip": node_ip,
    }
    if image_repository is not None:
        vars["image_repository"] = image_repository
    if skip_docker_config:
        vars["skip_docker_config"] = True
    if host_networks:
        vars["host_networks"] = host_networks
    if ip_autodetection_method:
        vars["ip_autodetection_method"] = ip_autodetection_method
    if db_port:
        vars['db_port'] = db_port
    if high_availability_vip:
        vars["high_availability_vip"] = high_availability_vip
    if keepalived_version_tag:
        vars['keepalived_version_tag'] = keepalived_version_tag
    if onecloud_version is not None:
        vars["onecloud_version"] = onecloud_version
    if operator_version is not None:
        vars["operator_version"] = operator_version
    if use_ee:
        vars["use_ee"] = True

    return new_site_item(
        PRIMARY_MASTER_NODE,
        "primary-master-node",
        vars)


def new_site_item_master(vars):
    return new_site_item(
        MASTER_NODES,
        "master-node",
        vars)


def new_site_item_worker(vars):
    return new_site_item(
        WORKER_NODES,
        "worker-node",
        vars)

def new_site_item_longhorn(vars):
    return new_site_item(
        LONGHORN_NODES,
        "longhorn-node",
        vars)

def new_site_item_reboot(vars):
    return new_site_item(
        REBOOT_NODES,
        "reboot-node",
        vars)

def to_yaml(data):
    return yaml.dump(data)


def load_config(config_file):
    with open(config_file) as f:
        config = yaml.load(f)
        return PlaybookConfig(config)

class PlaybookConfig(object):

    def __init__(self, config):
        self.mariadb_config = None
        self.mariadb_node = None
        self.registry_config = None
        self.registry_node = None
        self.primary_master_config = None
        self.primary_master_node = None
        self.master_config = None
        self.master_nodes = []
        self.worker_config = None
        self.worker_nodes = []
        self.longhorn_config = None
        self.longhorn_nodes = []

        self.reboot_config = None
        self.reboot_nodes = []
        self._fetch_conf(config, "mariadb_node", self.fetch_mariadb_config)
        self._fetch_conf(config, "registry_node", self.fetch_registry_config)
        self._fetch_conf(config, "primary_master_node", self.fetch_primary_master_config)
        self._fetch_conf(config, "master_nodes", self.fetch_master_config)
        self._fetch_conf(config, "worker_nodes", self.fetch_worker_config)
        self._fetch_conf(config, "longhorn_nodes", self.fetch_longhorn_config)
        self._fetch_conf(config, "reboot_nodes", self.fetch_reboot_config)

    def _fetch_conf(self, config, key, fetch_f):
        if config.get(key, None) is not None:
            fetch_f(config[key])

    def get_val(self, config, key, ensure=False):
        val = config.get(key, None)
        if ensure and val is None:
            raise Exception("%s not found in config %s" % (key, config))
        return val

    def get_default_val(self, config, key, default):
        ret = self.get_val(config, key)
        if ret is None:
            ret = default
        return ret

    def get_node(self, config):
        host_networks = self.get_val(config, "host_networks")
        host = self.get_val(config, "hostname")
        if host is None:
            host = self.get_val(config, "host")
        use_local = self.get_val(config, "use_local", False)
        if host is None and not use_local:
            raise Exception("'host' or 'use_local' not found in config: %s" % config)
        if use_local:
            host = "127.0.0.1"
        user = self.get_val(config, "user")
        return Node(host, use_local, user, host_networks=host_networks)

    def fetch_mariadb_config(self, config):
        self.mariadb_node = self.get_node(config)
        user = self.get_val(config, "db_user")
        if user is None:
            user = "root"
        password = self.get_val(config, "db_password", True)
        port = self.get_val(config, "db_port")
        self.mariadb_config = new_site_item_db(user, password, port)

    def fetch_registry_config(self, config):
        self.registry_node = self.get_node(config)
        self.registry_config = new_site_item_registry()

    def fetch_primary_master_config(self, config):
        self.primary_master_node = self.get_node(config)
        db_user = self.get_val(config, "db_user")
        if db_user is None:
            db_user = "root"
        db_passwd = self.get_val(config, "db_password", True)
        db_host = self.get_val(config, "db_host", True)
        db_port = self.get_val(config, "db_port", False)
        chost = self.get_val(config, "controlplane_host", True)

        try:
            node_ip = self.get_val(config, "node_ip", True)
        except Exception:
            node_ip = self.primary_master_node.host

        cport = self.get_default_val(config, "controlplane_port", "6443")
        as_host = self.get_val(config, "as_host", False)
        registry_mirrors = self.get_default_val(config, "registry_mirrors", [])
        insecure_regs = self.get_default_val(config, "insecure_registries", [])
        image_repo = self.get_val(config, "image_repository")
        skip_docker_config = self.get_default_val(config, "skip_docker_config", False)
        onecloud_version = self.get_default_val(config, "onecloud_version", "latest")
        host_networks = self.get_val(config, "host_networks", False)
        ip_autodetection_method = self.get_val(config, "ip_autodetection_method", False)
        high_availability_vip = None
        if self.get_val(config, "high_availability"):
            high_availability_vip = chost
        keepalived_version_tag = self.get_val(config, 'keepalived_version_tag')
        onecloud_user = self.get_default_val(config, "onecloud_user", "admin")
        onecloud_user_password = self.get_default_val(config, "onecloud_user_password", "admin@123")
        self.primary_master_config = new_site_item_primary_master(
            db_host, db_user, db_passwd,
            chost, cport, as_host,
            registry_mirrors=registry_mirrors,
            insecure_regs=insecure_regs,
            image_repository=image_repo,
            skip_docker_config=skip_docker_config,
            onecloud_user=onecloud_user,
            onecloud_user_password=onecloud_user_password,
            onecloud_version=onecloud_version,
			apiserver_advertise_address=node_ip,
            node_ip=node_ip,
            host_networks=host_networks,
            ip_autodetection_method=ip_autodetection_method,
            db_port=db_port,
            high_availability_vip=high_availability_vip,
            keepalived_version_tag=keepalived_version_tag,
            use_ee=self.get_val(config, "use_ee", False)
        )

    def get_nodes(self, config):
        hosts = self.get_val(config, "hosts", True)
        nodes = []
        for h in hosts:
            n = self.get_node(h)
            nodes.append(n)
        return nodes

    def fetch_join_vars(self, config):
        chost = self.get_val(config, "controlplane_host", True)
        cport = self.get_default_val(config, "controlplane_port", "6443")
        as_controller = self.get_val(config, "as_controller", False)
        as_host = self.get_val(config, "as_host", False)
        registry_mirrors = self.get_default_val(config, "registry_mirrors", [])
        insecure_regs = self.get_default_val(config, "insecure_registries", [])
        join_token = self.get_val(config, "join_token", None)
        join_cert_key = self.get_val(config, "join_certificate_key", None)
        skip_docker_config = self.get_default_val(config, "skip_docker_config", False)
        node_ip = self.get_default_val(config, "node_ip", False)
        host_networks = self.get_val(config, "host_networks", False)
        high_availability_vip = None
        ntpd_server = self.get_val(config, "ntpd_server", None)
        if self.get_val(config, "high_availability"):
            high_availability_vip = chost
        keepalived_version_tag = self.get_val(config, 'keepalived_version_tag')
        vars = {
            "docker_registry_mirrors": registry_mirrors,
            "docker_insecure_registries": insecure_regs,
            "k8s_controlplane_port": cport,
            "k8s_node_as_oc_controller": as_controller,
            "k8s_node_as_oc_host": as_host,
        }
        if chost is not None:
            vars["k8s_controlplane_host"] = chost
        if join_token is not None:
            vars["k8s_join_token"] = join_token
        if join_cert_key is not None:
            vars["k8s_join_certificate_key"] = join_cert_key
        if skip_docker_config:
            vars["skip_docker_config"] = True
        if node_ip:
            vars["node_ip"] = node_ip
            vars["apiserver_advertise_address"] = node_ip
        if host_networks:
            vars['host_networks'] = host_networks
        if high_availability_vip:
            vars['high_availability_vip'] = high_availability_vip
        if keepalived_version_tag:
            vars['keepalived_version_tag'] = keepalived_version_tag
        if ntpd_server:
            vars['ntpd_server'] = ntpd_server
        return vars

    def fetch_longhorn_vars(self, config):
        # chost = self.get_val(config, "controlplane_host", True)
        keys = [
            'k8s_host_node_ips',
            'longhorn_image_repository',
            'longhorn_data_path',
            'longhorn_over_provisioning_percentage',
            'high_availability_controlplane_as_host',
        ]
        vars = {}
        for key in keys:
            value = self.get_val(config, key)
            if value:
                vars[key] = value
        return vars

    def fetch_reboot_vars(self, config):
        vars = {}
        availability_controlplane_as_host = self.get_val(config, 'availability_controlplane_as_host')
        if availability_controlplane_as_host:
            vars['availability_controlplane_as_host'] = availability_controlplane_as_host
        return vars

    def fetch_master_config(self, config):
        self.master_nodes = self.get_nodes(config)
        vars = self.fetch_join_vars(config)
        self.master_config = new_site_item_master(vars)

    def fetch_worker_config(self, config):
        self.worker_nodes = self.get_nodes(config)
        vars = self.fetch_join_vars(config)
        self.worker_config = new_site_item_worker(vars)

    def fetch_longhorn_config(self, config):
        self.longhorn_nodes = self.get_nodes(config)
        vars = self.fetch_longhorn_vars(config)
        self.longhorn_config = new_site_item_longhorn(vars)

    def fetch_reboot_config(self, config):
        self.reboot_nodes = self.get_nodes(config)
        vars = self.fetch_reboot_vars(config)
        self.reboot_config = new_site_item_reboot(vars)

    def get_hosts_content(self):
        return new_inventory_content(
            self.mariadb_node,
            self.registry_node,
            self.primary_master_node,
            self.master_nodes,
            self.worker_nodes,
            self.longhorn_nodes,
            self.reboot_nodes,
            )

    def get_site_content(self):
        data = []
        def add(conf):
            if conf is not None:
                data.append(conf)
        for conf in [
                self.mariadb_config,
                self.registry_config,
                self.primary_master_config,
                self.master_config,
                self.worker_config,
                self.longhorn_config,
                self.reboot_config,
        ]:
            add(conf)
        return to_yaml(data)

    def generate_hosts_file(self, path):
        content = self.get_hosts_content()
        with open(path, "w") as f:
            f.write(content)

    def generate_site_file(self, path):
        content = self.get_site_content()
        with open(path, "w") as f:
            f.write(content)

    def debug_str(self):
        return "hosts_file:\n%s\n\nsite.yml:\n%s\n" % (self.get_hosts_content(), self.get_site_content())

    def get_login_info(self):
	    # TODO 验证接口、参数是否 OK
        if self.primary_master_config is None:
            return None
        master_config = self.primary_master_config.get("vars", {})
        frontend_ip = master_config.get("k8s_controlplane_host", None)
        user = master_config.get("onecloud_user", None)
        password = master_config.get("onecloud_user_password", None)
        if frontend_ip is None:
            raise Exception("Not found controlplane_host in config")
        if user is None:
            raise Exception("Not found onecloud_user in config")
        if password is None:
            raise Exception("Not found onecloud_user_password in config")
        return (frontend_ip, user, password)

    def is_using_ee(self):
        return self.primary_master_config.get('vars', {}).get('use_ee')

if __name__ == "__main__":
    def p(data):
        print(to_yaml(data))

    p(new_site_item_primary_master(
        "127.0.0.1", "root", "sql-pass", "vip",
        registry_mirrors=["https://a.b.c", "http://x.y.z"]))

    with open("./config-example.yml") as f:
        ret = yaml.load(f)
        conf = PlaybookConfig(ret)
        print(conf.debug_str())
