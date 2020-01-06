#!/usr/bin/env python

import os
import sys
import subprocess

from lib import ansible


def run_cmd(cmds):
    print(' '.join(cmds))
    os.environ['ANSIBLE_FORCE_COLOR'] = '1'
    proc = subprocess.Popen(
        cmds,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,)
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        print(line.rstrip())
    proc.wait()
    return proc.returncode


def ansible_playbook(hosts_f, playbook_f):
    cmd = ["ansible-playbook", "-e", "ANSIBLE_HOST_KEY_CHECKING=False",
           "-i", hosts_f, playbook_f]
    return run_cmd(cmd)


def start(config_file):
    root = os.path.dirname(os.path.realpath(__file__))
    config = ansible.load_config(config_file)
    playbook_f = os.path.join( root, "onecloud/zz_generated.site.yml")
    hosts_f = os.path.join(root, "onecloud/zz_generated.hosts")
    config.generate_hosts_file(hosts_f)
    config.generate_site_file(playbook_f)
    returncode = ansible_playbook(hosts_f, playbook_f)
    if returncode is not None and returncode != 0:
        return returncode
    login_info = config.get_login_info()
    if login_info is None:
        return 0
    print("""Initialized successfully!
Web page: https://%s
User: %s
Password: %s
""" % (login_info[0], login_info[1], login_info[2])
)
    return 0


def show_usage():
    usage = '''
Usage: %s <config_file>.yml
''' % __file__
    print(usage)


def main():
    if len(sys.argv) != 2:
        show_usage()
        sys.exit(1)
    return start(sys.argv[1])


if __name__ == "__main__":
    sys.exit(main())
