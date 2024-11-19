# encoding: utf-8
from __future__ import unicode_literals

import os

from . import consts

def inject_ssh_options(parser):
    # optional options
    help_d = lambda help: help + " (default: %(default)s)"

    parser.add_argument("--user", "-u",
                        dest="ssh_user",
                        default="root",
                        help=help_d("target host ssh user"))

    parser.add_argument("--key-file", "-k",
                        dest="ssh_private_file",
                        default=os.path.expanduser("~/.ssh/id_rsa"),
                        help=help_d("target host ssh private key file"))

    parser.add_argument("--port", "-p",
                        dest="ssh_port",
                        type=int,
                        default="22",
                        help=help_d("target host host ssh port"))
    return parser


def inject_ssh_hosts_options(parser):
    parser.add_argument("target_node_hosts",
                        nargs='+',
                        default=[],
                        metavar="TARGET_NODE_HOSTS",
                        help="target nodes")

    inject_ssh_options(parser)
    return parser


def inject_primary_node_options(parser):
    parser.add_argument("primary_master_host",
                        metavar="FIRST_MASTER_HOST",
                        help="onecloud cluster primary master host, \
                              e.g., 10.1.2.56")


def inject_add_nodes_options(parser):
    inject_primary_node_options(parser)

    parser.add_argument("target_node_hosts",
                        nargs='+',
                        default=[],
                        metavar="TARGET_NODE_HOSTS",
                        help="target nodes ip added into cluster")

    # optional options
    help_d = lambda help: help + " (default: %(default)s)"

    parser.add_argument("--user", "-u",
                        dest="ssh_user",
                        default="root",
                        help=help_d("primary master host ssh user"))

    parser.add_argument("--key-file", "-k",
                        dest="ssh_private_file",
                        default=os.path.expanduser("~/.ssh/id_rsa"),
                        help=help_d("primary master ssh private key file"))

    parser.add_argument("--port", "-p",
                        dest="ssh_port",
                        type=int,
                        default="22",
                        help=help_d("primary master host ssh port"))

    parser.add_argument("--node-port", "-n",
                        dest="ssh_node_port",
                        type=int,
                        default="22",
                        help=help_d("worker node host ssh port"))


def inject_add_hostagent_options(parser):
    parser.add_argument("--enable-host-on-vm",
                        dest="enable_host_on_vm",
                        action="store_true", default=False,
                        help="enable kvm host service inside virtual machine")

    parser.add_argument("--host-network",
                        nargs="*",
                        action="extend",
                        dest="host_networks",
                        help="networks option of /etc/yunion/host.conf")

    parser.add_argument("--disk-path",
                        nargs="*",
                        action="extend",
                        dest="disk_paths",
                        help="local_image_path of /etc/yunion/host.conf")


def inject_add_nodes_runtime_options(parser):
    parser.add_argument("--runtime",
                        dest="runtime",
                        default=consts.RUNTIME_QEMU,
                        choices=[consts.RUNTIME_QEMU, consts.RUNTIME_CONTAINERD],
                        help="select runtime type when adding node. default: qemu")


def inject_auto_backup_options(parser):
    parser.add_argument(
        '--backup-path', help="backup path, default: /opt/yunion/backup", default="/opt/yunion/backup")
    parser.add_argument('--light', action='store_true', default=True,
                        help="ignore yunionmeter and yunionlogger database; ignore tables start with 'opslog' and 'task'.")
    parser.add_argument('--max-backups', default=10, type=int,
                        help="how many backups to keep. default: 10")
    parser.add_argument('--max-disk-percentage', default=75, type=int,
                        help="the max usage percentage of the disk on which the backup will be done allowed to perform backup. the backup job will not work when the disk's usage is above the threshold. default: 75(%%).")
