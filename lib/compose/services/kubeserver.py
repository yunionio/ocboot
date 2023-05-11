from lib.compose.services import ClusterCommonService


class KubeServerService(ClusterCommonService):
    SVC_KUBESERVER = "kubeserver"
    SVC_PORT_KUBESERVER = 30442

    def __init__(self, version, db_svc, keystone_svc):
        super().__init__(self.SVC_KUBESERVER, version=version,
                         port=self.SVC_PORT_KUBESERVER,
                         db_svc=db_svc, keystone_svc=keystone_svc)

    def get_command(self):
        return [
            f"{self.YUNION_BIN_PATH}kube-server",
            "--config",
            f"{self.YUNION_ETC_PATH}kubeserver.conf",
            "--running-mode",
            "docker-compose"
        ]
