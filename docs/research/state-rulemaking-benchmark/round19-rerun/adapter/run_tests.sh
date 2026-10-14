#!/bin/sh
# Offline unittest only; synthetic transports and environments.
set -eu
cd "$(dirname "$0")"
"${R19_TEST_PYTHON:-python3}" -I -S -B -m unittest discover -s . -p 'test_*.py' -v
