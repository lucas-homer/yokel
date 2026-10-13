import copy
import json
import pathlib
import tempfile
import unittest
from pipeline import propose, normalize_date, validate_manifest, run, sha

ID = 'doc-0123456789ab'

def date_item(result):
    return next(c for c in result['candidates'] if c['field']=='comment_deadline')

def email_item(result):
    return next(c for c in result['candidates'] if c['field']=='submission_email')

class PipelineTests(unittest.TestCase):
    def test_clean_field_can_pass_with_other_missing_field(self):
        r=propose('Written comments must be received by October 31, 2026.',ID)
        c=date_item(r)
        self.assertEqual(c['normalized_value'],'2026-10-31')
        self.assertEqual(c['field_disposition'],'shadow_eligible_text_only')
        self.assertIn('parser_fallback_missing_submission_email_candidate',r['routes'])
        self.assertFalse(r['production_eligible'])
        self.assertIsNone(c['timezone'])

    def test_no_year_order_or_invalid_date_guess(self):
        for literal in ('October 31','01/02/2026','February 30, 2026','July 2223, 2026','July 22–23, 2026'):
            c=date_item(propose('Written comments close by '+literal+'.',ID))
            self.assertIsNone(c['normalized_value'])
            self.assertEqual(c['field_disposition'],'review')

    def test_submission_email_literal_exact(self):
        c=email_item(propose('Written comments may be submitted by email to A+b@Example.gov.',ID))
        self.assertEqual(c['normalized_value'],'A+b@Example.gov')
        self.assertEqual(c['field_disposition'],'shadow_eligible_text_only')

    def test_contact_is_not_submission_role(self):
        c=email_item(propose('Questions: contact person@example.gov.',ID))
        self.assertIn('submission_role_unverified',c['issues'])
        self.assertEqual(c['case']['candidate']['role'],'written_comment_submission_email')

    def test_trailing_conditions_retained(self):
        text='Written comments close October 31, 2026 if a hearing is requested.'
        c=date_item(propose(text,ID))
        self.assertEqual(c['case']['candidate']['conditions'],[text])
        self.assertIn(text,c['case']['candidate']['claim'])
        self.assertEqual(c['field_disposition'],'review')

    def test_remote_participation_condition_and_clock_retained(self):
        condition='If a hearing is requested, written comments may be submitted only electronically.'
        text='Written comments close October 31, 2026 at 5 p.m. ET.\n\n'+('x'*1200)+'\n\n'+condition
        c=date_item(propose(text,ID))
        self.assertIn(condition,c['case']['candidate']['conditions'])
        self.assertTrue(any('5 p.m. ET' in q for q in c['case']['candidate']['conditions']))
        self.assertEqual(c['field_disposition'],'review')
        self.assertIsNone(c['timezone'])

    def test_full_notice_not_decisive_excerpt(self):
        text='Unrelated preface 😀.\n\nWritten comments close October 31 2026.\n\nMore material.'
        r=propose(text,ID)
        c=date_item(r)
        self.assertEqual(c['case']['source_text'],text)
        self.assertFalse(r['full_source_context_map']['truncated'])
        for sp in c['case']['evidence']:
            self.assertEqual(text[sp['start']:sp['end']],sp['quote'])

    def test_multiple_values_lifecycle_and_rules_escalate(self):
        examples=[('Written comments close October 31, 2026.\n\nWritten comments close November 3, 2026.','multiple_same_role_values_scope_unresolved'),('This is an extension. Written comments close October 31, 2026.','lifecycle_scope_unresolved'),('Rule R1 and Rule R2. Written comments close October 31, 2026.','multiple_notice_or_rule_scopes')]
        for text,issue in examples:
            self.assertIn(issue,date_item(propose(text,ID))['issues'])

    def test_hearing_date_not_borrowed_and_ambiguous_role_reviewed(self):
        text='Public hearing October 2, 2026. Written comments close October 31, 2026.'
        dates=[c for c in propose(text,ID)['candidates'] if c['field']=='comment_deadline']
        self.assertEqual(len(dates),1)
        c=date_item(propose('Written comment and hearing deadline October 31, 2026.',ID))
        self.assertIn('competing_temporal_role_cues',c['issues'])

    def test_scope_unknown_or_slice(self):
        for scope in ('unknown','slice'):
            self.assertIn('source_scope_incomplete_or_unknown',date_item(propose('Written comments close October 31, 2026.',ID,scope=scope))['issues'])

    def test_empty_and_quality_signals(self):
        self.assertIn('parser_fallback_empty_text',propose('',ID)['routes'])
        r=propose('Written comments close October 31, 2026.\ufffd',ID)
        self.assertIn('replacement_character',date_item(r)['issues'])
        r=propose('Written comments close October 31, 2026.',ID,pdf_pages=2,page_map_known=True)
        self.assertIn('page_count_mismatch',date_item(r)['issues'])
        r=propose('Submit written comments to broken@\nexample.gov.',ID)
        self.assertIn('parser_fallback_wrapped_destination_signal',r['routes'])

    def test_overlimit_no_truncation_or_case_emission(self):
        text='Written comments close October 31, 2026.\n\n'+'x'*30000
        c=date_item(propose(text,ID))
        self.assertFalse(c['emit_case'])
        self.assertEqual(c['case']['source_text'],text)

    def test_existing_verifier_claim_limit_blocks_without_truncation(self):
        text='Written comments close October 31, 2026 if '+('x'*3001)
        c=date_item(propose(text,ID))
        self.assertIn('case_overlimit',c['hard_issues'])
        self.assertFalse(c['emit_case'])
        self.assertEqual(c['case']['source_text'],text)

    def test_multiple_emails_are_soft_role_resolution_not_asserted_conflict(self):
        r=propose('Written comments may be emailed to comments@example.gov. Questions: person@example.gov.',ID)
        for c in r['candidates']:
            self.assertIn('multiple_email_candidates_require_role_resolution',c['soft_issues'])
            self.assertNotIn('multiple_same_role_values_scope_unresolved',c['hard_issues'])

    def test_pdftotext_trailing_formfeed_whitespace_not_extra_page(self):
        r=propose('Written comments close October 31, 2026.\f\n',ID,pdf_pages=1,page_map_known=True)
        self.assertEqual(r['native_page_count'],1)
        self.assertNotIn('page_count_mismatch',date_item(r)['issues'])

    def test_unknown_page_null_and_known_page_mapped(self):
        text='Preface\fWritten comments close October 31, 2026.'
        self.assertIsNone(date_item(propose(text,ID))['pdf_page'])
        self.assertEqual(date_item(propose(text,ID,pdf_pages=2,page_map_known=True))['pdf_page'],2)

    def test_historical_and_relative_are_not_resolved(self):
        c=date_item(propose('Prior written comments closed October 31, 2026.',ID))
        self.assertEqual(c['field_disposition'],'review')
        r=propose('Written comments close 20 calendar days after publication.',ID)
        self.assertFalse(r['candidates'])
        self.assertIn('parser_fallback_unresolved_participation_date_evidence',r['routes'])

    def test_strict_manifest_labels_channel_hashes_path_and_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            raw=b'Written comments close October 31, 2026.'
            (root/'native.txt').write_bytes(raw)
            (root/'input.pdf').write_bytes(b'research synthetic PDF identity only')
            unit={'document_id':ID,'channel':'native','text_path':'native.txt','text_sha256':sha(raw),'pdf_path':'input.pdf','pdf_sha256':sha((root/'input.pdf').read_bytes()),'pdf_pages':1,'scope':'full_notice','native_page_map_known':False}
            manifest={'schema_version':'round4.sources.v1','documents':[unit]}
            path=root/'manifest.json';path.write_text(json.dumps(manifest))
            run(path,root,root/'out1');run(path,root,root/'out2')
            self.assertEqual((root/'out1/cases.jsonl').read_bytes(),(root/'out2/cases.jsonl').read_bytes())
            self.assertEqual((root/'out1/traces.json').read_bytes(),(root/'out2/traces.json').read_bytes())
            bad=copy.deepcopy(manifest);bad['documents'][0]['reference']='gold'
            with self.assertRaises(ValueError): validate_manifest(bad)
            bad=copy.deepcopy(manifest);bad['documents'][0]['channel']='fallback';path.write_text(json.dumps(bad))
            with self.assertRaises(ValueError): run(path,root,root/'mixed')
            bad=copy.deepcopy(manifest);bad['documents'][0]['text_path']='../outside.txt';path.write_text(json.dumps(bad))
            with self.assertRaises(ValueError): run(path,root,root/'outside')
            path.write_text(json.dumps(manifest));(root/'native.txt').write_bytes(b'changed')
            with self.assertRaises(ValueError): run(path,root,root/'changed')

if __name__=='__main__': unittest.main()
