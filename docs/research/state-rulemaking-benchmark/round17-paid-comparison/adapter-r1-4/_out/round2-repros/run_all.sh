#!/bin/sh
# Round-2 review repros, all offline, under isolated Python. See each script's docstring
# for its exit convention (most assert GOOD behaviour and exit 0 when it holds;
# repro_hd_timeout_row2.py and repro_hd_trust_store.py exit 0 when the FINDING reproduces).
cd "$(dirname "$0")" || exit 2
for f in repro_*.py; do
  echo; echo "### $f"; python3 -I -S -B "$f"; echo "exit=$?"
done
echo; echo "### original round-1 repros against r1.1 (exit 0 = finding still reproduces)"
sh orig-repros/run_all.sh 2>&1 | grep -E '^###|^exit='
