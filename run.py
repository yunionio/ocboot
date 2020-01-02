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


def ansible_playbook(hosts_f, playbook_f):
    cmd = ["ansible-playbook", "-e", "ANSIBLE_HOST_KEY_CHECKING=False",
           "-i", hosts_f, playbook_f]
    run_cmd(cmd)


def start(config_file):

    root = os.path.dirname(os.path.realpath(__file__))
    config = ansible.load_config(config_file)
    playbook_f = os.path.join( root, "onecloud/zz_generated.site.yml")
    hosts_f = os.path.join(root, "onecloud/zz_generated.hosts")
    config.generate_hosts_file(hosts_f)
    config.generate_site_file(playbook_f)
    ansible_playbook(hosts_f, playbook_f)


def show_usage():
    usage = '''
Usage: %s <config_file>.yml
''' % __file__
    print(usage)


def main():
    if len(sys.argv) != 2:
        show_usage()
        sys.exit(1)
    start(sys.argv[1])


if __name__ == "__main__":
    main()
