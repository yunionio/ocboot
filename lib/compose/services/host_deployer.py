from lib.compose.object import ServiceDataVolume, ServiceVolume
from lib.compose.services.cluster_service import ClusterCommonService


class HostDeployerService(ClusterCommonService):

    def __init__(self, version, keystone):
        super().__init__("host-deployer", "master-0617.0", keystone_svc=keystone)
        self.enable_privileged()
        self.add_volume(ServiceVolume("/dev", "/dev"))
        self.add_volume(ServiceVolume("/sys", "/sys"))
        self.add_volume(ServiceDataVolume(self.YUNION_RUN_ONECLOUD_PATH))
        self.add_volume(ServiceDataVolume(self.YUNION_RUN_VMWARE_PATH))
        self.add_volume(ServiceDataVolume(self.YUNION_CLOUD_PATH))

    def get_command(self):
        cmd = f"/opt/yunion/bin/host-deployer --common-config-file {self.get_config_path()} --config {self.YUNION_ETC_PATH}/host.conf"
        return cmd.split(' ')

    def _get_post_init_service(self):
        return None
