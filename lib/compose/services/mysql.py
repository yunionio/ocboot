from lib.compose.object import ServiceDataVolume
from lib.compose.services import ClusterService


class MysqlService(ClusterService):

    def __init__(self,
                 root_pwd="your-sql-password",
                 port="3306",
                 version="10.5.19",
                 repo="registry.cn-beijing.aliyuncs.com/yunionio"):
        super(MysqlService, self).__init__("mysql", version, repo=repo, image_name="mariadb")

        self.password = root_pwd
        self.port = port

        self.add_environment({
            "MYSQL_ROOT_PASSWORD": self.password,
            "MYSQL_TCP_PORT": self.port,
            "MYSQL_ROOT_HOST": "%",
            "MARIADB_AUTO_UPGRADE": "true",
            "MARIADB_DISABLE_UPGRADE_BACKUP": "true",
        })
        self.add_volume(ServiceDataVolume("/var/lib/mysql"))
        # self.set_healthcheck("/usr/local/bin/healthcheck.sh")
        self.set_healthcheck("mysqladmin ping -h mysql -P 3306 -p$$MYSQL_ROOT_PASSWORD")

    def get_port(self):
        return self.port

    def get_password(self):
        return self.password
