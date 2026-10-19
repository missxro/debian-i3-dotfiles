# Debian-family package profile notes

Installer package setup is gated by exact distro IDs and supported versions; `ID_LIKE` alone is never accepted. When the package step is approved, package candidates are checked with `apt-cache policy` before `apt-get update`, installation, or file placement. Missing candidates stop that operation and identify the missing packages; repository configuration is never changed. Existing skip semantics remain unchanged: `--yes`, `--files-only`, or declining the package prompt skip both package installation and candidate checks; users taking those paths must supply dependencies themselves. `--dry-run` does not check candidates or install anything.

## Ubuntu evidence and limitation

The official Ubuntu package archives show `i3-wm` for Jammy, Noble, and Resolute. Fastfetch is absent from the Jammy and Noble archive indexes, while the official Launchpad source index lists Fastfetch for Resolute 26.04 in Universe. Thus the default selection that includes Fastfetch fails closed on Ubuntu 22.04/24.04 when the package step is approved. Choose `--modules core` to omit Fastfetch. Skipping the package step bypasses these checks and does not provide the missing program. Ubuntu 26.04 package setup is not enabled: its complete package set was not verified. New Ubuntu support still needs clean-VM installation and desktop-session testing.

Sources (official Ubuntu/Launchpad):
- https://packages.ubuntu.com/jammy/i3-wm
- https://packages.ubuntu.com/noble/i3-wm
- https://packages.ubuntu.com/resolute/i3-wm
- https://launchpad.net/ubuntu/+source/fastfetch/+index

Debian 13 remains the previously supported target. Kali and Parrot are exact-ID candidates only; their package candidates and desktop compatibility have not been independently established in this work, so treat them as provisional pending candidate preflight and clean-VM testing. No repository is added automatically.
