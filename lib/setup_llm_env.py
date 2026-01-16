# encoding: utf-8
from __future__ import unicode_literals

from .service import BaseService, NodesConfig
from .parser import inject_ssh_hosts_options, help_d


class LLMEnvService(BaseService):

    def __init__(self, subparsers, action):
        super(LLMEnvService, self).__init__(subparsers,
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
        
        parser.add_argument("--nvidia-driver-tar-file-path",
                           dest="nvidia_driver_tar_file_path",
                           default="/root/nvidia/nvidia-driver-vol.tar.gz",
                           help=help_d("Full path to NVIDIA driver tar file"))
        
        parser.add_argument("--gpu-device-count",
                           dest="gpu_device_count",
                           type=int,
                           default=8,
                           help=help_d("Number of GPU devices"))

    def do_action(self, args):
        config = NodesConfig(args.target_node_hosts,
                             args.ssh_user,
                             args.ssh_private_file,
                             args.ssh_port)
        
        # Prepare ansible variables from command line arguments (using full paths)
        vars = {
            'nvidia_driver_installer_path': args.nvidia_driver_installer_path,
            'cuda_installer_path': args.cuda_installer_path,
            'nvidia_driver_tar_file_path': args.nvidia_driver_tar_file_path,
            'gpu_device_count': args.gpu_device_count,
            # Add SSH configuration for rsync commands
            'ansible_ssh_private_key_file': args.ssh_private_file,
        }
        
        return config.run(self.action, vars=vars)


def add_command(subparsers):
    LLMEnvService(subparsers, 'setup-llm-env')
