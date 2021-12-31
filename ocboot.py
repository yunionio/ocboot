#!/usr/bin/env python

import sys
import argparse

from lib import install, upgrade
from lib import backup, restore
from lib import ansible
from lib import add_node


def main():
    parser = argparse.ArgumentParser(prog='ocboot.py')
    subparsers = parser.add_subparsers(dest="subcmd",
                                       title="sub commands",
                                       help='sub-command help')
    install.add_command(subparsers)
    upgrade.add_command(subparsers)
    add_node.add_command(subparsers)
    backup.add_command(subparsers)
    restore.add_command(subparsers)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
