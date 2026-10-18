# Setup

## Interactive installer

Run as your desktop user, not with `sudo`:

```sh
./install.sh --dry-run --modules core,gtk,qt,fastfetch
./install.sh
```

The ASCII-headed wizard selects optional GTK, Qt and Fastfetch components, lists affected files and asks before applying. It offers Debian 13 packages through `sudo apt-get`, with separate approval and apt's own transaction prompt. Only apt is elevated. Python 3.11+ is required; cloning this repo changes nothing.

```sh
# Explicit components, still interactive
./install.sh --modules core,fastfetch
# Already have dependencies? Skip OS/package setup
./install.sh --files-only
# Unattended file placement; --yes never approves apt
./install.sh --files-only --yes --modules core,fastfetch
# Use an already installed font and change only Kitty's shell
./install.sh --font 'DejaVu Sans Mono' --shell bash
# Existing local video; requires mpv and xwinwrap
./install.sh --wallpaper "$HOME/Videos/wallpaper.mp4"
```

Core installs i3, Kitty, Picom, Polybar and helper scripts. Files are copied, not linked: the clone can move afterward. Unrelated files are retained; identical content and permissions are left untouched on repeat runs. This rice requires `$HOME/.config` because its startup paths use that convention. Other `XDG_CONFIG_HOME` values and symlinked destinations are refused instead of silently writing elsewhere.

Original files and a manifest are saved under `${XDG_STATE_HOME:-$HOME/.local/state}/debian-i3-dotfiles/backups/`. The installer prints the exact directory and restore command:

```sh
./install.sh --restore "$HOME/.local/state/debian-i3-dotfiles/backups/<backup>" --dry-run
./install.sh --restore "$HOME/.local/state/debian-i3-dotfiles/backups/<backup>"
```

Backups must remain inside that private state directory, owned by your user, with no symlinked or group/world-writable parents. Restore reinstates originals with their permissions and removes files created by that installation. It refuses later local edits and damaged backups: save/move edits deliberately before retrying. Backups, empty directories and installed packages are retained. File replacement is atomic; failed/interrupted placement or restore attempts rollback. Rollback also needs a writable filesystem; power loss, hard kill or persistent disk errors may require manual recovery from the retained backups. Restore multiple backups newest first, using the matching installer version.

The wizard offers the packaged DejaVu font as an alternative to the external Nerd Font (some glyphs may be absent), bash for Kitty when zsh is missing, and a local video path. It never runs `chsh`, reloads your desktop, rewrites login settings, replaces your audio stack or configures a display manager. Start an i3 X11 session yourself when ready.

**External assets are not downloaded:** DepartureMono Nerd Font Mono, Graphite-Dark, the Kitty cursor, xwinwrap and video files must already exist for the exact original appearance. Decline GTK if its theme/cursor assets are missing. Powerlevel10k and personal Zsh configuration are not included. Qt may need `QT_QPA_PLATFORMTHEME=qt5ct` in your session. Missing dependencies are reported; declining apt does not satisfy them. The Firefox and Flameshot shortcuts require those optional apps separately.

## Manual setup


## Requirements

Target: **Debian 13 with an existing i3/X11 session**. Not Wayland, a desktop migration tool, or a complete operating-system setup.

Debian package names are listed in `packages/debian.txt`. Inspect the list before installing anything. Kitty explicitly uses Zsh, but this repo does not change your login shell.

Additional components not bundled here:

- **DepartureMono Nerd Font**, including the Mono variant. Alternatively change font names in i3, Polybar, and Kitty.
- **xwinwrap**, only for animated wallpapers. No automatic download or build is provided yet.
- A local video of your choice. With no configured video, wallpaper startup is a no-op.
- An existing PulseAudio-compatible server, such as PipeWire with its PulseAudio interface. The repo does not replace your audio stack.

Optional GTK settings assume Graphite-Dark and the Kitty cursor are already installed. Qt5ct requires `QT_QPA_PLATFORMTHEME=qt5ct` in your own session environment. None of these optional settings is required for the core desktop.

## Trying it safely

1. Read the configs and back up every destination first.
2. Place `i3`, `kitty`, `picom`, and `polybar` from `config/` under `~/.config/`. Do not replace your entire config directory.
3. Place **all three files** from `bin/` under `~/.local/bin/`: `wallpaper-wrap`, `wallpaper-live`, and `launcher_common.py`. The two entry points must remain executable. Polybar's launcher imports the shared helper from this directory; its own launcher and Python modules must also remain executable.
4. Validate with `i3 -C -c "$HOME/.config/i3/config"`; read the output, not only the exit status.
5. Start a fresh i3 session when ready. Reloading the config does not deliberately restart background processes.

The i3 startup lines use conventional `~/.config/` and `~/.local/bin/` locations. Adjust them if yours differ. The wallpaper data file honors `XDG_CONFIG_HOME`.

**Do not overwrite a working desktop blindly.** The installer above backs up managed files; when copying manually, make your own backups first.

### Choose a wallpaper

Keep the video outside the repository. Store its local path as plain text:

```sh
mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/debian-i3-dotfiles"
printf '%s\n' "$HOME/Videos/wallpaper.mp4" > "${XDG_CONFIG_HOME:-$HOME/.config}/debian-i3-dotfiles/wallpaper-path"
```

Use an existing video on your machine. This file is data, not shell code; never commit your local path file.

Preview without launching background processes:

```sh
./bin/wallpaper-wrap --dry-run "$HOME/Videos/wallpaper.mp4"
./config/polybar/launch.sh --dry-run
```

The previews need X11 and `xrandr` to discover active monitors. Normal launch also requires the corresponding runtime programs.

Launchers use the existing display layout; they do not change modes, refresh rates, positions, or the primary display. Hotplug requires restarting the relevant supervisor; live reconfiguration is not included yet.

### Fastfetch (optional)

Back up `~/.config/fastfetch/`, then copy the entire `config/fastfetch/` directory there, including `roxy-mushoku-tensei-2.png`. Run `fastfetch` inside Kitty to display the bundled artwork using `kitty-direct`. The image path uses the current user's home, not the source machine's path. If you use a custom config directory, update `logo.source` accordingly.

### Shortcuts

`Mod` is the Super/Windows key.

- `Mod + Return`: Kitty; `Mod + d`: dmenu.
- `Mod + q`: close the focused window.
- `Mod + h/j/k/l` or arrows: focus left/down/up/right; add Shift to move a window.
- `Mod + b` / `Mod + v`: horizontal / vertical split.
- `Mod + 1…0`: workspaces 1–10; add Shift to move a window there.
- `Mod + Shift + Space`: toggle floating; `Mod + f`: fullscreen.
- `Mod + r`: resize mode; Escape to leave it.
- `Mod + Shift + c`: reload; `Mod + Shift + r`: restart i3 in place.
- `Mod + Shift + e`: ask before exiting.
- `Mod + Shift + g`: Flameshot; `Mod + Shift + f`: Firefox, if installed.

Polybar playback: left click previous, right click next, middle click play/pause.


[Back to README](../README.md) / [Portability notes](portability.md)
