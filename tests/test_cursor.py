"""Cursor integration and hostile archive regression tests, isolated HOME only."""
import importlib.util
import io
import os
from pathlib import Path
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import cursor
spec = importlib.util.spec_from_file_location('cursor_installer', ROOT / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class CursorTests(unittest.TestCase):
    def archive(self, path, hostile=False):
        with tarfile.open(path, 'w:gz') as bundle:
            files = {'Kitty/index.theme': b'[Icon Theme]\nName=Kitty\n',
                     'Kitty/cursors/left_ptr': b'cursor'}
            if hostile:
                files['Kitty/../../escape'] = b'bad'
            for name, data in files.items():
                member = tarfile.TarInfo(name)
                member.size = len(data)
                bundle.addfile(member, io.BytesIO(data))

    def test_install_restore_and_preserve_other_gtk_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            with mock.patch.dict(os.environ, {'HOME': folder, 'XDG_STATE_HOME': folder + '/.local/state',
                                              'XDG_CONFIG_HOME': folder + '/.config'}):
                gtk = home / '.config/gtk-3.0/settings.ini'
                gtk.parent.mkdir(parents=True)
                original = '[Settings]\ngtk-theme-name=MyTheme\ngtk-cursor-theme-name=OldCursor\n'
                gtk.write_text(original)
                staging = home / 'stage'
                staging.mkdir()
                args = SimpleNamespace(cursor=True, font=None, shell=None, wallpaper=None)
                def download(path):
                    self.archive(path)
                with mock.patch.object(cursor, 'download', side_effect=download):
                    files = installer.prepare([], args, staging)
                installer.install(files, installer.state_directory())
                self.assertIn('MyTheme', gtk.read_text())
                self.assertIn('Kitty', gtk.read_text())
                self.assertTrue((home / '.icons/Kitty/cursors/left_ptr').is_file())
                backup = next((installer.state_path() / 'backups').iterdir())
                installer.restore(backup, False)
                self.assertEqual(gtk.read_text(), original)
                self.assertFalse((home / '.icons/Kitty/cursors/left_ptr').exists())
                self.assertFalse((home / '.icons/default/index.theme').exists())

    def test_declining_cursor_preserves_existing_selection_with_gtk(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, {'HOME': folder}):
            home = Path(folder)
            target = home / '.config/gtk-3.0/settings.ini'
            target.parent.mkdir(parents=True)
            target.write_text('[Settings]\ngtk-cursor-theme-name=MyCursor\n')
            stage = home / 'stage'
            stage.mkdir()
            args = SimpleNamespace(cursor=False, font=None, shell=None, wallpaper=None)
            with mock.patch.object(cursor, 'download') as download:
                files = installer.prepare([(ROOT / 'config/gtk-3.0/settings.ini', target)], args, stage)
            self.assertIn('MyCursor', files[0][0].read_text())
            download.assert_not_called()

    def test_archive_traversal_rejected_before_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / 'bad.tar.gz'
            self.archive(archive, hostile=True)
            stage = Path(folder) / 'stage'
            with self.assertRaises(ValueError):
                cursor.unpack(archive, stage)
            self.assertFalse(stage.exists())

    def test_checksum_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch.object(cursor, 'fetch', side_effect=[b'<ocs><downloadlink>https://example.org/cursor</downloadlink></ocs>', b'bad']):
                with self.assertRaises(ValueError):
                    cursor.download(Path(folder) / 'cursor.tar.gz')
