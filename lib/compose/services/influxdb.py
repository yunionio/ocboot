from lib.compose.object import ServiceDataVolume, ServicePort
from lib.compose.services import ClusterCommonService


class InfluxdbService(ClusterCommonService):
    SVC_INFLUXDB = "influxdb"
    SVC_PORT_INFLUXDB = 30086
    VERSION = "1.7.7"

    def __init__(self, keystone):
        super().__init__(self.SVC_INFLUXDB, self.VERSION, port=self.SVC_PORT_INFLUXDB, keystone_svc=keystone)
        self.add_volume(self.get_data_vol())
        self.set_healthcheck(f"curl -k https://localhost:{self.port}")

    def get_data_vol(self):
        return ServiceDataVolume("/var/lib/influxdb")

    def get_command(self):
        return ["influxd", "-config", "/etc/yunion/influxdb.conf"]
