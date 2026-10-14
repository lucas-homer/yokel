"""Shared loader for the review repros. Offline only: loads the adapter module and the
test harness (fakes) from the sibling adapter/ directory by absolute path, so the scripts
run under `python3 -I -S -B`. Never performs a network call."""
import importlib.util
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADAPTER = HERE.parent.parent / 'adapter-r1-1'


def load():
    def mod(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m
    tests = mod('r17_tests_for_review', ADAPTER / 'test_adapter.py')
    # The test module imports its own adapter instance as `a`; reuse exactly that one so
    # Harness, packet and FakeClock talk to the same module object we patch.
    return tests.a, tests


def tempdir():
    return tempfile.TemporaryDirectory(prefix='.review-', dir=HERE)


def banner(title):
    print('=' * 78)
    print(title)
    print('=' * 78)
