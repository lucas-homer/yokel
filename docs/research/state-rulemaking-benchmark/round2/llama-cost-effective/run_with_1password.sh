#!/bin/sh
set +x
set -eu
if [ "$#" -lt 2 ]; then
  printf '%s\n' 'Usage: sh run_with_1password.sh op://vault/item/credential ARTIFACT_ROOT [runner flags]' >&2
  exit 2
fi
reference=$1
shift
case "$reference" in op://*) ;; *) printf '%s\n' 'Expected a non-secret op:// field reference, never a key value.' >&2; exit 2 ;; esac
exec env LLAMA_CLOUD_API_KEY="$reference" op run -- "${PYTHON_BIN:-python3}" "$(dirname "$0")/run_cost_effective.py" "$@"
