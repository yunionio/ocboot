# encoding: utf-8

from shutil import copyfile
import MySQLdb
import os

from . import ocboot
from .db import backup_config, backup_db
from cmd import run_bash_cmd

def add_command(subparsers):
    parser = subparsers.add_parser(
        "backup", help="backup onecloud cluster")
    parser.add_argument('config', help="config yaml file")
    parser.add_argument('--backup-path', help="backup path", default="/opt/backup")
    parser.set_defaults(func=do_backup)


def do_backup(args):
    config = ocboot.load_config(args.config)

    backup_config(args.config, args.backup_path)
    backup_db(config, args.backup_path)
