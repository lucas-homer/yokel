import copy,unittest
import common as c
import request,response,semantic
F=c.read(c.PROTO/'development-fixtures.json')['fixtures'];AUDITS=c.read(c.PROTO/'development-audit-inputs.json')['audits'];ENDORSED=c.read(c.ROUND/'approved-development-audits.json');PENDING=c.read(c.PROTO/'offline-audit-review.json')
def cases():
    for audit in AUDITS:
        family,variant_id=audit['audit_id'].split('/');fixture=next(f for f in F if f['fixture_id']==family);variant=next(v for v in fixture['variants'] if v['id']==variant_id)
        yield variant.get('source_text_override',fixture['source_text']),variant['record'],audit

def positive():return next(cases())
def result(audit,record=None,source=None,review=ENDORSED):
    text,original,_=positive();return semantic.aggregate(text if source is None else source,original if record is None else record,audit,review)
class BoundaryTests(unittest.TestCase):
    def test_exact_schedule_schema_request_and_expansion(self):
        built=request.wi();checked=c.read(c.PROTO/'wi70-schedule.json');registry=built['schedule']
        for key,value in registry.items():self.assertEqual(value,checked[key])
        self.assertEqual(registry['expected_item_count'],70);self.assertEqual(sum(x['kind']=='timing' for x in registry['items']),5);self.assertEqual(sum(x['kind']=='components' for x in registry['items']),26);self.assertNotIn('coverage',registry['sorted_ids']);self.assertEqual(built['body'],c.read(c.PROTO/'wi70-offline-request.fixture.json'));self.assertEqual(built['body']['response_format']['json_schema']['schema'],c.read(c.PROTO/'wi70-response.schema.json'));self.assertEqual(c.digest(response.expand(response.schema_for(registry))),request.SIZES['baseline_expanded_schema_canonical_sha256']);self.assertEqual((built['schema_bytes'],built['body_bytes'],built['estimate']),(7506,38432,39456))
    def test_all_active_raw_fixtures_and_lossless_uncertain_positives(self):
        for case in c.read(c.PROTO/'response-fixtures.json')['cases']:
            with self.subTest(case=case['id']):
                checked=response.validate_response(case['raw_json'],request.ASSEMBLED['source'],request.ASSEMBLED);self.assertEqual(checked['structural_valid'],case['expected_structural_valid']);self.assertEqual(checked['semantic_status'],'unverified');self.assertFalse(checked['production_eligible']);self.assertFalse(checked['action_ready'])
                if checked['structural_valid']:
                    wire=c.strict(case['raw_json']);legacy=checked['legacy_verdict'];self.assertEqual(legacy['schema_version'],'round7.record_verdict.v1');self.assertEqual({x['item_id']:{k:v for k,v in x.items() if k!='item_id'} for x in legacy['assessments']},wire['assessments'])
                    for key in wire:
                        if key not in ('assessments','schema_version'):self.assertEqual(legacy[key],wire[key])
                    self.assertTrue(checked['review_required'])
    def test_malformed_assembly_inputs_return_structured_invalid(self):
        raw=c.read(c.PROTO/'response-fixtures.json')['cases'][0]['raw_json']
        for assembled in (None,[],{'record':None},{}, {'record':{}}, {'record':[]}):
            with self.subTest(assembled=assembled):
                checked=response.validate_response(raw,request.ASSEMBLED['source'],assembled);self.assertFalse(checked['structural_valid']);self.assertIsNone(checked['legacy_verdict']);self.assertEqual(checked['semantic_status'],'unverified');self.assertTrue(checked['errors'])
        for source in (None,[],{}):
            checked=response.validate_response(raw,source,request.ASSEMBLED);self.assertFalse(checked['structural_valid']);self.assertIsNone(checked['legacy_verdict'])
    def test_raw_duplicates_constants_trailing_and_array_no_fallback(self):
        for raw in ('{"x":1,"x":2}','{"x":{"y":0,"y":1}}','{"x":NaN}','{"x":Infinity}','{"x":1e999}','{} {}','{'):
            with self.assertRaises(ValueError):c.strict(raw)
        array_cases=c.read(c.PROTO/'comparison-array-response-fixtures.json')
        self.assertIn('cases',array_cases)
        for row in array_cases['cases']:
            raw=row.get('raw_json',c.encode(row.get('response',{})))
            if 'raw_json' not in row and 'response' not in row:continue
            checked=response.validate_response(raw,request.ASSEMBLED['source'],request.ASSEMBLED);self.assertFalse(checked['structural_valid'])
    def test_input_schedule_collisions_reserved_empty_and_limit(self):
        record=request.ASSEMBLED['record']
        for kind in ('duplicate','cross_category','coverage','empty','overlimit'):
            value=copy.deepcopy(record)
            if kind=='duplicate':value['events'][1]['id']=value['events'][0]['id']
            elif kind=='cross_category':value['routes'][0]['components'][0]['id']=value['events'][0]['id']
            elif kind=='coverage':value['events'][0]['id']='coverage'
            elif kind=='empty':
                for category in response.CATEGORIES:value[category]=[]
            else:
                for category in response.CATEGORIES:value[category]=[]
                value['identities']=[{'id':str(n)} for n in range(1001)]
            with self.assertRaises(ValueError):response.schedule(value,'a'*64)
    def test_reference_failures_never_ignored(self):
        schema=response.schema_for(request.wi()['schedule']);first=next(iter(schema['properties']['assessments']['properties']))
        for kind in ('unknown','external','sibling','missing','cycle','deep'):
            value=copy.deepcopy(schema)
            if kind=='unknown':value['properties']['assessments']['properties'][first]={'$ref':'#/$defs/z'}
            elif kind=='external':value['properties']['assessments']['properties'][first]={'$ref':'https://invalid.example/a'}
            elif kind=='sibling':value['properties']['assessments']['properties'][first]['type']='object'
            elif kind=='missing':value['$defs'].pop('e')
            elif kind=='cycle':value['$defs']['e']={'$ref':'#/$defs/a'}
            else:
                child={'$ref':'#/$defs/e'}
                for _ in range(5):child={'type':'object','properties':{'x':child}}
                value['properties']['deep']=child
            with self.assertRaises(ValueError):response.expand(value)
        odd=copy.deepcopy(request.ASSEMBLED['record']);odd['events'][0]['id']='$ref';odd_registry=response.schedule(odd,'a'*64);self.assertIn('$ref',response.expand(response.schema_for(odd_registry))['properties']['assessments']['properties'])
    def test_provider_allowlist_and_guard_without_oracle(self):
        built=request.wi();self.assertEqual(set(built['body']),{'model','stream','max_tokens','reasoning','provider','messages','response_format'});self.assertEqual(built['body']['messages'][1],request.BASELINE['messages'][1]);self.assertEqual(built['body']['messages'][0]['content'],request.BASELINE['messages'][0]['content']+'\n'+request.SIZES['added_neutral_instruction'])
        for private in ('oracle_mapping','candidate_claim_checks','source_dispositions','primary_reviewer','whole_notice_complete_eligible','expected_structural_valid'):self.assertNotIn(private,c.encode(built['body']).decode())
        before=c.encode(request.BASELINE);withheld=copy.deepcopy(request.BASELINE);withheld['messages'][0]['content']+='x'*545
        from unittest.mock import patch
        with patch.object(request,'BASELINE',withheld):
            with self.assertRaises(ValueError):request.wi()
        self.assertEqual(c.encode(request.BASELINE),before)

