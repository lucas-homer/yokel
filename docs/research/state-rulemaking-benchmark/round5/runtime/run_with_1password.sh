#!/bin/sh
# Primary executes only after source/label freeze and explicit live authorization.
set -eu
RUNTIME_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export TYPESAFE_API_KEY='op://Private/frcq53h65pb4t66mffj2yixo34/credential'
exec op run -- /Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B "$RUNTIME_DIR/run_pipeline.py" "$@"
