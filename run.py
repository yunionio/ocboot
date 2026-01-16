#!/usr/bin/env python3
# encoding: utf-8
from __future__ import unicode_literals
from __future__ import absolute_import

import os
import os.path
from os import path
import sys
import re
import argparse
import subprocess

from lib import install
from lib import cmd
from lib.parser import inject_add_hostagent_options, inject_add_nodes_runtime_options, help_d, inject_ssh_options
from lib.utils import init_local_user_path
from lib.utils import pr_red, pr_green
from lib.utils import regex_search
from lib.utils import is_valid_dns
from lib import ocboot
from lib import consts


def show_usage():
    usage = '''
Usage: %s [master_ip|<config_file>.yml]
''' % __file__
    print(usage)


IPADDR_REG_PATTERN = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
IPADDR_REG = re.compile(IPADDR_REG_PATTERN)


def _match_ip4addr(string):
    global IPADDR_REG
    return IPADDR_REG.match(string) is not None


def _match_ipv6addr(string):
    # 判断字符串是否为合法 IPv6 地址
    ipv6_pattern = re.compile(
        r'^('
        r'(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}'                  # 全写
        r'|(?:[A-Fa-f0-9]{1,4}:){1,7}:'                              # 以::结尾
        r'|:(?::[A-Fa-f0-9]{1,4}){1,7}'                              # 以::开头
        r'|(?:[A-Fa-f0-9]{1,4}:){1,6}:[A-Fa-f0-9]{1,4}'              # 单::中间
        r'|(?:[A-Fa-f0-9]{1,4}:){1,5}(?::[A-Fa-f0-9]{1,4}){1,2}'
        r'|(?:[A-Fa-f0-9]{1,4}:){1,4}(?::[A-Fa-f0-9]{1,4}){1,3}'
        r'|(?:[A-Fa-f0-9]{1,4}:){1,3}(?::[A-Fa-f0-9]{1,4}){1,4}'
        r'|(?:[A-Fa-f0-9]{1,4}:){1,2}(?::[A-Fa-f0-9]{1,4}){1,5}'
        r'|[A-Fa-f0-9]{1,4}:(?:(?::[A-Fa-f0-9]{1,4}){1,6})'
        r'|:(?:(?::[A-Fa-f0-9]{1,4}){1,7}|:)'                        # :: 或 ::xxxx
        r')'
        r'(?:/([0-9]|[1-9][0-9]|1[01][0-9]|12[0-8]))?'               # 可选前缀长度
        r'$'
    )
    return ipv6_pattern.match(string) is not None


def match_ipaddr(string):
    if _match_ip4addr(string):
        return (True, consts.IP_TYPE_IPV4)
    if _match_ipv6addr(string):
        return (True, consts.IP_TYPE_IPV6)
    return (False, None)


def match_dual_stack_ipaddr(ip1_string, ip2_string):
    """检测双栈IP地址配置"""
    # 检测两个IP地址的类型
    ip1_is_ipv4 = _match_ip4addr(ip1_string) if ip1_string else False
    ip1_is_ipv6 = _match_ipv6addr(ip1_string) if ip1_string else False
    ip2_is_ipv4 = _match_ip4addr(ip2_string) if ip2_string else False
    ip2_is_ipv6 = _match_ipv6addr(ip2_string) if ip2_string else False

    # 检查是否构成有效的双栈配置
    if (ip1_is_ipv4 and ip2_is_ipv6) or (ip1_is_ipv6 and ip2_is_ipv4):
        return (True, consts.IP_TYPE_DUAL_STACK)
    elif ip1_is_ipv4 or ip2_is_ipv4:
        return (True, consts.IP_TYPE_IPV4)
    elif ip1_is_ipv6 or ip2_is_ipv6:
        return (True, consts.IP_TYPE_IPV6)
    else:
        return (False, None)


def versiontuple(v):
    return tuple(map(int, (v.split("."))))


def version_ge(v1, v2):
    return versiontuple(v1) >= versiontuple(v2)


def get_username():
    import getpass
    # python2 / python3 are all tested to get username
    return getpass.getuser()


