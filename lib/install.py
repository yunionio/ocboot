# encoding: utf-8
import argparse
import sys
import os

from . import ocboot
from . import cmd
from . import logger

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


def start(config_file):
    config = ocboot.load_config(config_file)
    inventory_f = config.generate_inventory_file()

    return_code = cmd.run_ansible_playbook(
        inventory_f,
        './onecloud/install-cluster.yml',
        vars=config.ansible_global_vars(),
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
    return 0
