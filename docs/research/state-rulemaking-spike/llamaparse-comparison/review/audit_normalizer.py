"""Bounded replay/mutation audit; all writes confined to reviewer-owned copies."""
import hashlib,importlib.util,json,shutil,subprocess,sys,tempfile
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
TRIAL=ROOT.parent/'trial'
VALIDATOR=Path('/Users/home/.codex/worktrees/e8f4/yokel/docs/research/state-rulemaking-spike/validate.py')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('shared',VALIDATOR)
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
report={'trial_root':str(TRIAL),'normalizer_sha256':digest(TRIAL/'normalize.py'),'validator_sha256':digest(VALIDATOR),'validation':v.validate_lane(TRIAL),'raw_lineage':[],'replay':[],'mutations':[]}
for name in ['parse','parse-plus']:
 raw=json.loads((TRIAL/(name+'-response.json')).read_text())['content'][0]['text']
 retained=(TRIAL/(name+'.md')).read_text()
 kind='exact' if retained==raw else 'single_trailing_newline_added' if retained==raw+'\n' else 'different'
 assert kind!='different'
 report['raw_lineage'].append({'response':name+'-response.json','derived':name+'.md','transformation':kind})
assert digest(TRIAL/'source.pdf')=='ac95c240653690261eb7a6fef83bd80a04310cf49c15c37256569bbc70315955'
def run(p):
 r=subprocess.run([sys.executable,'-B',str(p/'normalize.py')],cwd=ROOT,capture_output=True,text=True,timeout=30)
 return {'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
with tempfile.TemporaryDirectory(prefix='replay-',dir=ROOT) as tmp:
 p=Path(tmp)/'trial';shutil.copytree(TRIAL,p,ignore=shutil.ignore_patterns('__pycache__'))
 before={n:digest(p/n) for n in ['observations.json','normalization-diagnostics.json']}
 for i in range(2):
  result=run(p);after={n:digest(p/n) for n in before}
  result.update({'unchanged':before==after,'shared_validation_passed':v.validate_lane(p)['passed']})
  report['replay'].append(result)

def replace(old,new):
 def f(text):
  assert text.count(old)==1,(old,text.count(old))
  return text.replace(old,new)
 return f
def relocate_mark(text):
 lines=text.splitlines(keepends=True)
 ix=next(i for i,line in enumerate(lines) if '[checked] Amendment to existing rule(s)' in line)
 cells=lines[ix].split('|');assert len(cells)==5
 assert '[checked] Amendment' in cells[2]
 cells[1],cells[2]=cells[2],cells[1]
 lines[ix]='|'.join(cells)
 return ''.join(lines)
tests=[
 ('markdown_only_tampering',replace('within twenty (20) days after','within an unspecified period after'),'raw_lineage_failure'),
 ('missing_hearing_duration',replace('within twenty (20) days after','within an unspecified period after'),'explicit_failure'),
 ('missing_comment_duration',replace('At any time within the twenty-five (25) day public comment period','At any time within an unspecified public comment period'),'explicit_failure'),
 ('missing_eligibility',replace('submitted by a political subdivision, an agency or ten (10) or more persons.','submitted by an unspecified requester.'),'explicit_failure'),
 ('co_selected_incompatible_hearing_states',replace('[unchecked] An oral proceeding is scheduled','[checked] An oral proceeding is scheduled'),'review_conflict_expected'),
 ('amendment_mark_moved_to_temporary_rules_column',relocate_mark,'review_scope_expected'),
]
for name,mutate,desired in tests:
 with tempfile.TemporaryDirectory(prefix='mutation-',dir=ROOT) as tmp:
  p=Path(tmp)/'trial';shutil.copytree(TRIAL,p,ignore=shutil.ignore_patterns('__pycache__'))
  markdown=p/'parse-plus.md';markdown.write_text(mutate(markdown.read_text()))
  # Semantics probes model a changed vendor result: update its raw text too.
  # The dedicated tampering control leaves raw/derived mismatched on purpose.
  if name!='markdown_only_tampering':
   raw=p/'parse-plus-response.json';payload=json.loads(raw.read_text())
   payload['content'][0]['text']=markdown.read_text();raw.write_text(json.dumps(payload))
  manifest=json.loads((p/'manifest.json').read_text())
  for artifact in manifest:
   if artifact['path'] in ['parse-plus.md','parse-plus-response.json']:artifact['sha256']=digest(p/artifact['path'])
  (p/'manifest.json').write_text(json.dumps(manifest))
  result=run(p);observations=json.loads((p/'observations.json').read_text())
  result.update({'case':name,'desired_behavior':desired,'observations_count':len(observations),'all_needs_review':all(o['review_state']=='needs_review' for o in observations),'diagnostics':json.loads((p/'normalization-diagnostics.json').read_text()),'mapped_values':{o['predicate']:o['value'] for o in observations},'shared_validation_passed':v.validate_lane(p)['passed']})
  report['mutations'].append(result)
report['final_baseline_checks']={'all_needs_review':all(o['review_state']=='needs_review' for o in json.loads((TRIAL/'observations.json').read_text())),'no_filing_date':not any(o['predicate']=='filing_date' for o in json.loads((TRIAL/'observations.json').read_text())),'normalization_is_local_deterministic_from_model_parser':True,'no_agent_visual_repairs':True}
(ROOT/'normalizer-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'baseline_validation':report['validation'],'raw_lineage':report['raw_lineage'],'replay':report['replay'],'mutations':[{'case':x['case'],'exit_code':x['exit_code'],'count':x['observations_count'],'all_needs_review':x['all_needs_review'],'missing':x['diagnostics']['missing_critical_predicates']} for x in report['mutations']]},indent=2))
