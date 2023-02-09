# encoding: utf-8
from __future__ import unicode_literals

from .service import AddLBAgentService


def add_command(subparsers):
    AddLBAgentService(subparsers, "add-lbagent", "add new lbagent node into cluster")
