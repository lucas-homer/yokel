#!/bin/sh
set -eu
TASK_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TASK_PYTHON=/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
case "$1" in
 jev) TYPESAFE_API_KEY='op://Private/frcq53h65pb4t66mffj2yixo34/credential'; export TYPESAFE_API_KEY ;;
 openrouter) OPENROUTER_API_KEY='op://Private/2ckbxjceztfy4wsix7fkbh4gfa/credential'; export OPENROUTER_API_KEY ;;
 *) exit 2 ;;
esac
TASK_PROVIDER=$1
exec /opt/homebrew/bin/op run -- "$TASK_PYTHON" "$TASK_DIR/staged/verifier.py" --input "$TASK_DIR/staged/runtime.jsonl" --provider "$TASK_PROVIDER" --output "$TASK_DIR/$TASK_PROVIDER" --live --max-cases 16 --max-estimated-cost 0.25
