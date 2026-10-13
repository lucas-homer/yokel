#!/usr/bin/env python3
"""One-time local baseline/amendment preparation; never performs acquisition."""
import ast,datetime,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent;S=ROOT.parent;R=S.parent
assert not (ROOT/'preparation.READY.json').exists()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
review=R/'verification/collection-reconciliation/results.json';recommendation=R/'verification/collection-reconciliation/RECOMMENDATION.md';audit=json.loads(review.read_text());assert audit['queries_audited']==14
original=[{'path':str(p.relative_to(S)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(S.rglob('*')) if p.is_file() and not p.is_relative_to(ROOT)];assert len(original)==503 # Original500 plus the three preserved all14/converter audit files.
freeze=R/'execution/freeze-A.json';pins=json.loads(freeze.read_text())['files'];assert len(pins)==69
for x in pins:assert sha(R/x['path'])==x['sha256']
put(ROOT/'original-baseline.json',{'schema_version':'round8.original-source-baseline.v1','source_files':original,'freeze_A_files':pins,'freeze_A_sha256':sha(freeze),'original_ledger_sha256':sha(S/'search-access-ledger.jsonl'),'original_preparation_sha256':sha(S/'preparation.READY.json'),'original_release_sha256':sha(S/'freeze-release.json')})
put(ROOT/'plan-amendment.json',{'schema_version':'round8.bounded-plan-amendment.v1','status':'PREPARED_ACCESS_HELD','recommendation_path':str(recommendation),'recommendation_sha256':sha(recommendation),'independent_audit_path':str(review),'independent_audit_sha256':sha(review),'queries':[{a:x[a] for a in ['query_id','record_sha256','raw_text_sha256','original_bounded_display_orders','corrected_bounded_candidates','metadata_omissions']} for x in audit['queries']],'corrected_bounds':{'Q03':[2,5,6],'Q05':[2,4,6],'Q14':[1,2,3]},'source_criteria_unchanged':True,'logical_replay_before_future_queries':True,'physical_access_order_restored':False,'cohort_classification':'protocol-deviation corrected','catchup_acquisition_query':'Q05','existing_artifact_paths':'Original sources/documents preserved; explicit artifact_folder accompanies each selected identity. New artifacts isolated in reconciliation/candidates and reconciliation/documents. IDs use unchanged original-PDF SHA prefix.','approval_required':'Primary amendment-release.json binds this companion preparation, plan amendment and original ledger with explicit authorized_reconciliation approval. No fresh access on preparation authorization alone.'})
for n in ['access-ledger.jsonl','correction-ledger.jsonl']:
 assert not (ROOT/n).exists();(ROOT/n).write_text('')
for p in ROOT.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
print(json.dumps({'status':'PREPARED_ACCESS_HELD','original_source_files':len(original),'freeze_A_files':len(pins),'fresh_access':0}))
