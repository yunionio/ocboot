# encoding: utf-8
from __future__ import unicode_literals

from .service import BaseService, NodesConfig
from .parser import inject_ssh_hosts_options, help_d


class AIEnvService(BaseService):

    def __init__(self, subparsers, action):
        super(AIEnvService, self).__init__(subparsers,
                                            action, "%s services of hosts" % action)

    def inject_options(self, parser):
        inject_ssh_hosts_options(parser)
        
        # NVIDIA driver and CUDA installer full paths
        parser.add_argument("--nvidia-driver-installer-path",
                           dest="nvidia_driver_installer_path",
                           required=True,
                           help="Full path to NVIDIA driver installer (e.g., /root/nvidia/NVIDIA-Linux-x86_64-570.133.07.run)")
        
        parser.add_argument("--cuda-installer-path",
                           dest="cuda_installer_path",
                           required=True,
                           help="Full path to CUDA installer (e.g., /root/nvidia/cuda_12.8.1_570.124.06_linux.run)")
        
        parser.add_argument("--gpu-device-virtual-number",
                           dest="gpu_device_virtual_number",
                           type=int,
                           default=2,
                           help=help_d("Virtual number for NVIDIA GPU share device (default: 2)"))

    def do_action(self, args):
        config = NodesConfig(args.target_node_hosts,
                             args.ssh_user,
                             args.ssh_private_file,
                             args.ssh_port)
        
        # Prepare ansible variables from command line arguments (using full paths)
        vars = {
            'nvidia_driver_installer_path': args.nvidia_driver_installer_path,
            'cuda_installer_path': args.cuda_installer_path,
            'gpu_device_virtual_number': args.gpu_device_virtual_number,
            # Add SSH configuration for rsync commands
            'ansible_ssh_private_key_file': args.ssh_private_file,
        }
        
        return config.run(self.action, vars=vars)


def add_command(subparsers):
    AIEnvService(subparsers, 'setup-ai-env')
