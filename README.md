# 介绍

ocboot 能够快速的在 CentOS 7 或者 Debian 10 机器上搭建部署 [Cloudpods](https://github.com/yunionio/cloudpods) 服务。

ocboot 依赖 ansible-playbook 部署 cloudpods 服务，可以在单节点使用 local 的方式部署，也可以在多个节点使用 ssh 的方式同时部署。

# 依赖说明

- 操作系统: Centos 7.x 或者 Debian 10
- 最低配置要求: 4核8G
- 软件: ansible-2.9.25
- 能够 ssh 免密登录待部署机器

# 使用方法

## 安装 ansible

ocboot 使用 ansible 来部署服务，所以请先在自己的系统上安装 ansible ，可以使用发型版自带的包管理工具安装，或者直接使用 pip 安装。

```bash
# centos install ansible
$ yum install -y epel-release git python3-pip
$ python3 -m pip install --upgrade pip setuptools wheel
$ python3 -m pip install --upgrade ansible

# kylin install ansible
$ yum install -y git python3-pip
$ python3 -m pip install --upgrade pip setuptools wheel
$ python3 -m pip install --upgrade ansible

# archlinux install ansible
$ pacman -S python3-pip
$ python3 -m pip install --upgrade pip setuptools wheel
$ python3 -m pip install --upgrade ansible

# others
$ python3 -m pip install --upgrade pip setuptools wheel
$ python3 -m pip install --upgrade ansible
```

## clone 代码

```bash
$ git clone https://github.com/yunionio/ocboot.git
$ cd ./ocboot & pip install -r ./requirements.txt
```

## 部署服务

ocboot 的运行方式很简单，只需要按自己机器的规划写好 yaml 配置文件，然后执行 `./ocboot.py install` 脚本，便会调用 ansible-playbook 在对应的机器上部署服务。

ocboot 可以很简单的在一台机器上部署 all in one 环境，也可以同时在多台机器上部署大规模集群，以下举例说明使用方法和配置文件的编写。

### 快速开始

如果只想在一个节点上部署一个当前最新版本的AllInOne demo，可以用如下命令快速开始。其中ip为待部署节点的用于通信的IP地址。

```bash
./run.py <ip>
```

对于某些网络环境，registry.cn-beijing.aliyuncs.com 访问缓慢或不可达，在版本 `v3.9.5`之后（含），可指定镜像源：docker.io](http://docker.io) 来安装。命令如下：
```bash
IMAGE_REPOSITORY=docker.io/yunion ./run.py <ip>
```

也可在修改文件的`primary_master_node`节点的 `image_repository`字段为 `docker.io/yunion`。

样例配置片段：

```yaml
primary_master_node:
  hostname: 10.127.10.158
  ...
  onecloud_version: 'v3.9.8'
  ...
  image_repository: docker.io/yunion
```

### 单节点 all in one 部署

假设已经准备好了 1 台 Centos 7 机器，它的 ip 是 `10.127.10.158`，我想在这台机器上 allinone 安装 OneCloud v3.8.8 版本。

```bash
# 编写 config-allinone.yml 文件
$ cat <<EOF >./config-allinone.yml
# mariadb_node 表示需要部署 mariadb 服务的节点
mariadb_node:
  # 待部署节点 ip
  hostname: 10.127.10.158
  # 待部署节点登录用户
  user: root
  # mariadb 的用户
  db_user: root
  # mariadb 用户密码
  db_password: your-sql-password
# clickhouse_node 表示运行 clickhouse 服务的节点
clickhouse_node:
  use_local: true
  user: root
  ch_password: "your-clickhouse-password"
  ch_port: 9000   # clickhouse port
# primary_master_node 表示运行 k8s 和 onecloud 服务的节点
primary_master_node:
  hostname: 10.127.10.158
  user: root
  # onecloud 版本
  onecloud_version: v3.9.8
  # 数据库连接地址
  db_host: 10.127.10.158
  # 数据库用户
  db_user: root
  # 数据库密码
  db_password: your-sql-password
  # k8s 控制节点的 ip
  controlplane_host: 10.127.10.158
  # k8s 控制节点的端口
  controlplane_port: "6443"
  # onecloud 登录用户
  onecloud_user: demo
  # onecloud 登录用户密码
  onecloud_user_password: demo@123
  # 该节点作为 OneCloud 私有云计算节点（默认为 false）
  as_host: true
  # 虚拟机强行作为 OneCloud 私有云计算节点（默认为 false）。开启此项时，请确保as_host: true
  as_host_on_vm: true
  # 是否宿主机开启大页内存(宿主机为 x86_64 架构非控制节点默认开启，且内存超过 30G时生效，预留内存为总内存的10%，最大预留20G内存)
  enable_hugepage: false
  # k8s pod network CIDR:
  pod_network_cidr: 10.40.0.0/16
  # k8s service CIDR
  service_cidr: 10.96.0.0/12
  # k8s service DNS domain
  service_dns_domain: 'cluster.local'
EOF

# 开始部署
$ ./ocboot.py install ./config-allinone.yml
....
# 部署完成后会有如下输出，表示运行成功
# 浏览器打开 https://10.127.10.158
# 使用 demo/demo@123 用户密码登录就能访问前端界面
Initialized successfully!
Web page: https://10.127.10.158
User: demo
Password: demo@123
```

### 多节点部署

假设已经准备好了 4 台 Centos 7 机器，它的 ip 是 `10.127.10.156-160`，各个节点做出以下的规划：

- k8s master 节点: 10.127.10.156-158
  - 其中 156 作为第一个部署的主节点并且运行 mariadb
  - 这 3 个节点都可以调度运行 onecloud 控制服务
- k8s worker 节点: 10.127.10.159-160
  - 这 2 个节点可以作为 onecloud 私有云计算节点

```bash
# 根据规划编写 config-nodes.yml 文件
$ cat <<EOF >./config-nodes.yml
mariadb_node:
  hostname: 10.127.10.156
  # 待部署节点 ssh 端口
  port: 22
  user: root
  db_user: root
  db_password: your-sql-password
primary_master_node:
  onecloud_version: v3.9.8
  hostname: 10.127.10.156
  # 待部署节点 ssh 端口
  port: 22
  user: root
  db_host: 10.127.10.156
  db_user: root
  db_password: your-sql-password
  controlplane_host: 10.127.10.156
  controlplane_port: "6443"
master_nodes:
  hosts:
  - hostname: 10.127.10.157
    # 待部署节点 ssh 端口
    port: 22
    user: root
  - hostname: 10.127.10.158
    # 待部署节点 ssh 端口
    port: 22
    user: root
  controlplane_host: 10.127.10.156
  controlplane_port: "6443"
  as_controller: true
worker_nodes:
  hosts:
  - hostname: 10.127.10.159
    # 待部署节点 ssh 端口
    port: 22
    user: root
  - hostname: 10.127.10.160
    # 待部署节点 ssh 端口
    port: 22
    user: root
  controlplane_host: 10.127.10.156
  controlplane_port: "6443"
  as_host: true
EOF

# 开始部署
$ ./ocboot.py install ./config-nodes.yml
```

### 高可用部署
假设准备好了 3 台 CentOS7 机器，安装的成高可用的模式，以及双主的高可用数据库。规划如下：

role              | ip            | interface    |  note
----------------- | ------------- | ------------ | ------------------------------
k8s primary       | 10.127.90.101 | eth0         | -                             |
k8s master 1 ,db1 | 10.127.90.102 | eth0         | pswd="0neC1oudDB#",  port=3306|
k8s master 2 ,db2 | 10.127.90.103 | eth0         | pswd="0neC1oudDB#",  port=3306|
k8s vip           | 10.127.190.10 | -            | -                             |
db vip            | 10.127.190.11 | -            | db_nic=eth0                   |

```bash
# 填充变量，生成配置
DB_VIP="10.127.190.11"
DB_PORT=3306
DB_PSWD="0neC1oudDB#"
DB_USER=root
DB_NIC="eth0"

K8S_VIP=10.127.190.10
PRIMARY_INTERFACE="eth0"
PRIMARY_IP=10.127.90.101

MASTER_1_INTERFACE="eth0"
MASTER_1_IP=10.127.90.102
MASTER_2_INTERFACE="eth0"
MASTER_2_IP=10.127.90.103

cat > config-k8s-ha.yml <<EOF
mariadb_ha_nodes:
  db_vip: $DB_VIP
  db_user: "$DB_USER"
  db_password: "$DB_PSWD"
  db_port: $DB_PORT
  db_nic: $DB_NIC
  hosts:
  - user: root
    hostname: $MASTER_1_IP
  - user: root
    hostname: $MASTER_2_IP

primary_master_node:
  hostname: $PRIMARY_IP
  use_local: false
  user: root
  onecloud_version: "v3.9.8"
  db_host: $DB_IP
  db_user: "$DB_USER"
  db_password: "$DB_PSWD"
  db_port: "$DB_PORT"
  skip_docker_config: true
  image_repository: registry.cn-beijing.aliyuncs.com/yunionio
  ha_using_local_registry: false
  node_ip: "$PRIMARY_IP"
  ip_autodetection_method: "can-reach=$PRIMARY_IP"
  controlplane_host: $K8S_VIP
  controlplane_port: "6443"
  as_host: true
  high_availability: true
  use_ee: false
  enable_minio: true
  host_networks: "$PRIMARY_INTERFACE/br0/$PRIMARY_IP"

master_nodes:
  controlplane_host: $K8S_VIP
  controlplane_port: "6443"
  as_controller: true
  as_host: true
  high_availability: true
  hosts:
  - user: root
    hostname: "$MASTER_1_IP"
    host_networks: "$MASTER_1_INTERFACE/br0/$MASTER_1_IP"
  - user: root
    hostname: "$MASTER_2_IP"
    host_networks: "$MASTER_2_INTERFACE/br0/$MASTER_2_IP"
EOF

# 开始部署
$ ./ocboot.py install ./config-k8s-ha.yml
```

## 添加节点

添加节点使用 add-node 子命令把节点加入到已有集群。

```bash
# 比如把节点 192.168.121.61 加入到已有集群 192.168.121.21
$ ./ocboot.py add-node 192.168.121.21 192.168.121.61

# 可以一次添加多个节点，格式如下
$ ./ocboot.py add-node $PRIMARY_IP $node1_ip $node2_ip ... $nodeN_ip

# 把 $node_ip ssh 端口 2222 的节点加入到 $PRIMARY_IP ssh 端口 4567 的集群
$ ./ocboot.py add-node --port 4567 --node-port 2222 $PRIMARY_IP $node_ip

# 查看 add-node 命令帮助信息
$ ./ocboot.py add-node --help
```

## 添加 lbagent 节点

添加节点使用 add-lbagent 子命令把运行 lb agent 服务的节点加入到已有集群。

```bash
# 比如把节点 192.168.121.62 加入到已有集群 192.168.121.21
$ ./ocboot.py add-lbagent 192.168.121.21 192.168.121.62

# 可以一次添加多个节点，格式如下
$ ./ocboot.py add-lbagent $PRIMARY_IP $node1_ip $node2_ip ... $nodeN_ip

# 把 $node_ip ssh 端口 2222 的节点加入到 $PRIMARY_IP ssh 端口 4567 的集群
$ ./ocboot.py add-lbagent --port 4567 --node-port 2222 $PRIMARY_IP $node_ip
```

## 升级节点

```bash
# 执行升级
$ ./ocboot.py upgrade <PRIMARY_HOST> v3.8.8

# 查看升级可选参数
$ ./ocboot.py upgrade -h
usage: ocboot.py upgrade [-h] [--user SSH_USER] [--key-file SSH_PRIVATE_FILE] [--port SSH_PORT] [--as-bastion]
                         FIRST_MASTER_HOST VERSION

positional arguments:
  FIRST_MASTER_HOST     onecloud cluster primary master host, e.g., 10.1.2.56
  VERSION               onecloud version to be upgrade

optional arguments:
  -h, --help            show this help message and exit
  --user SSH_USER, -u SSH_USER
                        primary master host ssh user (default: root)
  --key-file SSH_PRIVATE_FILE, -k SSH_PRIVATE_FILE
                        primary master ssh private key file (default: /home/lzx/.ssh/id_rsa)
  --port SSH_PORT, -p SSH_PORT
                        primary master host ssh port (default: 22)
  --as-bastion, -B      use primary master node as ssh bastion host to run ansible
```

## 备份节点

### 原理

备份流程会备份当前系统的配置文件（`config.yml`） 以及使用`mysqldump` 来备份数据库。

### 命令行参数

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

### 注意事项

下面详细介绍各个参数的作用和注意事项。

* `config`是必选参数，即，需要备份的配置文件名称，例如`config-allinone.yml, config-nodes.yml, config-k8s-ha.yml，`以及使用快速安装时会生成的`config-allinone-current.yml`，因此备份命令不对配置文件名称作假设，**需由使用者自行输入配置文件名称**。
* `--backup-path` 这个参数记录备份的目标目录。备份的内容包括配置文件（几 `k` 级别），以及`mysqldump`命令备份的数据库文件临时文件：`onecloud.sql`，然后会将该文件压缩为`onecloud.sql.tgz`，并删除临时文件。用户需确保 `/opt/backup` 目录存在且可写且磁盘空间足够。
* `--light` 这个选项用来做精简备份，原理是在备份过程中，忽略掉一些尺寸较大的特定文件，主要是账单、操作日志等相关的文件。默认保留。
* 备份后的配置文件名称为`config.yml`。
* 备份的流程全部采用命令行参数接受输入，备份过程中无交互。因此支持 `crontab`方式自动备份。但备份程序本身不支持版本 `rotate`，用户可以使用 `logrotate` 之类的工具来做备份管理。

### FAQ

* Q:  备份时提示缺`MySQLdb` 包怎么办？

* A：在centos上，可以执行如下命令来安装（其他os发行版请酌情修改，或联系客服）：
  ```bash
  sudo yum install -y mariadb-devel python3-devel
  sudo yum groupinstall -y "Development Tools"
  sudo pip3 install mysqlclient
  ```

* Q: 怎样查看、手工解压备份文件？

* A：备份文件默认用户名为: `/opt/backup/onecloud.sql.gz`, 预览、手工解压的方式如下：
  ```bash
  # 预览该文件：
  gunzip --stdout /opt/backup/onecloud.sql.gz | less

  # 解压，同时保留源文件：
  gunzip --stdout /opt/backup/onecloud.sql.gz > /opt/backup/onecloud.sql

  # 有些高版本的gunzip 提供 -k/--keep 选项，来保存源文件。可以直接执行：
  gunzip -k /opt/backup/onecloud.sql.gz
  ```



## 恢复节点

### 原理

恢复是备份的逆操作，流程包括：

* 解压备份好的数据库文件；
* 依照用户输入，或者在本机安装` mariadb-server`，并导入数据库；或者将备份的数据库 source 到指定的数据库中。
* 根据之前备份好的` config.yml`，结合用户输入（当前机器 `ip`、`worker node ips`、`master node ips`），来重新生成 config.yml，然后提示用户重新安装云管系统。

### 命令行参数

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

### 注意事项

* `primary_ip` 为必填项，作为位置参数传入。

* `--backup-path`，默认值为`/opt/backup`。

* `--install-db-to-localhost`，是否在本机（`primary`节点） 安装数据库。默认为否。如果选择了`--install-db-to-localhost`，则会在本机安装数据(`mariadb-server` 的稳定版)，并自动赋予下列参数以默认值：

  * ```bash
    --mysql-host=127.0.0.1
    --mysql-user=root
    --mysql-password=<继承备份文件里 mysql 的密码>
    --mysql-port=3306
    ```

* `--mysql-host` 以及其他同类选项：不安装数据库，直接复用给定数据库。注意：`--install-db-to-localhost`参数与`--mysql-*`系列参数互斥，只能选择其中一种，要么本机安装数据库，要么给定具体参数。

* `--master-node-ips`同时安装`master ` 节点。该参数是以半角逗号分隔的 `ip` 列表。适用于多节点模式。

* `--master-node-as-host`安装`master`节点时，将其作为`host` 节点。

* `--worker-node-ips`、`--worker-node-as-host`，作用同上，如其名。

## 使用docker部署

为了避免因为环境依赖产生的问题，我们也提供了使用容器来部署，由于部署过程中有重启容器引擎的操作，故**使用容器时只能以远程的方式部署(即部署的目标机器和运行 ocboot 容器的机器不能是同一台)**。使用容器时，只需要配置好 ssh 免密登录，按需创建配置文件，以及安装好 docker 即可开始部署。

<details>

<summary>
查看命令
</summary>

```bash
# Allinone install
$ ./run-in-docker.sh <IP>
$ ./run-in-docker.sh install config-allinone.yml

# Multiple nodes install
$ ./run-in-docker.sh install config-nodes.yml

# High availability install
$ ./run-in-docker.sh install config-k8s-ha.yml

# Add node
$ ./run-in-docker.sh add-node <PRIMARY_HOST> <NODE_IP1> <NODE_IP2> ... <NODE_IPN>

# Upgrade node
$ ./run-in-docker.sh upgrade <PRIMARY_HOST> v3.8.13
```

</details>
