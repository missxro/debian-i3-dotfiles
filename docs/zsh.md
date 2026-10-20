# Zsh and Powerlevel10k

Selecting the `core` module installs `config/zsh/zshrc` as `~/.zshrc`, the sanitized prompt configuration as `~/.p10k.zsh`, and the pinned Powerlevel10k runtime under `~/.local/share/debian-i3-dotfiles/powerlevel10k/`. Existing targets are handled by the installer's normal backup and restore flow.

The setup does not require Oh My Zsh, change the login shell, or run network commands. Startup is interactive-shell-only. The configuration wizard is disabled; Git status uses Powerlevel10k's built-in `vcs` segment with gitstatus disabled, avoiding gitstatus binary installation/download at shell startup. Zsh is included in the core package list and installed with the normal package approval. With `--files-only` or skipped package installation, dependencies remain user-managed. Nerd Font glyphs require a compatible terminal font; without one, prompt icons may render as replacement characters.

## Vendored runtime

`vendor/powerlevel10k` contains only the upstream theme entry point, the `internal/` files it sources, and the upstream license. Provenance records the exact source revision. Gitstatus is intentionally excluded because it is explicitly disabled and its optional runtime bootstrap can fetch/build binaries.
