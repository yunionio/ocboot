# encoding: utf-8
from __future__ import unicode_literals

import os

from .ansible import AnsibleBastionHost
from .cmd import run_ansible_playbook
from .utils import get_major_version
from .cluster import construct_cluster
from .ocboot import get_ansible_global_vars
from . import consts
from getpass import getuser
from lib import utils
from lib import color

UPGRADE_MODES_UPGRADE = 'upgrade'
UPGRADE_MODES_UPGRADE_CONTROLLER = 'upgrade-controller'
UPGRADE_MODES_UPGRADE_HOST = 'upgrade-host'
UPGRADE_MODES_UPGRADE_FINAL = 'upgrade-final'

UPGRADE_MODES_HELP_MSGS = {
    UPGRADE_MODES_UPGRADE: 'upgrade onecloud cluster to specified version',
    UPGRADE_MODES_UPGRADE_CONTROLLER: 'upgrade onecloud controller to specified version',
    UPGRADE_MODES_UPGRADE_HOST: 'upgrade onecloud host(s) to specified version',
    UPGRADE_MODES_UPGRADE_FINAL: 'upgrade onecloud cluster to specified version',
}

UPGRADE_MODES_ROLE_FILE = {
    UPGRADE_MODES_UPGRADE: './onecloud/upgrade-cluster.yml',
    UPGRADE_MODES_UPGRADE_CONTROLLER: './onecloud/upgrade-cluster-controller.yml',
    UPGRADE_MODES_UPGRADE_HOST: './onecloud/upgrade-cluster-host.yml',
    UPGRADE_MODES_UPGRADE_FINAL: './onecloud/upgrade-cluster-final.yml',
}

UPGRADE_MODES_FINISH_MSG = {
    UPGRADE_MODES_UPGRADE: "The system has been upgraded to the latest version.",
    UPGRADE_MODES_UPGRADE_CONTROLLER: "The Controller has been upgraded to the latest version.",
    UPGRADE_MODES_UPGRADE_HOST: "Worker nodes have been upgraded to the latest version.",
    UPGRADE_MODES_UPGRADE_FINAL: "The final step of the upgraded is now finished.",
}


