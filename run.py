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
from lib import install
from lib import cmd
from lib.parser import inject_add_hostagent_options
from lib.utils import init_local_user_path
from lib.utils import prRed
from lib.utils import tryBackupFile
import subprocess


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
    minimal_ansible_version = '2.9.27'
    cmd.init_ansible_playbook_path()
    ret = os.system("ansible-playbook --version >/dev/null 2>&1")
    if ret == 0:
        ansible_version = os.popen("""ansible-playbook --version | head -1 | grep -oP '[0-9.]+' """).read().strip()
        if version_ge(ansible_version, minimal_ansible_version):
            print("current ansible version: %s. PASS" % ansible_version)
            return
        else:
            print("Current ansible version (%s) is lower than expected(%s). upgrading ... " % (ansible_version, minimal_ansible_version))
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
    cmdline = 'sudo %s install -y %s' % (packager, ' '.join(pkgs))
    return os.system(cmdline)

def install_ansible(mirror):

    def get_pip_install_cmd(suffix_cmd, mirror):
        cmd = "python3 -m pip install --user --upgrade"
        if mirror:
            cmd = f'{cmd} -i {mirror}'
        return f'{cmd} {suffix_cmd}'

    for pkg in ['python2-pyyaml', 'PyYAML']:
        install_packages([pkg])

    if os.system('rpm -qa | grep -q python3-pip') != 0:
        ret = os.system(get_pip_install_cmd('pip setuptools wheel', mirror))
        if ret != 0:
            raise Exception("Install/updrade pip3 failed. ")
    os.system(get_pip_install_cmd('pip', mirror))
    ret = os.system(get_pip_install_cmd('ansible', mirror))
    if ret != 0:
        raise Exception("Install ansible failed. ")

def check_passless_ssh(ipaddr):
    username = get_username()
    cmd = f"ssh -o 'StrictHostKeyChecking=no' -o 'PasswordAuthentication=no' {username}@{ipaddr} uptime"
    print('cmd:', cmd)
    ret = os.system(cmd)
    if ret == 0:
        return
    else:
        raise Exception(
            "Passwordless ssh failed, please configure passwordless ssh to %s@%s" % (username, ipaddr))
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
    check_ansible(pip_mirror)
    if ipaddr:
        check_passless_ssh(ipaddr)


def random_password(num):
    assert (num >= 6)
    digits = r'23456789'
    letters = r'abcdefghjkmnpqrstuvwxyz'
    uppers = letters.upper()
    punc = r'' # !$@#%^&*-=+?;'
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
  as_host: true
  # as_host_on_vm: true
  # enable_eip_man for all-in-one mode only
  enable_eip_man: true
  # chose product_version in ['FullStack', 'CMP', 'Edge']
  product_version: 'product_stack'
  image_repository: registry.cn-beijing.aliyuncs.com/yunion
  # host_networks: '<interface>/br0/<ip>'
