# debian-i3-dotfiles

My Debian 13 rice — i3wm, Polybar, Kitty, Picom & animated wallpapers.

## Preview

![Desktop preview](assets/desktop.gif)

### Polybar

![Polybar modules and controls explained](assets/polybar-described.png)

## Setup

- **OS:** Debian 13 / X11
- **WM:** i3 / gaps / pixel borders / Mod4
- **Bar:** Polybar / Cava / MPRIS / volume / system stats
- **Terminal:** Kitty / Ayaka / Zsh
- **Compositor:** Picom / blur / transparency / fading
- **Wallpaper:** xwinwrap + MPV / one video per active monitor
- **Font:** DepartureMono Nerd Font Mono
- **Included by default:** Fastfetch with bundled artwork
- **Optional:** GTK3 / Graphite-Dark / Qt5ct / Kitty cursor download

## Features

- Automatic monitor detection — no fixed outputs or resolutions.
- Bundled Lain video wallpaper, configured automatically; `--wallpaper` selects another local video.
- Launcher dry-runs and per-display singleton locks.
- Cleanup limited to each launcher's own children.

## Files

```text
config/     i3 / Polybar / Kitty / Picom / optional appearance
bin/        Wallpaper launchers + shared supervisor helper
packages/   Core and optional Debian package lists
assets/     Desktop preview + licensed DepartureMono fonts
docs/       Manual setup + portability notes
tests/      Repository, launcher and MPRIS checks
```

## Getting started

On Debian 13, run from the repository directory as your normal user:

```sh
./install.sh
```

The installer offers to install the required packages, installs missing bundled fonts and configures the animated wallpaper automatically. Existing files are backed up. Do not run the installer with `sudo`.

Experimental package setup also recognizes Ubuntu 22.04/24.04, Kali rolling and Parrot 6/7; these still need clean-VM testing. When package installation is approved, missing package candidates stop setup before file placement. Fastfetch stays included: if apt has no candidate, the approved package step downloads the official Fastfetch 2.70.0 `.deb` for amd64/arm64, verifies its pinned SHA256 and metadata, and installs it through apt without adding repositories. Python 3.11+ must already be available. See [package support and limitations](docs/package-support.md).

To preview changes without installing anything:

```sh
./install.sh --dry-run
```

Python 3.11+ is required to start the installer. An existing i3 session is not required: after installation, select i3 in your login screen. See [setup & recovery](docs/setup.md) for prerequisites, optional components and restore instructions.

## Checks

```sh
python3 -m unittest discover -s tests -v
```

- Automated tests use isolated external-program mocks.
- i3 / Polybar parser checks and real-monitor dry-runs completed.
- Fresh-install visual verification still pending.

[Manual setup & shortcuts](docs/setup.md) / [Portability & remaining work](docs/portability.md)
