"""Offline INIT baseline and frozen evidence selection checks."""
import importlib.util
import json
from pathlib import Path
import types
import unittest

HERE=Path(__file__).resolve().parent
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m
r=load('r18_records',HERE/'release_records.py')
m=load('r18_manifest',HERE/'prepare_manifest.py')
a=load('r18_adapter_prep',HERE.parent/'adapter/r17_adapter.py')

class BaselinePrepTests(unittest.TestCase):
    def test_init_requires_recorded_integer_baseline(self):
        value=r.init_record(a,b'synthetic budget',59_408_500)
        self.assertEqual(value['key_initial_usage'],59_408_500)
        self.assertEqual(value['namespace'],'r18.paid-rerun.v1')
        for u in (-1,True,1.5,'1',None):
            with self.subTest(u=u),self.assertRaises(a.Refused):
                r.init_record(a,b'synthetic budget',u)
        with self.assertRaises(TypeError):
            r.init_record(a,b'synthetic budget')

    def test_manifest_selects_paccept_and_frozen_gates_but_no_paid_output_or_machine(self):
        manifest=m.build()['files']
        prefix='round17-paid-comparison/design-r3-1-paccept/'
        for name in ('READY.json','READY.primary.json','PROTOCOL.md','BUDGET.md','fixtures/check.py'):
            self.assertIn(prefix+name,manifest)
        for name in ('primary-acceptance/A1-FIXTURE-GATE.json',
                     'primary-acceptance/A2-FIXTURE-GATE.json',
                     'reference/ACCEPTANCE.json','scoring-manifest/MANIFEST.json'):
            self.assertIn('round17-paid-comparison/'+name,manifest)
        self.assertFalse(any('/run-live/' in n or n.endswith('/KEY-MACHINE.json') or n.endswith('/content.body') for n in manifest))
        self.assertIn('round18-rerun/amendments/A5-A6.md',manifest)
        self.assertIn('round18-rerun/wire/wire.py',manifest)
        self.assertIn('round18-rerun/recon/r17recon.py',manifest)

if __name__=='__main__':
    unittest.main(verbosity=2)
