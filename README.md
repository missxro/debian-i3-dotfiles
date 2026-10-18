# debian-i3-dotfiles

My Debian 13 rice — i3wm, Polybar, Kitty, Picom & animated wallpapers.

## Preview

![Desktop preview](assets/desktop.gif)

## Setup

- **OS:** Debian 13 · X11
- **WM:** i3 · gaps · pixel borders · Mod4
- **Bar:** Polybar · Cava · MPRIS · volume · system stats
- **Terminal:** Kitty · Ayaka · Zsh
- **Compositor:** Picom · blur · transparency · fading
- **Wallpaper:** xwinwrap + MPV · one video per active monitor
- **Font:** DepartureMono Nerd Font Mono
- **Optional:** GTK3 / Graphite-Dark · Qt5ct · Fastfetch

## Features

- Automatic monitor detection — no fixed outputs or resolutions.
- Local wallpaper selection — no personal paths or bundled video.
- Launcher dry-runs and per-display singleton locks.
- Cleanup limited to each launcher's own children.

## Files

```text
config/     i3 · Polybar · Kitty · Picom · optional appearance
bin/        Wallpaper launchers + shared supervisor helper
packages/   Core and optional Debian package lists
assets/     Desktop preview
docs/       Manual setup + portability notes
tests/      Repository, launcher and MPRIS checks
```

## Getting started

1. **Requirements:** existing Debian 13 i3/X11 session and an audio server.
2. **Packages:** [core](packages/debian.txt) · [optional](packages/optional-debian.txt).
3. **Extra components:** DepartureMono Nerd Font; xwinwrap and a local video for animated wallpaper.
4. **Back up first**, then follow the [manual setup guide](docs/setup.md).

> **Work in progress:** no automatic installer, backup or rollback yet. Optional theme/cursor assets are not bundled. Cloning this repository does not change your desktop.

## Checks

```sh
python3 -m unittest discover -s tests -v
```

- Automated tests use isolated external-program mocks.
- i3 / Polybar parser checks and real-monitor dry-runs completed.
- Fresh-install visual verification still pending.

[Manual setup & shortcuts](docs/setup.md) · [Portability & remaining work](docs/portability.md)
