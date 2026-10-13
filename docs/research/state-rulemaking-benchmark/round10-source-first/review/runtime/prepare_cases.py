"""Prepare explicitly private test annotations from already reviewed R9 fixtures."""
import json
from pathlib import Path
from review_support import encode,sha,span_encode,span_restore,fields,identities,charge,RESERVE
HERE=Path(__file__).resolve().parent;BENCH=HERE.parents[2]
fixture=BENCH/'round9-exact-id-completeness/protocol/development-fixtures.json';data=json.loads(fixture.read_text());cases=[]
expected={'rule_assertion/semantic_positive':'all_inventoried_units_matched','rule_assertion/evidence_only_negative':'not_complete','rule_assertion/coverage_rationale_cannot_repair':'not_complete','rule_assertion/source_only_extra_negative':'not_complete','full_alternatives/full_group_positive':'all_inventoried_units_matched','full_alternatives/phone_subgroup_negative':'not_complete','full_alternatives/unknown_endpoint_blocks_group':'unverified','modality_preservation/optional_positive':'all_inventoried_units_matched','modality_preservation/unclear_negative':'unverified','modality_preservation/mandatory_negative':'not_complete'}
for fam in data['fixtures']:
 for variant in fam['variants']:
  caseid=fam['fixture_id']+'/'+variant['id'];source=variant.get('source_text_override',fam['source_text']);record=variant['record'];assert sha(source.encode())==record['source_text_sha256']
  su=fam['source_units']+variant.get('additional_source_units',[]);names={u['source_unit_id']:f'u{i+1:03}' for i,u in enumerate(su)};oracle={u['source_unit_id']:u for u in variant['oracle_mapping']};units=[];mappings={}
  for unit in su:
   uid=unit['source_unit_id'];o=oracle[uid];newid=names[uid];evidence=[]
   for e in unit['source_evidence']:
    assert source[e['start']:e['end']]==e['quote'];positions=[i for i in range(len(source)) if source.startswith(e['quote'],i)];evidence.append({'quote':e['quote'],'occurrence':positions.index(e['start'])+1})
   units.append({'id':newid,'kind':unit['category'],'assertion':unit['assertion'],'modality':'optional' if uid=='src-optional' else 'mandatory' if uid=='src-receipt' else 'informational','applicability':'unconditional','uncertainty':'none','uncertainty_reason':'','required_unit_ids':[names[u] for u in o['required_source_unit_ids']],'evidence':evidence})
   mappings[newid]={'disposition':'missing' if o['expected_disposition']=='omitted' else o['expected_disposition'],'operative_pointers':o['semantic_record_pointers'],'reason':o['basis']}
  inventory={'schema_version':'round10.source-inventory.v1','source_text_sha256':sha(source.encode()),'units':units}
  response={'schema_version':'round10.source-mapping.v1','source_text_sha256':sha(source.encode()),'record_sha256':sha(encode(record)),'inventory_sha256':sha(encode(inventory)),'mappings':mappings}
  assert span_restore(span_encode(inventory,source),source,inventory)==inventory
  assert all(p in fields(record) for m in mappings.values() for p in m['operative_pointers'])
  cases.append({'case_id':caseid,'classification':'Private supplied offline annotation, never a provider response or measured discovery','source_text':source,'record':record,'inventory':inventory,'mapping_response':response,'expected_mapping_status':expected[caseid],'expected_semantic_status':'unverified','private_canary':'REVIEW_PRIVATE_EXPECTATION_c91fbd:'+caseid})
report={'schema_version':'round10.review.offline-cases.v1','classification':'Private independent review cases; runtime must not read this file except in a guarded offline test harness','fixture_path':str(fixture),'fixture_sha256':sha(fixture.read_bytes()),'derivation':'Original source assertions, evidence and oracle pointers/dispositions copied transparently; IDs assigned u001 onward. The src-optional modality is optional, src-receipt mandatory, remaining units informational. Evidence-only transition retains partial event assertion and remains mismatched. Unknown endpoint/modality are record-recovery unknowns, not newly invented source uncertainty. This is supplied annotation aggregation, not semantic discovery.','cases':cases}
(HERE/'synthetic_cases.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert charge({'prompt_tokens':100,'completion_tokens':100,'cost':.01})==RESERVE
assert charge({'cost':.2000000001})==200000001
assert charge({'prompt_tokens':200000,'completion_tokens':123,'cost':.001})==401230000
assert charge({'cost':True})==RESERVE
assert len(cases)==10
summary={'state':'harness_prepared_only','case_count':10,'source_dispositions':sum(len(c['inventory']['units']) for c in cases),'case_span_roundtrips':10,'selected_source_hashes':10,'pointer_membership_checks':sum(len(m['operative_pointers']) for c in cases for m in c['mapping_response']['mappings'].values()),'expected_distribution':{v:sum(c['expected_mapping_status']==v for c in cases) for v in set(expected.values())},'budget_oracle_checks':4,'runtime_imported':False,'runtime_tested':False,'provider_calls':0}
(HERE/'preparation-checks.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
