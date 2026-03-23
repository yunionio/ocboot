#!/usr/bin/env python3

import argparse
from pathlib import Path


def normalize_product_version(raw: str) -> str:
    if raw is None:
        return "Edge"
    s = str(raw).strip()
    if not s:
        return "Edge"
    sl = s.lower()
    if sl == "ai":
        return "AI"
    if sl == "cmp":
        return "CMP"
    if sl == "edge":
        return "Edge"
    if sl == "lightedge":
        return "LightEdge"
    if sl == "fullstack":
        return "FullStack"
    # Keep behavior predictable; original sh supported only these values.
    return s


def build_yaml(product_version: str, cfg: dict) -> str:
    # Keep values consistent with the original generate-ha-config.sh template,
    # but all variables must come from CLI args (no hard-coded environment).
    DB_IP = cfg["db_ip"]
    DB_PORT = cfg["db_port"]
    DB_PSWD = cfg["db_password"]
    DB_USER = cfg["db_user"]

    K8S_VIP = cfg["k8s_vip"]
    PRIMARY_INTERFACE = cfg["primary_interface"]
    PRIMARY_IP = cfg["primary_ip"]

    MASTER_1_INTERFACE = cfg["master_1_interface"]
    MASTER_1_IP = cfg["master_1_ip"]
    MASTER_2_INTERFACE = cfg["master_2_interface"]
    MASTER_2_IP = cfg["master_2_ip"]

    REGION = cfg["region"]
    ZONE = cfg["zone"]

    version = (Path(__file__).resolve().parent / "VERSION").read_text(encoding="utf-8").strip()

    ai_extra_primary = ""
    ai_extra_master = ""
    if product_version == "AI":
        ai_extra_primary = "  enable_containerd: true"
        ai_extra_master = "  enable_containerd: true"

    # Note: no YAML library is used; we rely on deterministic text templates.
    return f"""# primary_master_node 表示运行 k8s 和 Cloudpods 服务的节点
primary_master_node:
  # ssh login IP
  hostname: {PRIMARY_IP}
  # 不使用本地登录方式
  use_local: false
  # ssh login user
  user: root
  # cloudpods version
  onecloud_version: {version}
  # mariadb connection address
  db_host: "{DB_IP}"
  # mariadb user
  db_user: "{DB_USER}"
  # mariadb password
  db_password: "{DB_PSWD}"
  # mariadb port
  db_port: "{DB_PORT}"
  # 节点服务监听的地址，多网卡时可以指定对应网卡的地址
  node_ip: "{PRIMARY_IP}"
  # 对应 Kubernetes calico 插件默认网卡选择规则
  ip_autodetection_method: "can-reach={PRIMARY_IP}"
  # K8s 控制节点的 IP，对应keepalived 监听的 VIP
  controlplane_host: {K8S_VIP}
  # K8s 控制节点 apiserver 监听的端口
  controlplane_port: "6443"
  # 该节点作为 Cloudpods 私有云计算节点，如果不想让控制节点作为计算节点，可以设置为 false
  as_host: true
  # 虚拟机可作为 Cloudpods 内置私有云计算节点（默认为 false）。开启此项时，请确保 as_host: true
  as_host_on_vm: true
  # 产品版本，从 [Edge, CMP, FullStack] 选择一个，FullStack 会安装融合云，CMP 安装多云管理版本，Edge 安装私有云
  product_version: '{product_version}'
{ai_extra_primary}
  # 服务对应的镜像仓库，如果待部署的机器不在中国大陆，可以用 dockerhub 的镜像仓库：docker.io/yunion
  image_repository: registry.cn-beijing.aliyuncs.com/yunion
  # 启用高可用模式
  high_availability: true
  # 使用 minio 作为后端虚拟机镜像存储
  enable_minio: true
  ha_using_local_registry: false
  # 计算节点默认网桥 br0 对应的网卡
  host_networks: "{PRIMARY_INTERFACE}/br0/{PRIMARY_IP}"
  # region 设置
  region: {REGION}
  # zone 设置
  zone: {ZONE}

master_nodes:
  # 加入控制节点的 k8s vip
  controlplane_host: {K8S_VIP}
  # 加入控制节点的 K8s apiserver 端口
  controlplane_port: "6443"
  # 作为 K8s 和 Cloudpods 控制节点
  as_controller: true
  # 该节点作为 Cloudpods 私有云计算节点，如果不想让控制节点作为计算节点，可以设置为 false
  as_host: true
  # 虚拟机可作为 Cloudpods 内置私有云计算节点（默认为 false）。开启此项时，请确保 as_host: true
  as_host_on_vm: true
{ai_extra_master}
  # 从 primary 节点同步 ntp 时间
  ntpd_server: "{PRIMARY_IP}"
  # 启用高可用模式
  high_availability: true
  hosts:
  - user: root
    hostname: "{MASTER_1_IP}"
    # 计算节点默认网桥 br0 对应的网卡
    host_networks: "{MASTER_1_INTERFACE}/br0/{MASTER_1_IP}"
  - user: root
    hostname: "{MASTER_2_IP}"
    # 计算节点默认网桥 br0 对应的网卡
    host_networks: "{MASTER_2_INTERFACE}/br0/{MASTER_2_IP}"
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate config-ha.yml for HA deployment")
    parser.add_argument(
        "--product-version",
        dest="product_version",
        required=True,
        help="Product version: Edge/CMP/FullStack/LightEdge/AI",
    )

    # All deployment parameters are required so users can fully control the generated YAML.
    parser.add_argument("--db-ip", dest="db_ip", required=True, help="MARIADB db_host")
    parser.add_argument("--db-port", dest="db_port", required=True, type=int, help="MARIADB db_port")
    parser.add_argument("--db-user", dest="db_user", required=True, help="MARIADB db_user")
    parser.add_argument("--db-password", dest="db_password", required=True, help="MARIADB db_password")

    parser.add_argument("--k8s-vip", dest="k8s_vip", required=True, help="keepalived/controlplane VIP")

    parser.add_argument("--primary-interface", dest="primary_interface", required=True, help="primary host NIC for br0")
    parser.add_argument("--primary-ip", dest="primary_ip", required=True, help="primary host ssh/cluster IP")

    parser.add_argument("--master-1-interface", dest="master_1_interface", required=True, help="master-1 NIC for br0")
    parser.add_argument("--master-1-ip", dest="master_1_ip", required=True, help="master-1 hostname IP")
    parser.add_argument("--master-2-interface", dest="master_2_interface", required=True, help="master-2 NIC for br0")
    parser.add_argument("--master-2-ip", dest="master_2_ip", required=True, help="master-2 hostname IP")

    parser.add_argument("--region", dest="region", required=True, help="product region")
    parser.add_argument("--zone", dest="zone", required=True, help="product zone")
    args = parser.parse_args()

    product_version = normalize_product_version(args.product_version)

    print(f"Normalized PRODUCT_VERSION: {product_version}")

    cfg_path = Path(__file__).resolve().parent / "config-ha.yml"
    cfg = {
        "db_ip": args.db_ip,
        "db_port": args.db_port,
        "db_password": args.db_password,
        "db_user": args.db_user,
        "k8s_vip": args.k8s_vip,
        "primary_interface": args.primary_interface,
        "primary_ip": args.primary_ip,
        "master_1_interface": args.master_1_interface,
        "master_1_ip": args.master_1_ip,
        "master_2_interface": args.master_2_interface,
        "master_2_ip": args.master_2_ip,
        "region": args.region,
        "zone": args.zone,
    }
    cfg_path.write_text(build_yaml(product_version, cfg), encoding="utf-8")
    print(f"Write configuration: {cfg_path.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

