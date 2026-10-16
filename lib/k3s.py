import hashlib
import os
import re
import shlex

from lib import consts
from lib.cmd import run_cmd
from lib.ssh import StderrException

def GET_AIRGAP_DIR():
    default_dir = os.path.join(os.getcwd(), "airgap_assets")
    if os.environ.get('K3S_AIRGAP_DIR', None):
        return os.environ.get('K3S_AIRGAP_DIR')
    return default_dir


VERSION_V1_28_5_K3S_1 = "v1.28.5+k3s1"

UPSTREAM_RELEASE_URL = (
    "https://github.com/k3s-io/k3s/releases/download/"
    "v1.28.5%2Bk3s1"
)
ARCH_ALIASES = {
    'amd64': 'amd64',
    'x86_64': 'amd64',
    'arm64': 'arm64',
    'aarch64': 'arm64',
    'riscv64': 'riscv64',
}

ARCH_ASSETS = {
    'amd64': ('k3s', 'k3s-airgap-images-amd64.tar.zst'),
    'arm64': ('k3s-arm64', 'k3s-airgap-images-arm64.tar.zst'),
    'riscv64': ('k3s-riscv64', 'k3s-airgap-images-riscv64.tar.zst'),
}

# ocboot has historically prepared both official architectures up front. Keep
# that behavior so adding RISC-V does not make mixed amd64/arm64 deployments
# dependent on the architecture of the machine running ocboot.
DEFAULT_ASSET_ARCHITECTURES = {'amd64', 'arm64'}
SHA256_RE = re.compile(r'^[0-9a-fA-F]{64}$')

'''
from:

- https://github.com/k3s-io/k3s/releases/download/v1.29.0%2Bk3s1/sha256sum-amd64.txt
- https://github.com/k3s-io/k3s/releases/download/v1.29.0%2Bk3s1/sha256sum-arm64.txt
'''
SHA256_CHECK_SUM = {
    VERSION_V1_28_5_K3S_1: {
        'k3s': '38fadb2baf75cb516d59f7f4a40c1950fdc0dce5ebe7251aae235527b7de4083',
        'k3s-airgap-images-amd64.tar.zst': 'e259a812e77219f8436938d7ee871945549956defe12bd210ca206597198cd67',
        'k3s-arm64': 'ce46081904d461175f152493814d2f2ac1d5e40992d6b2b2b819eb6532c413f9',
        'k3s-airgap-images-arm64.tar.zst': '896a80cdfa8131efba625775c60c79a5525ef22b6d5a6c87560afed50b8a630b'
    }
}
RISCV64_SHA256_CHECK_SUM = {
    'k3s-riscv64': '95e4be533950399efedb694e7a2a8a431c1d20886d491dda61a06e41fdca736b',
    'k3s-airgap-images-riscv64.tar.zst': 'ad8e1047194ee7462af3d912225e1e9d14d70dfd65f5b73e11f5743c6c96a7e4',
}


def cal_file_sha256(filename):
    sha256_hash = hashlib.sha256()
    with open(filename,"rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096),b""):
            sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


def normalize_architecture(architecture):
    value = str(architecture or '').strip().lower()
    normalized = ARCH_ALIASES.get(value)
    if normalized is None:
        raise ValueError("unsupported K3s architecture: %s" % architecture)
    return normalized


def _validate_sha256(value, field):
    if not isinstance(value, str) or not SHA256_RE.match(value):
        raise ValueError("%s must be a 64-character SHA-256 value" % field)
    return value.lower()


def _download_file(asset_url, target_path):
    temporary_path = "%s.part" % target_path
    try:
        run_cmd(
            'curl --fail --location --retry 5 --retry-all-errors '
            '--retry-delay 5 --connect-timeout 20 --max-time 1800 '
            '--speed-limit 1024 --speed-time 60 --output %s %s' % (
                shlex.quote(temporary_path), shlex.quote(asset_url)),
            no_strip=True,
            realtime_output=True)
        os.replace(temporary_path, target_path)
    except Exception:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)
        raise


def download_asset(dest_dir, asset_url, expect_checksum, target_name=None):
    asset_name = target_name or os.path.basename(asset_url)
    target_path = os.path.join(dest_dir, asset_name)
    expect_checksum = _validate_sha256(expect_checksum, asset_name)
    if os.path.exists(target_path):
        exists_checksum = cal_file_sha256(target_path)
        if exists_checksum == expect_checksum:
            print(f"{target_path} already exists, skip download.")
            return
        else:
            print(f"{target_path}'s sha256 checksum {exists_checksum} != {expect_checksum}, redownload it.")
            os.unlink(target_path)
    _download_file(asset_url, target_path)
    downloaded_checksum = cal_file_sha256(target_path)
    if downloaded_checksum != expect_checksum:
        os.unlink(target_path)
        raise ValueError(
            "%s's sha256 checksum %s != %s" % (
                asset_name, downloaded_checksum, expect_checksum))


def verify_bundled_riscv64_assets(dest_dir):
    for asset_name, expected in RISCV64_SHA256_CHECK_SUM.items():
        asset_path = os.path.join(dest_dir, asset_name)
        if not os.path.isfile(asset_path):
            raise FileNotFoundError(
                "%s is missing; rebuild the ocboot image from Dockerfile" %
                asset_path)
        actual = cal_file_sha256(asset_path)
        if actual != expected:
            raise ValueError(
                "%s has SHA-256 %s, expected %s; rebuild the ocboot image" %
                (asset_path, actual, expected))


NO_SUCH_FILE_OR_DIR_ERR = [
    'No such file or directory',
    '没有那个文件或目录',
]


def is_using_k3s(ssh_client=None, use_sudo=False):
    if ssh_client is None:
        if os.environ.get(consts.ENV_K8S_V115) == consts.ENV_VAL_TRUE:
            return False
        return True
    else:
        try:
            kubelet_config = '/etc/kubernetes/kubelet.conf'
            ret = ssh_client.exec_command(f'ls -alh {kubelet_config}', use_sudo)
            if kubelet_config in ret:
                return False
            return True
        except StderrException as e:
            for err in NO_SUCH_FILE_OR_DIR_ERR:
                if err in str(e):
                    return True
            raise e
        except Exception as e:
            raise e


def init_airgap_assets(dest_dir, k3s_version=VERSION_V1_28_5_K3S_1,
                       architectures=None):
    # usage: K3S_URL_PREFIX=http://LOCAL_k3s_host_url
    # in order to speed up testing.
    if not is_using_k3s():
        return

    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    requested_architectures = set(DEFAULT_ASSET_ARCHITECTURES)
    if architectures:
        requested_architectures.update(
            normalize_architecture(architecture)
            for architecture in architectures)

    if 'riscv64' in requested_architectures:
        verify_bundled_riscv64_assets(dest_dir)

    upstream_url = os.environ.get('K3S_URL_PREFIX', UPSTREAM_RELEASE_URL)
    for architecture in sorted(
            requested_architectures.difference({'riscv64'})):
        for asset_name in ARCH_ASSETS[architecture]:
            download_asset(
                dest_dir,
                '%s/%s' % (upstream_url, asset_name),
                SHA256_CHECK_SUM[k3s_version][asset_name])
