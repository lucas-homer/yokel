import json,tempfile,shutil,hashlib,subprocess,sys
from pathlib import Path
P=Path(__file__).resolve().parent
reports=[]
for label,old,new,missing in [('hearing_duration','within twenty (20) days after','within an unspecified period after','hearing_request_duration'),('comment_duration','At any time within the twenty-five (25) day public comment period','Unspecified public comment period','comment_duration'),('eligibility','submitted by a political subdivision, an agency or ten (10) or more persons.','submitted by unspecified requesters.','hearing_request_duration')]:
 with tempfile.TemporaryDirectory(prefix='guard-',dir=P) as d:
  T=Path(d); m=json.loads((P/'manifest.json').read_text())
  for a in m: shutil.copyfile(P/a['path'],T/a['path'])
  shutil.copyfile(P/'normalize.py',T/'normalize.py')
  s=(T/'parse-plus.md').read_text(); assert old in s; (T/'parse-plus.md').write_text(s.replace(old,new))
  # Mutate the synthetic vendor payload consistently so clause guards, not
  # raw-to-derived integrity checks, are the tested failure mechanism.
  raw=json.loads((T/'parse-plus-response.json').read_text())
  raw['content'][0]['text']=(T/'parse-plus.md').read_text()
  (T/'parse-plus-response.json').write_text(json.dumps(raw))
  for a in m:a['sha256']=hashlib.sha256((T/a['path']).read_bytes()).hexdigest()
  (T/'manifest.json').write_text(json.dumps(m));run=subprocess.run([sys.executable,str(T/'normalize.py')],capture_output=True,text=True)
  diag=json.loads((T/'normalization-diagnostics.json').read_text()); obs=json.loads((T/'observations.json').read_text())
  assert run.returncode and diag['missing_critical_predicates']==[missing] and len(obs)==6
  assert not any(o['predicate'] in [missing,'filing_date','comment_close','effective_date'] for o in obs)
  reports.append({'case':label,'exit':run.returncode,'missing':missing,'partial_count':6,'passed':True})
(P/'guard-test-results.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports))
