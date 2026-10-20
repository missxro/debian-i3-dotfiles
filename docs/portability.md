# Portability notes
Ubuntu core requires i3 >= 4.22. If its native candidate is older, a **separate default-no confirmation** offers the sur5r signed repository recommended by i3. Its pinned keyring is checksum-verified; HTTPS, `signed-by` and i3-only apt pinning are used. Repository files and keyring persist after restore. No automatic session restart or login-shell change occurs. This option never runs with `--yes`, `--files-only` or `--dry-run`. See `docs/package-support.md` for exact paths and limitations.


## What was kept

The original desktop's Ayaka palette, Kitty settings, Picom blur/fading, i3 gaps and borders, and Polybar's Cava/MPRIS integration form the core of this rice. The existing Cava and MPRIS modules are imported, not rewritten in this first pass.

## Intentional changes

- No personal files, SSH keys, service units, environment files, histories, browser/app profiles, or GTK bookmarks.
- No fixed monitor identifiers, resolution, refresh rate, absolute home path, OneDrive dependency, or hardware-vendor-specific video decoding.
- One Polybar definition instantiated per active monitor. Undefined module references were removed rather than left broken. Font Awesome and emoji family names match the intended Debian font packages.
- Video wallpaper scripts use the current X11 monitor geometry, accept a local file, and own their launched processes. No global process killing.
- i3 launches its desktop helpers once per session rather than on every config reload. Its startup lines use the conventional config directory; customize them if you use a non-default one.
- Focus uses h/j/k/l or arrows rather than a keyboard-layout-specific letter. Horizontal split uses Mod+b.
- Floating-only color directives that produced parser errors were replaced with valid i3 client color directives.
- No obsolete Picom experimental backend flag; the opacity-rule list is terminated correctly.
- Fastfetch includes the original artwork with a portable home-relative path and automatic GPU information rather than a fixed model suffix.
- No dangerous direct terminate-user shortcut; exiting the session asks for confirmation.

## Optional pieces, not silently installed

GTK and Qt configuration are opt-in. Theme and cursor files are not bundled, and GTK4 theme assets are not copied in this first pass. Zsh is selected in Kitty, but personal shell configuration, Powerlevel10k files, clipboard tooling, and SDDM are not included yet. Adding these should not overwrite an existing shell or change the display manager as a side effect.

A wallpaper is optional. The launchers do not configure monitor layout, manage display hotplug, or replace your audio system. Missing external runtime programs should be reported, not installed automatically.

## Validation boundary

The i3 configuration was checked with the Debian i3 parser without reloading the source desktop. Polybar's parser also read the configuration using its dump-only mode, without starting a bar. Wallpaper and Polybar dry-runs were exercised against an actual three-monitor X11 layout without launching background processes. Automated launcher tests use fake external X11/media programs and temporary files: they check behavior, not rendering or GPU compatibility. Imported Cava/MPRIS code retains its existing runtime dependencies; Python compilation is not a full audio-player integration test.

A visual check on a disposable Debian 13 X11 session is still needed before calling this a tested fresh-install experience. Do not assume a passing unit suite makes the setup safe to copy over an existing desktop without a backup.

## Installer boundary

`install.sh` provides interactive component selection, optional apt package setup, dry-run, idempotent file placement, private backups and guarded restore. Package setup remains supported on Debian 13. Ubuntu 22.04/24.04, Kali, and Parrot package setup is provisional, awaiting candidate and VM validation. Fastfetch stays included: if no native candidate exists, the approved package step verifies and installs the pinned official 2.70.0 `.deb` for amd64/arm64. Declining package installation, `--yes`, or `--files-only` bypass candidate checks and leave dependency provisioning to the user. Ubuntu 26.04 is not enabled for package setup because the complete package set was not verified. See [package support notes](package-support.md). Missing apt candidates stop setup before file placement, with guidance; only the separately approved Ubuntu i3 flow changes repositories. Login-shell, display-manager and running-session settings remain untouched. It offers an explicitly approved, checksum-pinned Kitty cursor download; it also supports the verified Fastfetch package fallback and builds bundled pinned xwinwrap source after package approval. Fonts and the default video are bundled; Graphite-Dark remains external. This does not prove GPU/rendering compatibility. Credits and licensing review are deferred to a later pass, as requested; existing metadata in imported files is preserved.