def check_pip3():
    ret = os.system("pip3 --version >/dev/null 2>&1")
    if ret == 0:
        return
    if install_packages(['python3-pip']) == 0:
        return
    raise Exception("install python3-pip failed")


def check_ansible(pip_mirror):
    minimal_ansible_version = '2.11.12'
    cmd.init_ansible_playbook_path()
    ret = os.system("ansible-playbook --version >/dev/null 2>&1")
    if ret == 0:
        ver_out = os.popen("""ansible-playbook --version | head -1""").read().strip()
        ver_re = re.compile(r'ansible-playbook \[core\s(.*)]')
        match = ver_re.match(ver_out)
        if match:
            ansible_version = match.group(1)
            if version_ge(ansible_version, minimal_ansible_version):
                print("current ansible version: %s. PASS" % ansible_version)
                return
            else:
                print("Current ansible version (%s) is lower than expected(%s). upgrading ... " % (
                    ansible_version, minimal_ansible_version))
        else:
            raise Exception(f"Invalid ansible-playbook --version output: {ver_out}")
    else:
        print("No ansible found. Installing ... ")
    try:
        install_ansible(pip_mirror)
    except Exception as e:
        print("Install ansible failed, please try to install ansible manually")
        raise e


def install_packages(pkgs):
    ignore_check = os.getenv("IGNORE_ALL_CHECKS")
    if ignore_check == "true":
        return

    packager = None

    for p in ['/usr/bin/dnf', '/usr/bin/yum', '/usr/bin/apt']:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            packager = p
            break

    if packager is None:
        print('Current os-release:')
        with open('/etc/os-release', 'r') as f:
            print(f.read())
        raise Exception("Install ansible failed for os-release is not supported.")

    username = get_username()
    if packager == '/usr/bin/apt' and username != 'root':
        packager == 'sudo /usr/bin/apt'

    cmdline = '%s install -y %s' % (packager, ' '.join(pkgs))
    return os.system(cmdline)


def install_ansible(mirror):

    def get_pip_install_cmd(suffix_cmd, mirror):
        cmd = "python3 -m pip install --user --upgrade"
        if mirror:
            cmd = f'{cmd} -i {mirror}'
        return f'{cmd} {suffix_cmd}'

    for pkg in ['PyYAML']:
        install_packages([pkg])

    if os.system('rpm -qa | grep -q python3-pip') != 0:
        ret = os.system(get_pip_install_cmd('pip setuptools wheel', mirror))
        if ret != 0:
            raise Exception("Install/updrade pip3 failed. ")
    os.system(get_pip_install_cmd('pip', mirror))
    ret = os.system(get_pip_install_cmd("'ansible<=9.0.0'", mirror))
    if ret != 0:
        raise Exception("Install ansible failed. ")


def check_passless_ssh(ipaddr, ip_type):
    username = get_username()
    cmd = f"ssh -o 'StrictHostKeyChecking=no' -o 'PasswordAuthentication=no' {username}@{ipaddr} uptime"
    print('cmd:', cmd)
    ret = os.system(cmd)
    if ret == 0:
        return
    try:
        install_passless_ssh(ipaddr)
    except Exception as e:
        print("Configure passwordless ssh failed, please try to configure it manually")
        raise e


def install_passless_ssh(ipaddr):
    username = get_username()
    rsa_path = os.path.join(os.environ.get("HOME"), ".ssh/id_rsa")
    if not os.path.exists(rsa_path):
        ret = os.system("ssh-keygen -f %s -P '' -N ''" % (rsa_path))
        if ret != 0:
            raise Exception("ssh-keygen")
    print("We are going to run the following command to enable passwordless SSH login:")
    print("")
    print("    ssh-copy-id -i ~/.ssh/id_rsa.pub %s@%s" % (username, ipaddr))
    print("")
    print("Press any key to continue and then input %s's password to %s" % (username, ipaddr))
    os.system("read")
    ret = os.system("ssh-copy-id -i ~/.ssh/id_rsa.pub %s@%s" % (username, ipaddr))
    if ret != 0:
        raise Exception("ssh-copy-id")
    ret = os.system(
        "ssh -o 'StrictHostKeyChecking=no' -o 'PasswordAuthentication=no' %s@%s hostname" % (username, ipaddr))
    if ret != 0:
        raise Exception("check passwordless ssh login failed")


