#!/usr/bin/env python3
"""Consume separate image-review mapping with frozen R8 scoring; never create claim judgments."""
import copy,hashlib,importlib.util,json
from pathlib import Path
OUT=Path(__file__).resolve().parent;R=OUT.parents[1];OLD=R.parent/'round8'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
a=load('cap_audit_helpers',OUT/'audit.py')
def main():
 audit_path=R/'execution/semantic-audit/matching-audit.json'
 if not audit_path.exists():
  a.save('evaluation-status.json',{'status':'pending_separate_image_reviewer','matching_audit_path':str(audit_path),'semantic_claims_scored':False,'reason':'No substitute matching audit is manufactured; all 31 reference units remain in the projection.'});print('Pending separate image reviewer matching-audit.json');return
 # Reverify exact source/run/debit/freeze lineage before consuming the completed independent mapping.
 a.main()
 schedule_path=R/'execution/schedule.json';truth_path=OUT/'truth-WI-projection.json';observed_path=OUT/'observed-with-costs.json'
 paths={'schedule':schedule_path,'truth':truth_path,'audit':audit_path,'observed':observed_path};inputs={k:a.read(p) for k,p in paths.items()};before={k:a.sha(p) for k,p in paths.items()}
 audit=inputs['audit'];truth=inputs['truth'];observed=inputs['observed'];assert audit['schema_version']=='round8.matching-audit.v1'
 assert len(audit['documents'])==1 and audit['documents'][0]['document_id']=='doc-92211b8c7ba0'
 inv=audit['documents'][0]['inventory'];assert inv is not None and inv['review_complete'] is True and inv['sha256']==observed['documents'][0]['inventory_sha256'];assert audit['documents'][0]['record'] is None
 assert {x['source_unit_id'] for x in inv['source_matches']}=={x['id'] for x in truth['documents'][0]['units']} and len(inv['source_matches'])==31
 scorer=load('frozen_r8_cap_probe_scoring',OLD/'protocol/evaluate.py');report=scorer.evaluate(**inputs);report['input_file_sha256']=before
 report['supplementary_reference_caveat']=a.read(OUT/'reference-caveat.json')
 report['limitations'].append('The PDF hyperlink annotation supports the model URL lowercase-l spelling; a mismatch against the frozen image reference uppercase-I reading is reference ambiguity, not established fabrication. Frozen truth and mapping are not corrected by this evaluator.')
 report['limitations'].extend(['Reused single Wisconsin notice: descriptive development reachability probe; not fresh unseen accuracy or production approval.','Experiment cost fields contain incremental cap-probe costs only. Combined prior-attempt costs are reported separately in postrun-audit/cost-audit.json.','The inventory is complete provider output but failed deterministic assembly; no emitted record or verifier judgment exists.'])
 assert report['scheduled_notices']==1 and report['cohort_adequacy'] is False and report['runtime_gates']=={'assembly_review':1}
 for artifact in ('inventory','record'):assert sum(x['denominator'] for x in report['quality'][artifact]['source_coverage_by_category'].values())==31
 for arm in ('jev','stronger'):
  assert report['arm_invocations'][arm]=={'called':0,'uncalled':1} and report['arms'][arm]['accepted_records']==report['arms'][arm]['correct_complete_accepted']==report['arms'][arm]['unsafe_accepted']==0
  assert report['arms'][arm]['unsafe_acceptance_fraction']['value'] is None and report['arms'][arm]['review_or_unserved_fraction']['value']==1
  assert all(v is None for v in report['costs'][arm]['scenario_cost_per_correct_complete_record'].values())
 assert all(a.sha(paths[k])==h for k,h in before.items())
 a.save('evaluation-report.json',report)
 a.save('evaluation-status.json',{'status':'complete','matching_audit_path':str(audit_path),'matching_audit_sha256':before['audit'],'independent_semantic_reviewer':audit['reviewer'],'frozen_evaluator_path':str(OLD/'protocol/evaluate.py'),'frozen_evaluator_sha256':a.sha(OLD/'protocol/evaluate.py'),'report_sha256':a.sha(OUT/'evaluation-report.json'),'source_units_retained':31,'record_assessment':None,'self_matching_performed':False,'incremental_costs_only':True})
 print(json.dumps({'status':'complete','inventory':report['quality']['inventory'],'record':report['quality']['record'],'costs':report['costs']['experiment_total']}))
if __name__=='__main__':main()
