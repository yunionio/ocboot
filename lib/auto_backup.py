# encoding: utf-8

from . import ocboot
from .utils import print_title
from .cmd import ensure_pv
from .service import AutoBackupService


def add_command(subparsers):
    AutoBackupService(subparsers, 'auto-backup')
