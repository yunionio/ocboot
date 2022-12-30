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
