import os
import tempfile
import unittest
from unittest import mock

from lib import k3s


class TestK3sAssets(unittest.TestCase):

    def test_normalize_architecture_aliases(self):
        aliases = {
            'amd64': 'amd64',
            'x86_64': 'amd64',
            'arm64': 'arm64',
            'aarch64': 'arm64',
            'riscv64': 'riscv64',
            'RISCV64': 'riscv64',
        }
        for value, expected in aliases.items():
            with self.subTest(value=value):
                self.assertEqual(
                    k3s.normalize_architecture(value), expected)

    def test_normalize_architecture_rejects_unknown_values(self):
        with self.assertRaisesRegex(ValueError, 'unsupported K3s architecture'):
            k3s.normalize_architecture('mips64')

    def test_checksums_reject_invalid_values(self):
        with self.assertRaisesRegex(ValueError, '64-character'):
            k3s._validate_sha256('invalid', 'asset')

    @mock.patch('lib.k3s.download_asset')
    @mock.patch('lib.k3s.is_using_k3s', return_value=True)
    def test_default_assets_preserve_amd64_and_arm64(
            self, _is_using_k3s, download_asset):
        with tempfile.TemporaryDirectory() as directory:
            k3s.init_airgap_assets(directory)

        names = [os.path.basename(call.args[1])
                 for call in download_asset.call_args_list]
        self.assertEqual(names, [
            'k3s',
            'k3s-airgap-images-amd64.tar.zst',
            'k3s-arm64',
            'k3s-airgap-images-arm64.tar.zst',
        ])

    @mock.patch('lib.k3s.verify_bundled_riscv64_assets')
    @mock.patch('lib.k3s.download_asset')
    @mock.patch('lib.k3s.is_using_k3s', return_value=True)
    def test_riscv64_is_added_without_removing_default_assets(
            self, _is_using_k3s, download_asset, verify_assets):
        with tempfile.TemporaryDirectory() as directory:
            k3s.init_airgap_assets(directory, architectures=['riscv64'])
            verify_assets.assert_called_once_with(directory)

        names = [os.path.basename(call.args[1])
                 for call in download_asset.call_args_list]
        self.assertEqual(names, [
            'k3s',
            'k3s-airgap-images-amd64.tar.zst',
            'k3s-arm64',
            'k3s-airgap-images-arm64.tar.zst',
        ])

    def test_missing_bundled_riscv64_asset_fails_before_download(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(FileNotFoundError, 'rebuild'):
                k3s.verify_bundled_riscv64_assets(directory)

    @mock.patch('lib.k3s.cal_file_sha256', return_value='0' * 64)
    def test_corrupt_bundled_riscv64_asset_fails(self, _checksum):
        with tempfile.TemporaryDirectory() as directory:
            for asset_name in k3s.RISCV64_SHA256_CHECK_SUM:
                with open(os.path.join(directory, asset_name), 'wb'):
                    pass
            with self.assertRaisesRegex(ValueError, 'rebuild'):
                k3s.verify_bundled_riscv64_assets(directory)

    @mock.patch('lib.k3s.cal_file_sha256')
    def test_valid_bundled_riscv64_assets(self, checksum):
        checksum.side_effect = lambda path: k3s.RISCV64_SHA256_CHECK_SUM[
            os.path.basename(path)]
        with tempfile.TemporaryDirectory() as directory:
            for asset_name in k3s.RISCV64_SHA256_CHECK_SUM:
                with open(os.path.join(directory, asset_name), 'wb'):
                    pass
            k3s.verify_bundled_riscv64_assets(directory)

    @mock.patch('lib.k3s.run_cmd')
    def test_download_failure_removes_partial_file(self, run_cmd):
        run_cmd.side_effect = RuntimeError('download failed')
        with tempfile.TemporaryDirectory() as directory:
            target = os.path.join(directory, 'asset')
            partial = target + '.part'
            with open(partial, 'w', encoding='utf-8') as stream:
                stream.write('stale')
            with self.assertRaisesRegex(RuntimeError, 'download failed'):
                k3s._download_file('https://example.test/asset', target)
            self.assertFalse(os.path.exists(partial))
            self.assertFalse(os.path.exists(target))

    @mock.patch('lib.k3s._download_file', side_effect=RuntimeError('failed'))
    def test_failed_retry_removes_known_bad_cached_asset(self, _download_file):
        with tempfile.TemporaryDirectory() as directory:
            target = os.path.join(directory, 'asset')
            with open(target, 'wb') as stream:
                stream.write(b'bad cache')
            with self.assertRaisesRegex(RuntimeError, 'failed'):
                k3s.download_asset(
                    directory, 'https://example.test/asset', '0' * 64)
            self.assertFalse(os.path.exists(target))

    @mock.patch('lib.k3s._download_file')
    def test_bad_checksum_removes_downloaded_asset(self, download_file):
        def write_bad_asset(_url, target):
            with open(target, 'wb') as stream:
                stream.write(b'bad')

        download_file.side_effect = write_bad_asset
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'sha256 checksum'):
                k3s.download_asset(
                    directory, 'https://example.test/asset', '0' * 64)
            self.assertFalse(os.path.exists(os.path.join(directory, 'asset')))

if __name__ == '__main__':
    unittest.main()
