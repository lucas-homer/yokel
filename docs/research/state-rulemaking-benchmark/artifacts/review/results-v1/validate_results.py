from pathlib import Path
import json,hashlib,collections
R=Path('/private/tmp/docketclock-expanded-benchmark-2026-10-05');O=R/'review/results-v1';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def rows(n):return [json.loads(l) for l in (O/n).read_text().splitlines()]
f=rows('field-scores.jsonl');d=rows('document-scores.jsonl');a=rows('extra-assertions.jsonl');fr=json.loads((R/'corpus-freeze.json').read_text());errors=[]
assert len(f)==696 and len(d)==80
assert len({(r['fixture_id'],r['arm'],r['field_id']) for r in f})==696
assert len({(r['fixture_id'],r['arm']) for r in d})==80
assert sha(R/'corpus-freeze.json')=='900f21e8a75d50444f12a0e3814d665a4f401a0d689194465d0b00467a762946'
for p,v in fr['files'].items():assert sha(R/p)==v['sha256'],p
for r in f:
 if r['evaluation_status']!='complete':continue
 if r['output_artifact']:
  p=R/r['output_artifact'];assert sha(p)==r['output_artifact_hash']
  if r['exact_output_quote'] is not None:
   t=p.read_text();loc=r['output_locator'];assert t[loc['char_start']:loc['char_end']]==r['exact_output_quote'],(r['fixture_id'],r['field_id'])
 if r['outcome'] in ['supported','partial_ambiguous','incorrect']:assert r['exact_output_quote'] and r['exact_output_quote'].strip(),(r['fixture_id'],r['field_id'])
 if r['outcome'] in ['missing','not_assessable']:assert r['omission_scope'] or r['reason_code']=='reference_uncertainty'
 if r['outcome']=='safe_abstention':assert r['answerability']=='not_stated' and r['scope_coverage']=='complete'
 assert r['field_gate_pass']==(r['outcome'] in ['supported','safe_abstention'])
for x in d:
 if x['evaluation_status']!='complete':continue
 rr=[r for r in f if (r['fixture_id'],r['arm'])==(x['fixture_id'],x['arm'])];assert all(r['evaluation_status']=='complete' for r in rr)
 if x['gate_outcome']=='pass':assert x['reference_gate_eligible'] and x['operation_status']=='completed_nonempty' and all(r['field_gate_pass'] for r in rr if r['critical']) and x['extra_assertion_audit_complete'] and not x['critical_extra_assertion_ids']
for r in a:
 p=R/r['output_artifact'];assert sha(p)==r['output_artifact_hash'];assert r['assertion_text'] in p.read_text()
out={'passed':True,'scheduled_documents':len(d),'scheduled_fields':len(f),'completed_documents':sum(r['evaluation_status']=='complete' for r in d),'completed_fields':sum(r['evaluation_status']=='complete' for r in f),'exact_output_quotes_valid':True,'frozen_files_unchanged':len(fr['files']),'critical_extra_assertions':sum(r['critical'] for r in a)}
(O/'validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
