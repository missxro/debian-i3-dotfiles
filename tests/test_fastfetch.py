"""Pinned upstream fallback without package-manager mutations in tests."""
import hashlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


class FastfetchTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('installer_fastfetch', ROOT / 'install.py')
        self.installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.installer)

    def setup_context(self, missing):
        from contextlib import ExitStack
        stack = ExitStack()
        for name, value in [('xwinwrap_available', True), ('package_names', ['i3-wm', 'fastfetch']),
                            ('ask', True), ('preflight_packages', missing)]:
            stack.enter_context(mock.patch.object(self.installer, name, return_value=value))
        stack.enter_context(mock.patch.object(self.installer, 'apt_candidate', return_value='4.24-1'))
        stack.enter_context(mock.patch.object(self.installer.shutil, 'which', return_value='/usr/bin/tool'))
        return stack

    def test_missing_fastfetch_uses_verified_local_deb(self):
        calls = []
        def run(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, 'arm64\n', '')
        with self.setup_context(['fastfetch']), \
             mock.patch.object(self.installer.subprocess, 'run', side_effect=run), \
             mock.patch.object(self.installer, 'download_fastfetch', side_effect=lambda directory, arch: directory / 'fastfetch.deb') as download:
            self.installer.setup_packages(['core', 'fastfetch'], True, 'ubuntu')
        self.assertEqual(download.call_args.args[1], 'arm64')
        self.assertEqual(calls[-1][:4], ['sudo', 'apt-get', 'install', 'i3-wm'])
        self.assertTrue(calls[-1][-1].endswith('/fastfetch.deb'))
        self.assertNotIn('fastfetch', calls[-1])

    def test_native_candidate_does_not_download(self):
        with self.setup_context([]), mock.patch.object(self.installer.subprocess, 'run') as run, \
             mock.patch.object(self.installer, 'download_fastfetch') as download:
            self.installer.setup_packages(['fastfetch'], True, 'ubuntu')
        download.assert_not_called()
        self.assertIn('fastfetch', run.call_args.args[0])

    def test_other_missing_package_blocks_download_and_apt(self):
        with self.setup_context(['i3-wm', 'fastfetch']), mock.patch.object(self.installer.subprocess, 'run') as run, \
             mock.patch.object(self.installer, 'download_fastfetch') as download:
            with self.assertRaisesRegex(ValueError, 'i3-wm'):
                self.installer.setup_packages(['fastfetch'], True, 'ubuntu')
        run.assert_not_called()
        download.assert_not_called()

    def test_failed_verification_blocks_privileged_calls(self):
        with self.setup_context(['fastfetch']), \
             mock.patch.object(self.installer.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'amd64\n', '')) as run, \
             mock.patch.object(self.installer, 'download_fastfetch', side_effect=ValueError('checksum')):
            with self.assertRaisesRegex(ValueError, 'checksum'):
                self.installer.setup_packages(['fastfetch'], True, 'ubuntu')
        self.assertFalse(any(call.args[0][0] == 'sudo' for call in run.call_args_list))

    def test_skip_and_decline_do_not_download(self):
        with mock.patch.object(self.installer, 'download_fastfetch') as download, \
             mock.patch.object(self.installer, 'ask', return_value=False), \
             mock.patch.object(self.installer, 'preflight_packages') as preflight:
            self.installer.setup_packages(['fastfetch'], False, 'ubuntu')
            self.installer.setup_packages(['fastfetch'], True, 'ubuntu')
        download.assert_not_called()
        preflight.assert_not_called()

    def test_checksum_mismatch_rejected_before_metadata(self):
        response = io.BytesIO(b'corrupt')
        response.geturl = lambda: 'https://release-assets.githubusercontent.com/package'
        with tempfile.TemporaryDirectory() as directory, \
             mock.patch.object(self.installer.urllib.request, 'urlopen', return_value=response), \
             mock.patch.object(self.installer, 'verify_fastfetch_deb') as verify:
            with self.assertRaisesRegex(ValueError, 'checksum'):
                self.installer.download_fastfetch(Path(directory), 'arm64')
        verify.assert_not_called()

    def test_unsupported_architecture_rejected_without_download(self):
        with mock.patch.object(self.installer.urllib.request, 'urlopen') as request:
            with self.assertRaisesRegex(ValueError, 'architecture'):
                self.installer.download_fastfetch(Path('/unused'), 'mips')
        request.assert_not_called()

    def test_download_failure_is_actionable(self):
        with tempfile.TemporaryDirectory() as directory, \
             mock.patch.object(self.installer.urllib.request, 'urlopen', side_effect=OSError('offline')):
            with self.assertRaisesRegex(ValueError, 'download failed'):
                self.installer.download_fastfetch(Path(directory), 'amd64')
