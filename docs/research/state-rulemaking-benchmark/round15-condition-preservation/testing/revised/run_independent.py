"""Run unchanged original 17 methods with an explicit in-memory C override."""
import importlib.util
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
OLD=load('r15_original_independent_tests',ROOT/'testing/execution/test_independent.py')
NEW=load('r15_1_independent_contract',ROOT/'protocol-revised/compact.py')
OLD.C=NEW
assert OLD.C.VERSION=='r15.1'
if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OLD.IndependentTests))
    raise SystemExit(0 if result.wasSuccessful() else 1)
