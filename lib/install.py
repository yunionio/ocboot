# encoding: utf-8

import platform
import os
import time

from . import ocboot
from . import cmd
from . import logger
from . import kernel_utils

logger = logger.new(__file__)


EE_INSTALLED_STR = """Initialized successfully!

Check Web Page: https://%s

To start using the command line tools, you need to `source ~/.bashrc` profile or relogin.
"""


CE_INSTALLED_STR = """Initialized successfully!
Web page: https://%s
User: %s
Password: %s
"""

REBOOT_MSG = """
┌───────────────────────────────────────────────────────────────────────────────┐
│                                                                               │
│   The system is about to reboot in 30 secs to use new kernel.                 │
│   You may abort the reboot by press Ctrl + C, and manually reboot later.      │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘

"""

REBOOT_TIMEOUT = 30

def add_command(subparsers):
    parser = subparsers.add_parser("install", help="install onecloud cluster")
    parser.add_argument('config', help="config yaml file")
    parser.set_defaults(func=do_install)


def do_install(args):
    try:
        return start(args.config)
    except (ocboot.ConfigNotFoundException) as e:
        logger.error("%s" % e)
    except Exception as e:
        raise e

def need_reboot(ip, inside):
    if not kernel_utils.is_centos():
        return False
    if os.environ.get('NO_REBOOT', ''):
        print("NO_REBOOT flag passed, ignore rebooting")
        return False
    if not ip:
        return False
    if (inside is False) and (not kernel_utils.is_local_ip(ip)):
        return False
    if kernel_utils.is_local_ip(ip) and inside is True:
        return False
    if kernel_utils.is_yunion_kernel():
        return False
    return True


def try_reboot_primary(ip):
    if not need_reboot(ip, inside=False):
        return

    print(REBOOT_MSG)

    for i in range(REBOOT_TIMEOUT):
        time.sleep(1)
        print("."),
    os.system('reboot')


def start(config_file):
    config = ocboot.load_config(config_file)

    inventory_f = config.generate_inventory_file()
    ip = None
    try:
        ip = config.primary_master_config.node.node_ip
    except AttributeError:
        pass
    vars = config.ansible_global_vars()
    vars['no_reboot'] = 'false' if need_reboot(ip, inside=True) else 'true'
    return_code = cmd.run_ansible_playbook(
        inventory_f,
        './onecloud/install-cluster.yml',
        vars=vars,
    )
    if return_code is not None and return_code != 0:
        return return_code

    login_info = config.get_login_info()
    if login_info is None:
        return 0
    if config.is_using_ee():
        print(EE_INSTALLED_STR % (login_info[0]))
    else:
        print(CE_INSTALLED_STR % (login_info[0],
                                  login_info[1],
                                  login_info[2]))

    try_reboot_primary(ip)

    return 0
