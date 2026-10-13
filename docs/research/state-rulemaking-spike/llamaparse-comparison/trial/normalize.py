"""Guarded offline mapping of agentic_plus vendor markdown; no visual repair."""
import json,re,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent

def main():
 for a in json.loads((P/'manifest.json').read_text()):
  f=(P/a['path']).resolve()
  if not f.is_relative_to(P) or hashlib.sha256(f.read_bytes()).hexdigest()!=a['sha256']: raise ValueError('Artifact integrity failure')
 for raw,derived in [('parse-response.json','parse.md'),('parse-plus-response.json','parse-plus.md')]:
  payload=json.loads((P/raw).read_text())
  expected=payload['content'][0]['text']
  if (P/derived).read_text()!=expected: raise ValueError('Raw-to-markdown mismatch: '+derived)
 t=(P/'parse-plus.md').read_text(); out=[]
 def add(pred,val,quotes,kind='proceeding',suffix='form',warnings=[]):
  assert all(q in t for q in quotes)
  out.append({'schema_version':'state-spike-v1','observation_id':'llama-'+pred,'jurisdiction':'US-MS','source_record_id':'00027305a','subject':{'kind':kind,'id':'research:ms:00027305a:'+suffix},'predicate':pred,'value':val,'evidence':[{'artifact_id':'llama-parse-plus','locator':'one-page vendor markdown; exact span offset '+str(t.index(q)),'quote':q,'support':'text_exact'} for q in quotes],'method':{'kind':'deterministic','name':'guarded-mapping-from-llamaparse-agentic-plus-model-output','version':'1'},'review_state':'needs_review','warnings':['Upstream source is model-assisted LlamaParse agentic_plus/latest; local mapping is deterministic, not independent corroboration.','Critical filing-stamp date omitted by vendor parser; no visual repair or submit-date substitution.','Selected one-page form; attachment and discovery completeness untested.']+warnings})
 m=re.search(r'\*\*AGENCY NAME:\*\* ([^\n]+)',t)
 if m: add('agency',m[1],[m[0]])
 m=re.search(r'\*\*Name or number of rule\(s\):\*\* (Rule \d+\.\d+)',t)
 if m: add('rule_citations',[m[1]],[m[0]])
 m=re.search(r'\[checked\] Amendment to existing rule\(s\)',t)
 if m and 'PROPOSED ACTION ON RULES' in t:
  add('rule_action','amendment',[m[0]])
  add('event_type','proposal',['PROPOSED ACTION ON RULES',m[0]])
 m=re.search(r'\[checked\] Presently, an oral proceeding is not scheduled on this rule\.',t)
 if m: add('hearing_status','not_scheduled',[m[0]],'hearing','oral-proceeding')
 eligibility=re.search(r'If an oral proceeding is not scheduled, an oral proceeding must be held if a written request for an oral proceeding is submitted by a political subdivision, an agency or ten \(10\) or more persons\.',t)
 m=re.search(r'within [a-z-]+ \((\d+)\) days after (the filing of this notice of proposed rule adoption)',t)
 if m and eligibility: add('hearing_request_duration',{'kind':'relative','duration':int(m[1]),'unit':'days','anchor':m[2],'day_basis':None,'computed_close':None},[m[0],eligibility[0]],'participation_window','hearing-request',['Eligibility preserved in evidence, not separately typed; no unconditional individual entitlement to a hearing.'])
 m=re.search(r'At any time within the [a-z-]+ \((\d+)\) day public comment period, written submissions[^.]+\.',t)
 if m: add('comment_duration',{'kind':'relative','duration':int(m[1]),'unit':'days','anchor':None,'day_basis':None,'computed_close':None},[m[0]],'participation_window','public-comment')
 # Date extraction requires FILED/stamp evidence, never SUBMIT DATE. These retained
 # vendor outputs omit the stamp. A changed fixture needs renewed review.
 missing=sorted({'agency','rule_citations','event_type','rule_action','hearing_status','hearing_request_duration','comment_duration'}-{o['predicate'] for o in out})
 diag={'status':'needs_review','missing_critical_predicates':missing,'withheld':{'filing_date':'Vendor output lacks dated filing stamp; handwriting submit date cannot substitute','comment_close':'No explicit absolute close or resolved comment anchor','effective_date':'Unmarked options only'},'observations_emitted':len(out),'no_agent_visual_repairs':True,'unmapped_roles':['submit_date','economic_impact_status: not in shared predicate vocabulary']}
 (P/'observations.json').write_text(json.dumps(out,indent=2)+'\n'); (P/'normalization-diagnostics.json').write_text(json.dumps(diag,indent=2)+'\n')
 if missing: raise SystemExit('Missing critical clauses: '+', '.join(missing))
 print(str(len(out))+' supported candidate observations; filing date withheld; review required')
if __name__=='__main__': main()
