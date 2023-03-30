from lib.compose.object import ComposeManifest
from lib.compose.services import ClimcService, new_scheduler_service, WebService, new_apigateway_service, \
    new_webconsole_service, new_yunionconf_service, new_monitor_service, InfluxdbService, EtcdService, \
    new_glance_service, KubeServerService
from lib.compose.services import new_keystone_service, new_region_service, new_ansibleserver_service
from lib.compose.services import MysqlService


def new_oc_manifest(version):
    manifest = ComposeManifest()

    mysql = MysqlService()
    manifest.add_service(mysql)

    etcd = EtcdService()

    keystone = new_keystone_service(version, mysql, etcd)
    influxdb = InfluxdbService(keystone)
    region = new_region_service(version, mysql, keystone)
    scheduler = new_scheduler_service(version, mysql, region)
    glance = new_glance_service(version, mysql, keystone)
    kubeServer = KubeServerService(version, mysql, keystone)
    ansibleserver = new_ansibleserver_service(version, mysql, keystone)
    climc = ClimcService(version, keystone)
    apigateway = new_apigateway_service(version, keystone)
    webconsole = new_webconsole_service(version, mysql, keystone)
    yunionconf = new_yunionconf_service(version, mysql, keystone)
    monitor = new_monitor_service(version, mysql, region)
    web = WebService(version, apigateway, webconsole)

    for svc in [
        etcd,
        keystone,
        influxdb,
        region,
        scheduler,
        glance,
        kubeServer,
        ansibleserver,
        climc,
        yunionconf,
        apigateway,
        webconsole,
        monitor,
        web,
    ]:
        init_svc = svc.get_init_service()
        if init_svc:
            manifest.add_service(init_svc)
        manifest.add_service(svc)
        post_init_svc = svc.get_post_init_service()
        if post_init_svc:
            manifest.add_service(post_init_svc)

    return manifest
