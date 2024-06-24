from lib.compose.services.cluster_service import ClusterCommonService
from lib.compose.object import ServiceDataVolume, ServicePort


class BaremetalService(ClusterCommonService):
    SVC_PORT_BAREMETAL = 8879

    def __init__(self, version, keystone, region, dhcp_relay):
        super().__init__("baremetal-agent", version,
                         port=self.SVC_PORT_BAREMETAL,
                         keystone_svc=keystone, depend_svc=region)
        self.enable_privileged()
        self.use_host_network()
        self.add_volume(ServiceDataVolume(self.YUNION_CLOUD_WORKSPACE_PATH))
        self.depend_on_health(dhcp_relay)
        # self.add_port(ServicePort(67, 67, 'udp'))
        # self.add_port(ServicePort(69, 69, 'udp'))
        # http_port = self.SVC_PORT_BAREMETAL + 1000
        # self.add_port(ServicePort(http_port, http_port, 'tcp'))

    def get_command(self):
        cmd = [self.get_bin_path(),
               "--auth-url", "https://${PUBLIC_IP}:30357/v3",
               "--listen-interface", "${LISTEN_INTERFACE}",
               "--session-endpoint-type", "public",
               "--config", self.get_config_path()]
        return cmd
