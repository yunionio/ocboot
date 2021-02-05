import argparse
import sys
import os


from . import ansible


def add_command(subparsers):
    parser = subparsers.add_parser("install", help="install onecloud cluster")
    parser.add_argument('config', help="config yaml file")
    parser.set_defaults(func=do_install)


def do_install(args):
    return start(args.config)


def start(config_file):
    return ansible.AnsiblePlaybook(config_file).run_install()
