"""Offline evaluation only. Never imported by the provider runtime."""
import argparse,json
from pathlib import Path
GOOD={'support':'supported','role':'matched','condition':'preserved','conflict':'absent'}
def evaluate(labels,folder):
 rows=[]
 for g in labels:
  f=folder/g['case_id']/'result.json'
  if not f.exists():
   rows.append({'case_id':g['case_id'],'scheduled':True,'result_present':False});continue
  r=json.loads(f.read_text()); got={k:v['label'] for k,v in r['dimensions'].items()}
  accepted=got==GOOD and not r['deterministic']['blocking_issues']
  ambiguous=g.get('evaluation_ambiguous',False)
  rows.append({'case_id':g['case_id'],'scheduled':True,'result_present':True,'provider_response_present':(f.parent/'response.body').exists(),'accepted_text_support':accepted,'labels':got,'reference_labels':g['expected_verdict'],'origin':g['candidate_origin'],'ambiguous':ambiguous,'limitation':g['limitation_case'],'detectable_error':g['include_in_detectable_error_denominator'] and not ambiguous,'correct_control':g['candidate_origin']=='correct_control','source_fidelity':g['expected_source_fidelity']})
 complete=[x for x in rows if x.get('result_present')]
 errors=[x for x in complete if x['detectable_error']]
 controls=[x for x in complete if x['correct_control']]
 accepted=[x for x in complete if x['accepted_text_support'] and not x['ambiguous']]
 return {'scheduled':len(rows),'results':len(complete),'provider_responses':sum(x['provider_response_present'] for x in complete),'deterministic_preblocks':sum(not x['provider_response_present'] for x in complete),'detectable_errors':{'caught':sum(not x['accepted_text_support'] for x in errors),'total':len(errors)},'correct_controls':{'accepted':sum(x['accepted_text_support'] for x in controls),'total':len(controls)},'text_support_acceptances_excluding_ambiguous':len(accepted),'accepted_source_incorrect':sum(x['source_fidelity']=='incorrect' for x in accepted),'ambiguous_excluded':[x['case_id'] for x in complete if x['ambiguous']],'rows':rows,'limitations':'Development challenge, selected contexts and reviewer-authored claims. Not extraction recall, natural error prevalence, deployment calibration or routing validation.'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--labels',type=Path,required=True);p.add_argument('--runs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 result=evaluate([json.loads(s) for s in a.labels.read_text().splitlines() if s.strip()],a.runs)
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
