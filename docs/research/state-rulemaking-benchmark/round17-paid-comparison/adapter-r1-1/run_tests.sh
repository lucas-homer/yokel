#!/bin/sh
# Offline tests only; no native runner, job, provider or real credential lookup.
set -eu
cd "$(dirname "$0")"
python3 -I -S -B test_adapter.py
python3 -I -S -B test_revision.py
python3 -I -S -B test_host_driver.py
python3 -I -S -B test_repros.py
