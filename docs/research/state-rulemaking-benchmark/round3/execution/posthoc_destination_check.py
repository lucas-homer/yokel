"""Post-hoc development amendment, not part of the frozen pilot. No API calls."""
import json,re
from pathlib import Path
P=Path(__file__).resolve().parent
EMAIL=re.compile(r"(?<![\w.+-])[\w.!#$%&'*+/=?^`{|}~-]+@[\w-]+(?:\.[\w-]+)+")
def check(case):
 if case['candidate']['field']!='submission_email':return None
 value=case['candidate']['value']
 return {'exact_candidate_in_source_email_set':value in set(EMAIL.findall(case['source_text'])), 'evidence_channel':'supplied parser text only','does_not_establish_source_fidelity':True}
if __name__=='__main__':
 cases=[json.loads(x) for x in (P/'staged/runtime.jsonl').read_text().splitlines()]
 result={'status':'posthoc_development_not_frozen_evaluation','reason':'Both frozen model arms accepted C002; literal destinations should be checked in code','cases':[{'case_id':c['case_id'],**check(c)} for c in cases if check(c) is not None]}
 assert result['cases'][0]['exact_candidate_in_source_email_set']
 assert not result['cases'][1]['exact_candidate_in_source_email_set']
 assert result['cases'][2]['exact_candidate_in_source_email_set']
 (P/'posthoc-destination-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
