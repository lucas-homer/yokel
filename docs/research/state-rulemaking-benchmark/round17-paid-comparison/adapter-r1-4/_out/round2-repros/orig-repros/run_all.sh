#!/bin/sh
# Runs every offline repro under isolated Python. Exit 0 from a repro = the finding reproduces.
cd "$(dirname "$0")" || exit 2
for f in repro_*.py; do
  echo; echo "### $f"; python3 -I -S -B "$f"; echo "exit=$?"
done
