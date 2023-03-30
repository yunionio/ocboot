from lib.compose.services import ClusterCommonService


class EtcdService(ClusterCommonService):
    SVC_ETCD = "etcd"
    SVC_PORT_ETCD_CLIENT = 2379
    SVC_PORT_ETCD_PEER_PORT = 2380
    VERSION = "3.4.6"

    def __init__(self):
        super().__init__(self.SVC_ETCD, self.VERSION,
                         port=self.SVC_PORT_ETCD_CLIENT)
        self.set_healthcheck(f"/bin/sh -ec ETCDCTL_API=3 etcdctl endpoint status")
        self.add_environment({
            "ETCDCTL_API": "3",
        })

    def get_config_path(self):
        return None

    def _get_init_service(self):
        return None

    def _get_post_init_service(self):
        return None

    def get_command(self):
        return [
            "/usr/local/bin/etcd",
            "--data-dir=/var/etcd/data",
            "--name=etcd",
            f"--initial-advertise-peer-urls=http://etcd:{self.SVC_PORT_ETCD_PEER_PORT}",
            f"--listen-peer-urls=http://0.0.0.0:{self.SVC_PORT_ETCD_PEER_PORT}",
            f"--listen-client-urls=http://0.0.0.0:{self.SVC_PORT_ETCD_CLIENT}",
            f"--advertise-client-urls=http://etcd:{self.SVC_PORT_ETCD_CLIENT}",
            f"--initial-cluster=etcd=http://etcd:{self.SVC_PORT_ETCD_PEER_PORT}",
            "--initial-cluster-state=new",
            "--quota-backend-bytes",
            "134217728",
            "--auto-compaction-retention",
            "1",
            "--max-wals",
            "1",
            "--initial-cluster-token=7f283eed-0f7f-4d55-9159-32e673517b53"
        ]
