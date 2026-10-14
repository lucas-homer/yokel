#!/bin/sh
# Offline tests only; no native runner, job, provider or real credential lookup.
set -eu
cd "$(dirname "$0")"
"${R17_TEST_PYTHON:-python3}" -I -S -B test_adapter.py
"${R17_TEST_PYTHON:-python3}" -I -S -B test_revision.py
"${R17_TEST_PYTHON:-python3}" -I -S -B test_host_driver.py
"${R17_TEST_PYTHON:-python3}" -I -S -B test_repros.py
"${R17_TEST_PYTHON:-python3}" -I -S -B test_round2.py
"${R17_TEST_PYTHON:-python3}" -I -S -B test_native.py
