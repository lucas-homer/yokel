import copy
import unittest
import pipeline as p
from development_fixtures import evidence as ev,empty_inventory,event,timing,route,requirement,source_from_round5,ky_fixture


class Controls(unittest.TestCase):
    def build(self,text):
        src=p.make_source(text,'dev');return src,empty_inventory(src)
    def valid(self,src,inv):
        out=p.assemble(src,inv);self.assertTrue(out['validation']['valid'],out['validation']['errors'])
        self.assertFalse(out['action_ready']);self.assertFalse(out['production_eligible']);return out
    def test_exact_unicode_spans(self):
        self.assertEqual(p.resolve_evidence('é🙂a\nB',ev('a\nB')[0]),dict(start=2,end=5,quote='a\nB'))
    def test_repeated_evidence_resolution(self):
        for sel in [ev('email')[0],ev('email',3)[0],ev('email',1,'b email c')[0],ev('email',context='email')[0]]:
            with self.subTest(sel=sel),self.assertRaises(ValueError):p.resolve_evidence('a email b email c',sel)
        self.assertEqual(p.resolve_evidence('a email b email c',ev('email',2)[0])['start'],10)
        self.assertEqual(p.resolve_evidence('a email b email c',ev('email',context='b email c')[0])['start'],10)
    def test_no_fuzzy_repair(self):
        with self.assertRaises(ValueError):p.resolve_evidence('no\nlater than',ev('no later than')[0])
    def test_source_integrity_boundaries(self):
        src,inv=self.build('notice')
        for key,val in [('scope','unknown'),('channel','ocr'),('source_text_sha256','0'*64),('source_text','x'*30001),('pdf_pages',True)]:
            altered=copy.deepcopy(src);altered[key]=val
            with self.subTest(key=key):self.assertFalse(p.assemble(altered,inv)['validation']['valid'])
        with self.assertRaises(ValueError):p.make_source('a\ufffd','d')
        with self.assertRaises(ValueError):p.make_source('a\fb','d',pdf_pages=1,page_map_known=True)
    def test_schema_and_reference_integrity(self):
        src,inv=self.build('Comments due January 1, 2026.');inv['events']=[event('e','written_comment',src['source_text'])]
        for mutate in [lambda x:x['events'][0].update(extra=True),lambda x:x['coverage']['evidence'][0].update(occurrence=True),lambda x:x.pop('requirements')]:
            bad=copy.deepcopy(inv);mutate(bad);self.assertFalse(p.assemble(src,bad)['validation']['valid'])
        inv['routes']=[route('e','Comments',src['source_text'],['missing'])]
        errors=p.assemble(src,inv)['validation']['errors'];self.assertTrue(any('duplicate id' in x for x in errors));self.assertTrue(any('dangling' in x for x in errors))
    def test_no_date_inference_or_clock_conversion(self):
        for raw,value in [('March 31','2026-03-31'),('February 30, 2026','2026-02-30'),('04/05/2026','2026-04-05')]:
            src,inv=self.build(raw);inv['events']=[event('e','written_comment',raw,[timing('t',raw,value)])]
            self.assertFalse(p.assemble(src,inv)['validation']['valid'])
        src,inv=self.build('10:30 AM');inv['events']=[event('e','hearing',src['source_text'],[timing('t','10:30 AM',None,'clock')])];self.valid(src,inv)
        inv['events'][0]['timing'][0]['value']='2026-01-01T18:30Z';self.assertFalse(p.assemble(src,inv)['validation']['valid'])
    def test_conditional_record_not_scalar_hard_block(self):
        src,inv=self.build('Comments close thirty days after posting, unless extended.')
        inv['coverage']['status']='claimed_complete';inv['events']=[event('e','written_comment',src['source_text'],[timing('t',src['source_text'],None,'conditional',relation='after',anchors=['posting'],conditions=['extension'])])]
        inv['events'].append(event('posting','publication','posting'));inv['requirements']=[requirement('extension','extension','unless extended.',events=['e'])]
        out=self.valid(src,inv);self.assertEqual(out['validation']['review_reasons'],[]);self.assertEqual(out['validation']['source_completeness'],'unverified')
    def test_absence_is_not_proven_by_valid_empty_inventory(self):
        src,inv=self.build('Comments must include docket ABC and PDF format.');inv['coverage']['status']='claimed_complete'
        out=self.valid(src,inv);self.assertEqual(out['validation']['source_completeness'],'unverified')
        self.assertIn('Identify omissions',p.verification_request(src,out)['system'])
    def test_source_first_request_and_common_pairing(self):
        src,inv=self.build('notice');import json
        self.assertEqual(set(json.loads(p.inventory_request(src)['user'])),{'source','response_schema'})
        out=self.valid(src,inv);self.assertEqual(p.verification_payload(src,out)['payload_sha256'],p.verification_request(src,out)['payload_sha256'])
        altered=copy.deepcopy(out);altered['record']['coverage']['status']='claimed_complete'
        with self.assertRaises(ValueError):p.verification_payload(src,altered)
        self.assertEqual(len(p.jev_question_specs()),5)
    def test_ky_large_fixture_phase_routes_and_requirements(self):
        src,inv=ky_fixture();out=self.valid(src,inv)
        self.assertEqual(src['pdf_pages'],8);self.assertGreater(len(src['source_text']),19000)
        self.assertEqual(len(out['record']['routes']),3);self.assertEqual(out['record']['routes'][0]['alternative_group'],out['record']['routes'][1]['alternative_group'])
        self.assertEqual(out['record']['events'][0]['timing'][0]['value'],'2025-03-31')
        self.assertEqual(out['record']['events'][2]['timing'][0]['kind'],'relative')
        self.assertEqual(len(out['record']['requirements']),5)
    def test_nm_phase_wrap_publication_identity(self):
        src,inv=source_from_round5('doc-1c5c46ddcd64')
        quote='Written initial comments may be filed no later than August 21, 2025, written response comments may be filed no\nlater than September 8, 2025.'
        inv['events']=[event('initial','initial',quote,[timing('initial-close','August 21, 2025','2025-08-21')]),event('response','response',quote,[timing('response-close','September 8, 2025','2025-09-08')])]
        inv['requirements']=[requirement('posting','publication','within three days of their receipt by the Commission’s Records Management\nBureau.',['initial','response'])]
        inv['identities']=[dict(id='heading',kind='docket',literal='23-00119-UT',relation='unresolved',event_ids=['initial','response'],evidence=ev('DOCKET NO. 23-00119-UT')),dict(id='footer',kind='docket',literal='23-00188-UT',relation='unresolved',event_ids=['initial','response'],evidence=ev('Docket No. 23-00188-UT'))]
        out=self.valid(src,inv);self.assertIn('source_identity_unresolved',out['validation']['review_reasons']);p.verification_payload(src,out)
    def test_mi_remote_reference(self):
        src,inv=source_from_round5('doc-1276066c75b8')
        inv['events']=[event('comment','written_comment','Comments on the proposal may be submitted by October 1, 2022',[timing('close','October 1, 2022','2022-10-01')])]
        inv['routes']=[route('email','ADMcomment@courts.mi.gov','via email at ADMcomment@courts.mi.gov.',['comment'])]
        quote='When\nfiling a comment, please refer to ADM File No. 2021-29.'
        inv['requirements']=[requirement('ref','reference',quote,['comment'],['email'])];out=self.valid(src,inv)
        self.assertEqual(out['record']['requirements'][0]['text'],quote)
    def test_oh_heading_and_registration(self):
        src,inv=source_from_round5('doc-ad2425138393');inv['events']=[event('comment','written_comment','proposed rulemaking will be held')];self.valid(src,inv)
        src,inv=source_from_round5('doc-7d9d82dcb9a8');inv['events']=[event('hearing','hearing','October 5, 2026, 10:30 AM.')]
        inv['routes']=[route('registration','mary.mccarron@epa.ohio.gov','by emailing mary.mccarron@epa.ohio.gov.',['hearing'],role='hearing_registration')]
        out=self.valid(src,inv);self.assertEqual(out['record']['routes'][0]['role'],'hearing_registration')
    def test_document_level_requirement_and_wrong_literal(self):
        src,inv=self.build('All comments will be made public.');inv['requirements']=[requirement('pub','publication',src['source_text'])];self.valid(src,inv)
        inv['routes']=[route('bad','x@y.gov',src['source_text'],[])];self.assertFalse(p.assemble(src,inv)['validation']['valid'])
    def test_verdict_id_coverage_omission_and_exact_evidence(self):
        src,inv=self.build('Comments due January 1, 2026.');inv['events']=[event('comment','written_comment',src['source_text'])];out=self.valid(src,inv)
        verdict=dict(schema_version='round6.record_verdict.v1',document_id=src['document_id'],payload_sha256=p.verification_payload(src,out)['payload_sha256'],completeness=dict(label='complete',reason='fixture',evidence=ev(src['source_text'])),source_identity=dict(label='uncertain',reason='fixture',evidence=ev(src['source_text'])),assessments=[dict(item_id='comment',support='supported',association='matched',requirements='not_applicable',reason='fixture',evidence=ev(src['source_text']))],missing_items=[],contradictions=[])
        self.assertTrue(p.validate_verdict(src,out,verdict)['valid'])
        bad=copy.deepcopy(verdict);bad['assessments']=[];self.assertFalse(p.validate_verdict(src,out,bad)['valid'])
        bad=copy.deepcopy(verdict);bad['missing_items']=[dict(kind='timing',description='missed date',evidence=ev('January 1, 2026'))]
        self.assertFalse(p.validate_verdict(src,out,bad)['valid']);bad['completeness']['label']='incomplete';self.assertTrue(p.validate_verdict(src,out,bad)['valid'])
        bad['missing_items'][0]['evidence']=ev('January 2, 2026');self.assertFalse(p.validate_verdict(src,out,bad)['valid'])

    def test_open_close_and_explicit_dependency(self):
        src,inv=self.build('Posting is January 1, 2026. Comments close thirty days after posting.')
        inv['events']=[event('posting','publication','Posting is January 1, 2026.',[timing('open','January 1, 2026','2026-01-01',role='opens')]),event('comment','written_comment','Comments close thirty days after posting.',[timing('close','thirty days after posting',None,'relative',role='closes',relation='after',anchors=['posting'])])]
        out=self.valid(src,inv);self.assertEqual(out['record']['events'][0]['timing'][0]['role'],'opens')
        self.assertEqual(out['record']['events'][1]['timing'][0]['anchor_event_ids'],['posting'])
        bad=copy.deepcopy(inv);bad['events'][1]['timing'][0]['anchor_event_ids']=['missing'];self.assertFalse(p.assemble(src,bad)['validation']['valid'])
        bad=copy.deepcopy(inv);bad['events'][1]['timing'][0]['dependency_relation']='none';self.assertFalse(p.assemble(src,bad)['validation']['valid'])
        bad=copy.deepcopy(inv);bad['events'][1]['timing'][0]['anchor_event_ids']=[];self.assertFalse(p.assemble(src,bad)['validation']['valid'])
    def test_modality_and_disclosure_are_preserved(self):
        src,inv=self.build('Comments will be public. PDF is required. A hearing may be requested.')
        inv['requirements']=[requirement('disclose','publication','Comments will be public.'),requirement('format','format','PDF is required.'),requirement('option','hearing_procedure','A hearing may be requested.')]
        inv['requirements'][2]['modality']='optional';out=self.valid(src,inv)
        self.assertEqual(out['record']['requirements'][0]['semantic_class'],'disclosure')
        self.assertEqual(out['record']['requirements'][1]['modality'],'mandatory')
        self.assertEqual(out['record']['requirements'][2]['modality'],'optional')
        inv['requirements'][1]['modality']='unclear';self.assertIn('requirement_modality_unresolved',self.valid(src,inv)['validation']['review_reasons'])
    def test_aggregate_bound_no_silent_drop(self):
        src,inv=self.build('notice');inv['events']=[event('e'+str(i),'other','notice') for i in range(200)]
        inv['requirements']=[requirement('extra','other','notice')]
        out=p.assemble(src,inv);self.assertFalse(out['validation']['valid']);self.assertIsNone(out['record'])
        self.assertTrue(any('aggregate item limit' in x for x in out['validation']['errors']))

    def test_unknown_event_phase_requires_review(self):
        src,inv=self.build('Participation information is unclear.')
        inv['coverage']['status']='claimed_complete'
        inv['events']=[event('unclear','unknown',src['source_text'])]
        out=self.valid(src,inv);self.assertIn('event_phase_unresolved',out['validation']['review_reasons'])
        inv['events'][0]['phase']='other'
        self.assertNotIn('event_phase_unresolved',self.valid(src,inv)['validation']['review_reasons'])
    def test_unknown_route_role_and_channel_require_review(self):
        src,inv=self.build('Contact a@b.gov for participation information.')
        inv['coverage']['status']='claimed_complete'
        inv['events']=[event('comment','written_comment',src['source_text'])]
        inv['routes']=[route('unclear','a@b.gov',src['source_text'],['comment'],role='unknown')]
        out=self.valid(src,inv);self.assertIn('route_role_unresolved',out['validation']['review_reasons'])
        inv['routes'][0]['role']='information_contact';inv['routes'][0]['channel']='unknown'
        out=self.valid(src,inv);self.assertIn('route_channel_unresolved',out['validation']['review_reasons'])
        self.assertNotIn('route_role_unresolved',out['validation']['review_reasons'])
        inv['routes'][0]['channel']='email'
        out=self.valid(src,inv);self.assertNotIn('route_channel_unresolved',out['validation']['review_reasons'])

    def test_fixed_completeness_universe_in_prompts(self):
        for prompt in [p.INVENTORY_SYSTEM,p.VERIFIER_SYSTEM]:
            for term in ['modality','disclosure','confidentiality','accessibility','copies','query','ancillary']:
                with self.subTest(term=term):self.assertIn(term,prompt)
        probes=p.jev_question_specs();self.assertEqual(len(probes),5)
        joined=' '.join(q['question'] for q in probes)
        for term in ['modality','disclosure','confidentiality','accessibility','copies','query','ancillary']:
            with self.subTest(term=term):self.assertIn(term,joined)
        self.assertIn('mandatory/optional/conditional',probes[2]['question'])
        self.assertIn('separately',probes[2]['question'])

if __name__=='__main__':unittest.main()
