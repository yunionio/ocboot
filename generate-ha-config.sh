#!/bin/bash

# 设置 shell 环境变量

DB_IP="10.127.190.11"
DB_PORT=3306
DB_PSWD="0neC1oudDB#"
DB_USER=root

K8S_VIP=10.127.190.10
PRIMARY_INTERFACE="eth0"
PRIMARY_IP=10.127.90.101

MASTER_1_INTERFACE="eth0"
MASTER_1_IP=10.127.90.102
MASTER_2_INTERFACE="eth0"
MASTER_2_IP=10.127.90.103

REGION=region0
ZONE=zone0
VERSION=$(cat ./VERSION)

# 生成 yaml 部署配置文件

CONFIG_YML_PATH="config-ha.yml"

cat > $CONFIG_YML_PATH <<EOF
# primary_master_node 表示运行 k8s 和 Cloudpods 服务的节点
primary_master_node:
  # ssh login IP
  hostname: $PRIMARY_IP
  # 不使用本地登录方式
  use_local: false
  # ssh login user
  user: root
  # cloudpods version
  onecloud_version: $VERSION
  # mariadb connection address
  db_host: "$DB_IP"
  # mariadb user
  db_user: "$DB_USER"
  # mariadb password
  db_password: "$DB_PSWD"
  # mariadb port
  db_port: "$DB_PORT"
  # 节点服务监听的地址，多网卡时可以指定对应网卡的地址
  node_ip: "$PRIMARY_IP"
  # 对应 Kubernetes calico 插件默认网卡选择规则
  ip_autodetection_method: "can-reach=$PRIMARY_IP"
  # K8s 控制节点的 IP，对应keepalived 监听的 VIP
  controlplane_host: $K8S_VIP
  # K8s 控制节点 apiserver 监听的端口
  controlplane_port: "6443"
  # 该节点作为 Cloudpods 私有云计算节点，如果不想让控制节点作为计算节点，可以设置为 false
  as_host: true
  # 虚拟机可作为 Cloudpods 内置私有云计算节点（默认为 false）。开启此项时，请确保 as_host: true
  as_host_on_vm: true
  # 产品版本，从 [Edge, CMP, FullStack] 选择一个，FullStack 会安装融合云，CMP 安装多云管理版本，Edge 安装私有云
  product_version: 'Edge'
  # 服务对应的镜像仓库，如果待部署的机器不在中国大陆，可以用 dockerhub 的镜像仓库：docker.io/yunion
  image_repository: registry.cn-beijing.aliyuncs.com/yunion
  # 启用高可用模式
  high_availability: true
  # 使用 minio 作为后端虚拟机镜像存储
  enable_minio: true
  ha_using_local_registry: false
  # 计算节点默认网桥 br0 对应的网卡
  host_networks: "$PRIMARY_INTERFACE/br0/$PRIMARY_IP"
  # region 设置
  region: $REGION
  # zone 设置
  zone: $ZONE

master_nodes:
  # 加入控制节点的 k8s vip
  controlplane_host: $K8S_VIP
  # 加入控制节点的 K8s apiserver 端口
  controlplane_port: "6443"
  # 作为 K8s 和 Cloudpods 控制节点
  as_controller: true
  # 该节点作为 Cloudpods 私有云计算节点，如果不想让控制节点作为计算节点，可以设置为 false
  as_host: true
  # 虚拟机可作为 Cloudpods 内置私有云计算节点（默认为 false）。开启此项时，请确保 as_host: true
  as_host_on_vm: true
  # 从 primary 节点同步 ntp 时间
  ntpd_server: "$PRIMARY_IP"
  # 启用高可用模式
  high_availability: true
  hosts:
  - user: root
    hostname: "$MASTER_1_IP"
    # 计算节点默认网桥 br0 对应的网卡
    host_networks: "$MASTER_1_INTERFACE/br0/$MASTER_1_IP"
  - user: root
    hostname: "$MASTER_2_IP"
    # 计算节点默认网桥 br0 对应的网卡
    host_networks: "$MASTER_2_INTERFACE/br0/$MASTER_2_IP"
EOF

echo "Write configuration: $CONFIG_YML_PATH"
