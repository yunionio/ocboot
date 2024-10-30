# encoding: utf-8
from __future__ import unicode_literals

from .service import PrimaryMasterService


def add_command(subparsers):
    PrimaryMasterService(subparsers, 'ce')
