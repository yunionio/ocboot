from lib.compose.services import ClusterCommonService
from lib.compose.object import Quoted


class ClimcService(ClusterCommonService):

    def __init__(self, version, keystone, region):
        super().__init__("climc", version, keystone_svc=keystone, depend_svc=region)
        self.depend_on_completed(keystone.get_post_init_service())

    def get_command(self):
        # cmd = "grep -q rcadmin /root/.bashrc || echo 'source /etc/yunion/rcadmin' >> /root/.bashrc; socat TCP-LISTEN:2023,reuseaddr,fork EXEC:/bin/bash,pty,stderr,setsid,sigint,sane"
        cmd = "/opt/climc-entrypoint.sh"
        return ["/bin/bash", Quoted(cmd)]

    def get_config_path(self):
        return self.YUNION_ETC_PATH + "rcadmin"

    def _get_init_service(self):
        svc = super()._get_init_service()
        svc.add_environment({
            "CLIMC_DEFAULT_USER": "admin",
            "CLIMC_DEFAULT_USER_PASSWORD": "admin@123",
        })
        return svc

    def _get_post_init_service(self):
        return None
