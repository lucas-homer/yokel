#!/bin/sh
# Only key paths/proposal metadata are arguments; no private material in argv/env.
set -eu
release_dir=$(CDPATH= cd "$(dirname "$0")" && pwd)
release_python=/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12
exec /usr/bin/env -i HOME="$HOME" PATH=/usr/bin:/bin LANG=en_US.UTF-8 "$release_python" -I -S -B -c 'import sys,runpy; sys.path.insert(0,"/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/site-packages"); script=sys.argv.pop(1); runpy.run_path(script,run_name="__main__")' "$release_dir/release.py" "$@"
