#!/usr/bin/env python3
"""Consume a READY separate semantic audit with frozen R8 scoring; no self-matching."""
import importlib.util,json
from pathlib import Path
OUT=Path(__file__).resolve().parent;R=OUT.parents[1];OLD=R.parent/'round8'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
a=load('contract_audit_helpers',OUT/'audit.py')
def main():
 semantic=R/'execution/semantic-audit';audit_path=semantic/'matching-audit.json';ready_path=semantic/'READY.json'
 if not ready_path.exists():
  a.save('evaluation-status.json',{'status':'pending_separate_image_reviewer_READY','matching_audit_path':str(audit_path),'semantic_claims_scored':False,'reason':'No substitute matching is manufactured. Both emitted artifacts require independent complete assessments of all 31 unchanged reference units.'});print('Pending separate semantic reviewer READY.json');return
 a.main()
 ready=a.read(ready_path);ready_hash=a.sha(ready_path)
 assert ready['status']=='ready_edits_stopped'
 assert ready['freeze_E_sha256']==a.EXPECTED_E
 assert ready['reference_sha256']==a.sha(OLD/'protocol/source-labels/truth.json')
 assert ready_hash=='5d7859b9b7f84da143450c3ce988a6a6f8e722cfee5dd1e9a08c73c114002ca9'
 assert a.sha(audit_path)=='295b0cea69077f928f97adbfd59f8de4cd9e6b31701a2622b6bfebe1dc15cd11'
 for name,h in ready['artifacts'].items():
  path=(semantic/name).resolve();assert path.is_relative_to(semantic.resolve()) and a.sha(path)==h
 assert ready['artifacts']['matching-audit.json']==a.sha(audit_path)
 paths={'schedule':OUT/'schedule-WI-projection.json','truth':OUT/'truth-WI-projection.json','audit':audit_path,'observed':OUT/'observed-with-costs.json'}
 inputs={k:a.read(p) for k,p in paths.items()};before={k:a.sha(p) for k,p in paths.items()}
 audit=inputs['audit'];truth=inputs['truth'];observed=inputs['observed'];assert audit['schema_version']=='round8.matching-audit.v1'
 assert len(audit['documents'])==1 and audit['documents'][0]['document_id']==a.DOC
 for artifact in ('inventory','record'):
  assessment=audit['documents'][0][artifact];assert assessment is not None and assessment['review_complete'] is True
  assert assessment['sha256']==observed['documents'][0][artifact+'_sha256']==ready[artifact+'_sha256']
  assert {x['source_unit_id'] for x in assessment['source_matches']}=={x['id'] for x in truth['documents'][0]['units']} and len(assessment['source_matches'])==31
 scorer_path=OLD/'protocol/evaluate.py';assert a.sha(scorer_path)=='f485d747ba4deca2bfcee1963c3aefda2fc54b1e9a2d4d531bccd93c802a499f'
 scorer=load('frozen_r8_contract_probe_scoring',scorer_path);report=scorer.evaluate(**inputs);report['input_file_sha256']=before
 caveat_path=R.parent/'round8-cap-probe/execution/postrun-audit/reference-caveat.json';sidecar_path=R.parent/'round8-cap-probe/execution/supplementary-pdf-link.json';caveat=a.read(caveat_path)
 assert a.sha(sidecar_path)==caveat['sidecar_sha256']=='26bff39b22082cfe59183b2a36e7832c365d767080c4178a14e8dc974898367b'
 report['supplementary_reference_caveat']={'prior_audit_path':str(caveat_path),'prior_audit_sha256':a.sha(caveat_path),'caveat':caveat,'scope':'Same original WI PDF; carried forward provenance caveat, no rematching or truth modification.'}
 report['limitations'].extend(['Reused single Wisconsin notice: descriptive development reachability probe; not fresh unseen accuracy or production approval.','Experiment costs contain incremental contract-probe costs only. Combined three-attempt costs are separately reported in postrun-audit/cost-audit.json.','A structurally valid record was emitted with explicit uncertainties. Both verifier requests failed local admission before dispatch; neither arm produced a judgment.','The same original PDF hyperlink annotation supports lowercase-l in the Zoom URL. The uppercase-I image-reference glyph remains ambiguous; frozen scoring is retained and any such mismatch must not be called established fabrication.'])
 assert report['scheduled_notices']==1 and report['cohort_adequacy'] is False and report['runtime_gates']=={'request_size_review':1}
 for artifact in ('inventory','record'):assert sum(x['denominator'] for x in report['quality'][artifact]['source_coverage_by_category'].values())==31
 for arm in ('jev','stronger'):
  assert report['arm_invocations'][arm]=={'called':0,'uncalled':1} and report['arms'][arm]['accepted_records']==report['arms'][arm]['correct_complete_accepted']==report['arms'][arm]['unsafe_accepted']==0
  assert report['arms'][arm]['unsafe_acceptance_fraction']['value'] is None and report['arms'][arm]['review_or_unserved_fraction']['value']==1
  assert all(v is None for v in report['costs'][arm]['scenario_cost_per_correct_complete_record'].values())
 assert all(a.sha(paths[k])==h for k,h in before.items()) and a.sha(ready_path)==ready_hash
 for name,h in ready['artifacts'].items():assert a.sha(semantic/name)==h
 a.save('evaluation-report.json',report)
 a.save('evaluation-status.json',{'status':'complete','matching_audit_path':str(audit_path),'matching_audit_sha256':before['audit'],'semantic_READY_sha256':ready_hash,'independent_semantic_reviewer':audit['reviewer'],'frozen_evaluator_path':str(scorer_path),'frozen_evaluator_sha256':a.sha(scorer_path),'report_sha256':a.sha(OUT/'evaluation-report.json'),'source_units_retained_per_artifact':31,'record_assessment':'complete independent mapping consumed','self_matching_performed':False,'incremental_costs_only':True})
 print(json.dumps({'status':'complete','inventory':report['quality']['inventory'],'record':report['quality']['record'],'costs':report['costs']['experiment_total']}))
if __name__=='__main__':main()
