from lib.compose.object import ServiceDataVolume, ServicePort
from lib.compose.services import ClusterCommonService


class WebService(ClusterCommonService):

    def __init__(self, version, apigateway, webconsole):
        super().__init__("web", version)
        self.depend_on_completed(apigateway.get_post_init_service())
        self.depend_on_completed(webconsole.get_post_init_service())
        self.set_restart_on_failure()
        self.add_port(ServicePort(443, 443))

    def get_config_path(self):
        return "/etc/nginx/conf.d/default.conf"

    def get_command(self):
        return ["nginx", "-g", "daemon off;"]

    def _get_init_service(self):
        svc = super()._get_init_service()
        svc.add_volume(ServiceDataVolume("/etc/nginx/conf.d/"))
        return svc

    def _get_post_init_service(self):
        return None
