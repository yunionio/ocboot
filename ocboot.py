#!/usr/bin/env python3

import sys
import argparse

from lib import install
from lib import upgrade
from lib import backup, restore
from lib import ansible
from lib import add_node
from lib import ce, ee
from lib import auto_backup


def main():
    parser = argparse.ArgumentParser(prog='ocboot.py')
    subparsers = parser.add_subparsers(dest="subcmd",
                                       title="sub commands",
                                       help='sub-command help')
    add_node.add_command(subparsers)
    auto_backup.add_command(subparsers)
    backup.add_command(subparsers)
    ce.add_command(subparsers)
    ee.add_command(subparsers)
    install.add_command(subparsers)
    restore.add_command(subparsers)
    upgrade.add_command(subparsers, command=upgrade.UPGRADE_MODES_UPGRADE)
    upgrade.add_command(subparsers, command=upgrade.UPGRADE_MODES_UPGRADE_CONTROLLER)
    upgrade.add_command(subparsers, command=upgrade.UPGRADE_MODES_UPGRADE_HOST)
    upgrade.add_command(subparsers, command=upgrade.UPGRADE_MODES_UPGRADE_FINAL)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
