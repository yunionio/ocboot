# encoding: utf-8

from . import ocboot
from .db import backup_config, backup_db
from .utils import print_title
from .cmd import ensure_pv

def add_command(subparsers):
    parser = subparsers.add_parser(
        "backup", help="backup onecloud cluster")
    parser.add_argument('config', help="config yaml file")
    parser.add_argument('--backup-path', help="backup path, default: /opt/backup", default="/opt/backup")
    parser.add_argument('--light', action='store_true', help="ignore yunionmeter and yunionlogger database; ignore tables start with 'opslog' and 'task'.")
    parser.set_defaults(func=do_backup)


def do_backup(args):
    ensure_pv()
    config = ocboot.load_config(args.config)

    backup_config(args.config, args.backup_path)
    backup_db(config, args.backup_path, args.light)
    print_title('Backup to: %s' % args.backup_path)
