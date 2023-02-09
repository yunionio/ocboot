# encoding: utf-8
from __future__ import unicode_literals

from .service import AddNodeService


def add_command(subparsers):
    AddNodeService(subparsers, "add-node", "add new node into cluster")
