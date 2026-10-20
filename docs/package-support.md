# Debian-family package profile notes

Installer package setup is gated by exact distro IDs and supported versions; `ID_LIKE` alone is never accepted. When the package step is approved, package candidates are checked with `apt-cache policy` before `apt-get update`, installation, or file placement. Missing candidates other than Fastfetch stop that operation and identify the missing packages; repository configuration is never changed. Existing skip semantics remain unchanged: `--yes`, `--files-only`, or declining the package prompt skip both package installation and candidate checks; users taking those paths must supply dependencies themselves. `--dry-run` does not check candidates or install anything.

## Ubuntu evidence and limitation

The official Ubuntu package archives show `i3-wm` for Jammy, Noble, and Resolute. Fastfetch is absent from the Jammy and Noble archive indexes, while the official Launchpad source index lists Fastfetch for Resolute 26.04 in Universe. The default selection keeps Fastfetch included. If its native candidate is absent, the approved package step downloads the official fastfetch-cli/fastfetch 2.70.0 release `.deb` for amd64/arm64 and verifies its pinned SHA256, package name, architecture and version before any apt changes. No PPA or repository is added. Unsupported fallback architectures or verification/download failures stop before configuration placement. Private temporary staging is removed afterward; apt may print its standard unsandboxed-local-file warning because `_apt` cannot traverse that staging directory. Sandbox settings are not changed. Restore does not uninstall packages. Skipping the package step bypasses these checks and does not provide the missing program. Ubuntu 26.04 package setup is not enabled: its complete package set was not verified. New Ubuntu support still needs clean-VM installation and desktop-session testing.

Sources (official Ubuntu/Launchpad):
- https://packages.ubuntu.com/jammy/i3-wm
- https://packages.ubuntu.com/noble/i3-wm
- https://packages.ubuntu.com/resolute/i3-wm
- https://launchpad.net/ubuntu/+source/fastfetch/+index

Debian 13 remains the previously supported target. Kali and Parrot are exact-ID candidates only; their package candidates and desktop compatibility have not been independently established in this work, so treat them as provisional pending candidate preflight and clean-VM testing. No repository is added automatically.
