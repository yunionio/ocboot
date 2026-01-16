# encoding: utf-8
from __future__ import unicode_literals

import socket

from . import consts
from .service import AddNodeService, AddNodesConfig
from .cluster import construct_cluster
from .parser import inject_add_nodes_runtime_options, inject_ai_nvidia_options
from .utils import is_ipv4, is_ipv6


class AddWorkerNodeService(AddNodeService):

    def inject_options(self, parser):
        super(AddWorkerNodeService, self).inject_options(parser)
        inject_add_nodes_runtime_options(parser)
        inject_ai_nvidia_options(parser)
        parser.add_argument("--enable-ai-env",
                            dest="enable_ai_env",
                            action="store_true",
                            default=False,
                            help="enable AI environment on the new node (NVIDIA driver/CUDA, containerd device mapping). Implies --runtime containerd.")

    def do_action(self, args):
        cluster = construct_cluster(
            args.primary_master_host,
            args.ssh_user,
            args.ssh_private_file,
            args.ssh_port)

        if args.ip_type == '':
            if is_ipv4(args.primary_master_host):
                args.ip_type = consts.IP_TYPE_IPV4
            elif is_ipv6(args.primary_master_host):
                args.ip_type = consts.IP_TYPE_IPV6
            else:
                raise ValueError("ip type is not set and cannot be determined from primary master host")

        # AI 环境必须使用 containerd；若用户指定了 enable_ai_env 且 runtime 为 qemu 则报错
        if getattr(args, 'enable_ai_env', False):
            if args.runtime == consts.RUNTIME_QEMU:
                raise ValueError("AI 环境必须使用 containerd 运行时，不能与 --runtime qemu 同时使用。请去掉 --runtime qemu 或改用 containerd。")
            args.runtime = consts.RUNTIME_CONTAINERD

        # 处理双栈配置
        kwargs = {
            'runtime': args.runtime,
            'host_networks': args.host_networks,
            'disk_paths': args.disk_paths,
            'ip_dual_conf': getattr(args, 'ip_dual_conf', None),
            'ip_type': args.ip_type,
            'offline_data_path': args.offline_data_path,
            'enable_ai_env': getattr(args, 'enable_ai_env', False),
            'gpu_device_virtual_number': getattr(args, 'gpu_device_virtual_number', 2),
            'nvidia_driver_installer_path': getattr(args, 'nvidia_driver_installer_path', None),
            'cuda_installer_path': getattr(args, 'cuda_installer_path', None),
        }

        # 如果是双栈配置，需要处理IPv4和IPv6地址
        if args.ip_type == consts.IP_TYPE_DUAL_STACK and hasattr(args, 'ip_dual_conf') and args.ip_dual_conf:
            # 确定哪个是IPv4，哪个是IPv6
            if is_ipv4(args.target_node_hosts[0]):
                # 主IP是IPv4，ip_dual_conf是IPv6
                kwargs['node_ip_v4'] = args.target_node_hosts[0]
                kwargs['node_ip_v6'] = args.ip_dual_conf
            else:
                # 主IP是IPv6，ip_dual_conf是IPv4
                kwargs['node_ip_v4'] = args.ip_dual_conf
                kwargs['node_ip_v6'] = args.target_node_hosts[0]

        config = AddNodesConfig(cluster,
                                args.target_node_hosts,
                                args.ssh_user,
                                args.ssh_private_file,
                                args.ssh_port,
                                args.ssh_node_port,
                                enable_host_on_vm=True,
                                **kwargs)
        return config.run()


def add_command(subparsers):
    AddWorkerNodeService(subparsers, "add-node", "add new node into cluster")
