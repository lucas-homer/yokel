"""Independent source-first public-interface controls; no owner fixtures imported."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

R7 = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('independent_r7_pipeline', R7/'pipeline/pipeline.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def ev(text):
    return [{'quote': text, 'occurrence': None, 'context': None}]


def fixture(text='Help: call 555-0100 or email help@example.test.\nComments are publicly posted except private identifiers.\nOffice: 4 River Road.'):
    s = p.make_source(text, 'independent-control')
    i = {'schema_version':'round7.source_inventory.v1', 'document_id':s['document_id'], 'source_text_sha256':s['source_text_sha256'], 'coverage':{'status':'claimed_complete','rationale':'Authored control, subject to independent audit','evidence':ev(text)}, 'events':[], 'routes':[], 'requirements':[], 'identities':[], 'uncertainties':[], 'alternative_groups':[]}
    return s, i


def route(ident, literal, events=None):
    return {'id':ident,'channel':'telephone' if literal.startswith('555') else 'email','role':'information_contact','event_ids':events or [],'association':'source_resolved','evidence':ev('Help: call 555-0100 or email help@example.test.'),'alternative_group_id':'help-options','description':'Technical help','components':[{'id':ident+'-endpoint','kind':'endpoint','literal':literal,'evidence':ev(literal)}]}


def grouped():
    s,i=fixture()
    i['routes']=[route('phone','555-0100'),route('email','help@example.test')]
    i['alternative_groups']=[{'id':'help-options','purpose':'hearing_help','route_ids':['phone','email'],'event_ids':[],'requirement_ids':[],'association':'source_resolved','evidence':ev('Help: call 555-0100 or email help@example.test.')}]
    return s,i


def positive_verdict(s,a):
    # Explicit IDs from authored fixture, not production all_items enumeration.
    return {'schema_version':'round7.record_verdict.v1','document_id':s['document_id'],'payload_sha256':p.verification_payload(s,a)['payload_sha256'],'completeness':{'label':'complete','reason':'Synthetic response','evidence':ev(s['source_text'])},'source_identity':{'label':'resolved','reason':'Synthetic response','evidence':ev(s['source_text'])},'assessments':[{'item_id':ident,'support':'supported','association':'matched','requirements':'preserved','reason':'Synthetic response','evidence':ev(s['source_text'])} for ident in ['phone','phone-endpoint','email','email-endpoint','help-options']],'missing_items':[],'contradictions':[]}


class IndependentPipeline(unittest.TestCase):
    def valid(self,s,i):
        a=p.assemble(s,i)
        self.assertTrue(a['validation']['valid'],a['validation']['errors'])
        return a

    def rejected(self,s,i):
        a=p.assemble(s,i)
        self.assertFalse(a['validation']['valid'])
        self.assertIsNone(a['record'])
        with self.assertRaises(ValueError): p.verification_request(s,a)
        return a

    def test_explicit_calendar_oracles_and_negatives(self):
        cases=[('Monday July 13, 2026','2026-07-13',True),('Friday July 10, 2026','2026-07-10',True),('Mon., October 5, 2026','2026-10-05',True),('Fri., October 2, 2026','2026-10-02',True),('2026-10-02','2026-10-02',True),('October 2, 2026','2026-10-02',True),('Tuesday July 13, 2026','2026-07-13',False),('February 29, 2026','2026-02-29',False),('July 13','2026-07-13',False),('07/13/2026','2026-07-13',False),('July 13, 2026 at noon','2026-07-13',False),('July 13, 2026 deadline','2026-07-13',False),('July 13, 2026','2026-07-14',False)]
        for raw,value,valid in cases:
            with self.subTest(raw=raw,value=value):
                s,i=fixture(raw)
                i['events']=[{'id':'comments','phase':'written_comment','description':'Comments close','evidence':ev(raw),'timing':[{'id':'deadline','kind':'absolute_date','role':'closes','dependency_relation':'none','anchor_event_ids':[],'condition_requirement_ids':[],'raw':raw,'value':value,'evidence':ev(raw)}]}]
                if valid:
                    a=self.valid(s,i)
                    self.assertEqual(a['record']['events'][0]['timing'][0]['raw'],raw)
                    self.assertEqual(a['record']['events'][0]['timing'][0]['value'],value)
                else:
                    a=self.rejected(s,i)
                    if raw.startswith('Tuesday'): self.assertIn('weekday/date inconsistent',' '.join(a['validation']['errors']))

    def test_unsupported_components_and_envelope_tampering(self):
        for mode in ['invented','changed_quote','ambiguous','display','duplicate_id','empty']:
            with self.subTest(mode=mode):
                s,i=grouped()
                c=i['routes'][0]['components'][0]
                if mode=='invented': c['literal']='555-9999'
                elif mode=='changed_quote': c['evidence']=ev('555 0100')
                elif mode=='ambiguous':
                    s=p.make_source(s['source_text']+'\n555-0100','independent-control');i['source_text_sha256']=s['source_text_sha256']
                elif mode=='display': i['routes'][0]['display']='invented presentation'
                elif mode=='duplicate_id': c['id']='help-options'
                else: i['routes'][0]['components']=[]
                self.rejected(s,i)
        s,i=grouped();a=self.valid(s,i)
        a['record']['routes'][0]['components'][0]['literal']='555-9999'
        with self.assertRaises(ValueError):p.verification_payload(s,a)

    def test_group_reciprocity_roles_and_scopes(self):
        for mode in ['dangling','nonreciprocal','singleton','duplicate','mixed_role','cross_event','missing_evidence']:
            with self.subTest(mode=mode):
                s,i=grouped();g=i['alternative_groups'][0]
                if mode=='dangling': g['route_ids'][1]='absent'
                elif mode=='nonreciprocal':i['routes'][0]['alternative_group_id']=None
                elif mode=='singleton':g['route_ids']=['phone']
                elif mode=='duplicate':g['route_ids']=['phone','phone']
                elif mode=='mixed_role':i['routes'][0]['role']='submission'
                elif mode=='cross_event':
                    i['events']=[{'id':'hearing','phase':'hearing','description':'Hearing','timing':[],'evidence':ev(s['source_text'])}]
                    i['routes'][0]['event_ids']=['hearing']
                else:g['evidence']=[]
                self.rejected(s,i)

    def test_group_uncertainty_preserved_in_common_payload(self):
        s,i=grouped();i['alternative_groups'][0]['association']='uncertain'
        a=self.valid(s,i);v=positive_verdict(s,a)
        self.assertTrue(p.validate_verdict(s,a,v)['valid'])
        common=p.verification_payload(s,a)
        self.assertIn('association_unresolved',common['payload']['review_reasons'])
        self.assertEqual(common['payload']['source_text'],s['source_text'])
        self.assertNotIn('inventory',common['payload'])
        self.assertEqual(p.verification_request(s,a)['payload_sha256'],common['payload_sha256'])

    def test_components_and_groups_require_verdict_assessments(self):
        s,i=grouped();a=self.valid(s,i);v=positive_verdict(s,a)
        self.assertTrue(p.validate_verdict(s,a,v)['valid'])
        for ident in ['phone-endpoint','help-options']:
            with self.subTest(ident=ident):
                bad=copy.deepcopy(v);bad['assessments']=[x for x in bad['assessments'] if x['item_id']!=ident]
                self.assertFalse(p.validate_verdict(s,a,bad)['valid'])

    def test_semantic_classification_and_omission_are_not_assembly_proof(self):
        s,i=grouped()
        policy='Comments are publicly posted except private identifiers.'
        i['requirements']=[{'id':'posting','kind':'publication','modality':'informational','semantic_class':'disclosure','text':policy,'event_ids':[],'route_ids':[],'association':'source_resolved','evidence':ev(policy)}]
        a=self.valid(s,i)
        self.assertEqual(a['validation']['source_completeness'],'unverified')
        for change in ['class','modality','omit']:
            with self.subTest(change=change):
                bad=copy.deepcopy(i)
                if change=='class':bad['requirements'][0]['semantic_class']='instruction'
                elif change=='modality':bad['requirements'][0]['modality']='mandatory'
                else:bad['requirements']=[]
                b=self.valid(s,bad)
                self.assertEqual(b['validation']['source_correctness'],'unverified')
                # Independent authored oracle: exact policy AND classification/modality required.
                recovered=any(r['text']==policy and r['semantic_class']=='disclosure' and r['modality']=='informational' for r in b['record']['requirements'])
                self.assertFalse(recovered)
        self.assertFalse(any(c['literal']=='4 River Road' for r in a['record']['routes'] for c in r['components']))

    def test_aggregate_component_accounting_at_limit(self):
        s,i=fixture('A')
        i['routes']=[{'id':f'r{x}','channel':'other','role':'information_contact','event_ids':[],'association':'source_resolved','evidence':ev('A'),'alternative_group_id':None,'description':None,'components':[{'id':f'c{x}','kind':'name','literal':'A','evidence':ev('A')}]} for x in range(100)]
        self.valid(s,i)
        i['routes'][0]['components'].append({'id':'extra','kind':'name','literal':'A','evidence':ev('A')})
        a=self.rejected(s,i)
        self.assertIn('aggregate item limit',' '.join(a['validation']['errors']))

    def test_r6_discriminator_and_prior_round_lineage(self):
        s,i=fixture();i['schema_version']='round6.source_inventory.v1';self.rejected(s,i)
        baseline=json.loads((R7/'verification/prior-round-hashes.json').read_text())['files']
        root=R7.parent
        current={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for n in range(1,7) for f in sorted((root/f'round{n}').rglob('*')) if f.is_file()}
        self.assertEqual(current,baseline)


if __name__=='__main__':
    def guard(event,args):
        if event.startswith('socket.') or event in ('subprocess.Popen','os.system'):
            raise RuntimeError('Independent offline verification forbids network/process dispatch')
        if event=='open' and isinstance(args[0],(str,bytes)):
            name=str(args[0]).lower()
            if any(word in name for word in ('.env','.keychain','credentials','/secrets/')):
                raise RuntimeError('Independent offline verification forbids credential file access')
    sys.addaudithook(guard)
    unittest.main(verbosity=2)
