# encoding: utf-8
from __future__ import unicode_literals

from .service import RoutineInspectionService


def add_command(subparsers):
    RoutineInspectionService(subparsers, "check", "routine check")
