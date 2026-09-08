# encoding: utf-8
from __future__ import unicode_literals

from .service import BaseService, NodesConfig
from .parser import inject_ssh_hosts_options, help_d


class ContainerEnvService(BaseService):

    def __init__(self, subparsers, action):
        super(ContainerEnvService, self).__init__(
            subparsers, action, "%s services of hosts" % action)

    def inject_options(self, parser):
        inject_ssh_hosts_options(parser)
        parser.add_argument("--nvidia-runtime",
                            dest="nvidia_runtime",
                            action="store_true",
                            default=False,
                            help="Assume NVIDIA driver is already installed; install NVIDIA Container Toolkit if nvidia-ctk is missing, and configure containerd nvidia runtime only (do not install driver/CUDA)")
        parser.add_argument("--gpu-device-virtual-number",
                            dest="gpu_device_virtual_number",
                            type=int,
                            default=None,
                            help=help_d("Virtual number for NVIDIA GPU share device. Requires --nvidia-runtime. If omitted, GPUs use HAMi by default"))

    def do_action(self, args):
        if args.gpu_device_virtual_number is not None and not args.nvidia_runtime:
            raise ValueError("--gpu-device-virtual-number requires --nvidia-runtime")

        vars = {}
        if args.nvidia_runtime:
            vars['nvidia_runtime_only'] = True
        if args.gpu_device_virtual_number is not None:
            vars['gpu_device_virtual_number'] = args.gpu_device_virtual_number
        if args.ssh_private_file:
            vars['ansible_ssh_private_key_file'] = args.ssh_private_file

        config = NodesConfig(args.target_node_hosts,
                             args.ssh_user,
                             args.ssh_private_file,
                             args.ssh_port)
        return config.run(self.action, vars=vars or None)


def add_command(subparsers):
    ContainerEnvService(subparsers, 'setup-container-env')
