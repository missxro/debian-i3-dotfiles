"""Real launcher subprocess tests; only desktop executables are replaced."""
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
WALL = ROOT / 'bin/wallpaper-wrap'
BAR = ROOT / 'config/polybar/launch.sh'
LIVE = ROOT / 'bin/wallpaper-live'


class Launchers(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='launcher-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.mock = self.base / 'commands'
        self.mock.mkdir()
        (self.mock / 'python3').symlink_to(sys.executable)
        self.env = dict(os.environ, PATH=str(self.mock), DISPLAY=':test',
                        XDG_RUNTIME_DIR=str(self.base / 'runtime'),
                        XDG_CONFIG_HOME=str(self.base / 'config'), XDG_SESSION_TYPE='x11',
                        MONITORS='Monitors: 2\n 0: +*DP-1 1920/500x1080/300+0+0 DP-1\n 1: +HDMI-1 1280/300x720/200-1280-40 HDMI-1\n',
                        EVENTS=str(self.base / 'events'))
        self.command('xrandr', 'import os, sys\nassert sys.argv[1:] == ["--listactivemonitors"]\nprint(os.environ["MONITORS"])\n')
        self.video = self.base / 'a video.mp4'
        self.video.write_bytes(b'video')

    def command(self, name, body):
        path = self.mock / name
        path.write_text('#!' + sys.executable + '\n' + body)
        path.chmod(0o755)

    def run_script(self, script, *args, env=None):
        self.assertTrue(script.is_file(), f'Missing launcher: {script.name}')
        return subprocess.run([str(script), *map(str, args)], env=env or self.env,
                              text=True, capture_output=True, timeout=5)

    def test_wallpaper_finds_user_xwinwrap_without_login_path(self):
        binary = self.base / '.local/bin/xwinwrap'
        binary.parent.mkdir(parents=True)
        binary.write_text('#!/bin/sh\nexit 0\n')
        binary.chmod(0o755)
        result = self.run_script(WALL, '--dry-run', self.video,
                                 env=dict(self.env, HOME=str(self.base)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(all(item['argv'][0] == str(binary) for item in json.loads(result.stdout)))

    def test_polybar_plans_each_monitor_and_single_and_empty(self):
        for output, names in [(self.env['MONITORS'], ['DP-1', 'HDMI-1']),
                              ('Monitors: 1\n 0: +DP-2 900/200x600/100+0+0 DP-2\n', ['DP-2']),
                              ('Monitors: 0\n', [])]:
            with self.subTest(names=names):
                env = dict(self.env, MONITORS=output)
                result = self.run_script(BAR, '--dry-run', env=env)
                self.assertEqual(result.returncode, 0, result.stderr)
                plan = json.loads(result.stdout)
                self.assertEqual([item['env']['MONITOR'] for item in plan], names)
                for item in plan:
                    self.assertEqual(item['argv'], ['polybar', '--config=' + str(BAR.with_name('config.ini')), 'main'])
        self.assertFalse(Path(self.env['XDG_RUNTIME_DIR']).exists())

    def test_x11_preflight_and_xrandr_failure_are_graceful(self):
        for script, args in [(WALL, [self.video]), (BAR, [])]:
            for overrides in [{'DISPLAY': ''}, {'XDG_SESSION_TYPE': 'wayland'}]:
                result = self.run_script(script, '--dry-run', *args,
                                         env=dict(self.env, **overrides))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), [])
        (self.mock / 'xrandr').unlink()
        result = self.run_script(BAR, '--dry-run')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('xrandr', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.command('xrandr', 'import sys\nsys.exit(1)\n')
        result = self.run_script(BAR, '--dry-run')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Traceback', result.stderr)

    def test_live_exec_preserves_paths_and_uses_safe_hardware_decode(self):
        self.command('mpv', 'import json, os, sys\nprint(json.dumps(sys.argv[1:]))\n')
        result = self.run_script(LIVE, '0x123', self.video)
        self.assertEqual(result.returncode, 0, result.stderr)
        argv = json.loads(result.stdout)
        self.assertIn('--hwdec=auto-safe', argv)
        self.assertIn('--wid=0x123', argv)
        self.assertEqual(argv[-2:], ['--', str(self.video)])
        option_video = self.base / '--input-conf=bad.mp4'
        option_video.write_bytes(b'video')
        result = subprocess.run([str(LIVE), '42', '--', option_video.name],
                                cwd=self.base, env=self.env, text=True,
                                capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)[-2:], ['--', str(option_video)])
        for args in [('WID', self.video), ('0', self.video), ('-1', self.video),
                     ('1', self.base), ('1', self.base / 'absent'), ()]:
            with self.subTest(args=args):
                result = self.run_script(LIVE, *args)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Traceback', result.stderr)
        (self.mock / 'mpv').unlink()
        result = self.run_script(LIVE, '1', self.video)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Traceback', result.stderr)

    def events(self):
        path = Path(self.env['EVENTS'])
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def wait_for(self, predicate):
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.03)
        self.fail('Timed out waiting for subprocess state')

    def stop(self, process):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=6)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()

    def start(self, script, *args):
        process = subprocess.Popen([str(script), *map(str, args)], env=self.env,
                                   text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(self.stop, process)
        return process

    def desktop_mocks(self):
        body = '''import json, os, signal, sys, time
fd = os.open(os.environ['EVENTS'], os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
def event(kind):
    os.write(fd, (json.dumps({'kind': kind, 'pid': os.getpid(), 'argv': sys.argv,
                             'monitor': os.environ.get('MONITOR')}) + '\\n').encode())
def stop(signum, frame):
    event('stop')
    sys.exit(0)
signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
event('start')
while True:
    time.sleep(0.05)
'''
        for name in ['polybar', 'xwinwrap', 'mpv']:
            self.command(name, body)

    def test_supervisors_launch_owned_children_and_cleanup_on_signals(self):
        self.desktop_mocks()
        for script, args, signum in [(WALL, [self.video], signal.SIGTERM),
                                     (BAR, [], signal.SIGINT)]:
            with self.subTest(script=script.name):
                previous = len([e for e in self.events() if e['kind'] == 'start'])
                process = self.start(script, *args)
                self.wait_for(lambda: len([e for e in self.events() if e['kind'] == 'start']) == previous + 2)
                children = [e for e in self.events() if e['kind'] == 'start'][-2:]
                if script == BAR:
                    self.assertEqual({e['monitor'] for e in children}, {'DP-1', 'HDMI-1'})
                else:
                    self.assertTrue(all(e['argv'][-1] == str(self.video) for e in children))
                process.send_signal(signum)
                self.assertEqual(process.wait(timeout=5), 0)
                stopped = {e['pid'] for e in self.events() if e['kind'] == 'stop'}
                self.assertTrue({e['pid'] for e in children} <= stopped)
                for child in children:
                    with self.assertRaises(ProcessLookupError):
                        os.kill(child['pid'], 0)

    def test_singleton_lock_survives_duplicate_exit_and_allows_restart(self):
        self.desktop_mocks()
        unrelated = self.start(self.mock / 'polybar')
        self.wait_for(lambda: len(self.events()) == 1)
        for script, args in [(WALL, [self.video]), (BAR, [])]:
            with self.subTest(script=script.name):
                baseline = len([e for e in self.events() if e['kind'] == 'start'])
                owner = self.start(script, *args)
                self.wait_for(lambda: len([e for e in self.events() if e['kind'] == 'start']) == baseline + 2)
                for _ in range(2):
                    duplicate = self.start(script, *args)
                    self.wait_for(lambda: duplicate.poll() is not None)
                    self.assertEqual(duplicate.returncode, 0)
                    self.assertEqual(len([e for e in self.events() if e['kind'] == 'start']), baseline + 2)
                    self.assertIsNone(owner.poll())
                dry = self.run_script(script, '--dry-run', *args)
                self.assertEqual(dry.returncode, 0, dry.stderr)
                self.assertEqual(len(json.loads(dry.stdout)), 2)
                self.assertEqual(len([e for e in self.events() if e['kind'] == 'start']), baseline + 2)
                self.stop(owner)
                replacement = self.start(script, *args)
                self.wait_for(lambda: len([e for e in self.events() if e['kind'] == 'start']) == baseline + 4)
                self.stop(replacement)
                self.assertIsNone(unrelated.poll())

    def test_missing_player_is_detected_before_any_wallpaper_child(self):
        self.desktop_mocks()
        (self.mock / 'mpv').unlink()
        process = self.start(WALL, self.video)
        self.wait_for(lambda: process.poll() is not None)
        self.assertNotEqual(process.returncode, 0)
        assert process.stderr is not None
        self.assertIn('mpv', process.stderr.read())
        self.assertEqual(self.events(), [])

    def test_lock_directory_must_be_private_and_not_a_symlink(self):
        self.desktop_mocks()
        runtime = Path(self.env['XDG_RUNTIME_DIR'])
        runtime.mkdir()
        lock_dir = runtime / 'debian-i3-dotfiles'
        lock_dir.mkdir(mode=0o777)
        lock_dir.chmod(0o777)
        process = self.start(BAR)
        self.wait_for(lambda: process.poll() is not None)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(self.events(), [])
        lock_dir.rmdir()
        target = self.base / 'private'
        target.mkdir(mode=0o700)
        lock_dir.symlink_to(target, target_is_directory=True)
        process = self.start(BAR)
        self.wait_for(lambda: process.poll() is not None)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(self.events(), [])

    def test_validation_help_no_outputs_and_missing_dependencies(self):
        for script in [WALL, BAR, LIVE]:
            result = self.run_script(script, '--help')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('usage:', result.stdout)
            result = self.run_script(script, '--unknown-mode')
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('Traceback', result.stderr)
        for path in [self.base / 'missing.mp4', self.base]:
            result = self.run_script(WALL, '--dry-run', path)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('Traceback', result.stderr)
        for script, args in [(WALL, [self.video]), (BAR, [])]:
            result = self.run_script(script, *args, env=dict(self.env, MONITORS='Monitors: 0\n'))
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(Path(self.env['XDG_RUNTIME_DIR']).exists())
        self.assertEqual(self.run_script(WALL).returncode, 0)
        for dependency, script, args in [('xwinwrap', WALL, [self.video]), ('polybar', BAR, [])]:
            self.desktop_mocks()
            (self.mock / dependency).unlink()
            result = self.run_script(script, *args)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(dependency, result.stderr)
            self.assertNotIn('Traceback', result.stderr)
            self.assertEqual(self.events(), [])

    def test_cleanup_escalates_only_for_owned_unresponsive_child(self):
        self.command('polybar', '''import json, os, signal, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
fd = os.open(os.environ['EVENTS'], os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
os.write(fd, (json.dumps({'kind': 'start', 'pid': os.getpid()}) + '\\n').encode())
while True:
    time.sleep(0.05)
''')
        process = self.start(BAR)
        self.wait_for(lambda: len(self.events()) == 2)
        children = [e['pid'] for e in self.events()]
        process.terminate()
        self.assertEqual(process.wait(timeout=5), 0)
        for pid in children:
            with self.assertRaises(ProcessLookupError):
                os.kill(pid, 0)

    def test_failed_child_stops_its_supervised_siblings(self):
        self.desktop_mocks()
        process = self.start(BAR)
        self.wait_for(lambda: len(self.events()) == 2)
        children = [e['pid'] for e in self.events()]
        os.kill(children[0], signal.SIGKILL)
        self.assertNotEqual(process.wait(timeout=5), 0)
        for pid in children:
            with self.assertRaises(ProcessLookupError):
                os.kill(pid, 0)

    def test_copied_install_layout_and_tilde_config_need_no_bin_path(self):
        home = self.base / 'home with spaces'
        local_bin = home / '.local/bin'
        polybar = home / '.config/polybar'
        local_bin.mkdir(parents=True)
        polybar.mkdir(parents=True)
        for source in [WALL, LIVE, WALL.with_name('launcher_common.py')]:
            shutil.copy2(source, local_bin / source.name)
        installed_bar = polybar / 'launch.sh'
        shutil.copy2(BAR, installed_bar)
        env = dict(self.env, HOME=str(home), XDG_CONFIG_HOME=str(home / '.config'))
        config = home / '.config/debian-i3-dotfiles/wallpaper-path'
        config.parent.mkdir()
        video = home / 'a video.mp4'
        video.write_bytes(b'video')
        config.write_text('~/a video.mp4\n')
        result = self.run_script(local_bin / WALL.name, '--dry-run', env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        argv = json.loads(result.stdout)[0]['argv']
        self.assertEqual(argv[-3:], [str(local_bin / LIVE.name), 'WID', str(video)])
        result = self.run_script(installed_bar, '--dry-run', env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)[0]['argv'][1], '--config=' + str(polybar / 'config.ini'))
        option_video = home / '--odd video.mp4'
        option_video.write_bytes(b'video')
        result = subprocess.run([str(local_bin / WALL.name), '--dry-run', '--', option_video.name],
                                cwd=home, env=env, text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)[0]['argv'][-1], str(option_video))

    def test_optional_video_and_config_are_data(self):
        result = self.run_script(WALL, '--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [])
        config = Path(self.env['XDG_CONFIG_HOME']) / 'debian-i3-dotfiles/wallpaper-path'
        config.parent.mkdir(parents=True)
        config.write_text(str(self.video) + '\n')
        result = self.run_script(WALL, '--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)[0]['argv'][-1], str(self.video))
        config.write_text('$(touch should-not-exist)\n')
        result = self.run_script(WALL, '--dry-run')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((ROOT / 'should-not-exist').exists())

    def test_wallpaper_dry_run_dynamic_geometry(self):
        result = self.run_script(WALL, '--dry-run', self.video)
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads(result.stdout)
        self.assertEqual(len(plan), 2)
        for item, geometry in zip(plan, ['1920x1080+0+0', '1280x720-1280-40']):
            self.assertEqual(item['argv'][:3], ['xwinwrap', '-g', geometry])
            self.assertEqual(item['argv'][-3:], [str(LIVE), 'WID', str(self.video)])
        self.assertFalse(Path(self.env['XDG_RUNTIME_DIR']).exists())


if __name__ == '__main__':
    unittest.main()
