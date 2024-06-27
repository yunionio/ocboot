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
from lib.parser import inject_add_hostagent_options
from lib.utils import init_local_user_path
from lib.utils import pr_red, pr_green
from lib.utils import regex_search
from lib.utils import is_valid_dns
from lib import ocboot


def show_usage():
    usage = '''
Usage: %s [master_ip|<config_file>.yml]
''' % __file__
    print(usage)


IPADDR_REG_PATTERN = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
IPADDR_REG = re.compile(IPADDR_REG_PATTERN)


def match_ip4addr(string):
    global IPADDR_REG
    return IPADDR_REG.match(string) is not None


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


def check_passless_ssh(ipaddr):
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
    if match_ip4addr(ipaddr):
        check_passless_ssh(ipaddr)


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


def update_config(yaml_conf, produc_stack):
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
    if to_write:
        with open(yaml_conf, 'w') as f:
            f.write(yaml.dump(yaml_data))

    return yaml_conf


def generate_config(ipv4, produc_stack, dns_list=[]):
    global conf
    import os.path
    import os
    dynamic_load()
    import yaml
    from lib.get_interface_by_ip import get_interface_by_ip

    config_dir = os.getenv("OCBOOT_CONFIG_DIR")
    image_repository = os.getenv('IMAGE_REPOSITORY')

    cur_path = os.path.abspath(os.path.dirname(__file__))
    if not config_dir:
        config_dir = cur_path
    if not match_ip4addr(ipv4):
        pr_red(f'invalid ipv4 {ipv4}!')
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

    if yaml_data.get(ocboot.GROUP_PRIMARY_MASTER_NODE, {}).get(ocboot.KEY_HOSTNAME, '') == ipv4 and \
            yaml_data.get(ocboot.GROUP_PRIMARY_MASTER_NODE, {}).get(ocboot.KEY_ONECLOUD_VERSION, '') == ver:
        update_config(temp, produc_stack)
        pr_green(f"reuse conf: {temp}")
        return temp

    # using given image_repository if provided;
    if image_repository not in ['', None, 'none']:
        yaml_data[ocboot.GROUP_PRIMARY_MASTER_NODE]['image_repository'] = image_repository
    # else set to 'yunionio' namespace if it is daily build.
    # default is 'yunion', for the official and public release.
    elif re.search(r'\b\d{8}\.\d$', ver):
        yaml_data[ocboot.GROUP_PRIMARY_MASTER_NODE]['image_repository'] = 'registry.cn-beijing.aliyuncs.com/yunionio'

    if image_repository and '5000' in image_repository:
        r = image_repository
        if '/' in r:
            r = r.split('/')[0]
        yaml_data[ocboot.GROUP_PRIMARY_MASTER_NODE]['insecure_registries'] = [r]

    interface = get_interface_by_ip(ipv4)
    username = get_username()
    db_password = random_password(12) if brand_new else yaml_data.get(ocboot.GROUP_PRIMARY_MASTER_NODE, {}).get('db_password')
    assert db_password
    extra_db_dict = {
        'db_password': db_password,
        'user': username,
        ocboot.KEY_HOSTNAME: ipv4,
    }
    enable_host = produc_stack in [ocboot.KEY_STACK_FULLSTACK, ocboot.KEY_STACK_EDGE]
    extra_pri_dict = {
        'controlplane_host': ipv4,
        'db_host': ipv4,
        'db_password': db_password,
        'host_networks': f'{interface}/br0/{ipv4}',
        'user': username,
        ocboot.KEY_AS_HOST: enable_host,
        ocboot.KEY_AS_HOST_ON_VM: enable_host,
        ocboot.KEY_HOSTNAME: ipv4,
        ocboot.KEY_ONECLOUD_VERSION: ver,
        ocboot.KEY_PRODUCT_VERSION: produc_stack,
    }

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


def get_args():
    global parser
    parser = argparse.ArgumentParser()
    parser.add_argument('STACK', metavar="stack", type=str, nargs=1,
                        help="Choose the product type from ['full', 'cmp', 'virt']",
                        choices=['full', 'cmp', 'virt'])
    parser.add_argument('IP_CONF', metavar="ip_conf", type=str, nargs='?',
                        help="Input the target IPv4 or Config file")
    parser.add_argument('--offline-data-path', nargs='?',
                        help="offline packages location")
    parser.add_argument('--dns', nargs='*', help='Space seperated DNS server(s), eg: --dns 1.1.1.1 8.8.8.8')
    pip_mirror_help = "specify pip mirror to install python packages smoothly"
    pip_mirror_suggest = "https://mirrors.aliyun.com/pypi/simple/"
    parser.add_argument('--pip-mirror', '-m', type=str, dest='pip_mirror',
                        help=f"{pip_mirror_help}, e.g.: {pip_mirror_suggest}")
    parser.add_argument('--k3s', action='store_true', default=False,
                        help="Using k3s rather than k8s to manage the cluster. Default: False (using k8s)")
    inject_add_hostagent_options(parser)
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
    if match_ip4addr(ip_conf):
        pr_green(f"choose local ip address: {ip_conf}")
    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    stackDict = {
        'full': ocboot.KEY_STACK_FULLSTACK,
        'cmp': ocboot.KEY_STACK_CMP,
        'virt': ocboot.KEY_STACK_EDGE,
    }

    if args.k3s:
        os.environ['K3S'] = 'TRUE'

    # 1. try to get offline data path from optional args
    # 2. if not exist, try to get from os env
    # 3. if got one, save to env for later use.
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
    if match_ip4addr(ip_conf):
        conf = generate_config(ip_conf, stackDict.get(stack), user_dns)
    elif path.isfile(ip_conf) and path.getsize(ip_conf) > 0:
        conf = update_config(ip_conf, stackDict.get(stack))
    else:
        pr_red(f'The configuration file <{ip_conf}> does not exist or is not valid!')
        exit()
    check_env(ip_conf, pip_mirror=args.pip_mirror)
    return install.start(conf)


if __name__ == "__main__":
    sys.exit(main())