def check_env(ipaddr=None, pip_mirror=None):

    ignore_check = os.getenv("IGNORE_ALL_CHECKS")
    if ignore_check == "true":
        return
    check_pip3()
    # check_ansible(pip_mirror)
    match_ip, ip_type = match_ipaddr(ipaddr)
    if match_ip:
        check_passless_ssh(ipaddr, ip_type)


def random_password(num):
    assert (num >= 6)
    digits = r'23456789'
    letters = r'abcdefghjkmnpqrstuvwxyz'
    uppers = letters.upper()
    punc = r''  # !$@#%^&*-=+?;'
    chars = digits + letters + uppers + punc
    npass = None
    while True:
        npass = ''
        digits_cnt = 0
        letters_cnt = 0
        uppers_cnt = 0
        for i in range(num):
            import random
            ch = random.choice(chars)
            if ch in digits:
                digits_cnt += 1
            elif ch in letters:
                letters_cnt += 1
            elif ch in uppers:
                uppers_cnt += 1
            npass += ch
        if digits_cnt > 1 and letters_cnt > 1 and uppers_cnt > 1:
            return npass
    return npass


conf = """
# # clickhouse_node indicates the node where the clickhouse service needs to be deployed
# clickhouse_node:
#   # IP of the machine to be deployed
#   hostname: 10.127.10.158
#   # SSH Login username of the machine to be deployed
#   user: ocboot_user
#   # Password of clickhouse
#   ch_password: your-clickhouse-password
# mariadb_node indicates the node where the mariadb service needs to be deployed
mariadb_node:
  # IP of the machine to be deployed
  hostname: 10.127.10.158
  # SSH Login username of the machine to be deployed
  user: ocboot_user
  # Username of mariadb
  db_user: root
  # Password of mariadb
  db_password: your-sql-password
# primary_master_node indicates the machine running Kubernetes and OneCloud Platform
primary_master_node:
  hostname: 10.127.10.158
  user: ocboot_user
  # Database connection address
  db_host: 10.127.10.158
  # Database connection username
  db_user: root
  # Database connection password
  db_password: your-sql-password
  # IP of Kubernetes controlplane
  controlplane_host: 10.127.10.158
  # Port of Kubernetes controlplane
  controlplane_port: "6443"
  # OneCloud version
  onecloud_version: 'v3.4.12'
  # OneCloud login username
  onecloud_user: admin
  # OneCloud login user's password
  onecloud_user_password: admin@123
  # This machine serves as a OneCloud private cloud computing node
  # as_host: true
  # as_host_on_vm: true
  # enable_eip_man for all-in-one mode only
  enable_eip_man: true
  product_version: 'product_stack'
  image_repository: registry.cn-beijing.aliyuncs.com/yunion
  # host_networks: '<interface>/br0/<ip>'
"""


def dynamic_load():
    username = get_username()
    homepath = '/root' if username == 'root' else os.path.expanduser("~" + username)

    import glob
    paths = glob.glob('/usr/local/lib64/python3.?/site-packages/') + \
        glob.glob('/usr/local/lib64/python3.??/site-packages/') + \
        glob.glob(f'{homepath}/.local/lib/python3.?/site-packages') + \
        glob.glob(f'{homepath}/.local/lib/python3.??/site-packages')

    print("loading path:")

    for p in paths:
        if os.path.isdir(p) and p not in sys.path:
            sys.path.append(p)
            print("\t%s" % p)


