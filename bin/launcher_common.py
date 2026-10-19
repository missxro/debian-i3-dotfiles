"""Shared X11 monitor planning for the portable launchers."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import shutil
import stat
import time
import subprocess
import sys
import tempfile


def monitors():
    result = subprocess.run(['xrandr', '--listactivemonitors'], check=True,
                            capture_output=True, text=True)
    found = []
    for line in result.stdout.splitlines():
        match = re.match(r'\s*\d+:\s+\S+\s+(\d+)/(?:\d+)x(\d+)/(?:\d+)([+-]\d+)([+-]\d+)\s+(\S+)', line)
        if match:
            width, height, x, y, name = match.groups()
            found.append((name, f'{width}x{height}{x}{y}'))
    return found


def main(kind, live=None, config=None):
    try:
        return run(kind, live, config)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'{kind}: {error}', file=sys.stderr)
        return 1


def run(kind, live, config):
    parser = argparse.ArgumentParser(description='Plan or supervise per-monitor X11 children.')
    parser.add_argument('--dry-run', action='store_true', help='Print JSON argv without launching children.')
    if kind == 'wallpaper':
        parser.add_argument('video', nargs='?', help='Video file; use -- before option-looking paths.')
    args = parser.parse_args()
    if not os.environ.get('DISPLAY') or os.environ.get('XDG_SESSION_TYPE', 'x11').lower() != 'x11':
        print(f'{kind}: no X11 session; skipping.', file=sys.stderr)
        if args.dry_run:
            print('[]')
        return 0
    if kind == 'polybar':
        plan = [{'argv': ['polybar', '--config=' + str(config), 'main'],
                 'env': {'MONITOR': name}} for name, geometry in monitors()]
    else:
        value = args.video
        if value is None:
            config_path = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'debian-i3-dotfiles/wallpaper-path'
            if config_path.is_file():
                value = config_path.read_text().strip()
        if not value:
            if args.dry_run:
                print('[]')
            return 0
        video = str(Path(value).expanduser().resolve())
        if not Path(video).is_file():
            parser.error('Video must be an existing regular file: ' + video)
        executable = 'xwinwrap'
        local = Path.home() / '.local/bin/xwinwrap'
        if not shutil.which(executable) and local.is_file() and os.access(local, os.X_OK):
            executable = str(local)
        plan = [{'argv': [executable, '-g', geometry, '-un', '-fdt', '-ni', '-b',
                          '-nf', '-ov', '--', str(live), 'WID', video]}
                for name, geometry in monitors()]
    if args.dry_run:
        print(json.dumps(plan))
        return 0
    if not plan:
        return 0
    for dependency in (['xwinwrap', 'mpv'] if kind == 'wallpaper' else ['polybar']):
        if dependency == 'xwinwrap':
            dependency = plan[0]['argv'][0]
        if shutil.which(dependency) is None:
            raise ValueError('Required executable not found: ' + dependency)
    runtime = os.environ.get('XDG_RUNTIME_DIR')
    directory = (Path(runtime) / 'debian-i3-dotfiles' if runtime else
                 Path(tempfile.gettempdir()) / f'debian-i3-dotfiles-{os.getuid()}')
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('Lock directory must be a private directory owned by this user: ' + str(directory))
    display_key = hashlib.sha256(os.environ['DISPLAY'].encode()).hexdigest()[:24]
    # Never unlink: waiters and future invocations must lock the same inode.
    with (directory / f'{kind}-{display_key}.lock').open('a') as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(f'{kind}: an instance already owns this display; skipping.', file=sys.stderr)
            return 0
        # The descriptor is non-inheritable and stays open through child cleanup.
        return supervise(plan)


def supervise(plan):
    """Signal and reap only Popen children created by this supervisor."""
    children = []
    stopping = False

    def request_stop(signum, frame):
        nonlocal stopping
        stopping = True

    previous = {sig: signal.signal(sig, request_stop)
                for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        for item in plan:
            if stopping:
                break
            children.append(subprocess.Popen(item['argv'], env={**os.environ, **item.get('env', {})}))
        while children and not stopping:
            for child in children:
                code = child.poll()
                if code is not None:
                    return 0 if code == 0 else 1
            time.sleep(0.05)
        return 0
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        deadline = time.monotonic() + 3
        for child in children:
            try:
                child.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        for sig, handler in previous.items():
            signal.signal(sig, handler)
