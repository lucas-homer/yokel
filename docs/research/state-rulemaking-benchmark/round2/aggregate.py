"""Offline integration of manually reviewed evidence; refuses incomplete comparison."""
from pathlib import Path
import json,hashlib,collections,argparse
R=Path(__file__).resolve().parent;B=R.parent;A=B/'artifacts'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def lines(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def resolve(rel):
 p=Path(rel)
 for candidate in [p if p.is_absolute() else B/p,A/p,R/p]:
  if candidate.is_file():return candidate
 raise AssertionError('Missing output '+rel)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cohort',choices=['diagnostic','heldout','all'],default='all');args=ap.parse_args()
 contract=json.loads((A/'review/scoring-contract.json').read_text());results={};verification={};ledgers={}
 for cohort in (['diagnostic','heldout'] if args.cohort=='all' else [args.cohort]):
  manifest=json.loads((A/'corpus-freeze.json' if cohort=='diagnostic' else R/'heldout-execution/freeze.json').read_text());units={u['fixture_id']:u for u in manifest['units']};refs={}
  for fid,u in units.items():
   p=(A if cohort=='diagnostic' else R)/u['reference_path'];assert sha(p)==u['reference_sha256'];refs[fid]={f['field_id']:f for f in json.loads(p.read_text())['reference_fields']}
  review='review' if cohort=='diagnostic' else 'review-heldout';docs=[];fields=[];extras=[]
  for folder in ['docling','llama-cost-effective','openrouter']:
   q=R/folder/review
   docs+=lines(q/'document-scores.jsonl');fields+=lines(q/'field-scores.jsonl');extras+=lines(q/'extra-assertions.jsonl')
   if folder=='docling' and not any(d['arm']=='native' for d in docs):
    docs+=lines(q/'native-document-scores.jsonl');fields+=lines(q/'native-field-scores.jsonl')
    ep=q/'native-extra-assertions.jsonl'
    if ep.exists():extras+=lines(ep)
  arms={d['arm'] for d in docs};assert len(arms)==4,(cohort,arms)
  expected={(fid,arm) for fid in units for arm in arms};assert len(docs)==len(expected) and {(d['fixture_id'],d['arm']) for d in docs}==expected
  expected_fields={(fid,arm,f) for fid,arm in expected for f in refs[fid]};assert len(fields)==len(expected_fields) and {(f['fixture_id'],f['arm'],f['field_id']) for f in fields}==expected_fields
  quotes=0
  for row in docs+fields+extras:
   fid=row['fixture_id'];assert row.get('evaluation_status','complete')=='complete';assert row.get('input_sha256',units[fid]['input_sha256'])==units[fid]['input_sha256'];assert row.get('reference_version_hash',units[fid]['reference_sha256'])==units[fid]['reference_sha256']
   p=resolve(row['output_artifact']);assert sha(p)==row['output_artifact_hash'];text=p.read_text();q=row.get('exact_output_quote') or row.get('assertion_text')
   if q:
    assert q in text,(fid,row.get('field_id'),'quote');quotes+=1
    loc=row.get('output_locator') or {}
    for l,h in [('char_start','char_end'),('start_char','end_char'),('start','end')]:
     if l in loc and h in loc:assert text[loc[l]:loc[h]]==q;break
  grouped=collections.defaultdict(list)
  for f in fields:
   ref=refs[f['fixture_id']][f['field_id']]
   for k in ['critical','answerability','semantic_group_id']:assert f[k]==ref[k]
   gate=f['operation_status']=='completed_nonempty' and f['outcome'] in contract['field_gate_rules'][f['answerability']]
   if gate and f['answerability']=='not_stated':gate=f['scope_coverage']=='complete'
   if gate and f['answerability'] in ['present','explicit_negative']:gate=f['decisive_relation_preserved'] is True;assert f['exact_output_quote']
   assert gate==f['field_gate_pass'],(f['fixture_id'],f['field_id'],'fieldgate');grouped[f['fixture_id'],f['arm']].append(f)
  assert len({(e['arm'],e['assertion_id']) for e in extras})==len(extras)
  for d in docs:
   fs=grouped[d['fixture_id'],d['arm']];extra=[e for e in extras if e['fixture_id']==d['fixture_id'] and e['arm']==d['arm'] and e['critical']]
   assert set(d['critical_extra_assertion_ids'])=={e['assertion_id'] for e in extra}
   eligible=not any(f['critical'] and f['answerability']=='uncertain' for f in fs);assert d['reference_gate_eligible']==eligible
   gate='insufficient_reference' if not eligible else 'operational_unusable' if d['operation_status']!='completed_nonempty' else 'pass' if all(f['field_gate_pass'] for f in fs if f['critical']) and not extra else 'content_fail'
   assert d['gate_outcome']==gate,(d['fixture_id'],d['arm'],gate);assert d['extra_assertion_audit_complete']
  metrics={}
  for arm in sorted(arms):
   ds=[d for d in docs if d['arm']==arm];fs=[f for f in fields if f['arm']==arm];pos=[f for f in fs if f['critical'] and f['answerability'] in ['present','explicit_negative']];neg=[f for f in fs if f['critical'] and f['answerability']=='not_stated'];groups=collections.defaultdict(list)
   for f in fs:
    if f['critical']:groups[f['fixture_id'],f['semantic_group_id']].append(f)
   groups={k:v for k,v in groups.items() if not any(f['answerability']=='uncertain' for f in v)}
   metrics[arm]={'documents':len(ds),'eligible':sum(d['reference_gate_eligible'] for d in ds),'gates':dict(collections.Counter(d['gate_outcome'] for d in ds)),'positive':{'preserved':sum(f['field_gate_pass'] for f in pos),'total':len(pos)},'not_stated':{'preserved':sum(f['field_gate_pass'] for f in neg),'total':len(neg)},'groups':{'preserved':sum(all(f['field_gate_pass'] for f in g) for g in groups.values()),'total':len(groups)},'failures':{d['fixture_id']:d['failure_categories'] for d in ds if d['gate_outcome']!='pass'}}
  results[cohort]=metrics;verification[cohort]={'documents':len(docs),'fields':len(fields),'quotes':quotes,'recomputed_gates':len(docs),'passed':True};ledgers[cohort]={'documents':docs,'fields':fields,'extras':extras}
 out=R/'integrated';out.mkdir(exist_ok=True)
 (out/(args.cohort+'-metrics.json')).write_text(json.dumps(results,indent=2)+'\n');(out/(args.cohort+'-verification.json')).write_text(json.dumps(verification,indent=2)+'\n')
 print(json.dumps({'verification':verification,'gates':{c:{a:v['gates'] for a,v in m.items()} for c,m in results.items()}},indent=2))
if __name__=='__main__':main()
