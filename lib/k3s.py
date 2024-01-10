import os
import hashlib

from lib.cmd import run_cmd


DEFAULT_AIRGAP_DIR = "airgap_assets"

VERSION_V1_28_5_K3S_1 = "v1.28.5+k3s1"

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


def download_asset(dest_dir, k3s_version, asset_url):
    asset_name = os.path.basename(asset_url)
    target_path = os.path.join(dest_dir, asset_name)
    expect_checksum = SHA256_CHECK_SUM[k3s_version][asset_name]
    if os.path.exists(target_path):
        exists_checksum = cal_file_sha256(target_path)
        if exists_checksum == expect_checksum:
            print(f"{target_path} already exists, skip download.")
            return
        else:
            print(f"{target_path}'s sha256 checksum {exists_checksum} != {expect_checksum}, redownload it.")
    run_cmd(f'curl -L {asset_url} > {target_path}', no_strip=True, realtime_output=True)


def init_airgap_assets(dest_dir, k3s_version):
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    download_asset(dest_dir, k3s_version, 'https://github.com/k3s-io/k3s/releases/download/v1.28.5%2Bk3s1/k3s')
    download_asset(dest_dir, k3s_version, 'https://github.com/k3s-io/k3s/releases/download/v1.28.5%2Bk3s1/k3s-arm64')
    download_asset(dest_dir, k3s_version, 'https://github.com/k3s-io/k3s/releases/download/v1.28.5%2Bk3s1/k3s-airgap-images-amd64.tar.zst')
    # download_asset(dest_dir, k3s_version, 'https://github.com/k3s-io/k3s/releases/download/v1.28.5%2Bk3s1/k3s-airgap-images-arm64.tar.zst')
