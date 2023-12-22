from lib.compose.object import ServiceVolume, ServiceDataVolume
from lib.compose.services.cluster_service import ClusterService, ComposeServiceInitService, ClusterCommonService
from lib.compose.services.mysql import MysqlService
from lib.compose.services.etcd import EtcdService
from lib.compose.services.climc import ClimcService
from lib.compose.services.kubeserver import KubeServerService
from lib.compose.services.web import WebService
from lib.compose.services.influxdb import InfluxdbService

SVC_KEYSTONE = "keystone"
SVC_PORT_KEYSTONE = 30500

SVC_REGION = "region"
SVC_PORT_REGION = 30888

SVC_SCHEDULER = "scheduler"
SVC_PORT_SCHEDULER = 30887

SVC_SCHEDULEDTASK = "scheduledtask"
SVC_PORT_SCHEDULEDTASK = 30978

SVC_GLANCE = "glance"
SVC_PORT_GLANCE = 30292

SVC_ESXI_AGENT = "esxi-agent"
SVC_PORT_ESXI_AGENT = 30883

SVC_APIGATEWAY = "apigateway"
SVC_PORT_APIGATEWAY = 30300

SVC_WEBCONSOLE = "webconsole"
SVC_PORT_WEBCONSOLE = 30899

SVC_YUNIONCONF = "yunionconf"
SVC_PORT_YUNIONCONF = 30889

SVC_ANSIBLESERVER = "ansibleserver"
SVC_PORT_ANSIBLESERVER = 30890

SVC_MONITOR = "monitor"
SVC_PORT_MONITOR = 30093

SVC_LOGGER = "logger"
SVC_PORT_LOGGER = 30999

SVC_NOTIFY = "notify"
SVC_PORT_NOTIFY = 30777

SVC_CLOUDMON = "cloudmon"
SVC_PORT_CLOUDMON = 30931

SVC_CLOUDID = "cloudid"
SVC_PORT_CLOUDID = 30893


def new_cloud_service(name, version, port,
                      db_svc=None,
                      keystone_svc=None,
                      depend_svc=None,
                      disable_auto_sync_table=False):
    return ClusterCommonService(name, version, db_svc,
                                port=port, keystone_svc=keystone_svc,
                                depend_svc=depend_svc,
                                disable_auto_sync_table=disable_auto_sync_table)


def new_keystone_service(version, db_svc, etcd_svc):
    svc = new_cloud_service(SVC_KEYSTONE, version, SVC_PORT_KEYSTONE, db_svc)
    svc.depend_on_health(etcd_svc)
    return svc


def new_region_service(version, db_svc, keystone_svc):
    return new_cloud_service(SVC_REGION, version, SVC_PORT_REGION, db_svc,
                             keystone_svc)


def new_scheduler_service(version, db_svc, region_svc):
    svc = new_cloud_service(SVC_SCHEDULER, version, SVC_PORT_SCHEDULER, db_svc,
                            depend_svc=region_svc,
                            disable_auto_sync_table=True)
    return svc


def new_scheduledtask_service(version, db_svc, region_svc):
    svc = new_cloud_service(SVC_SCHEDULEDTASK, version, SVC_PORT_SCHEDULEDTASK, db_svc,
                            depend_svc=region_svc,
                            disable_auto_sync_table=True)
    return svc


def new_glance_service(version, db_svc, keystone_svc, hostdeployer_svc):
    svc = new_cloud_service(SVC_GLANCE, version, SVC_PORT_GLANCE, db_svc, keystone_svc, depend_svc=hostdeployer_svc)
    svc.add_volume(ServiceDataVolume(svc.YUNION_GLANCE_DATA_PATH))
    svc.add_volume(ServiceDataVolume(svc.YUNION_RUN_ONECLOUD_PATH))
    return svc


def new_esxi_agent_service(version, keystone_svc, region_svc):
    svc = new_cloud_service(SVC_ESXI_AGENT, version, SVC_PORT_ESXI_AGENT, keystone_svc=keystone_svc, depend_svc=region_svc)
    svc.add_volume(ServiceDataVolume(svc.YUNION_RUN_VMWARE_PATH))
    svc.add_volume(ServiceDataVolume(svc.YUNION_RUN_ONECLOUD_PATH))
    svc.add_volume(ServiceDataVolume(svc.YUNION_CLOUD_PATH))
    return svc


def new_apigateway_service(version, keystone_svc, depend_svc):
    return new_cloud_service(SVC_APIGATEWAY, version, SVC_PORT_APIGATEWAY, keystone_svc=keystone_svc, depend_svc=depend_svc)


def new_webconsole_service(version, db_svc, keystone_svc):
    return new_cloud_service(SVC_WEBCONSOLE, version, SVC_PORT_WEBCONSOLE, db_svc, keystone_svc)


def new_yunionconf_service(version, db_svc, keystone):
    return new_cloud_service(SVC_YUNIONCONF, version, SVC_PORT_YUNIONCONF, db_svc, keystone)


def new_ansibleserver_service(version, db_svc, keystone_svc):
    return new_cloud_service(SVC_ANSIBLESERVER, version, SVC_PORT_ANSIBLESERVER, db_svc, keystone_svc)


def new_monitor_service(version, db_svc, region_svc):
    svc = new_cloud_service(SVC_MONITOR, version, SVC_PORT_MONITOR, db_svc, depend_svc=region_svc)
    return svc


def new_logger_service(version, db_svc, keystone_svc):
    return new_cloud_service(SVC_LOGGER, version, SVC_PORT_LOGGER, db_svc, keystone_svc)


def new_notify_service(version, db_svc, keystone_svc):
    return new_cloud_service(SVC_NOTIFY, version, SVC_PORT_NOTIFY, db_svc, keystone_svc)


def new_cloudid_service(version, db_svc, region_svc):
    return new_cloud_service(SVC_CLOUDID, version, SVC_PORT_CLOUDID, db_svc, depend_svc=region_svc)


def new_cloudmon_service(version, keystone_svc):
    return new_cloud_service(SVC_CLOUDMON, version, SVC_PORT_CLOUDMON, keystone_svc=keystone_svc)
