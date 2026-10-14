"""Pure synthetic v3 field checks; never invokes the metadata transport."""
import decimal
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('v3_keycheck',HERE/'keycheck.py')
k=importlib.util.module_from_spec(s)
s.loader.exec_module(k)
KEY='SYNTHETIC-ONLY-NO-ACTUAL-CREDENTIAL'

class BaselineTests(unittest.TestCase):
    def parse(self, usage='0.059408500', remaining='49.940591500', label='DocketClock'):
        raw=('{"data":{"label":'+json.dumps(label)+',"limit":50,"limit_reset":null,"usage":'+usage+
             (',"limit_remaining":'+remaining if remaining is not None else '')+'}}').encode()
        return k.parse_fields(raw,KEY)

    def test_positive_usage_pass_and_candidate(self):
        fields,checks,meta=self.parse()
        self.assertTrue(all(v is True for v in checks.values()))
        self.assertEqual(meta['key_initial_usage_candidate_nanousd'],59_408_500)
        self.assertEqual(meta['key_initial_usage_candidate_usd'],decimal.Decimal('0.059408500'))
        self.assertEqual(fields['limit_remaining'],decimal.Decimal('49.940591500'))

    def test_masked_positive_usage_candidate_without_persisting_fragments(self):
        fields,checks,meta=self.parse(label='sk-or-v1-abc...def')
        self.assertEqual(checks['label'],'not_machine_verifiable')
        self.assertTrue(all(v is True for n,v in checks.items() if n!='label'))
        self.assertNotIn('label',fields)
        self.assertTrue(meta['user_attestation_required'])
        self.assertEqual(meta['key_initial_usage_candidate_nanousd'],59_408_500)

    def test_positive_usage_computed_remaining_exactly(self):
        fields,checks,meta=self.parse(remaining=None)
        self.assertEqual(fields['limit_remaining'],decimal.Decimal('49.940591500'))
        self.assertTrue(checks['limit_remaining'])
        self.assertTrue(meta['limit_remaining_computed'])

    def test_zero_usage_still_passes(self):
        _,checks,meta=self.parse('0','50')
        self.assertTrue(all(checks.values()))
        self.assertEqual(meta['key_initial_usage_candidate_nanousd'],0)

    def test_inconsistent_remaining_fails_even_when_usage_nonzero_valid(self):
        _,checks,meta=self.parse(remaining='50')
        self.assertTrue(checks['usage'])
        self.assertFalse(checks['limit_remaining'])

    def test_invalid_and_nonfinite_usage_rejected(self):
        for usage in ('-1','true','"1"','NaN','Infinity'):
            with self.subTest(usage=usage),self.assertRaises(k.Rejected):
                self.parse(usage)
        _,checks,meta=self.parse('null')
        self.assertFalse(checks['usage'])
        self.assertIsNone(meta['key_initial_usage_candidate_nanousd'])

    def test_subnano_usage_records_exact_usd_and_ceil_candidate(self):
        fields,checks,meta=self.parse('0.000000000000000000000000000001',None)
        self.assertTrue(checks['usage'])
        self.assertTrue(checks['limit_remaining'])
        self.assertEqual(meta['key_initial_usage_candidate_nanousd'],1)
        self.assertEqual(fields['limit_remaining'],decimal.Decimal('49.999999999999999999999999999999'))

if __name__=='__main__':
    unittest.main(verbosity=2)