class SemanticTests(unittest.TestCase):
    def test_endorsed_inputs_counts_positive_negative_unknown_and_pending(self):
        statuses=[];field_count=0;source_count=0
        for text,record,audit in cases():
            self.assertFalse(c.p.schema_errors(record,c.p.RECORD_SCHEMA));field_count+=len(semantic.fields(record));source_count+=len(audit['source_dispositions']);approved=semantic.aggregate(text,record,audit,ENDORSED);statuses.append(approved['semantic_status']);self.assertEqual(approved['review_required'],not approved['complete_supported']);self.assertFalse(approved['production_eligible']);self.assertFalse(approved['action_ready']);self.assertEqual(semantic.aggregate(text,record,audit,PENDING)['semantic_status'],'unverified')
        self.assertEqual((field_count,source_count),(214,44));self.assertEqual(statuses.count('complete_supported'),3);self.assertEqual(statuses.count('not_complete'),5);self.assertEqual(statuses.count('unverified'),2)
    def test_minimal_pairs_and_source_universe_independence(self):
        outcomes={audit['audit_id']:semantic.aggregate(text,record,audit,ENDORSED) for text,record,audit in cases()}
        self.assertEqual(outcomes['rule_assertion/evidence_only_negative']['semantic_status'],'not_complete');self.assertEqual(outcomes['rule_assertion/coverage_rationale_cannot_repair']['semantic_status'],'not_complete');self.assertEqual(outcomes['rule_assertion/source_only_extra_negative']['semantic_status'],'not_complete');self.assertEqual(outcomes['full_alternatives/phone_subgroup_negative']['semantic_status'],'not_complete');self.assertEqual(outcomes['full_alternatives/unknown_endpoint_blocks_group']['semantic_status'],'unverified');self.assertEqual(outcomes['modality_preservation/mandatory_negative']['semantic_status'],'not_complete');self.assertEqual(outcomes['modality_preservation/unclear_negative']['semantic_status'],'unverified')
        family=F[0];a=family['variants'][0]['record'];b=family['variants'][1]['record'];changed=copy.deepcopy(a);changed['events'][0]['description']=b['events'][0]['description'];self.assertEqual(changed,b)
        negative=family['variants'][1]['record'];coverage=family['variants'][2]['record'];changed=copy.deepcopy(negative);changed['coverage']['rationale']=coverage['coverage']['rationale'];self.assertEqual(changed,coverage)
        self.assertEqual(response.schedule(a,'a'*64)['sorted_ids'],response.schedule(family['variants'][3]['record'],'b'*64)['sorted_ids'])
    def test_missing_pending_rejected_duplicate_and_bad_reviewers(self):
        _,record,audit=positive();self.assertEqual(semantic.aggregate(record=record,source_text=positive()[0])['semantic_status'],'unverified');self.assertEqual(result(audit,review=None)['semantic_status'],'unverified')
        for kind in ('pending','rejected','duplicate','missing_primary','same','author','stale'):
            review=copy.deepcopy(ENDORSED);entry=review['entries'][0]
            if kind in ('pending','rejected'):entry['decision']=kind
            elif kind=='duplicate':review['entries'].append(copy.deepcopy(entry))
            elif kind=='missing_primary':entry['primary_reviewer']=None
            elif kind=='same':entry['primary_reviewer']=entry['independent_reviewer']
            elif kind=='author':entry['primary_reviewer']=audit['provenance']['author']
            else:entry['audit_sha256']='0'*64
            self.assertEqual(result(audit,review=review)['semantic_status'],'unverified',kind)
    def test_mutated_bindings_scopes_rows_and_extra_trust_flags_fail_closed(self):
        _,record,audit=positive()
        mutations=[]
        for key in ('source_text_sha256','record_sha256','source_reference_sha256'):
            bad=copy.deepcopy(audit);bad[key]='0'*64;mutations.append(bad)
        for key,value in (('status','partial'),('status','unknown'),('reviewed_start',1),('reviewed_end',len(positive()[0])-1),('exclusions',['part']),('unresolved_questions',['unclear'])):
            bad=copy.deepcopy(audit);bad['source_reference']['scope'][key]=value;mutations.append(bad)
        for section in ('source_dispositions','candidate_claim_checks'):
            for kind in ('remove','duplicate','add'):
                bad=copy.deepcopy(audit)
                if kind=='remove':bad[section].pop()
                else:
                    row=copy.deepcopy(bad[section][0])
                    if kind=='add':row['source_unit_id' if section=='source_dispositions' else 'claim_id']='extra'
                    bad[section].append(row)
                mutations.append(bad)
        for key,value in (('status','partial'),('status','unknown'),('unreviewed_pointers',['/events/0/phase'])):
            bad=copy.deepcopy(audit);bad['claim_coverage'][key]=value;mutations.append(bad)
        for key in ('asserted_complete','trusted','result'):
            bad=copy.deepcopy(audit);bad[key]=True;mutations.append(bad)
        for bad in mutations:self.assertEqual(result(bad)['semantic_status'],'unverified')
        changed=copy.deepcopy(record);changed['coverage']['rationale']='same-size false coverage repair';self.assertEqual(result(audit,record=changed)['semantic_status'],'unverified')
    def test_pointer_evidence_dependencies_and_reverse_links(self):
        _,record,audit=positive();mutations=[]
        for pointer in ('/coverage/rationale','/events/0/evidence','/events/0/id','/source_text','/events/99/description'):
            bad=copy.deepcopy(audit);bad['candidate_claim_checks'][0]['record_pointer']=pointer;mutations.append((bad,'pointer_or_evidence_invalid'))
        bad=copy.deepcopy(audit);bad['candidate_claim_checks'][0]['value_sha256']='0'*64;mutations.append((bad,'pointer_or_evidence_invalid'))
        bad=copy.deepcopy(audit);bad['source_reference']['units'][0]['source_evidence'][0]['quote']='wrong';mutations.append((bad,'pointer_or_evidence_invalid'))
        for kind in ('absent','self','cycle'):
            bad=copy.deepcopy(audit);units=bad['source_reference']['units']
            if kind=='absent':units[0]['required_source_unit_ids']=['absent']
            elif kind=='self':units[0]['required_source_unit_ids']=[units[0]['source_unit_id']]
            else:units[0]['required_source_unit_ids']=[units[1]['source_unit_id']];units[1]['required_source_unit_ids']=[units[0]['source_unit_id']]
            mutations.append((bad,'dependency_invalid'))
        bad=copy.deepcopy(audit);bad['candidate_claim_checks'][0]['source_unit_ids']=[];mutations.append((bad,'mapping_inconsistent'))
        for bad,code in mutations:
            checked=result(bad);self.assertEqual(checked['semantic_status'],'unverified');self.assertIn(code,checked['diagnostic_codes'])
    def test_unsupported_addition_not_ignored_and_requires_new_external_review(self):
        text,record,audit=positive();changed=copy.deepcopy(record);changed['identities'].append({'id':'i_addition','kind':'agency','literal':'Unsupported added agency','relation':'canonical','event_ids':['e_hearing'],'evidence':copy.deepcopy(record['identities'][0]['evidence'])})
        bad=copy.deepcopy(audit);bad['record_sha256']=c.digest(changed);old=semantic.fields(record)
        for pointer,value in semantic.fields(changed).items():
            if pointer not in old:bad['candidate_claim_checks'].append({'claim_id':'added-'+pointer.rsplit('/',1)[-1],'record_pointer':pointer,'value_sha256':c.digest(value),'disposition':'unsupported','source_unit_ids':[],'basis':'Unendorsed negative mutation: additional assertion has no source mapping.'})
        checked=semantic.aggregate(text,changed,bad,ENDORSED);self.assertEqual(checked['semantic_status'],'unverified');self.assertIn('semantic_defect',checked['diagnostic_codes']);self.assertIn('binding_mismatch',checked['diagnostic_codes']);self.assertNotIn('claim_set_mismatch',checked['diagnostic_codes'])
        # No re-signed or manufactured approval: a new audit/record legitimately requires new external review.
    def test_unknown_precedes_defect_and_parent_cannot_hide_endpoint(self):
        _,_,audit=positive();bad=copy.deepcopy(audit);bad['candidate_claim_checks'][0]['disposition']='unknown';bad['source_dispositions'][-1]['disposition']='mismatched';checked=result(bad);self.assertEqual(checked['semantic_status'],'unverified');self.assertIn('semantic_unknown',checked['diagnostic_codes']);self.assertIn('semantic_defect',checked['diagnostic_codes'])
        text,record,group=next((x for x in cases() if x[2]['audit_id']=='full_alternatives/unknown_endpoint_blocks_group'));bad=copy.deepcopy(group);parent=next(row for row in bad['source_dispositions'] if row['source_unit_id']==next(u['source_unit_id'] for u in bad['source_reference']['units'] if u['required_source_unit_ids']));parent['disposition']='matched';checked=semantic.aggregate(text,record,bad,ENDORSED);self.assertEqual(checked['semantic_status'],'unverified');self.assertIn('dependency_invalid',checked['diagnostic_codes'])
    def test_malformed_raw_audit_and_record_never_get_semantic_pass(self):
        text,record,audit=positive()
        for raw in ('{"trusted":true,"trusted":false}','{"cost":NaN}','{} {}'):
            checked=semantic.aggregate_json(c.encode(text),c.encode(record),raw,c.encode(ENDORSED));self.assertEqual(checked['semantic_status'],'unverified')
        for bad in ({},None,{'coverage':[]}):self.assertEqual(semantic.aggregate(text,bad,audit,ENDORSED)['semantic_status'],'unverified')
if __name__=='__main__':unittest.main(verbosity=2)
