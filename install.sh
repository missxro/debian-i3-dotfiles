#!/bin/sh
# Keep privilege escalation limited to explicitly approved apt commands.
set -eu
command -v python3 >/dev/null 2>&1 || {
    printf '%s\n' 'Python 3.11+ is required. Install python3 using your package manager.' >&2
    exit 1
}
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$SCRIPT_DIR/install.py" "$@"
