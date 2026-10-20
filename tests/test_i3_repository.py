"""Repository approval and ordering, without modifying the host."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]

class RepositoryTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('i3repo', ROOT / 'install.py')
        self.i = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.i)

    def test_conflicting_and_symlinked_sources_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'source'
            p.write_text('custom')
            with self.assertRaises(ValueError):
                self.i.check_repository_target(p, 'expected')
            link = Path(folder)/'link'
            link.symlink_to(p)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                self.i.check_repository_target(link, 'custom')

    def test_old_candidate_approval_refresh_and_install(self):
        events = []
        with mock.patch.object(self.i, 'xwinwrap_available', return_value=True), \
             mock.patch.object(self.i, 'package_names', return_value=['i3-wm']), \
             mock.patch.object(self.i, 'ask', return_value=True), \
             mock.patch.object(self.i.shutil, 'which', return_value='/usr/bin/tool'), \
             mock.patch.object(self.i, 'preflight_packages', return_value=[]), \
             mock.patch.object(self.i, 'os_release_version', return_value='22.04'), \
             mock.patch.object(self.i, 'apt_candidate', side_effect=['4.20.1-1', '4.24-1']), \
             mock.patch.object(self.i, 'approve_sur5r', side_effect=lambda version: events.append('approve') or 'source'), \
             mock.patch.object(self.i, 'download_sur5r_key', side_effect=lambda path: events.append('verify') or path/'key.deb'), \
             mock.patch.object(self.i, 'install_sur5r', side_effect=lambda *args: events.append('repo')), \
             mock.patch.object(self.i.subprocess, 'run', side_effect=lambda argv, **kw: events.append(argv) or subprocess.CompletedProcess(argv,0)):
            self.i.setup_packages(['core'], True, 'ubuntu')
        self.assertEqual(events[:3], ['approve', 'verify', 'repo'])
        self.assertEqual(events[3], ['sudo','apt-get','update'])
        self.assertEqual(events[4], ['sudo','apt-get','install','i3-wm'])

    def test_disabled_package_setup_never_prompts_or_downloads(self):
        with mock.patch.object(self.i, 'ask') as ask, mock.patch.object(self.i, 'download_sur5r_key') as download:
            self.i.setup_packages(['core'], False, 'ubuntu')
        ask.assert_not_called()
        download.assert_not_called()