"""


def dynamic_load():
    username = get_username()

    import glob
    paths = glob.glob('/usr/local/lib64/python3.?/site-packages/') + \
        glob.glob('/usr/local/lib64/python3.??/site-packages/') + \
        glob.glob(f'/home/{username}/.local/lib/python3.?/site-packages') + \
        glob.glob(f'/home/{username}/.local/lib/python3.??/site-packages')

    print("loading path:")

    for p in paths:
        if os.path.isdir(p) and p not in sys.path:
            sys.path.append(p)
            print("\t%s" % p)


def gen_config(ipaddr, product_stack, enable_host_on_vm):
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
    temp = os.path.join(config_dir, "config-allinone-current.yml")
    tryBackupFile(temp)
    verf = os.path.join(cur_path, "VERSION")
    with open(verf, 'r') as f:
        ver = f.read().strip()

    # parameter first; then daily build; at last official build
    if image_repository not in ['', None, 'none']:
        conf = conf.replace('registry.cn-beijing.aliyuncs.com/yunion', image_repository)
    elif re.search(r'\b\d{8}\.\d$', ver):
        conf = conf.replace('registry.cn-beijing.aliyuncs.com/yunion', 'registry.cn-beijing.aliyuncs.com/yunionio')

    if os.path.exists(temp):
        with open(temp, 'r') as stream:
            try:
                data = (yaml.safe_load(stream))
                if data.get('primary_master_node', {}).get('hostname', '') == ipaddr and \
                   data.get('primary_master_node', {}).get('onecloud_version', '') == ver:
                    print("reuse current yaml: %s" % temp)
                    return temp
            except yaml.YAMLError as exc:
                raise Exception("paring %s error: %s" % (temp, exc))

    mypass_clickhouse = random_password(12)
    mypass_mariadb = random_password(12)
    interface = get_interface_by_ip(ipaddr)
    host_networks = f'''host_networks: "{interface}/br0/{ipaddr}"'''
    with open(temp, 'w') as f:
        conf_result = conf.replace('10.127.10.158', ipaddr) \
                .replace('your-sql-password', mypass_mariadb) \
                .replace('your-clickhouse-password', mypass_clickhouse) \
                .replace('ocboot_user', get_username()) \
                .replace('v3.4.12', ver) \
                .replace("# host_networks: '<interface>/br0/<ip>'", host_networks) \
                .replace('product_stack', product_stack)
        if enable_host_on_vm:
            conf_result = conf_result.replace('# as_host_on_vm: true', 'as_host_on_vm: true')

        f.write(conf_result)
    return temp


def update_config(conf_file, product_version):
    if not os.path.exists(conf_file):
        raise Exception(f"Conf file {conf_file} dose not exist!")

    if product_version not in ['FullStack', 'CMP', 'Edge']:
        raise Exception(f"Product version {product_version} is not valid! Only 'FullStack', 'CMP', 'Edge' ar supported.")

    with open(conf_file, 'r') as f:
        conf = f.read().strip()

    with open(conf_file, 'w') as f:
        regex = r"^  product_version: (.*)"
        subst = f"  product_version: '{product_version}'"
        conf = re.sub(regex, subst, conf, 0, re.MULTILINE)
        f.write(conf)
        print('conf updated.')
        return conf


parser = None

def get_args():
    """show argpase snippets"""
    global parser
    parser = argparse.ArgumentParser()
    parser.add_argument('IP_CONF', nargs=1, type=str,
                        help="Input the target IPv4 or Config file")
    parser.add_argument('--offline-data-path', nargs='?',
                        help="offline packages location")
    # chose product_version in ['FullStack', 'CMP', 'Edge']
    parser.add_argument('--stack', type=str, default='fullstack',
                        help="choose product version",
                        choices=['fullstack', 'cmp', 'edge'])
    pip_mirror_help = "specify pip mirror to install python packages smoothly"
    pip_mirror_suggest = "https://mirrors.aliyun.com/pypi/simple/"
    parser.add_argument('--pip-mirror', '-m', type=str, dest='pip_mirror',
                        help=f"{pip_mirror_help}, e.g.: {pip_mirror_suggest}")
    inject_add_hostagent_options(parser)
    return parser.parse_args()


def ensure_python3_yaml(os):

    if os == 'redhat':
        query = "sudo rpm -qa"
        installer = "yum"
    elif os == 'debian':
        query = "sudo dpkg -l"
        installer = "apt"
    else:
        print("OS not supported")
        exit(1)

    print(f'ensure_python3_yaml: os: {os}; query: {query}; installer: {installer}')
    output = subprocess.check_output(query, shell=True).decode('utf-8')

    if "python3.*pyyaml" in output:
        print("PyYAML already installed")
        return

    output = subprocess.check_output(f"sudo {installer} search pyyaml", shell=True).decode('utf-8')

    match = re.search(r'python3\d?-pyyaml', output, re.IGNORECASE)
    if match:
        pkg = match.group(0)
    else:
        pkg = None

    if not pkg:
        print("No python3 package found")
        exit(1)
    else:
        subprocess.run(f"sudo {installer} install -y {pkg}", shell=True)


def main():
    init_local_user_path()
    args = get_args()
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    ip_conf = str(args.IP_CONF[0])

    product_stack = ''
    got_stack = args.stack.lower()
    if got_stack in ['fullstack', '', None]:
        product_stack = 'FullStack'
    elif got_stack == 'cmp':
        product_stack = 'CMP'
    elif got_stack == 'edge':
        product_stack = 'Edge'

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
            if os.system('grep -wq "Ubuntu" /etc/os-release') == 0:
                install_packages(['python3-pip', 'python3-yaml'])
            else:
                install_packages(['python3-pip'])
                ensure_python3_yaml('debian')
        elif os.system('test -x /usr/bin/yum') == 0:
            install_packages(['python3-pip', 'python2-pyyaml'])
            ensure_python3_yaml('redhat')

    if match_ip4addr(ip_conf):
        check_env(ip_conf, pip_mirror=args.pip_mirror)
        conf = gen_config(ip_conf, product_stack, args.enable_host_on_vm)
    elif path.isfile(ip_conf):
        sz = path.getsize(ip_conf)
        if sz == 0:
            prRed(f'Config file <{ip_conf}> is Empty!')
            exit()
        check_env(pip_mirror=args.pip_mirror)
        update_config(ip_conf, product_stack)
        conf = ip_conf
    else:
        prRed(f'The configuration file <{ip_conf}> does not exist or is not valid!')
        exit(1)
    return install.start(conf)


if __name__ == "__main__":
    sys.exit(main())