def update_config(yaml_conf, produc_stack, runtime):
    import os.path
    import os
    import yaml
    yaml_data = {}
    to_write = False

    offline_path = os.environ.get('OFFLINE_DATA_PATH', )
    if offline_path:
        pr_green('offline mode, no need to update config.')
        return yaml_conf

    assert produc_stack in ocboot.KEY_STACK_LIST
    try:
        if path.isfile(yaml_conf) and path.getsize(yaml_conf) > 0:
            with open(yaml_conf, 'r') as stream:
                yaml_data.update(yaml.safe_load(stream))
    except yaml.YAMLError as exc:
        pr_red("paring %s error: %s" % (yaml_conf, exc))
        raise Exception("paring %s error: %s" % (yaml_conf, exc))

    if not yaml_data.get(ocboot.GROUP_PRIMARY_MASTER_NODE, {}):
        return yaml_conf

    if yaml_data.get(ocboot.GROUP_PRIMARY_MASTER_NODE, {}).get(ocboot.KEY_PRODUCT_VERSION, '') != produc_stack:
        to_write = True
        yaml_data[ocboot.GROUP_PRIMARY_MASTER_NODE][ocboot.KEY_PRODUCT_VERSION] = produc_stack
        if produc_stack == ocboot.KEY_STACK_CMP:
            yaml_data[ocboot.GROUP_PRIMARY_MASTER_NODE][ocboot.KEY_AS_HOST] = False
            yaml_data[ocboot.GROUP_PRIMARY_MASTER_NODE][ocboot.KEY_AS_HOST_ON_VM] = False
        else:
            yaml_data[ocboot.GROUP_PRIMARY_MASTER_NODE][ocboot.KEY_AS_HOST] = True
            yaml_data[ocboot.GROUP_PRIMARY_MASTER_NODE][ocboot.KEY_AS_HOST_ON_VM] = True

    enable_containerd = yaml_data.get(ocboot.GROUP_PRIMARY_MASTER_NODE, {}).get(ocboot.KEY_ENABLE_CONTAINERD, False)
    if enable_containerd:
        if runtime != consts.RUNTIME_CONTAINERD:
            to_write = True
            yaml_data[ocboot.GROUP_PRIMARY_MASTER_NODE][ocboot.KEY_ENABLE_CONTAINERD] = False
    else:
        if runtime == consts.RUNTIME_CONTAINERD:
            to_write = True
            yaml_data[ocboot.GROUP_PRIMARY_MASTER_NODE][ocboot.KEY_ENABLE_CONTAINERD] = True

    if to_write:
        with open(yaml_conf, 'w') as f:
            f.write(yaml.dump(yaml_data))

    return yaml_conf


