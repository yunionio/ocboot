from lib.compose.services.cluster_service import ClusterCommonService


class DHCPRelayService(ClusterCommonService):
    def __init__(self, version):
        super().__init__("dhcprelay", "v3.11-0621.0")
        self.enable_privileged()
        self.use_host_network()
        self.set_healthcheck("netstat -ulnp | grep 68 | grep dhcprelay")

    def get_command(self):
        return ["/opt/yunion/bin/dhcprelay",
                "--interface", "${LISTEN_INTERFACE}",
                "--ip", "${PUBLIC_IP}",
                "--relay", "${PUBLIC_IP}",
                ]

    def get_volumes(self):
        return []

    def get_config_path(self):
        return None

    def _get_init_service(self):
        return None

    def _get_post_init_service(self):
        return None
