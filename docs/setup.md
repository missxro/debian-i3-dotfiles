# Manual setup

> Work in progress. Back up existing files before replacing them. No installer or rollback is provided yet.


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

**Do not overwrite a working desktop blindly.** Automatic backup, installation, and rollback are not implemented yet.

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
