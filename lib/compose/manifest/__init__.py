from lib.compose.object import ComposeManifest
from lib.compose.services import ClimcService, new_cloudid_service, new_scheduler_service, WebService, \
    new_apigateway_service, \
    new_webconsole_service, new_yunionconf_service, new_monitor_service, InfluxdbService, EtcdService, \
    new_glance_service, KubeServerService, new_scheduledtask_service, new_logger_service, new_notify_service, \
    new_cloudmon_service, new_esxi_agent_service
from lib.compose.services import new_keystone_service, new_region_service, new_ansibleserver_service
from lib.compose.services import MysqlService
from lib.compose.services.dhcp_relay import DHCPRelayService
from lib.compose.services.baremetal import BaremetalService
from lib.compose.services.host_deployer import HostDeployerService
from lib.compose import options


def new_cmp_manifest(version):
    manifest = ComposeManifest()

    mysql = MysqlService()
    manifest.add_service(mysql)

    etcd = EtcdService()

    keystone = new_keystone_service(version, mysql, etcd)
    hostdeployer = HostDeployerService(version, keystone)
    logger = new_logger_service(version, mysql, keystone)
    influxdb = InfluxdbService(keystone)
    region = new_region_service(version, mysql, keystone)
    scheduler = new_scheduler_service(version, mysql, region)
    scheduledtask = new_scheduledtask_service(version, mysql, region)
    glance = new_glance_service(version, mysql, keystone, hostdeployer)
    esxiagent = new_esxi_agent_service(version, keystone, region)
    kubeServer = KubeServerService(version, mysql, keystone)
    ansibleserver = new_ansibleserver_service(version, mysql, keystone)
    climc = ClimcService(version, keystone, region)
    apigateway = new_apigateway_service(version, keystone, region)
    webconsole = new_webconsole_service(version, mysql, keystone)
    yunionconf = new_yunionconf_service(version, mysql, keystone)
    monitor = new_monitor_service(version, mysql, region)
    cloudmon = new_cloudmon_service(version, keystone)
    notify = new_notify_service(version, mysql, keystone)
    cloudid = new_cloudid_service(version, mysql, region)
    web = WebService(version, apigateway, webconsole)

    for svc in [
        etcd,
        keystone,
        hostdeployer,
        logger,
        notify,
        influxdb,
        region,
        scheduler,
        scheduledtask,
        glance,
        kubeServer,
        ansibleserver,
        climc,
        yunionconf,
        apigateway,
        webconsole,
        monitor,
        cloudmon,
        cloudid,
        esxiagent,
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


def new_baremetal_manifest(version):
    options.set_has_public_ip(True)

    manifest = ComposeManifest()

    mysql = MysqlService()
    manifest.add_service(mysql)

    etcd = EtcdService()

    keystone = new_keystone_service(version, mysql, etcd)
    hostdeployer = HostDeployerService(version, keystone)
    logger = new_logger_service(version, mysql, keystone)
    influxdb = InfluxdbService(keystone)
    region = new_region_service(version, mysql, keystone)
    dhcp_relay = DHCPRelayService(version)
    baremetal = BaremetalService(version, keystone, region, dhcp_relay)
    scheduler = new_scheduler_service(version, mysql, region)
    scheduledtask = new_scheduledtask_service(version, mysql, region)
    glance = new_glance_service(version, mysql, keystone, hostdeployer)
    ansibleserver = new_ansibleserver_service(version, mysql, keystone)
    climc = ClimcService(version, keystone, region)
    apigateway = new_apigateway_service("v3.11-0621.0", keystone, region)
    webconsole = new_webconsole_service(version, mysql, keystone)
    yunionconf = new_yunionconf_service(version, mysql, keystone)
    monitor = new_monitor_service(version, mysql, region)
    # cloudmon = new_cloudmon_service(version, keystone)
    notify = new_notify_service(version, mysql, keystone)
    web = WebService(version, apigateway, webconsole)

    for svc in [
        etcd,
        keystone,
        hostdeployer,
        logger,
        notify,
        influxdb,
        region,
        scheduler,
        scheduledtask,
        glance,
        baremetal,
        dhcp_relay,
        ansibleserver,
        climc,
        yunionconf,
        apigateway,
        webconsole,
        monitor,
        # cloudmon,
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


PRODUCT_VERSION_CMP = "cmp"
PRODUCT_VERSION_BAREMETAL = "baremetal"

PRODUCT_VERSION_FACTORY = {
    PRODUCT_VERSION_CMP: new_cmp_manifest,
    PRODUCT_VERSION_BAREMETAL: new_baremetal_manifest,
}


def new_manifest(version, product_version=PRODUCT_VERSION_CMP):
    f = PRODUCT_VERSION_FACTORY.get(product_version.lower(), None)
    if not f:
        raise Exception(f'not found product_version {product_version}')
    return f(version)