def generate_config(
    ipaddr, produc_stack,
    dns_list=[], runtime=consts.RUNTIME_QEMU,
    image_repository=None,
    region=consts.DEFAULT_REGION_NAME,
    zone=consts.DEFAULT_ZONE_NAME,
    ip_dual_conf=None, ip_type=None, enable_ipip=False):
    global conf
    import os.path
    import os
    dynamic_load()
    import yaml
    from lib.get_interface_by_ip import get_interface_by_ip

    config_dir = os.getenv("OCBOOT_CONFIG_DIR")

    cur_path = os.path.abspath(os.path.dirname(__file__))
    if not config_dir:
        config_dir = cur_path

    # 使用传入的ip_type，如果没有则重新检测
    if ip_type is None:
        match_ip, ip_type = match_ipaddr(ipaddr)
        if not match_ip:
            pr_red(f'invalid ipaddr {ipaddr}!')
            exit(1)

    temp = os.path.join(config_dir, "config-allinone-current.yml")
    verf = os.path.join(cur_path, "VERSION")
    brand_new = True
    yaml_data = yaml.safe_load(conf)

    with open(verf, 'r') as f:
        ver = f.read().strip()
    try:
        if path.isfile(temp) and path.getsize(temp) > 0:
            with open(temp, 'r') as stream:
                yaml_data.update(yaml.safe_load(stream))
                brand_new = False
    except yaml.YAMLError as exc:
        pr_red("paring %s error: %s" % (temp, exc))
        raise Exception("paring %s error: %s" % (temp, exc))

    if yaml_data.get(ocboot.GROUP_PRIMARY_MASTER_NODE, {}).get(ocboot.KEY_HOSTNAME, '') == ipaddr and \
            yaml_data.get(ocboot.GROUP_PRIMARY_MASTER_NODE, {}).get(ocboot.KEY_ONECLOUD_VERSION, '') == ver:
        update_config(temp, produc_stack, runtime)
        pr_green(f"reuse conf: {temp}")
        return temp

    # using given image_repository if provided;
    if image_repository not in ['', None, 'none']:
        yaml_data[ocboot.GROUP_PRIMARY_MASTER_NODE]['image_repository'] = image_repository
    # else set to 'yunionio' namespace if it is daily build.
    # default is 'yunion', for the official and public release.
    elif re.search(r'\b\d{8}\.\d$', ver):
        yaml_data[ocboot.GROUP_PRIMARY_MASTER_NODE]['image_repository'] = consts.REGISTRY_ALI_YUNIONIO

    if image_repository and '5000' in image_repository:
        r = image_repository
        if '/' in r:
            r = r.split('/')[0]
        yaml_data[ocboot.GROUP_PRIMARY_MASTER_NODE]['insecure_registries'] = [r]

    interface = get_interface_by_ip(ipaddr)
    username = get_username()
    db_password = random_password(12) if brand_new else yaml_data.get(ocboot.GROUP_PRIMARY_MASTER_NODE, {}).get('db_password')
    assert db_password
    extra_db_dict = {
        'db_password': db_password,
        'user': username,
        ocboot.KEY_HOSTNAME: ipaddr,
    }
    enable_host = produc_stack in [ocboot.KEY_STACK_FULLSTACK, ocboot.KEY_STACK_EDGE, ocboot.KEY_STACK_LIGHT_EDGE]
    # 基础配置
    extra_pri_dict = {
        'controlplane_host': ipaddr,
        'db_host': ipaddr,
        'db_password': db_password,
        'user': username,
        ocboot.KEY_AS_HOST: enable_host,
        ocboot.KEY_AS_HOST_ON_VM: enable_host,
        ocboot.KEY_HOSTNAME: ipaddr,
        ocboot.KEY_ONECLOUD_VERSION: ver,
        ocboot.KEY_PRODUCT_VERSION: produc_stack,
        ocboot.KEY_REGION: region,
        ocboot.KEY_ZONE: zone,
    }

    # 添加双栈配置
    if ip_type == consts.IP_TYPE_DUAL_STACK and ip_dual_conf:
        extra_pri_dict['ip_type'] = ip_type
        extra_pri_dict['enable_ipip'] = enable_ipip

        # 确定哪个是IPv4，哪个是IPv6
        if _match_ip4addr(ipaddr):
            # 主IP是IPv4，ip_dual_conf是IPv6
            extra_pri_dict['node_ip'] = ipaddr  # 主IP作为node_ip
            extra_pri_dict['node_ip_v4'] = ipaddr
            extra_pri_dict['node_ip_v6'] = ip_dual_conf
            extra_pri_dict['pod_network_cidr_v4'] = '10.40.0.0/16'
            extra_pri_dict['service_cidr_v4'] = '10.96.0.0/12'
            extra_pri_dict['pod_network_cidr'] = 'fd85:ee78:d8a6:8607::/56'
            extra_pri_dict['service_cidr'] = 'fd85:ee78:d8a6:8608::/112'
            # 双栈host_networks格式：interface/br0/ipv4/ipv6
            extra_pri_dict['host_networks'] = f'{interface}/br0/{ipaddr}/{ip_dual_conf}'
        else:
            # 主IP是IPv6，ip_dual_conf是IPv4
            extra_pri_dict['node_ip'] = ipaddr  # 主IP作为node_ip
            extra_pri_dict['node_ip_v4'] = ip_dual_conf
            extra_pri_dict['node_ip_v6'] = ipaddr
            extra_pri_dict['pod_network_cidr'] = 'fd85:ee78:d8a6:8607::/56'
            extra_pri_dict['service_cidr'] = 'fd85:ee78:d8a6:8608::/112'
            extra_pri_dict['pod_network_cidr_v4'] = '10.40.0.0/16'
            extra_pri_dict['service_cidr_v4'] = '10.96.0.0/12'
            # 双栈host_networks格式：interface/br0/ipv4/ipv6
            extra_pri_dict['host_networks'] = f'{interface}/br0/{ip_dual_conf}/{ipaddr}'
    else:
        # 单栈配置
        extra_pri_dict['ip_type'] = ip_type
        if ip_type == consts.IP_TYPE_IPV4:
            extra_pri_dict['enable_ipip'] = enable_ipip
        extra_pri_dict['host_networks'] = f'{interface}/br0/{ipaddr}'

    if runtime == consts.RUNTIME_CONTAINERD:
        yaml_data[ocboot.GROUP_PRIMARY_MASTER_NODE].update({
            ocboot.KEY_ENABLE_CONTAINERD: True,
        })

    if len(dns_list) > 0:
        yaml_data[ocboot.GROUP_PRIMARY_MASTER_NODE].update({
            ocboot.KEY_USER_DNS: dns_list
        })

    yaml_data[ocboot.GROUP_PRIMARY_MASTER_NODE].update(extra_pri_dict)
    yaml_data[ocboot.GROUP_MARIADB_NODE].update(extra_db_dict)
    with open(temp, 'w') as f:
        f.write(yaml.dump(yaml_data))

    return temp


