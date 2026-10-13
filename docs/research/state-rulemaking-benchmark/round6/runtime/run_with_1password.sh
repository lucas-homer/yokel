#!/bin/sh
# Primary executes only after approved model/protocol/source/label freezes.
set -eu
TASK_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TYPESAFE_API_KEY='op://Private/frcq53h65pb4t66mffj2yixo34/credential'
OPENROUTER_API_KEY='op://Private/2ckbxjceztfy4wsix7fkbh4gfa/credential'
export TYPESAFE_API_KEY OPENROUTER_API_KEY
exec /opt/homebrew/bin/op run -- /Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B "$TASK_DIR/run_pipeline.py" "$@"
