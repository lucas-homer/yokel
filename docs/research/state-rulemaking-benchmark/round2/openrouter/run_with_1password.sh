#!/bin/sh
set -eu
TASK_PYTHON=${PYTHON_BIN:-/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3}
TASK_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OPENROUTER_API_KEY='op://Private/2ckbxjceztfy4wsix7fkbh4gfa/credential'
export OPENROUTER_API_KEY
exec /opt/homebrew/bin/op run -- "$TASK_PYTHON" "$TASK_DIR/run_ocr.py" "$@"
