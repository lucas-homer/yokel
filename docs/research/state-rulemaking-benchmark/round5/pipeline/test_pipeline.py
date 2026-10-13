import unittest
import json
from pipeline import propose,normalize_date,SOFT_ISSUES,HARD_ISSUES
ID='doc-0123456789ab'
def dates(r):return [i for i in r['candidates'] if i['field']=='comment_deadline']
def emails(r):return [i for i in r['candidates'] if i['field']=='submission_email']
class ProposerTests(unittest.TestCase):
    def test_before_demonstrative_and_subject_lifecycle_positive(self):
        text='The regulation was superseded by statute. The following proposed rule is available.\n\nWritten comments must be received on or before October 31, 2026. Submit written comments to the following email address: A+b@Example.gov.'
        r=propose(text,ID)
        self.assertEqual(dates(r)[0]['normalized_value'],'2026-10-31')
        self.assertTrue(all(i['verifier_eligible'] for i in r['candidates']))
        self.assertFalse(any('following email address' in c for i in r['candidates'] for c in i['case']['candidate']['conditions']))
        self.assertEqual(r['lifecycle_cues'][0]['association'],'subject_or_unbound')

    def test_conditional_date_not_salvaged_by_quote(self):
        r=propose('Written comments close October 31, 2026 if a hearing is requested. Submit written comments to a@example.gov.',ID)
        d=dates(r)[0];self.assertIn('conditional_deadline_unresolved',d['hard_issues']);self.assertFalse(d['verifier_eligible'])
        self.assertIn('actual unconditional absolute',d['case']['candidate']['claim'])
        self.assertTrue(any('if a hearing' in c for c in d['case']['candidate']['conditions']))

    def test_form_header_date_and_email_association(self):
        text='8. Deadline for submission of materials in writing or, if practicable, electronically:\n\nThursday, November 12, 2026\n\nX Email A+b@Example.gov'
        r=propose(text,ID);d=dates(r)[0];e=emails(r)[0]
        self.assertTrue(d['form_association']);self.assertTrue(d['verifier_eligible']);self.assertTrue(e['form_association'])
        self.assertTrue(any('if practicable' in c for c in e['case']['candidate']['conditions']))
        self.assertEqual(e['normalized_value'],'A+b@Example.gov')

    def test_no_form_year_or_cross_page_borrow(self):
        for text in ['Deadline for submission of materials in writing:\n\nOctober 31','Deadline for submission of materials in writing:\fOctober 31, 2026']:
            r=propose(text,ID)
            self.assertFalse(any(i['verifier_eligible'] for i in dates(r)))
        self.assertEqual(dates(propose('Publication: 2026. Written comments close October 31.',ID))[0]['normalized_value'],None)

    def test_clock_preserved_no_utc(self):
        r=propose('Written comments close October 31, 2026 at 5 p.m. ET.',ID);d=dates(r)[0]
        self.assertTrue(d['verifier_eligible']);self.assertIsNone(d['timezone'])
        self.assertTrue(any('5 p.m. ET' in c for c in d['case']['candidate']['conditions']))

    def test_relative_date_review_email_can_verify(self):
        text='Written comments must be submitted within 20 calendar days after publication by email to a@example.gov.'
        r=propose(text,ID);self.assertFalse(dates(r));self.assertTrue(emails(r)[0]['verifier_eligible'])
        self.assertTrue(any('within 20 calendar days after publication' in c for c in emails(r)[0]['case']['candidate']['conditions']))
        text='Written comments close October 31, 2026, within 20 calendar days after publication.'
        self.assertIn('relative_participation_window_unresolved',dates(propose(text,ID))[0]['hard_issues'])

    def test_actual_window_lifecycle_remains_hard(self):
        for context in ['The comment period has been extended.','This notice has been withdrawn.','The proposed rule has been withdrawn.']:
            r=propose(context+' Written comments close October 31, 2026.',ID)
            self.assertIn('participation_lifecycle_unresolved',dates(r)[0]['hard_issues'])

    def test_multiple_actual_windows_review_and_hearing_competitor_semantic(self):
        r=propose('Written comments close October 31, 2026. Written comments close November 2, 2026.',ID)
        self.assertTrue(all('multiple_same_role_values_scope_unresolved' in i['hard_issues'] for i in dates(r)))
        r=propose('Written comments and hearing deadline October 30, 2026. Written comments close October 31, 2026.',ID)
        self.assertTrue(all('multiple_date_candidates_require_role_resolution' in i['soft_issues'] for i in dates(r)))

    def test_invalid_dates_numeric_order_and_missing_year(self):
        for value in ['February 30, 2026','July 2223, 2026','10/11/2026','October 31']:
            d=dates(propose('Written comments close '+value+'.',ID))[0];self.assertIsNone(d['normalized_value']);self.assertFalse(d['verifier_eligible'])

    def test_scope_corruption_limits_and_native_only(self):
        for kwargs in [{'scope':'unknown'},{'scope':'slice'},{'pdf_pages':2,'page_map_known':True}]:
            self.assertFalse(dates(propose('Written comments close October 31, 2026.',ID,**kwargs))[0]['verifier_eligible'])
        self.assertFalse(dates(propose('Written comments close October 31, 2026.\ufffd',ID))[0]['verifier_eligible'])
        self.assertFalse(dates(propose('Written comments close October 31, 2026.\n\n'+'x'*30000,ID))[0]['emit_case'])
        with self.assertRaises(ValueError):propose('x',ID,channel='fallback')
        self.assertIn('source_review_empty_text',propose('',ID)['routes'])

    def test_full_source_unrelated_condition_not_assigned_and_spans(self):
        text='😀 If you need accessibility assistance for the hearing, call staff.\n\nWritten comments close October 31, 2026. Submit written comments to a@example.gov.'
        r=propose(text,ID)
        for i in r['candidates']:
            self.assertEqual(i['case']['source_text'],text)
            self.assertFalse(any('accessibility' in c for c in i['case']['candidate']['conditions']))
            for s in i['case']['evidence']:self.assertEqual(text[s['start']:s['end']],s['quote'])
        self.assertTrue(r['qualification_cues'])
        self.assertFalse(SOFT_ISSUES & HARD_ISSUES)

    def test_many_unrelated_conditions_not_duplicated_into_claim(self):
        text='\n\n'.join('If you need hearing accommodations, call staff '+str(n)+'.' for n in range(25))+'\n\nWritten comments close October 31, 2026.'
        d=dates(propose(text,ID))[0];self.assertTrue(d['emit_case']);self.assertEqual(d['case']['candidate']['conditions'],[])
        self.assertEqual(d['case']['source_text'],text)

if __name__=='__main__':unittest.main()