parser = None


def inject_common_options(parser):
    """添加 run.py 中所有命令共用的参数"""
    parser.add_argument('--ip-dual-conf', type=str, dest='ip_dual_conf',
                       help="Input the second IP address for dual-stack configuration (IPv6 if IP_CONF is IPv4, or IPv4 if IP_CONF is IPv6)")
    parser.add_argument('--enable-ipip', action='store_true', dest='enable_ipip',
                       help="Enable IPIP mode for IPv4 (default: VXLAN mode for both IPv4 single-stack and dual-stack)")
    parser.add_argument('--offline-data-path', nargs='?',
                       help="offline packages location")
    parser.add_argument('--dns', nargs='*', help='Space seperated DNS server(s), eg: --dns 1.1.1.1 8.8.8.8')
    pip_mirror_help = "specify pip mirror to install python packages smoothly"
    pip_mirror_suggest = "https://mirrors.aliyun.com/pypi/simple/"
    parser.add_argument('--pip-mirror', '-m', type=str, dest='pip_mirror',
                       help=f"{pip_mirror_help}, e.g.: {pip_mirror_suggest}")
    parser.add_argument('--k8s-v115', action='store_true', default=False,
                       help="Using old k8s v1.15 rather than k3s to manage the cluster. Default: False (using k3s)")
    parser.add_argument('--image-repository', '-i', type=str, dest='image_repository',
                       default=consts.REGISTRY_ALI_YUNIONIO,
                       help=f"Image repository for container images, e.g.: docker.io/yunion. Default: {consts.REGISTRY_ALI_YUNIONIO}")
    parser.add_argument('--region', type=str, dest='region',
                       default=consts.DEFAULT_REGION_NAME,
                       help=f"Default region name: {consts.DEFAULT_REGION_NAME}")
    parser.add_argument('--zone', type=str, dest='zone',
                       default=consts.DEFAULT_ZONE_NAME,
                       help=f"Default zone name: {consts.DEFAULT_ZONE_NAME}")


def inject_llm_nvidia_options(parser):
    """添加 llm 命令专用的 NVIDIA 相关参数"""
    parser.add_argument("--nvidia-driver-installer-path",
                       dest="nvidia_driver_installer_path",
                       required=False,
                       help="Full path to NVIDIA driver installer (e.g., /root/nvidia/NVIDIA-Linux-x86_64-570.133.07.run). If not provided, assumes NVIDIA driver is already installed")
    parser.add_argument("--cuda-installer-path",
                       dest="cuda_installer_path",
                       required=False,
                       help="Full path to CUDA installer (e.g., /root/nvidia/cuda_12.8.1_570.124.06_linux.run). If not provided, assumes CUDA is already installed")
    parser.add_argument("--nvidia-driver-tar-file-path",
                       dest="nvidia_driver_tar_file_path",
                       default="/root/nvidia/nvidia-driver-vol.tar.gz",
                       help=help_d("Full path to NVIDIA driver tar file"))
    parser.add_argument("--gpu-device-count",
                       dest="gpu_device_count",
                       type=int,
                       default=8,
                       help=help_d("Number of GPU devices"))


