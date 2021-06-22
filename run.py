#!/usr/bin/env python

import os
import sys
import re
import yaml

from lib import install


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


def random_password(num):
    assert(num >= 6)
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


conf = """# mariadb_node indicates the node where the mariadb service needs to be deployed
mariadb_node:
  # IP of the machine to be deployed
  hostname: 10.127.10.158
  # SSH Login username of the machine to be deployed
  user: root
  # Username of mariadb
  db_user: root
  # Password of mariadb
  db_password: your-sql-password
# primary_master_node indicates the machine running Kubernetes and OneCloud Platform
primary_master_node:
  hostname: 10.127.10.158
  user: root
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
  # Yunion OneCloud version
  onecloud_version: 'v3.4.12'
  # Yunion OneCloud login username
  onecloud_user: admin
  # Yunion OneCloud login user's password
  onecloud_user_password: admin@123
  # This machine serves as a Yunion OneCloud private cloud computing node
  as_host: true
"""

def gen_config(ipaddr):
    global conf
    import os.path
    cur_path = os.path.abspath(os.path.dirname(__file__))
    temp = os.path.join(cur_path, "config-allinone-current.yml")
    verf = os.path.join(cur_path, "VERSION")
    with open(verf, 'r') as f:
        ver = f.read().strip()

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

    mypass = random_password(12)
    with open(temp, 'w') as f:
        f.write(conf.replace('10.127.10.158', ipaddr).replace('your-sql-password', mypass).replace('v3.4.12', ver))
    return temp


def main():
    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    if len(sys.argv) != 2:
        show_usage()
        sys.exit(1)

    if match_ip4addr(sys.argv[1]):
        conf = gen_config(sys.argv[1])
    else:
        conf = sys.argv[1]
    return install.start(conf)


if __name__ == "__main__":
    sys.exit(main())
