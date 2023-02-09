# encoding: utf-8
from __future__ import unicode_literals

import os


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


def inject_add_nodes_options(parser):
    parser.add_argument("primary_master_host",
                        metavar="FIRST_MASTER_HOST",
                        help="onecloud cluster primary master host, \
                              e.g., 10.1.2.56")

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
                        action="store_true", default=False)