def get_args():
    global parser
    parser = argparse.ArgumentParser()
    
    parser.add_argument('STACK', metavar="stack", type=str, nargs=1,
                        help="Choose the product type from ['full', 'cmp', 'virt', 'light-virt', 'llm']",
                        choices=['full', 'cmp', 'virt', 'light-virt', 'llm'])
    parser.add_argument('IP_CONF', metavar="ip_conf", type=str, nargs='?',
                       help="Input the target IPv4 or Config file")
    
    # 添加共用参数
    inject_common_options(parser)
    
    # 添加 hostagent 和 runtime 选项
    inject_add_hostagent_options(parser)
    inject_add_nodes_runtime_options(parser)
    
    # 如果是 llm stack，添加 NVIDIA 相关参数
    # 注意：这里需要在解析后才能判断，所以参数总是添加，但只在 llm 模式下必需
    inject_llm_nvidia_options(parser)
    
    return parser.parse_args()


def ensure_python3_yaml(os):

    username = get_username()
    if os == 'redhat':
        query = "sudo rpm -qa"
        installer = "yum"
    elif os == 'debian':
        if username == 'root':
            query = "dpkg -l"
            installer = "apt"
        else:
            query = "sudo dpkg -l"
            installer = "sudo apt"
        # subprocess.check_output(f"{installer} update -y", shell=True)
    else:
        print("OS not supported")
        exit(1)

    print(f'ensure_python3_yaml: os: {os}; query: {query}; installer: {installer}')

    output = subprocess.check_output(query, shell=True).decode('utf-8')

    if regex_search(r'python3.*pyyaml', output, ignore_case=True):
        print("PyYAML already installed")
        return

    output = subprocess.check_output(f"{installer} search yaml", shell=True).decode('utf-8')

    pkg = regex_search(r'python3\d?-(py)?yaml|PyYAML', output, ignore_case=True)
    if not pkg:
        print("No python3 package found")
    else:
        cmd = f"{installer} install -y {pkg}"
        print(f'command to run : [{cmd}]')
        subprocess.run(f"{installer} install -y {pkg}", shell=True)


def get_default_ip(args):
    ip_conf = args.IP_CONF
    if ip_conf and len(ip_conf) > 0:
        return str(ip_conf)
    # find default ip address
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 1))  # connect() for UDP doesn't send packets
    sockname = s.getsockname()
    local_ip_address = sockname[0]
    s.close()
    return local_ip_address


def main():
    init_local_user_path()
    args = get_args()
    user_dns = []
    if args.dns:
        user_dns = [i for i in args.dns if is_valid_dns(i)]

    stack = args.STACK[0]
    ip_conf = get_default_ip(args)

    # 检测IP类型，支持双栈配置
    detect_and_display_ip_type(ip_conf, args.ip_dual_conf)

    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    stackDict = {
        'full': ocboot.KEY_STACK_FULLSTACK,
        'cmp': ocboot.KEY_STACK_CMP,
        'virt': ocboot.KEY_STACK_EDGE,
        'light-virt': ocboot.KEY_STACK_LIGHT_EDGE,
        'llm': ocboot.KEY_STACK_FULLSTACK,  # llm 使用 full stack
    }

    # 设置共同环境
    setup_common_environment(args)

    # 重新检测IP类型（因为上面的检测可能被覆盖）
    if args.ip_dual_conf:
        match_ip, ip_type = match_dual_stack_ipaddr(ip_conf, args.ip_dual_conf)
    else:
        match_ip, ip_type = match_ipaddr(ip_conf)

    # 处理 llm 模式
    is_llm_mode = (stack == 'llm')
    if is_llm_mode:
        # llm 模式自动使用 containerd runtime
        runtime = consts.RUNTIME_CONTAINERD
        pr_green("LLM mode: Using containerd runtime and full stack")
    else:
        # 普通模式：使用用户指定的 runtime
        runtime = args.runtime

    # 生成配置文件
    if match_ip:
        conf = generate_config(ip_conf, stackDict.get(stack),
                               user_dns, runtime,
                               args.image_repository,
                               args.region, args.zone,
                               ip_dual_conf=args.ip_dual_conf,
                               ip_type=ip_type,
                               enable_ipip=args.enable_ipip)
    elif path.isfile(ip_conf) and path.getsize(ip_conf) > 0:
        conf = update_config(ip_conf, stackDict.get(stack), runtime)
    else:
        pr_red(f'The configuration file <{ip_conf}> does not exist or is not valid!')
        exit()
    
    check_env(ip_conf, pip_mirror=args.pip_mirror)
    
    # 如果是 llm 模式，设置 enable_llm_env，并根据是否提供参数决定是否传递 NVIDIA 变量
    extra_vars = None
    if is_llm_mode:
        extra_vars = {
            'enable_llm_env': True,
            'gpu_device_count': args.gpu_device_count,
        }
        
        # 只有在提供了 NVIDIA 相关参数时才添加这些变量
        if args.nvidia_driver_installer_path:
            extra_vars['nvidia_driver_installer_path'] = args.nvidia_driver_installer_path
        if args.cuda_installer_path:
            extra_vars['cuda_installer_path'] = args.cuda_installer_path
        if args.nvidia_driver_tar_file_path:
            extra_vars['nvidia_driver_tar_file_path'] = args.nvidia_driver_tar_file_path
        
        if args.nvidia_driver_installer_path and args.cuda_installer_path:
            pr_green("Starting allinone installation with containerd runtime and LLM environment setup (including NVIDIA driver installation)...")
        else:
            pr_green("Starting allinone installation with containerd runtime and LLM environment setup (assuming NVIDIA drivers are already installed)...")
    else:
        pr_green(f"Starting installation with {stack} stack...")
    
    return install.start(conf, extra_vars=extra_vars)


