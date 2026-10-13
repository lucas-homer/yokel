#!/usr/bin/env python3
"""Frozen R8 scorer over exact reused claim mapping and new truthful verifier states/costs."""
import importlib.util,json
from pathlib import Path
OUT=Path(__file__).resolve().parent;R=OUT.parents[1];OLD=R.parent/'round8';PREV=R.parent/'round8-contract-probe'
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
a=load('table_postrun_helpers',OUT/'audit.py')
def main():
 a.main()
 sem=PREV/'execution/semantic-audit';ready_path=sem/'READY.json';ready=a.read(ready_path);assert a.sha(ready_path)=='5d7859b9b7f84da143450c3ce988a6a6f8e722cfee5dd1e9a08c73c114002ca9' and ready['status']=='ready_edits_stopped'
 for name,h in ready['artifacts'].items():assert a.sha(sem/name)==h
 assert ready['reference_sha256']==a.sha(OLD/'protocol/source-labels/truth.json') and ready['freeze_E_sha256']==a.sha(PREV/'execution/freeze-E.json')
 paths={'schedule':OUT/'schedule-WI-projection.json','truth':OUT/'truth-WI-projection.json','audit':sem/'matching-audit.json','observed':OUT/'observed-with-costs.json'};before={k:a.sha(p) for k,p in paths.items()};inputs={k:a.read(p) for k,p in paths.items()};assert before['audit']=='295b0cea69077f928f97adbfd59f8de4cd9e6b31701a2622b6bfebe1dc15cd11'
 mapping=inputs['audit'];doc=inputs['observed']['documents'][0];assert len(mapping['documents'])==1 and mapping['documents'][0]['document_id']==doc['document_id']==a.DOC
 for artifact in ('inventory','record'):
  v=mapping['documents'][0][artifact];assert v['review_complete'] and v['sha256']==doc[artifact+'_sha256']==ready[artifact+'_sha256'];assert len(v['source_matches'])==31 and {x['source_unit_id'] for x in v['source_matches']}=={x['id'] for x in inputs['truth']['documents'][0]['units']}
 scorer_path=OLD/'protocol/evaluate.py';assert a.sha(scorer_path)=='f485d747ba4deca2bfcee1963c3aefda2fc54b1e9a2d4d531bccd93c802a499f';scorer=load('frozen_table_R8_scoring',scorer_path);report=scorer.evaluate(**inputs)
 report['input_files']={k:str(p) for k,p in paths.items()};report['input_file_sha256']=before
 report['reused_artifact_provenance']={'mapping_path':str(paths['audit']),'mapping_sha256':before['audit'],'semantic_READY_sha256':a.sha(ready_path),'original_extraction_freeze_E_sha256':ready['freeze_E_sha256'],'new_verifier_freeze_E_sha256':a.E,'new_extractions':0,'new_claim_review':False,'reason':'Exact same inventory and normalized record canonical hashes, source, source truth and all 31 units; mapping reused without modifications. Quality fields describe retained artifacts, not new extraction accuracy.'}
 caveat_path=PREV/'execution/semantic-audit/supplementary-finding.json';report['supplementary_reference_caveat']={'path':str(caveat_path),'sha256':a.sha(caveat_path),'finding':a.read(caveat_path)}
 new_sem=R/'execution/semantic-audit';new_ready_path=new_sem/'READY.json';new_ready=a.read(new_ready_path)
 assert a.sha(new_ready_path)=='67bfc1c1dde5d724ae1d33511a2dd5743845da43db3b8e9331c5fdd0f92007e4' and new_ready['status']=='ready_edits_stopped' and new_ready['freeze_E_sha256']==a.E and new_ready['prior_audit_sha256']==before['audit'] and new_ready['unchanged_record_sha256']==doc['record_sha256']
 for name,h in new_ready['artifacts'].items():assert (new_sem/name).resolve().is_relative_to(new_sem.resolve()) and a.sha(new_sem/name)==h
 findings=a.read(new_sem/'findings.json');assert a.sha(new_sem/'findings.json')=='9ffc1abb38482b63f19bae5734bb51fcbe3f38757f3872e4ec1aff5b2bf5518c' and findings['record_sha256']==doc['record_sha256'] and findings['original_payload_sha256']==doc['payload_sha256']
 assert {x['dimension']:x['selected_label'] for x in findings['jev']['dimensions']}==doc['arms']['jev']['judgment']['common_dimensions'] and findings['stronger']['scored_judgment'] is None and not findings['stronger']['partial_reason_or_assessment_scored']
 report['independent_verifier_semantic_audit']={'READY_path':str(new_ready_path),'READY_sha256':a.sha(new_ready_path),'findings_path':str(new_sem/'findings.json'),'findings_sha256':a.sha(new_sem/'findings.json'),'dimensions':[{k:x[k] for k in ('dimension','selected_label','assessment','specific_defect_detection')} for x in findings['jev']['dimensions']],'stronger_valid_verdict':False,'interpretation':findings['jev']['outcome_interpretation'],'no_metric_or_matching_rewrite':True}
 report['limitations'].extend(['Zero new extraction: inventory/record quality describes exactly reused prior artifacts and prior independent matching, not a new extraction trial.','Incremental experiment costs include verifier operations only. Prior extraction costs are separately retained; Jev provider-reported dollars are unknown, so the complete provider-reported total remains null.','Strong HTTP 200 transport success ended with finish length at the fixed output cap; no complete stronger judgment exists. Do not score truncated fragments as a verdict.','Jev valid parsing/source_coverage_complete means the required answer schedule was returned; it does not prove source correctness or completeness.','Distinguish native verifier defect detection from policy review independently forced by retained deterministic uncertainties. The separately owned semantic audit evaluates the actual judgments.','Single reused, previously audited incomplete WI notice; not blinded fresh accuracy or calibrated/general model evidence-table comprehension.','The original Zoom uppercase-I/lowercase-l glyph caveat remains separate; original truth and matching are unchanged.'])
 assert report['scheduled_notices']==1 and not report['cohort_adequacy'] and report['runtime_gates']=={'verification_failed':1}
 for artifact in ('inventory','record'):
  q=report['quality'][artifact];assert q['claimed_semantic_units']==80 and q['claim_precision']['numerator']==73 and q['incorrect_claims']==1 and q['unknown_claims']==6 and q['complete_records']==0
  assert sum(x['denominator'] for x in q['source_coverage_by_category'].values())==31 and sum(x['numerator'] for x in q['source_coverage_by_category'].values())==21
 for arm in ('jev','stronger'):
  assert report['arm_invocations'][arm]=={'called':1,'uncalled':0} and report['arms'][arm]['accepted_records']==report['arms'][arm]['correct_complete_accepted']==report['arms'][arm]['unsafe_accepted']==0
  assert report['arms'][arm]['unsafe_acceptance_fraction']['value'] is None and report['arms'][arm]['review_or_unserved_fraction']['value']==1 and all(x is None for x in report['costs'][arm]['scenario_cost_per_correct_complete_record'].values())
 assert report['arms']['jev']['status_counts']=={'review':1} and report['arms']['stronger']['status_counts']=={'failed':1}
 assert report['costs']['extraction']=={'usage_estimate_usd':0,'conservative_charge_usd':0,'provider_reported_usd':0} and report['costs']['experiment_total']['provider_reported_usd'] is None
 assert all(a.sha(paths[k])==h for k,h in before.items())
 a.save('evaluation-report.json',report);a.save('evaluation-status.json',{'status':'complete','reused_claim_mapping':True,'new_inventory_calls':0,'source_units_retained_per_artifact':31,'input_files':report['input_files'],'input_file_sha256':before,'frozen_evaluator_path':str(scorer_path),'frozen_evaluator_sha256':a.sha(scorer_path),'report_sha256':a.sha(OUT/'evaluation-report.json'),'incremental_costs_only':True,'self_matching_performed':False,'stronger_judgment_fabricated':False,'independent_verifier_semantic_READY_sha256':a.sha(new_ready_path),'independent_verifier_semantic_findings_sha256':a.sha(new_sem/'findings.json')})
 print(json.dumps({'status':'complete','quality_is_reused':True,'arms':{k:report['arms'][k]['status_counts'] for k in ('jev','stronger')},'costs':report['costs']['experiment_total']}))
if __name__=='__main__':main()
