"""Exercise the public installer against an isolated home."""
import importlib.util
import os
from unittest import mock
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def run_installer(self, home, *args, input=None):
        return subprocess.run(['python3', str(ROOT / 'install.py'), *args],
                              env={**os.environ, 'HOME': str(home), 'XDG_CONFIG_HOME': str(home / '.config'),
                                   'XDG_STATE_HOME': str(home / '.local/state')},
                              input=input, capture_output=True, text=True)

    def test_dry_run_never_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            result = self.run_installer(home, '--dry-run', '--modules', 'core,fastfetch')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('DEBIAN', result.stdout)
            self.assertIn('i3/config', result.stdout)
            self.assertEqual(list(home.iterdir()), [])

    def test_install_repeat_and_restore_preserve_existing_files(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            target = home / '.config/i3/config'
            target.parent.mkdir(parents=True)
            target.write_text('original desktop\n')
            unrelated = target.parent / 'local-notes'
            unrelated.write_text('keep me')
            result = self.run_installer(home, '--yes', '--files-only', '--modules', 'core,fastfetch')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(target.read_bytes(), (ROOT / 'config/i3/config').read_bytes())
            self.assertTrue(os.access(home / '.local/bin/wallpaper-wrap', os.X_OK))
            self.assertTrue(os.access(home / '.config/polybar/launch.sh', os.X_OK))
            manifests = list((home / '.local/state/debian-i3-dotfiles/backups').glob('*/manifest.json'))
            self.assertEqual(len(manifests), 1)
            repeat = self.run_installer(home, '--yes', '--files-only', '--modules', 'core,fastfetch')
            self.assertEqual(repeat.returncode, 0, repeat.stderr)
            self.assertEqual(len(list(manifests[0].parent.parent.iterdir())), 1)
            restored = self.run_installer(home, '--yes', '--restore', str(manifests[0].parent))
            self.assertEqual(restored.returncode, 0, restored.stderr)
            self.assertEqual(target.read_text(), 'original desktop\n')
            self.assertEqual(unrelated.read_text(), 'keep me')
            self.assertFalse((home / '.local/bin/wallpaper-wrap').exists())
            self.assertFalse((home / '.config/fastfetch/config.jsonc').exists())


    def test_restore_refuses_local_edits_and_symlinks(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            result = self.run_installer(home, '--yes', '--files-only')
            self.assertEqual(result.returncode, 0, result.stderr)
            backup = next((home / '.local/state/debian-i3-dotfiles/backups').iterdir())
            target = home / '.config/i3/config'
            target.write_text('changed after installation')
            result = self.run_installer(home, '--yes', '--restore', str(backup))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(target.read_text(), 'changed after installation')
            target.unlink()
            outside = home / 'leave-alone'
            outside.write_text('untouched')
            target.symlink_to(outside)
            result = self.run_installer(home, '--yes', '--files-only')
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(outside.read_text(), 'untouched')

    def test_wizard_cancel_does_not_write(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            result = self.run_installer(home, '--files-only', input='n\nn\nn\nn\n')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Cancelled', result.stdout)
            self.assertEqual(list(home.iterdir()), [])

    def test_customization_and_invalid_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            result = self.run_installer(home, '--yes', '--files-only', '--font', 'DejaVu Sans Mono', '--shell', 'bash')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('font pango:DejaVu Sans Mono 12', (home / '.config/i3/config').read_text())
            self.assertIn('font-0 = DejaVu Sans Mono:', (home / '.config/polybar/config.ini').read_text())
            kitty = (home / '.config/kitty/kitty.conf').read_text()
            self.assertIn('shell bash', kitty)
            self.assertIn('font_family DejaVu Sans Mono', kitty)
            self.assertIn('shell zsh', (ROOT / 'config/kitty/kitty.conf').read_text())
            for arguments in [('--modules', 'bad'), ('--font', 'bad\nexec command'),
                              ('--wallpaper', str(home / 'missing-video'))]:
                result = self.run_installer(home, '--yes', '--files-only', *arguments)
                self.assertNotEqual(result.returncode, 0)

    def test_package_setup_has_its_own_confirmation(self):
        spec = importlib.util.spec_from_file_location('installer_test_packages', ROOT / 'install.py')
        assert spec is not None and spec.loader is not None
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        with mock.patch.object(installer.subprocess, 'run') as run:
            installer.setup_packages(['core'], enabled=False)
            run.assert_not_called()
            with mock.patch.object(installer, 'ask', return_value=False):
                installer.setup_packages(['core'], enabled=True)
            run.assert_not_called()
            with mock.patch.object(installer, 'ask', return_value=True), mock.patch.object(installer.shutil, 'which', return_value='/available'):
                installer.setup_packages(['core', 'fastfetch'], enabled=True)
            self.assertEqual(run.call_args_list[0].args[0], ['sudo', 'apt-get', 'update'])
            self.assertEqual(run.call_args_list[1].args[0][:3], ['sudo', 'apt-get', 'install'])
            self.assertNotIn('-y', run.call_args_list[1].args[0])
            self.assertIn('fastfetch', run.call_args_list[1].args[0])

    def test_backup_integrity_and_destination_allowlist(self):
        import json
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            target = home / '.config/i3/config'
            target.parent.mkdir(parents=True)
            target.write_text('original')
            result = self.run_installer(home, '--yes', '--files-only')
            self.assertEqual(result.returncode, 0, result.stderr)
            backup = next((home / '.local/state/debian-i3-dotfiles/backups').iterdir())
            manifest_path = backup / 'manifest.json'
            manifest = json.loads(manifest_path.read_text())
            original = next(entry['original'] for entry in manifest['entries'] if entry['original'] is not None)
            (backup / original).write_text('corrupted')
            result = self.run_installer(home, '--yes', '--restore', str(backup))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('damaged', result.stderr)
            manifest['entries'][0]['target'] = str(home / '.ssh/authorized_keys')
            manifest_path.write_text(json.dumps(manifest))
            result = self.run_installer(home, '--yes', '--restore', str(backup))
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((home / '.ssh').exists())

    def test_interrupted_placement_rolls_back(self):
        spec = importlib.util.spec_from_file_location('installer_test_rollback', ROOT / 'install.py')
        assert spec is not None and spec.loader is not None
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            old = home / '.config/i3/config'
            old.parent.mkdir(parents=True)
            old.write_text('previous config')
            source = home / 'source'
            source.write_text('new config')
            original_copy = installer.atomic_copy
            calls = 0

            def failing_copy(src, dst):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError('simulated write failure')
                return original_copy(src, dst)

            with mock.patch.dict(os.environ, {'HOME': str(home), 'XDG_CONFIG_HOME': str(home / '.config'),
                                             'XDG_STATE_HOME': str(home / '.local/state')}):
                with mock.patch.object(installer, 'atomic_copy', side_effect=failing_copy):
                    with self.assertRaises(OSError):
                        installer.install([(source, old), (source, home / '.config/kitty/kitty.conf')],
                                          installer.state_directory())
            self.assertEqual(old.read_text(), 'previous config')
            self.assertFalse((home / '.config/kitty/kitty.conf').exists())

    def test_wizard_can_install_and_restore_dry_run_is_read_only(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            result = self.run_installer(home, '--files-only', input='n\nn\ny\ny\n')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((home / '.config/fastfetch/config.jsonc').exists())
            backup = next((home / '.local/state/debian-i3-dotfiles/backups').iterdir())
            manifest = (backup / 'manifest.json').read_bytes()
            result = self.run_installer(home, '--dry-run', '--restore', str(backup))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((backup / 'manifest.json').read_bytes(), manifest)
            self.assertTrue((home / '.config/i3/config').exists())

    def test_state_rejects_writable_parent(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            parent = home / '.local'
            parent.mkdir(mode=0o777)
            parent.chmod(0o777)
            result = self.run_installer(home, '--yes', '--files-only')
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((home / '.config/i3/config').exists())

    def test_restore_rejects_relocated_backup(self):
        import shutil
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            result = self.run_installer(home, '--yes', '--files-only')
            self.assertEqual(result.returncode, 0, result.stderr)
            backup = next((home / '.local/state/debian-i3-dotfiles/backups').iterdir())
            relocated = home / 'untrusted-backup'
            shutil.copytree(backup, relocated)
            result = self.run_installer(home, '--dry-run', '--restore', str(relocated))
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue((home / '.config/i3/config').exists())

    def test_interrupted_restore_preserves_installed_state(self):
        spec = importlib.util.spec_from_file_location('installer_test_restore_failure', ROOT / 'install.py')
        assert spec is not None and spec.loader is not None
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            for name in ('i3/config', 'kitty/kitty.conf'):
                path = home / '.config' / name
                path.parent.mkdir(parents=True)
                path.write_text('previous ' + name)
            result = self.run_installer(home, '--yes', '--files-only')
            self.assertEqual(result.returncode, 0, result.stderr)
            backup = next((home / '.local/state/debian-i3-dotfiles/backups').iterdir())
            with mock.patch.dict(os.environ, {'HOME': str(home), 'XDG_CONFIG_HOME': str(home / '.config'),
                                             'XDG_STATE_HOME': str(home / '.local/state')}):
                expected = {path: installer.signature(path) for _, path in installer.plan(['core'])}
                real_copy = installer.atomic_copy
                calls = 0

                def failing_copy(source, target):
                    nonlocal calls
                    calls += 1
                    if calls == 2:
                        raise OSError('simulated restore failure')
                    return real_copy(source, target)

                with mock.patch.object(installer, 'atomic_copy', side_effect=failing_copy):
                    with self.assertRaises(OSError):
                        installer.restore(backup, False)
                for path, signature in expected.items():
                    self.assertTrue(path.exists(), str(path))
                    self.assertEqual(installer.signature(path), signature)
                import json
                self.assertFalse(json.loads((backup / 'manifest.json').read_text())['restored'])

    def test_manifest_write_preserves_existing_temporary_file(self):
        import stat
        spec = importlib.util.spec_from_file_location('installer_test_json', ROOT / 'install.py')
        assert spec is not None and spec.loader is not None
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'manifest.json'
            existing = path.with_suffix('.tmp')
            existing.write_text('keep me')
            installer.write_json(path, {'restored': False})
            self.assertTrue(existing.exists())
            self.assertEqual(existing.read_text(), 'keep me')
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_wrapper_runs_from_another_directory(self):
        result = subprocess.run(['sh', str(ROOT / 'install.sh'), '--help'], cwd='/',
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--dry-run', result.stdout)


if __name__ == '__main__':
    unittest.main()
