#!/bin/sh
# Round-4 repros: offline only. Runner interpreter, -I -S -B. Writes only adapter-review-r4/.
set -u
cd "$(dirname "$0")"
PY=${R17_TEST_PYTHON:-/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12}
status=0
for f in repro_r4_shim_grammar.py repro_r4_deadline_kill.py repro_r4_a4_bounds.py repro_r4_stage.py repro_r4_proposals.py repro_r4_readme_values.py; do
  echo "### $f"
  "$PY" -I -S -B "$f" 2>&1
  rc=$?
  echo "exit=$rc"
  [ "$rc" -eq 0 ] || status=1
done
rm -rf _tmp
echo "### overall exit=$status"
exit $status
