#!/bin/sh
# Round-3 review repros, all offline, under isolated Python. Every round-3 script asserts
# GOOD behaviour and exits 0 when it holds. Then the ported round-2 repros (import path only
# changed) and the round-1 originals run against r1.2; see r2-repros-vs-r1-2.txt.
cd "$(dirname "$0")" || exit 2
for f in repro_r3_*.py; do
  echo; echo "### $f"; python3 -I -S -B "$f"; echo "exit=$?"
done
