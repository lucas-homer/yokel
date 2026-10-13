"""Offline mutation checks confined to temporary copies inside this research lane."""
from pathlib import Path
import json,hashlib,tempfile,shutil,subprocess,sys
P=Path(__file__).resolve().parent
cases={'hearing_request_duration':('within twenty (20) days after','within an unspecified period after'),'comment_duration':('At any time within the twenty-five (25) day public comment period','At any time within the unspecified public comment period')}
cases['hearing_request_eligibility']=('submitted by a political subdivision, an agency or ten (10) or more persons.', 'submitted by an unspecified eligible requester.')
reports=[]
for predicate,(old,new) in cases.items():
 with tempfile.TemporaryDirectory(prefix='guard-test-',dir=P) as d:
  T=Path(d); manifest=json.loads((P/'manifest.json').read_text())
  for a in manifest:
   target=T/a['path']; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(P/a['path'],target)
  shutil.copyfile(P/'normalize.py',T/'normalize.py')
  text=(T/'derived/firecrawl.md').read_text(); assert old in text
  (T/'derived/firecrawl.md').write_text(text.replace(old,new))
  for a in manifest:
   a['sha256']=hashlib.sha256((T/a['path']).read_bytes()).hexdigest()
  (T/'manifest.json').write_text(json.dumps(manifest))
  run=subprocess.run([sys.executable,str(T/'normalize.py')],capture_output=True,text=True)
  diag=json.loads((T/'normalization-diagnostics.json').read_text()); obs=json.loads((T/'observations.json').read_text())
  missing_predicate='hearing_request_duration' if predicate=='hearing_request_eligibility' else predicate
  assert run.returncode!=0 and diag['missing_critical_predicates']==[missing_predicate]
  assert len(obs)==7 and all(o['predicate']!=missing_predicate and o['review_state']=='needs_review' for o in obs)
  reports.append({'removed_parse_pattern_for':predicate,'exit_code':run.returncode,'diagnostic':diag,'partial_observations':len(obs),'fabricated_missing_value':False,'passed':True})
(P/'guard-test-results.json').write_text(json.dumps(reports,indent=2)+'\n')
print(json.dumps(reports,indent=2))
