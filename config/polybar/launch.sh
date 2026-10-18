#!/usr/bin/env python3
"""Launch the main Polybar once for each active X11 monitor.

Keep launcher_common.py beside wallpaper-wrap in the repository bin directory,
(or install all bin files in ~/.local/bin when copying this config).
"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO_BIN = HERE.parent.parent / 'bin'
sys.path.insert(0, str(REPO_BIN if (REPO_BIN / 'launcher_common.py').is_file()
                       else Path.home() / '.local/bin'))
from launcher_common import main

if __name__ == '__main__':
    raise SystemExit(main('polybar', config=HERE / 'config.ini'))
