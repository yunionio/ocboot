# encoding: utf-8
from __future__ import unicode_literals

from .service import Service


def add_command(subparsers):
    Service(subparsers, 'ee')
