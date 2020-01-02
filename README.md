# 介绍

ocboot 是 OneCloud bootstrap 的简写，能够快速的在 Centos7 机器上搭建部署 OneCloud 服务。

ocboot 依赖 ansible-playbook 部署 onecloud 服务，可以在单节点使用 local 的方式部署，也可以在多个节点使用 ssh 的方式同时部署。

# 依赖说明

- 操作系统: Centos 7.x
- 最低配置要求: 4核4G
- 软件: ansible
- 能够 ssh 免密登录待部署机器

# 使用方法

## 安装 ansible

ocboot 使用 ansible 来部署服务，所以请先在自己的系统上安装 ansible ，可以使用发型版自带的包管理工具安装，或者直接使用 pip 安装。

```bash
# centos install ansible
$ yum install -y ansible

# archlinux install ansible
$ pacman -S ansible

# others
$ pip install ansible
```

## clone 代码

```bash
$ git clone https://github.com/yunionio/ocboot.git
$ cd ./ocboot
```

## 部署服务

ocboot 的运行方式很简单，只需要按自己机器的规划写好 yaml 配置文件，然后执行 `./run.py` 脚本，便会调用 ansible-playbook 在对应的机器上部署服务。

ocboot 可以很简单的在一台机器上部署 all in one 环境，也可以同时在多台机器上部署大规模集群，以下举例说明使用方法和配置文件的编写。

### 单节点 all in one 部署

假设已经准备好了 1 台 Centos 7 机器，它的 ip 是 `10.127.10.158`，我想在这台机器上 allinone 安装 OneCloud。

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
# primary_master_node 表示运行 k8s 和 onecloud 服务的节点
primary_master_node:
  hostname: 10.127.10.158
  user: root
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
  # 该节点作为 OneCloud 私有云计算节点
  as_host: true
  # docker registry 加速镜像
  registry_mirrors:
  - https://lje6zxpk.mirror.aliyuncs.com
  - https://lms7sxqp.mirror.aliyuncs.com
EOF

# 开始部署
$ ./run.py ./config-allinone.yml
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
  user: root
  db_user: root
  db_password: your-sql-password
primary_master_node:
  hostname: 10.127.10.156
  user: root
  db_host: 10.127.10.156
  db_user: root
  db_password: your-sql-password
  controlplane_host: 10.127.10.156
  controlplane_port: "6443"
  registry_mirrors:
  - https://lje6zxpk.mirror.aliyuncs.com
master_nodes:
  hosts:
  - hostname: 10.127.10.157
    user: root
  - hostname: 10.127.10.158
    user: root
  controlplane_host: 10.127.10.156
  controlplane_port: "6443"
  as_controller: true
  registry_mirrors:
  - https://lje6zxpk.mirror.aliyuncs.com
worker_nodes:
  hosts:
  - hostname: 10.127.10.159
    user: root
  - hostname: 10.127.10.160
    user: root
  controlplane_host: 10.127.10.156
  controlplane_port: "6443"
  as_host: true
  registry_mirrors:
  - https://lje6zxpk.mirror.aliyuncs.com
EOF

# 开始部署
$ ./run.py ./config-nodes.yml
```

## 添加节点

添加节点也很简单，只需要按照自己的规划，在已有的 config 里面添加对应的节点 ssh 登录 ip 和用户，然后再重复执行 `./run.py config.yml` 即可。
