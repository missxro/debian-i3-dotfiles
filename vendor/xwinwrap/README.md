# xwinwrap

Source: https://github.com/mmhobi7/xwinwrap

Pinned commit: `391519d3bb53e981218de41a37d1f0f95aef3d17`.

SHA-256 of unmodified `xwinwrap.c`: `00b7ec706bad901a3d224653575d8d05e878e3b4535844a624f73ceff29e04e8`.

Copyright and permission notice are retained in the source header (Novell, Inc.; author David Reveman; subsequent modifications credited there). This is the mmhobi7 fork, not a claim of original authorship.

The installer checks the source checksum and compiles it directly using `cc -O2 -Wall … -lX11 -lXext -lXrender`; no remote installer or upstream Makefile is executed. Only apt uses sudo. The binary is installed per-user in `~/.local/bin/xwinwrap` with backup/restore support. Existing xwinwrap on PATH is retained. `--yes`, `--files-only` and `--dry-run` never compile it.
