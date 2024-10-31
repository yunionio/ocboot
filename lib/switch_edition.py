# encoding: utf-8
from __future__ import unicode_literals

from lib import consts
from lib.ocboot import KEY_TARGET_EDITION

from .service import PrimaryMasterService


def add_command(subparsers):
    SwitchEditionService(subparsers)


class SwitchEditionService(PrimaryMasterService):

    def __init__(self, subparsers):
        super().__init__(subparsers, 'switch-edition')

    def inject_options(self, parser):
        super().inject_options(parser)
        parser.add_argument('edition',
                            metavar='EDITION',
                            choices=consts.EDITIONS,
                            help=f"choice edition from {consts.EDITIONS}")

    def get_ansible_vars(self, args, cluster, primary_master_host):
        vars = super().get_ansible_vars(args, cluster, primary_master_host)
        vars[KEY_TARGET_EDITION] = args.edition
        return vars
