# 介绍

ocboot 能够快速的在 CentOS 7 、Kylin V10、Debian 10等机器上搭建部署 [Cloudpods](https://github.com/yunionio/cloudpods) 服务。

ocboot 依赖 ansible-playbook 部署 cloudpods 服务，可以在单节点使用 local 的方式部署，也可以在多个节点使用 ssh 的方式同时部署。

## 依赖说明

- 操作系统: Centos 7.x 、Kylin V10、Debian 10
- 最低配置要求: 4 核 8G
- 软件: ansible 4.0 ~ 9.0 (ansible-core: 2.11 ~ 2.16)
- 能够 ssh 免密登录待部署机器

## 使用方法

### 安装 ansible

ocboot 使用 [buildash](https://github.com/containers/buildah) 运行容器来部署服务，容器镜像里面包含了 python3 和 ansible 等运行环境。

所以请先在自己的系统上安装 buildah ，请先参考 [buildah installation instructions](https://github.com/containers/buildah/blob/main/install.md) 安装 buildah。

### clone 代码

```bash
$ git clone https://github.com/yunionio/ocboot.git
$ cd ./ocboot
```

### 部署服务

ocboot 的运行方式很简单，只需要按自己机器的规划写好 yaml 配置文件，然后执行 `./ocboot.sh run.py full` 脚本，便会使用 buildah 启动容器，然后在容器里面运行 ansible-playbook 在对应的机器上部署服务。

#### 快速开始

- [All in One 安装](https://www.cloudpods.org/zh/docs/quickstart/allinone/)：在 CentOS 7 或 Debian 10 等发行版里搭建全功能 Cloudpods 服务，可以快速体验**内置私有云**和**多云管理**的功能。
- [多节点高可用安装](https://www.cloudpods.org/zh/docs/setup/ha-ce/)：在生产环境中使用高可用的方式部署 Cloudpods 服务，包括**内置私有云**和**多云管理**的功能。


### 添加节点

添加节点使用 add-node 子命令把节点加入到已有集群。

```bash
# 比如把节点 192.168.121.61 加入到已有集群 192.168.121.21
$ ./ocboot.sh add-node 192.168.121.21 192.168.121.61

# 可以一次添加多个节点，格式如下
$ ./ocboot.sh add-node $PRIMARY_IP $node1_ip $node2_ip ... $nodeN_ip

# 把 $node_ip ssh 端口 2222 的节点加入到 $PRIMARY_IP ssh 端口 4567 的集群
$ ./ocboot.sh add-node --port 4567 --node-port 2222 $PRIMARY_IP $node_ip

# 查看 add-node 命令帮助信息
$ ./ocboot.sh add-node --help
```

具体操作可参考文档：[添加节点](https://www.cloudpods.org/zh/docs/setup/host/)。

### 添加 lbagent 节点

添加节点使用 add-lbagent 子命令把运行 lb agent 服务的节点加入到已有集群。

```bash
# 比如把节点 192.168.121.62 加入到已有集群 192.168.121.21
$ ./ocboot.sh add-lbagent 192.168.121.21 192.168.121.62

# 可以一次添加多个节点，格式如下
$ ./ocboot.sh add-lbagent $PRIMARY_IP $node1_ip $node2_ip ... $nodeN_ip

# 把 $node_ip ssh 端口 2222 的节点加入到 $PRIMARY_IP ssh 端口 4567 的集群
$ ./ocboot.sh add-lbagent --port 4567 --node-port 2222 $PRIMARY_IP $node_ip
```

具体操作可参考文档：[部署Lbagent](https://www.cloudpods.org/zh/docs/function_principle/onpremise/lb/lbagent/#310%E5%90%AB%E4%B9%8B%E5%90%8E%E7%89%88%E6%9C%AC%E9%83%A8%E7%BD%B2lbagent)。

### 升级节点

升级节点参考文档：[升级服务](https://www.cloudpods.org/zh/docs/setup/upgrade/)。

### 备份节点

#### 原理

备份流程会备份当前系统的配置文件（`config.yml`） 以及使用 `mysqldump` 来备份数据库。

#### 命令行参数

```bash
usage: ocboot.py backup [-h] [--backup-path BACKUP_PATH] [--light] config

positional arguments:
  config                config yaml file

optional arguments:
  -h, --help            show this help message and exit
  --backup-path BACKUP_PATH
                        backup path, default: /opt/backup
  --light               ignore yunionmeter and yunionlogger database; ignore
                        tables start with 'opslog' and 'task'.
```

#### 注意事项

下面详细介绍各个参数的作用和注意事项。

- `config`是必选参数，即，需要备份的配置文件名称，例如 `config-allinone.yml, config-nodes.yml, config-k8s-ha.yml，` 以及使用快速安装时会生成的 `config-allinone-current.yml`，因此备份命令不对配置文件名称作假设，**需由使用者自行输入配置文件名称**。
- `--backup-path` 这个参数记录备份的目标目录。备份的内容包括配置文件（几 `k` 级别），以及 `mysqldump` 命令备份的数据库文件临时文件：`onecloud.sql`，然后会将该文件压缩为 `onecloud.sql.tgz`，并删除临时文件。用户需确保 `/opt/backup` 目录存在且可写且磁盘空间足够。
- `--light` 这个选项用来做精简备份，原理是在备份过程中，忽略掉一些尺寸较大的特定文件，主要是账单、操作日志等相关的文件。默认保留。
- 备份后的配置文件名称为 `config.yml`。
- 备份的流程全部采用命令行参数接受输入，备份过程中无交互。因此支持 `crontab`方式自动备份。但备份程序本身不支持版本 `rotate`，用户可以使用 `logrotate` 之类的工具来做备份管理。

#### FAQ

- Q:  备份时提示缺 `MySQLdb` 包怎么办？

- A：在centos上，可以执行如下命令来安装（其他os发行版请酌情修改，或联系客服）：

  ```bash
  sudo yum install -y mariadb-devel python3-devel
  sudo yum groupinstall -y "Development Tools"
  sudo pip3 install mysqlclient
  ```

- Q: 怎样查看、手工解压备份文件？

- A：备份文件默认用户名为: `/opt/backup/onecloud.sql.gz`, 预览、手工解压的方式如下：

  ```bash
  # 预览该文件：
  gunzip --stdout /opt/backup/onecloud.sql.gz | less

  # 解压，同时保留源文件：
  gunzip --stdout /opt/backup/onecloud.sql.gz > /opt/backup/onecloud.sql

  # 有些高版本的gunzip 提供 -k/--keep 选项，来保存源文件。可以直接执行：
  gunzip -k /opt/backup/onecloud.sql.gz
  ```

### 恢复节点

#### 原理

恢复是备份的逆操作，流程包括：

- 解压备份好的数据库文件；
- 依照用户输入，或者在本机安装 `mariadb-server`，并导入数据库；或者将备份的数据库 source 到指定的数据库中。
- 根据之前备份好的 `config.yml`，结合用户输入（当前机器 `ip`、`worker node ips`、`master node ips`），来重新生成 config.yml，然后提示用户重新安装云管系统。

#### 命令行参数

```bash
usage: ocboot.py restore [-h] [--backup-path BACKUP_PATH]
                         [--install-db-to-localhost]
                         [--master-node-ips MASTER_NODE_IPS]
                         [--master-node-as-host]
                         [--worker-node-ips WORKER_NODE_IPS]
                         [--worker-node-as-host] [--mysql-host MYSQL_HOST]
                         [--mysql-user MYSQL_USER]
                         [--mysql-password MYSQL_PASSWORD]
                         [--mysql-port MYSQL_PORT]
                         primary_ip

positional arguments:
  primary_ip            primary node ip

optional arguments:
  -h, --help            show this help message and exit
  --backup-path BACKUP_PATH
                        backup path, default=/opt/backup
  --install-db-to-localhost
                        use this option when install local db
  --master-node-ips MASTER_NODE_IPS
                        master nodes ips, seperated by comma ','
  --master-node-as-host
                        use this option when use master nodes as host
  --worker-node-ips WORKER_NODE_IPS
                        worker nodes ips, seperated by comma ','
  --worker-node-as-host
                        use this option when use worker nodes as host
  --mysql-host MYSQL_HOST
                        mysql host; not needed if set --install-db-to-
                        localhost
  --mysql-user MYSQL_USER
                        mysql user, default: root; not needed if set
                        --install-db-to-localhost
  --mysql-password MYSQL_PASSWORD
                        mysql password; not needed if set --install-db-to-
                        localhost
  --mysql-port MYSQL_PORT
                        mysql port, default: 3306; not needed if set
                        --install-db-to-localhost
```

#### 注意事项

- `primary_ip` 为必填项，作为位置参数传入。

- `--backup-path`，默认值为`/opt/backup`。

- `--install-db-to-localhost`，是否在本机（`primary`节点） 安装数据库。默认为否。如果选择了`--install-db-to-localhost`，则会在本机安装数据(`mariadb-server` 的稳定版)，并自动赋予下列参数以默认值：

  - ```bash
    --mysql-host=127.0.0.1
    --mysql-user=root
    --mysql-password=<继承备份文件里 mysql 的密码>
    --mysql-port=3306
    ```

- `--mysql-host` 以及其他同类选项：不安装数据库，直接复用给定数据库。注意：`--install-db-to-localhost`参数与`--mysql-*`系列参数互斥，只能选择其中一种，要么本机安装数据库，要么给定具体参数。

- `--master-node-ips`同时安装 `master` 节点。该参数是以半角逗号分隔的 `ip` 列表。适用于多节点模式。

- `--master-node-as-host`安装`master`节点时，将其作为`host` 节点。

- `--worker-node-ips`、`--worker-node-as-host`，作用同上，如其名。
