#!/usr/bin/env python3
"""Interactive, reversible user configuration installer. Python standard library only."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import sys
import uuid

ROOT = Path(__file__).resolve().parent
MODULES = {'core': ['i3', 'kitty', 'picom', 'polybar'],
           'gtk': ['gtk-3.0'], 'qt': ['qt5ct'], 'fastfetch': ['fastfetch']}
BANNER = r'''
    ____  __________  _________    _   __
   / __ \/ ____/ __ )/  _/   |  / | / /
  / / / / __/ / __  |/ // /| | /  |/ /
 / /_/ / /___/ /_/ // // ___ |/ /|  /
/_____/_____/_____/___/_/  |_/_/ |_/
          [ DEBIAN / i3 rice / dotfiles ]
'''


def plan(modules):
    home = Path.home()
    config = Path(os.environ.get('XDG_CONFIG_HOME', str(home / '.config')))
    if not config.is_absolute() or config != home / '.config':
        raise ValueError('This rice requires XDG_CONFIG_HOME=$HOME/.config (hardcoded launcher paths).')
    files = []
    for module in modules:
        for name in MODULES[module]:
            for source in sorted((ROOT / 'config' / name).rglob('*')):
                if source.is_file() and '__pycache__' not in source.parts:
                    files.append((source, config / source.relative_to(ROOT / 'config')))
    if 'core' in modules:
        files.extend((source, home / '.local/bin' / source.name)
                     for source in sorted((ROOT / 'bin').iterdir()) if source.is_file())
    return files


def safe_target(path):
    """Never follow a symlink out of the user's managed destination tree."""
    home = Path.home().absolute()
    if not path.is_absolute() or '..' in path.parts or not path.is_relative_to(home) or path == home:
        raise ValueError('Unsafe destination: ' + str(path))
    for parent in (path, *path.parents):
        if parent == home:
            break
        if parent.is_symlink():
            raise ValueError('Symlink destination; move it aside explicitly first: ' + str(parent))
    if path.exists() and not path.is_file():
        raise ValueError('Destination is not a regular file: ' + str(path))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signature(path):
    return {'sha256': digest(path), 'mode': stat.S_IMODE(path.stat().st_mode)}


def same(source, target):
    return target.is_file() and signature(source) == signature(target)


def validate_state_path(path):
    safe_target(path / 'probe')
    home = Path.home().absolute()
    for parent in (path, *path.parents):
        if parent.exists():
            info = parent.stat()
            if not parent.is_dir() or info.st_uid != os.getuid() or info.st_mode & 0o022:
                raise ValueError('State path must be owned by you and not writable by others: ' + str(parent))
        if parent == home:
            break


def state_path():
    return Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'debian-i3-dotfiles'


def state_directory():
    directory = state_path()
    validate_state_path(directory)
    safe_target(directory / 'lock')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if directory.stat().st_uid != os.getuid() or directory.stat().st_mode & 0o077:
        raise ValueError('State directory must be private (0700): ' + str(directory))
    return directory


