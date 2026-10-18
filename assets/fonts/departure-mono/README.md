# DepartureMono Nerd Font

Unmodified Regular and Mono OTFs from Nerd Fonts v3.5.1, bundled so a fresh setup does not need a separate font download.

Upstream archive: https://github.com/ryanoasis/nerd-fonts/releases/download/v3.5.1/DepartureMono.zip
Archive SHA-256: `a49e33d74093541c26f48cfb94f3db7bcf9f4d6c975cb0de34dd3a25bb4e4993`

- `DepartureMonoNerdFont-Regular.otf`: `9535041c4467325256a224b3b6dba0a300fce75c99a2b5279f5108b97de19fa4`
- `DepartureMonoNerdFontMono-Regular.otf`: `534cb9e9f8292ceec427f8524a92b94f15d798a9d96139f890d63ba4a5284a1d`

Font copyright: Helena Zhang. License: SIL Open Font License 1.1, included in `LICENSE`. The fonts remain under that license, not the repository's software license.

The installer uses the Regular family for i3 and the Mono family for Kitty and Polybar. Already installed exact families are retained. Missing families are copied to `~/.local/share/fonts/departure-mono/`, with their license, normal backups and restore support. Fontconfig cache is refreshed afterward. `--font` chooses an existing custom family and skips bundled font placement.
