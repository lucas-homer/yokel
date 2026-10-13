"""Held-out adapter around the reviewed diagnostic REST state machine; no reference hints."""
import importlib.util,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
PARENT=HERE.parent
ENGINE=PARENT/'llama-cost-effective/run_cost_effective.py'
assert hashlib.sha256(ENGINE.read_bytes()).hexdigest()=='b05803050e0200784f3947114258768212fc977c30e3494c6dfa2509a33c9963'
spec=importlib.util.spec_from_file_location('engine',ENGINE);engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
engine.LANE_DIR=HERE/'llama-cost-effective';engine.RUN_TAG='round2-heldout-cost-effective'
def plan(root):
 freeze=HERE/'freeze.json';d=json.loads(freeze.read_text())
 assert d['status']=='adjudicated_frozen_before_parser_execution'
 for rel,item in d['files'].items():
  b=(PARENT/rel).read_bytes();assert engine.sha(b)==item['sha256'] and len(b)==item['bytes']
 jobs=[]
 for u in d['units']:
  p=PARENT/'heldout'/u['fixture_id']/'input.pdf';b=p.read_bytes();assert engine.sha(b)==u['input_sha256']
  jobs.append({'fixture_id':u['fixture_id'],'tier':'cost_effective','input_path':str(p.relative_to(root)),'input_sha256':u['input_sha256'],'input_bytes':len(b),'pages':u['input_page_count'],'candidate_file_id':None})
 assert len(jobs)==8 and sum(j['pages'] for j in jobs)==22
 return {'schema':2,'benchmark_run':engine.RUN_TAG,'freeze_sha256':engine.sha(freeze.read_bytes()),'jobs':jobs,'max_active':2,'stop_consecutive_failures':3,'version':'latest','input_pages':22,'nominal_credits':66,'config_template':engine.config('<verified-file-id>','cost_effective','<token>','<sha>'),'interface_differences':engine.DIFFERENCES}
engine.local_plan=plan
if __name__=='__main__':engine.LANE_DIR.mkdir(exist_ok=True);engine.main()