def write_json(path, value):
    with tempfile.NamedTemporaryFile(mode='w', prefix='.manifest-', dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            output.write(json.dumps(value, indent=2) + '\n')
            output.flush()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def atomic_copy(source, target):
    with tempfile.NamedTemporaryFile(prefix='.dotfiles-', dir=target.parent, delete=False) as output:
        temporary = Path(output.name)
    try:
        shutil.copy2(source, temporary)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def install(files, state):
    changed = [(source, target) for source, target in files if not same(source, target)]
    if not changed:
        print('\nAlready up to date. No files changed; no new backup.')
        return
    safe_target(state / 'backups' / 'probe')
    backup = state / 'backups' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8])
    backup.mkdir(parents=True, mode=0o700)
    manifest = {'version': 1, 'home': str(Path.home()), 'entries': [], 'restored': False}
    # Prepare every original and the journal before changing any configuration.
    for index, (source, target) in enumerate(changed):
        original = str(index) if target.exists() else None
        if original is not None:
            shutil.copy2(target, backup / original)
        manifest['entries'].append({'target': str(target), 'original': original,
                                    'original_signature': signature(target) if original is not None else None,
                                    'installed': signature(source)})
    write_json(backup / 'manifest.json', manifest)
    print('\nBackup: ' + str(backup), flush=True)
    print('Restore: ./install.sh --restore ' + str(backup), flush=True)
    try:
        for source, target in changed:
            safe_target(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_copy(source, target)
            print('  Installed ' + str(target))
    except (OSError, KeyboardInterrupt):
        print('Installation interrupted; attempting rollback.', file=sys.stderr)
        restore(backup, False)
        raise
    print('\nDone. Start a new i3 session when ready; nothing was restarted.')


def restore(backup, dry_run):
    backup = backup.expanduser().absolute()
    if backup.parent != state_path() / 'backups':
        raise ValueError('Backup must be in your installer state directory.')
    validate_state_path(backup)
    if state_path().stat().st_mode & 0o077 or backup.stat().st_mode & 0o077:
        raise ValueError('Backup and state directories must be private (0700).')
    safe_target(backup / 'manifest.json')
    if (backup / 'manifest.json').stat().st_uid != os.getuid():
        raise ValueError('Backup manifest must belong to you.')
    allowed = {str(target) for source, target in plan(list(MODULES))}
    allowed.add(str(Path.home() / '.config/debian-i3-dotfiles/wallpaper-path'))
    manifest = json.loads((backup / 'manifest.json').read_text())
    if manifest.get('version') != 1 or manifest.get('home') != str(Path.home()):
        raise ValueError('Backup version or home does not match this user.')
    if manifest.get('restored'):
        print('This backup has already been restored.')
        return
    for entry in manifest['entries']:
        target = Path(entry['target'])
        if str(target) not in allowed:
            raise ValueError('Backup destination is not managed by this installer: ' + str(target))
        safe_target(target)
        original = entry['original']
        if original is not None and (not isinstance(original, str) or not original.isdecimal()
                                     or not (backup / original).is_file() or (backup / original).is_symlink()):
            raise ValueError('Invalid backup entry.')
        if original is not None and signature(backup / original) != entry['original_signature']:
            raise ValueError('Backup file is damaged or changed: ' + str(backup / original))
        # Do not silently delete edits made after installation, even with --yes.
        if target.exists() and signature(target) != entry['installed']:
            if original is None or not same(backup / original, target):
                raise ValueError('Changed since install; save/move it before restoring: ' + str(target))
        print('  Restore ' + str(target))
    if dry_run:
        return
    with tempfile.TemporaryDirectory(prefix='.restore-', dir=backup) as folder:
        staged = []
        for number, entry in enumerate(manifest['entries']):
            target = Path(entry['target'])
            current = Path(folder) / str(number) if target.exists() else None
            if current is not None:
                shutil.copy2(target, current)
            staged.append((target, current))
        try:
            for entry in reversed(manifest['entries']):
                target = Path(entry['target'])
                if entry['original'] is None:
                    target.unlink(missing_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    atomic_copy(backup / entry['original'], target)
            manifest['restored'] = True
            write_json(backup / 'manifest.json', manifest)
        except (OSError, KeyboardInterrupt):
            # Atomic manifest replacement is the commit point. An interruption
            # after it must not roll the files back to the installed state.
            persisted = json.loads((backup / 'manifest.json').read_text())
            if persisted.get('restored'):
                raise
            for target, current in staged:
                if current is None:
                    target.unlink(missing_ok=True)
                else:
                    atomic_copy(current, target)
            raise
    print('Restored. Backups retained; packages and empty directories are not removed.')


def ask(question, default=False):
    suffix = ' [Y/n] ' if default else ' [y/N] '
    while True:
        try:
            answer = input(question + suffix).strip().lower()
        except EOFError as error:
            raise ValueError('Input ended. Use --yes for unattended file-only installation.') from error
        if not answer:
            return default
        if answer in ('y', 'yes', 's', 'si', 'sí'):
            return True
        if answer in ('n', 'no'):
            return False
        print('Please answer y or n.')


def package_names(modules):
    packages = []
    if 'core' in modules:
        for line in (ROOT / 'packages/debian.txt').read_text().splitlines():
            packages.extend(line.split('#', 1)[0].split())
    for module, names in {'gtk': ['lxappearance', 'adwaita-icon-theme'],
                          'qt': ['qt5ct'], 'fastfetch': ['fastfetch']}.items():
        if module in modules:
            packages.extend(names)
    return list(dict.fromkeys(packages))


def check_system():
    if os.geteuid() == 0:
        raise ValueError('Run as your desktop user, not root. Only apt uses sudo.')
    release = Path('/etc/os-release').read_text()
    if 'ID=debian' not in release.splitlines() or 'VERSION_ID="13"' not in release.splitlines():
        raise ValueError('Automated package setup targets Debian 13. Use --files-only on other systems.')
    if os.environ.get('XDG_SESSION_TYPE') == 'wayland':
        raise ValueError('This configuration requires an X11/i3 session, not Wayland.')


def setup_packages(modules, enabled):
    packages = package_names(modules)
    print('\nDebian packages: ' + ' '.join(packages))
    print('Only apt is elevated. No shell changes, display-manager changes or service restarts are requested.')
    if not enabled:
        print('Package installation skipped (--yes never grants permission for apt).')
        return
    if not ask('Run sudo apt-get update, then sudo apt-get install for these packages?'):
        return
    if not shutil.which('sudo') or not shutil.which('apt-get'):
        raise ValueError('sudo/apt-get unavailable. Ask your administrator to install the listed packages.')
    subprocess.run(['sudo', 'apt-get', 'update'], check=True)
    # Do not use -y: apt displays its actual transaction and requests approval.
    subprocess.run(['sudo', 'apt-get', 'install', *packages], check=True)


def diagnostics(modules):
    print('\nDependency check:')
    commands = ['i3', 'i3lock', 'xss-lock', 'polybar', 'kitty', 'picom', 'dmenu_run', 'dex', 'cava', 'xrandr', 'pactl', 'zsh'] if 'core' in modules else []
    if 'fastfetch' in modules:
        commands.append('fastfetch')
    for command in commands:
        print(f"  {'OK     ' if shutil.which(command) else 'MISSING'} {command}")
    if 'core' in modules:
        for module in ('dbus', 'gi'):
            result = subprocess.run(['/usr/bin/python3', '-c', '__import__(' + repr(module) + ')'],
                                    capture_output=True, text=True)
            print(f"  {'OK     ' if result.returncode == 0 else 'MISSING'} python3-{module}")
        print('  DepartureMono Nerd Font Mono, Graphite-Dark and Kitty cursor assets are not bundled.')
        print('  No remote installer or unpinned third-party download is executed.')
    if 'qt' in modules:
        print('  Qt: set QT_QPA_PLATFORMTHEME=qt5ct in your session environment if needed (not overwritten).')


def prepare(files, args, staging):
    """Customize copies, never the versioned originals."""
    result = []
    for index, (source, target) in enumerate(files):
        if source.name == 'kitty.conf' and (args.font or args.shell):
            text = source.read_text()
            if args.font:
                text = text.replace('font_family DepartureMono Nerd Font Mono', 'font_family ' + args.font)
            if args.shell:
                text = text.replace('shell zsh', 'shell ' + args.shell)
            copy = staging / str(index)
            copy.write_text(text)
            copy.chmod(stat.S_IMODE(source.stat().st_mode))
            source = copy
        elif source.name == 'config' and source.parent.name == 'i3' and args.font:
            copy = staging / str(index)
            copy.write_text(source.read_text().replace('font pango:DepartureMono Nerd Font 12',
                                                       'font pango:' + args.font + ' 12'))
            copy.chmod(stat.S_IMODE(source.stat().st_mode))
            source = copy
        elif source.name == 'config.ini' and source.parent.name == 'polybar' and args.font:
            text = source.read_text().replace('DepartureMono Nerd Font Mono:size=13', args.font + ':size=13')
            copy = staging / str(index)
            copy.write_text(text)
            copy.chmod(stat.S_IMODE(source.stat().st_mode))
            source = copy
        result.append((source, target))
    if args.wallpaper:
        video = args.wallpaper.expanduser().resolve()
        if not video.is_file() or '\n' in str(video):
            raise ValueError('Wallpaper must be an existing local video file.')
        missing = [name for name in ('mpv', 'xwinwrap') if not shutil.which(name)]
        if missing:
            raise ValueError('Video wallpaper needs: ' + ', '.join(missing) + '. Install them separately or skip --wallpaper.')
        source = staging / 'wallpaper-path'
        source.write_text(str(video) + '\n')
        result.append((source, Path.home() / '.config/debian-i3-dotfiles/wallpaper-path'))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Print planned files; never write or install packages.')
    parser.add_argument('--modules', default='core', help='Comma-separated: core,gtk,qt,fastfetch')
    parser.add_argument('--yes', action='store_true', help='Accept file installation/restore; does not install packages.')
    parser.add_argument('--files-only', action='store_true', help='Only copy files; skip OS/dependency setup.')
    parser.add_argument('--restore', type=Path, help='Restore a backup directory, refusing later local edits.')
    parser.add_argument('--font', help='Installed font family for Kitty and Polybar; no font download.')
    parser.add_argument('--shell', choices=['zsh', 'bash'], help='Kitty shell only; never runs chsh.')
    parser.add_argument('--wallpaper', type=Path, help='Existing local video; requires mpv and xwinwrap.')
    args = parser.parse_args()
    for value in (args.font,):
        if value is not None and (not value.strip() or any(char in value for char in '\n\r;=')):
            parser.error('Invalid font family.')
    print(BANNER)
    if args.restore:
        if not args.dry_run and not args.yes and not ask('Restore this backup (later local edits will be refused)?'):
            print('Cancelled. No files changed.')
            return 0
        if args.dry_run:
            restore(args.restore, True)
        else:
            state = state_directory()
            with (state / 'lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                restore(args.restore, False)
        return 0
    modules = list(dict.fromkeys(args.modules.split(',')))
    if any(module not in MODULES for module in modules):
        parser.error('Unknown module; choose core,gtk,qt,fastfetch.')
    if not args.dry_run and not args.yes and args.modules == 'core':
        print('Core: i3 + Polybar + Picom + Kitty + wallpaper helpers.')
        for module, label in [('gtk', 'GTK settings (Graphite-Dark and Kitty cursor must already exist)'),
                              ('qt', 'Qt settings (qt5ct)'), ('fastfetch', 'Fastfetch + bundled artwork')]:
            if ask('Include ' + label + '?'):
                modules.append(module)
    if args.wallpaper and 'core' not in modules:
        parser.error('--wallpaper requires core.')
    files = plan(modules)
    for source, target in files:
        safe_target(target)
        print(f'  {source.relative_to(ROOT)} -> {target}')
    if args.dry_run:
        print('\nPackages (not executed): ' + ' '.join(package_names(modules)))
        print(f'Font: {args.font or "DepartureMono Nerd Font Mono"}; Kitty shell: {args.shell or "zsh"}')
        if args.wallpaper:
            print('Wallpaper path (not written): ' + str(args.wallpaper))
        return 0
    if not args.yes and not ask('Apply this selection? Existing managed files will be backed up.'):
        print('Cancelled. No files changed.')
        return 0
    if not args.files_only:
        check_system()
        setup_packages(modules, enabled=not args.yes)
        diagnostics(modules)
        if 'core' in modules and not args.yes:
            if not args.font and ask('Use DejaVu Sans Mono instead of the external Nerd Font? Icons may be missing.'):
                args.font = 'DejaVu Sans Mono'
            if not args.shell and not shutil.which('zsh'):
                if ask('zsh is missing. Use bash in Kitty?', default=True):
                    args.shell = 'bash'
                else:
                    raise ValueError('Install zsh or choose --shell bash before installing core.')
            if not args.wallpaper and ask('Configure a local video wallpaper? Requires mpv and xwinwrap.'):
                args.wallpaper = Path(input('Video path (no download): ').strip())
    with tempfile.TemporaryDirectory(prefix='dotfiles-') as folder:
        files = prepare(files, args, Path(folder))
        for source, target in files:
            safe_target(target)
        state = state_directory()
        with (state / 'lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            install(files, state)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, EOFError) as error:
        print(f'Error: {error}', file=sys.stderr)
        raise SystemExit(1)
    except KeyboardInterrupt:
        print('\nCancelled.', file=sys.stderr)
        raise SystemExit(130)