def add_command(subparsers, command="upgrade"):
    parser = subparsers.add_parser(
        command, help=UPGRADE_MODES_HELP_MSGS.get(command, ''))
    # parser.add_argument('config', help="config file")
    # requirement options
    parser.add_argument("primary_master_host",
                        metavar="FIRST_MASTER_HOST",
                        help="onecloud cluster primary master host, \
                              e.g., 10.1.2.56")
    parser.add_argument("version",
                        metavar="VERSION",
                        help="onecloud version to be upgrade, \
                              e.g., v3.6.9")

    # optional options
    def help_d(help): return help + " (default: %(default)s)"
    parser.add_argument("--user", "-u",
                        dest="ssh_user",
                        default=getuser(),
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

    parser.add_argument("--as-bastion", "-B",
                        dest="primary_as_bastion",
                        action="store_true",
                        help="use primary master node as ssh bastion host to run ansible")

    parser.add_argument("--image-repository", "-i",
                        dest="image_repository",
                        default=consts.REGISTRY_ALI_YUNION,
                        help="specify 3rd party image and namespace")

    parser.add_argument("--offline-data-path",
                        dest="offline_data_path",
                        default="",
                        help="offline rpm repo path for upgrade mode")

    parser.add_argument("--primary-node-ip",
                        dest="primary_node_ip",
                        default="",
                        help="offline rpm repo path for upgrade mode")

    parser.add_argument("--gpu-init", "-G",
                        dest="gpu_init",
                        action="store_true",
                        default=False,
                        help="re-init gpu druing upgrading. default: false.")

    if command == UPGRADE_MODES_UPGRADE_HOST:
        parser.add_argument("--hosts", "-H",
                            dest='target_node_hosts',
                            nargs='+',
                            default=[],
                            metavar="TARGET_NODE_HOSTS",
                            help="target nodes ip added into cluster")

    parser.set_defaults(func=do_upgrade)


def do_upgrade(args):
    cluster = construct_cluster(
        args.primary_master_host,
        args.ssh_user,
        args.ssh_private_file,
        args.ssh_port)
    playbook_file = UPGRADE_MODES_ROLE_FILE.get(args.subcmd, '')
    playbook_file = os.path.normpath(os.path.join(os.getcwd(), playbook_file))

    if os.path.getsize(playbook_file) == 0:
        print(color.red(f"Yaml file {playbook_file} is empty!"))
        exit(1)

    cur_ver = cluster.get_current_version()

    config = UpgradeConfig(cur_ver, args.version)

    bastion_host = None
    if args.primary_as_bastion:
        bastion_host = AnsibleBastionHost(args.primary_master_host)

    if args.subcmd == UPGRADE_MODES_UPGRADE_CONTROLLER:
        cluster.worker_nodes = []
    elif args.subcmd == UPGRADE_MODES_UPGRADE_HOST:
        cluster.worker_nodes = [i for i in cluster.worker_nodes if i.get_ip() in args.target_node_hosts]

    inventory_content = cluster.generate_playbook_inventory(bastion_host, args.ssh_port, args.ssh_node_port)
    inventory_f = '/tmp/test-hosts.ini'
    with open(inventory_f, 'w') as f:
        f.write(inventory_content)

    vars = config.to_ansible_vars(cluster)
    if args.image_repository:
        if args.image_repository == consts.REGISTRY_ALI_YUNION:
            if utils.is_below_v3_9(args.version):
                args.image_repository = consts.REGISTRY_ALI_YUNIONIO
        vars['image_repository'] = args.image_repository.rstrip('/')

    if args.offline_data_path:
        vars['offline_data_path'] = args.offline_data_path
        vars['primary_master_host'] = args.primary_master_host

    # for sync files. no ha ip.
    if args.primary_node_ip:
        vars['primary_node_ip'] = args.primary_node_ip

    # when using -G: include gpu_init task;
    # when not using -G: ignore gpu_init task;
    # installation with run.py: include gpu_init task. (remains the same)
    if not args.gpu_init:
        vars['upgrade_without_gpu'] = True

    return_code = run_ansible_playbook(
        inventory_f,
        playbook_file,
        vars=vars,
    )

    if return_code is not None and return_code != 0:
        return return_code
    cluster.set_current_version(args.version)
    utils.pr_green('\n' + UPGRADE_MODES_FINISH_MSG.get(args.subcmd) + '\n')


class UpgradeConfig(object):

    def __init__(self, cur_ver, upgrade_ver):
        self.current_onecloud_version = cur_ver
        self.current_onecloud_major_version = get_major_version(cur_ver)
        self.upgrade_onecloud_version = upgrade_ver
        self.upgrade_onecloud_major_version = get_major_version(upgrade_ver)

    def is_major_upgrade(self):
        return self.current_onecloud_major_version != self.upgrade_onecloud_major_version

    def get_yunion_yum_repo(self):
        ver = self.upgrade_onecloud_major_version.replace('_', '.')
        ver = ver[1:]
        return "https://iso.yunion.cn/centos/7/%s/x86_64/yunion.repo" % (ver)

    def to_ansible_vars(self, cluster):
        ret = {
            "current_onecloud_version": self.current_onecloud_version,
            "current_onecloud_major_version": self.current_onecloud_major_version,
            "upgrade_onecloud_version": self.upgrade_onecloud_version,
            "upgrade_onecloud_major_version": self.upgrade_onecloud_major_version,
            "is_major_upgrade": self.is_major_upgrade(),
            "yunion_yum_repo": self.get_yunion_yum_repo(),
            "yunion_qemu_package": "yunion-qemu-4.2.0",
        }
        g_var = get_ansible_global_vars(self.current_onecloud_version, cluster.is_using_k3s())
        ret.update(g_var)
        return ret
