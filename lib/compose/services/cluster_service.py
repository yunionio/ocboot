import os

from lib.compose.object import Service, ServiceDataVolume, ServicePort
from lib.compose import SERVICE_RESTART_ON_FAILURE
from lib.compose.object import DependOn
from lib.compose import options


def COMPOSE_SERVICE_INIT_VERSION():
    return os.environ.get('VERSION', 'v3.11-0530.0')


class ClusterService(Service):

    def __init__(self, name, version,
                 image_name='',
                 repo='registry.cn-beijing.aliyuncs.com/yunionio'):
        if image_name == '':
            image_name = name
        self.image = f'{repo}/{image_name}:{version}'
        super(ClusterService, self).__init__(name, self.image)


class ComposeServiceInitService(ClusterService):
    STEP_INIT = "init"
    STEP_POST_INIT = "post-init"

    def __init__(self,
                 component_name,
                 step,
                 db_svc=None,
                 keystone_svc=None,
                 depend_svc=None,
                 version='v3.11-0625.0',
                 product_version="CMP"):
        super().__init__(f"{component_name}-{step}", version, image_name='compose-service-init')

        if not step:
            raise Exception("step is required")

        pv = os.getenv("PRODUCT_VERSION", product_version)

        self.component_name = component_name
        self.db_svc = db_svc
        config_dir = ClusterCommonService.YUNION_ETC_PATH
        vol = ServiceDataVolume(config_dir)
        cmd = [
            "/opt/yunion/bin/compose-service-init",
            "--config-dir=/",
            f"--component={self.component_name}",
            f"--step={step}",
            f"--product-version={pv}",
        ]
        if self.db_svc:
            cmd = cmd + [
                f"--mysql-host={self.db_svc.get_name()}",
                f"--mysql-port={self.db_svc.get_port()}",
                "--mysql-user=root",
                f"--mysql-password={self.db_svc.get_password()}",
            ]

        self.set_command(*cmd)
        self.add_volume(vol)
        if options.has_public_ip():
            self.add_environment({
                "PUBLIC_IP": "$PUBLIC_IP",
            })
        if self.db_svc:
            self.depend_on_health(db_svc)
        if keystone_svc:
            self.depend_on_completed(keystone_svc.get_post_init_service())
        if depend_svc:
            if isinstance(depend_svc, ClusterCommonService):
                post_init_svc = depend_svc.get_post_init_service()
                if post_init_svc:
                    self.depend_on_completed(post_init_svc)


class ClusterCommonService(ClusterService):
    YUNION_BIN_PATH = "/opt/yunion/bin/"
    YUNION_ETC_PATH = "/etc/yunion/"
    YUNION_CLOUD_PATH = "/opt/cloud"
    YUNION_CLOUD_WORKSPACE_PATH = "/opt/cloud/workspace"
    YUNION_GLANCE_DATA_PATH = f'{YUNION_CLOUD_WORKSPACE_PATH}/data/glance'
    YUNION_RUN_ONECLOUD_PATH = "/var/run/onecloud"
    YUNION_RUN_VMWARE_PATH = "/var/run/vmware"
    YUNION_CERTS_PATH = YUNION_ETC_PATH + "pki/"
    STEP_INIT = ComposeServiceInitService.STEP_INIT
    STEP_POST_INIT = ComposeServiceInitService.STEP_POST_INIT

    def __init__(self, name, version,
                 db_svc=None,
                 disable_auto_sync_table=False,
                 keystone_svc=None,
                 depend_svc=None,
                 port=-1,
                 image_name="",
                 repo="registry.cn-beijing.aliyuncs.com/yunionio"):
        super().__init__(name, version, image_name=image_name, repo=repo)

        self.db_svc = db_svc
        self.disable_auto_sync_table = disable_auto_sync_table
        self.keystone_svc = keystone_svc
        self.depend_svc = depend_svc
        self.port = port
        self.init_svc = self._get_init_service()
        if self.init_svc:
            self.depend_on(self.init_svc, condition=DependOn.CONDITION_COMPLETED_SUCCESSFULLY)
        self.post_init_svc = self._get_post_init_service()
        if self.db_svc:
            self.depend_on(self.db_svc)
        self.set_command(*self.get_command())
        self.add_volume(ServiceDataVolume(self.YUNION_CERTS_PATH, readonly=True))
        if self.get_config_path():
            self.add_volume(ServiceDataVolume(self.get_config_path(), readonly=True))
        if self.port >= 0:
            self.set_healthcheck(f"netstat -tln | grep -c {self.port}")
        self.set_restart_on_failure()

    def get_ports(self):
        if self.port >= 0:
            if options.has_public_ip() and not self.is_host_network():
                self.add_port(ServicePort(self.port, self.port, 'tcp'))
        return super().get_ports()

    def get_command(self):
        cmd = [
            self.get_bin_path(),
            "--config",
            self.get_config_path(),
        ]
        if self.db_svc and not self.disable_auto_sync_table:
            cmd.append("--auto-sync-table")
        return cmd

    def get_bin_path(self):
        return self.YUNION_BIN_PATH + self.get_name()

    def get_config_path(self):
        return self.YUNION_ETC_PATH + self.get_name() + ".conf"

    def get_component_name(self):
        return self.get_name()

    def _get_init_service(self):
        init_svc = ComposeServiceInitService(
            self.get_component_name(),
            self.STEP_INIT,
            self.db_svc,
            keystone_svc=self.keystone_svc,
            depend_svc=self.depend_svc)
        return init_svc

    def get_init_service(self):
        return self.init_svc

    def _get_post_init_service(self):
        post_init_svc = ComposeServiceInitService(self.get_component_name(),
                                                  self.STEP_POST_INIT,
                                                  self.db_svc)
        post_init_svc.set_restart(SERVICE_RESTART_ON_FAILURE)
        post_init_svc.depend_on(self, DependOn.CONDITION_SERVICE_HEALTHY)
        return post_init_svc

    def get_post_init_service(self):
        return self.post_init_svc
