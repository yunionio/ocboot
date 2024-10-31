#!/usr/bin/env python3

import sys
import argparse

from lib import install, switch_edition
from lib import upgrade
from lib import backup, restore
from lib import add_node
from lib import add_lbagent
from lib import stop, start
from lib import ce, ee
from lib import auto_backup
from lib import setup_container_env


def main():
    parser = argparse.ArgumentParser(prog='ocboot.py')
    subparsers = parser.add_subparsers(dest="subcmd",
                                       title="sub commands",
                                       help='sub-command help')
    add_lbagent.add_command(subparsers)
    add_node.add_command(subparsers)
    auto_backup.add_command(subparsers)
    backup.add_command(subparsers)
    switch_edition.add_command(subparsers)
    install.add_command(subparsers)
    restore.add_command(subparsers)
    start.add_command(subparsers)
    stop.add_command(subparsers)
    setup_container_env.add_command(subparsers)
    upgrade.add_command(subparsers, command=upgrade.UPGRADE_MODES_UPGRADE)
    upgrade.add_command(subparsers, command=upgrade.UPGRADE_MODES_UPGRADE_CONTROLLER)
    upgrade.add_command(subparsers, command=upgrade.UPGRADE_MODES_UPGRADE_HOST)
    upgrade.add_command(subparsers, command=upgrade.UPGRADE_MODES_UPGRADE_FINAL)
    args = parser.parse_args()
    if not args.subcmd:
        parser.print_help()
    else:
        args.func(args)


if __name__ == "__main__":
    sys.exit(main())
