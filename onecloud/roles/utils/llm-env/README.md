# LLM Environment Role

这个 Ansible role 用于在主机上安装和配置 NVIDIA 驱动、CUDA 环境和容器运行时，用于 LLM 训练和推理环境。

## 功能

- 安装 NVIDIA 驱动
- 安装 CUDA 环境
- 安装 NVIDIA Container Toolkit
- 配置 containerd runtime
- 安装和配置 lxcfs
- 配置主机设备映射
- 更新 GRUB 配置

## 使用方法

### 1. 准备安装文件

将 NVIDIA 驱动和 CUDA 安装包放在本地目录中：

```bash
# 创建本地目录并放置安装包
mkdir -p /root/nvidia
cp NVIDIA-Linux-x86_64-570.133.07.run /root/nvidia/
cp cuda_12.8.1_570.124.06_linux.run /root/nvidia/
cp nvidia-driver-vol.tar.gz /root/nvidia/
```

### 2. 运行命令

使用 `ocboot.py` 命令，通过命令行参数传入配置：

```bash
ocboot.py setup-llm-env <target_host1> <target_host2> ... \
  --nvidia-driver-installer-path <full_path_to_driver> \
  --cuda-installer-path <full_path_to_cuda> \
  [--nvidia-driver-tar-file-path <full_path_to_tar>] \
  [--gpu-device-count 8]
```

#### 命令行参数说明：

- `--nvidia-driver-installer-path` (必需): NVIDIA 驱动安装包的完整路径，例如 `/root/nvidia/NVIDIA-Linux-x86_64-570.133.07.run`
- `--cuda-installer-path` (必需): CUDA 安装包的完整路径，例如 `/root/nvidia/cuda_12.8.1_570.124.06_linux.run`
- `--nvidia-driver-tar-file-path` (可选): NVIDIA 驱动 tar 文件的完整路径，默认为 `/root/nvidia/nvidia-driver-vol.tar.gz`
- `--gpu-device-count` (可选): GPU 设备数量，默认为 8
- `--user`, `-u` (可选): SSH 用户名，默认为 root
- `--key-file`, `-k` (可选): SSH 私钥文件路径
- `--port`, `-p` (可选): SSH 端口，默认为 22

#### 示例：

```bash
# 基本用法
ocboot.py setup-llm-env 10.127.222.247 \
  --nvidia-driver-installer-path /root/nvidia/NVIDIA-Linux-x86_64-570.133.07.run \
  --cuda-installer-path /root/nvidia/cuda_12.8.1_570.124.06_linux.run

# 指定自定义路径和 tar 文件
ocboot.py setup-llm-env 10.127.222.247 \
  --nvidia-driver-installer-path /opt/nvidia/NVIDIA-Linux-x86_64-570.172.08.run \
  --cuda-installer-path /opt/nvidia/cuda_12.8.1_570.172.08_linux.run \
  --nvidia-driver-tar-file-path /opt/nvidia/nvidia-driver-vol.tar.gz \
  --gpu-device-count 4

# 指定 SSH 用户和端口
ocboot.py setup-llm-env 10.127.222.247 \
  --nvidia-driver-installer-path /root/nvidia/NVIDIA-Linux-x86_64-570.133.07.run \
  --cuda-installer-path /root/nvidia/cuda_12.8.1_570.124.06_linux.run \
  --user admin \
  --port 2222
```

### 3. 直接使用 ansible-playbook（高级用法）

如果需要直接使用 ansible-playbook，可以通过 `-e` 参数传入变量：

```bash
ansible-playbook -i inventory setup-llm-env-services.yml \
  -e nvidia_driver_installer_path=/root/nvidia/NVIDIA-Linux-x86_64-570.133.07.run \
  -e cuda_installer_path=/root/nvidia/cuda_12.8.1_570.124.06_linux.run \
  -e nvidia_driver_tar_file_path=/root/nvidia/nvidia-driver-vol.tar.gz \
  -e gpu_device_count=8
```

## 注意事项

1. 安装过程中会自动重启系统（在安装内核包后和更新 GRUB 后）
2. 确保目标主机有足够的磁盘空间
3. 确保网络连接正常，能够下载 NVIDIA Container Toolkit
4. 对于不同的操作系统，会自动加载相应的变量文件
5. 确保本地安装包路径正确，且文件存在
6. 确保本地主机和目标主机之间可以通过 SSH 连接
7. **重要**：在运行 playbook 之前，需要先手动传输安装包文件到目标机器

## 文件传输方法

### 使用 rsync（推荐）
```bash
# 传输 NVIDIA 驱动
rsync -avP /path/to/nvidia/NVIDIA-Linux-x86_64-570.133.07.run target_host:/root/nvidia/

# 传输 CUDA 安装包
rsync -avP /path/to/cuda/cuda_12.8.1_570.124.06_linux.run target_host:/root/nvidia/

# 传输 nvidia-driver-vol.tar.gz
rsync -avP /path/to/nvidia/nvidia-driver-vol.tar.gz target_host:/root/nvidia/
```

### 使用 scp（备选）
```bash
# 传输 NVIDIA 驱动
scp /path/to/nvidia/NVIDIA-Linux-x86_64-570.133.07.run target_host:/root/nvidia/

# 传输 CUDA 安装包
scp /path/to/cuda/cuda_12.8.1_570.124.06_linux.run target_host:/root/nvidia/
```

## 安装流程

1. 检查操作系统支持
2. 检查本地安装文件是否存在
3. 安装内核头文件和开发包
4. 清理 vfio 相关配置
5. 安装 NVIDIA 驱动
6. 安装 CUDA 环境
7. 配置 GRUB（添加 nvidia-drm.modeset=1）
8. 安装 NVIDIA Container Toolkit
9. 配置 containerd runtime
10. 安装 lxcfs
11. 配置主机设备映射
12. 验证安装结果
