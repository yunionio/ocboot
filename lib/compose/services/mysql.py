from lib.compose.object import ServiceDataVolume
from lib.compose.services import ClusterService


class MysqlService(ClusterService):

    def __init__(self,
                 root_pwd="your-sql-password",
                 port="3306",
                 version="5.6",
                 repo="registry.cn-beijing.aliyuncs.com/yunionio"):
        super(MysqlService, self).__init__("mysql", version, repo=repo)

        self.password = root_pwd
        self.port = port

        self.add_environment({
            "MYSQL_ROOT_PASSWORD": self.password,
            "MYSQL_TCP_PORT": self.port,
        })
        self.add_volume(ServiceDataVolume("/var/lib/mysql"))
        self.set_healthcheck("mysqladmin ping -h 127.0.0.1 -u $$MYSQL_USER --password=$$MYSQL_PASSWORD")

    def get_port(self):
        return self.port

    def get_password(self):
        return self.password
