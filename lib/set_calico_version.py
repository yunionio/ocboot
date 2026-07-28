# encoding: utf-8
from __future__ import unicode_literals

import re

from .service import PrimaryMasterService

VERSION_RE = re.compile(r'^v?\d+\.\d+\.\d+$')


def add_command(subparsers):
    SetCalicoVersionService(subparsers)


def normalize_version(version):
    version = (version or '').strip()
    if not VERSION_RE.match(version):
        raise Exception(
            'invalid calico version %r, expect like v3.26.4' % version)
    if not version.startswith('v'):
        version = 'v' + version
    return version


class SetCalicoVersionService(PrimaryMasterService):

    def __init__(self, subparsers):
        super().__init__(subparsers, 'set-calico-version')

    def inject_options(self, parser):
        super().inject_options(parser)
        parser.add_argument(
            'version',
            help='calico version, e.g. v3.26.4')
        parser.add_argument(
            '--image-repository', '-i',
            dest='image_repository',
            default='',
            help='image repository prefix; default: parse from live calico-node')

    def get_ansible_vars(self, args, cluster, primary_master_host):
        vars = super().get_ansible_vars(args, cluster, primary_master_host)
        vars['calico_version'] = normalize_version(args.version)
        vars['calico_image_repository'] = (
            args.image_repository.rstrip('/') if args.image_repository else '')
        return vars
