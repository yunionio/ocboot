import hashlib
import json
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
RISCV64_ASSET_METADATA = 'k3s-riscv64-assets.json'
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


def normalize_riscv64_asset_config(config):
    if not isinstance(config, dict):
        raise ValueError("riscv64 K3s asset configuration must be a mapping")
    required = ('url_prefix', 'binary_sha256', 'airgap_images_sha256')
    missing = [field for field in required if not config.get(field)]
    if missing:
        raise ValueError(
            "riscv64 K3s asset configuration misses: %s" %
            ', '.join(missing))
    return {
        'url_prefix': str(config['url_prefix']).rstrip('/'),
        'binary_sha256': _validate_sha256(
            config['binary_sha256'], 'binary_sha256'),
        'airgap_images_sha256': _validate_sha256(
            config['airgap_images_sha256'], 'airgap_images_sha256'),
    }


def riscv64_asset_config_from_env():
    fields = {
        'url_prefix': os.environ.get('K3S_RISCV64_URL_PREFIX'),
        'binary_sha256': os.environ.get('K3S_RISCV64_BINARY_SHA256'),
        'airgap_images_sha256': os.environ.get(
            'K3S_RISCV64_AIRGAP_IMAGES_SHA256'),
    }
    if not any(fields.values()):
        return None
    return normalize_riscv64_asset_config(fields)


def _riscv64_asset_metadata_path(dest_dir):
    return os.path.join(dest_dir, RISCV64_ASSET_METADATA)


def load_cached_riscv64_asset_config(dest_dir):
    metadata_path = _riscv64_asset_metadata_path(dest_dir)
    if not os.path.exists(metadata_path):
        return None
    with open(metadata_path, encoding='utf-8') as stream:
        return normalize_riscv64_asset_config(json.load(stream))


def cache_riscv64_asset_config(dest_dir, config):
    metadata_path = _riscv64_asset_metadata_path(dest_dir)
    temporary_path = "%s.part" % metadata_path
    try:
        with open(temporary_path, 'w', encoding='utf-8') as stream:
            json.dump(config, stream, indent=2, sort_keys=True)
            stream.write('\n')
        os.replace(temporary_path, metadata_path)
    except Exception:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)
        raise


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
                       architectures=None, riscv64_assets=None):
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

    upstream_url = os.environ.get('K3S_URL_PREFIX', UPSTREAM_RELEASE_URL)
    for architecture in sorted(
            requested_architectures.difference({'riscv64'})):
        for asset_name in ARCH_ASSETS[architecture]:
            download_asset(
                dest_dir,
                '%s/%s' % (upstream_url, asset_name),
                SHA256_CHECK_SUM[k3s_version][asset_name])

    if 'riscv64' not in requested_architectures:
        return

    if riscv64_assets is None:
        riscv64_assets = riscv64_asset_config_from_env()
    if riscv64_assets is None:
        riscv64_assets = load_cached_riscv64_asset_config(dest_dir)
    if riscv64_assets is None:
        raise ValueError(
            "riscv64 K3s assets require an explicit URL and SHA-256 values")
    riscv64_assets = normalize_riscv64_asset_config(riscv64_assets)

    checksums = {
        'k3s-riscv64': riscv64_assets['binary_sha256'],
        'k3s-airgap-images-riscv64.tar.zst':
            riscv64_assets['airgap_images_sha256'],
    }
    for asset_name in ARCH_ASSETS['riscv64']:
        download_asset(
            dest_dir,
            '%s/%s' % (riscv64_assets['url_prefix'], asset_name),
            checksums[asset_name])
    cache_riscv64_asset_config(dest_dir, riscv64_assets)
