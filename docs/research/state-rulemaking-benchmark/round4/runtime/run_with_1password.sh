#!/bin/sh
set -eu
TASK_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TASK_PYTHON=${PYTHON_BIN:-/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3}
TYPESAFE_API_KEY='op://Private/frcq53h65pb4t66mffj2yixo34/credential'
OPENROUTER_API_KEY='op://Private/2ckbxjceztfy4wsix7fkbh4gfa/credential'
export TYPESAFE_API_KEY OPENROUTER_API_KEY
exec /opt/homebrew/bin/op run -- "$TASK_PYTHON" -B "$TASK_DIR/run_pipeline.py" "$@"