def detect_and_display_ip_type(ip_conf, ip_dual_conf=None):
    """检测并显示 IP 地址类型"""
    if ip_dual_conf:
        match_ip, ip_type = match_dual_stack_ipaddr(ip_conf, ip_dual_conf)
        if match_ip:
            if ip_type == consts.IP_TYPE_DUAL_STACK:
                if _match_ip4addr(ip_conf):
                    ipv4_addr = ip_conf
                    ipv6_addr = ip_dual_conf
                else:
                    ipv4_addr = ip_dual_conf
                    ipv6_addr = ip_conf
                pr_green(f"choose dual-stack configuration: IPv4={ipv4_addr}, IPv6={ipv6_addr}")
            else:
                pr_green(f"choose {ip_type} address: {ip_conf}")
        else:
            pr_red(f"Invalid dual-stack configuration: {ip_conf}, {ip_dual_conf}")
            exit(1)
        return match_ip, ip_type
    else:
        match_ip, ip_type = match_ipaddr(ip_conf)
        if match_ip:
            pr_green(f"choose local {ip_type} address: {ip_conf}")
        return match_ip, ip_type


def setup_common_environment(args):
    """设置共同的环境变量和处理离线数据路径"""
    # 设置环境变量
    if not args.k8s_v115:
        os.environ[consts.ENV_K3S] = consts.ENV_VAL_TRUE
    else:
        os.environ[consts.ENV_K8S_V115] = consts.ENV_VAL_TRUE
    
    # 处理离线数据路径
    offline_data_path = None
    if args.offline_data_path and os.path.isdir(args.offline_data_path):
        offline_data_path = os.path.realpath(args.offline_data_path)
    elif os.environ.get('OFFLINE_DATA_PATH') and os.path.isdir(os.environ.get('OFFLINE_DATA_PATH')):
        offline_data_path = os.path.realpath(os.environ.get('OFFLINE_DATA_PATH'))
    
    if offline_data_path:
        os.environ['OFFLINE_DATA_PATH'] = offline_data_path
    else:
        os.environ['OFFLINE_DATA_PATH'] = ''
        if os.system('test -x /usr/bin/apt') == 0:
            install_packages(['python3-pip'])
            ensure_python3_yaml('debian')
        elif os.system('test -x /usr/bin/yum') == 0:
            install_packages(['python3-pip'])
            os.system('python3 -m pip install pyyaml')
            ensure_python3_yaml('redhat')




if __name__ == "__main__":
    sys.exit(main())
