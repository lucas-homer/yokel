"""Bounded re-review of the five initial findings and their material regressions."""
import copy,hashlib,importlib.util,io,json,sys,unittest
from pathlib import Path
H=Path(__file__).resolve().parent;REVIEW=H.parent;ROUND=REVIEW.parent;P=ROUND/'protocol';REPO=ROUND.parents[3];OLD=P/'revisions/initial'
sys.dont_write_bytecode=True

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def guard(event,args):
 if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise AssertionError('network/process forbidden')
 if event=='open' and isinstance(args[0],(str,bytes)):
  p=Path(args[0]).resolve();mode,flags=args[1:3]
  if any(x in p.parts for x in ('.ssh','.aws','Keychains','.gnupg')) or p.suffix in ('.key','.pem') or p.name=='.env':raise AssertionError('private file forbidden')
  writing=isinstance(mode,str) and any(x in mode for x in 'wax+') or isinstance(flags,int) and flags&3 in (1,2)
  if writing and not p.is_relative_to(H):raise AssertionError('review-only writes')
sys.addaudithook(guard)
ready=read(P/'READY.json');readyhash=sha(P/'READY.json');oldready=read(OLD/'READY.json');initialreview=read(REVIEW/'READY-initial.json')
pins={str(P/f):x for f,x in ready['files'].items()};pins.update({str(REPO/f):x for f,x in ready['consulted_inputs'].items()});pins.update({str(OLD/f):x for f,x in oldready['files'].items()})
def intact():return all(sha(Path(f))==x['sha256'] and Path(f).stat().st_size==x['bytes'] for f,x in pins.items()) and all(sha(REVIEW/f)==h for f,h in initialreview['files'].items())
assert intact() and sha(OLD/'READY.json')=='fa473752bff2b750f41ed325e19f4e8b40408b820ef2e03e16cc5f8e3fd31a43'
sys.path.insert(0,str(P));import validator as v
checks=[]
def ck(name,passed,detail=None):checks.append({'name':name,'passed':bool(passed),'detail':detail})
def reject(name,c,reason=None):
 try:out=v.validate(c)
 except ValueError as exc:ck(name,reason is None or reason in str(exc),{'error':str(exc)})
 else:ck(name,False,{'unexpected_result':out})
def refresh_source(c):
 c['classified_inventory']=copy.deepcopy(c['inventory']);c['source_review'].update(source_sha256=hashlib.sha256(c['source'].encode()).hexdigest(),inventory_sha256=v.digest(c['inventory']),scopes_sha256=v.digest(c['scopes']))
def audit(c):c['record_audit']={'status':'reviewed','source_sha256':hashlib.sha256(c['source'].encode()).hexdigest(),'operative_sha256':v.digest(c['operative']),'reviewed_refs':list(c['operative']),'unsupported_refs':[],'unknown_refs':[]}
fixtures=v.strict_load((P/'fixtures.json').read_text());oldfixtures=read(OLD/'fixtures.json');byid={f['id']:f['case'] for f in fixtures}
ck('35 fixture sources/annotations/expectations unchanged except audit bindings',len(fixtures)==len(oldfixtures)==35 and all({k:x for k,x in n.items() if k!='case'}=={k:x for k,x in o.items() if k!='case'} and {k:x for k,x in n['case'].items() if k!='record_audit'}=={k:x for k,x in o['case'].items() if k!='record_audit'} and {k:x for k,x in n['case']['record_audit'].items() if k not in ('source_sha256','operative_sha256')}==o['case']['record_audit'] for n,o in zip(fixtures,oldfixtures)))
owner=v.run_fixtures();ck('35 owner fixtures rerun',len(owner)==35 and all(x['pass'] for x in owner))
spec=importlib.util.spec_from_file_location('r11_final_owner_tests',P/'test_validator.py');t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t);stream=io.StringIO();res=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(t));(H/'owner-tests.txt').write_text(stream.getvalue());ck('21 owner methods rerun',res.wasSuccessful() and res.testsRun==21)
# Replay original substantive mismatch, adding only the new empty not-run audit bindings.
c=read(REVIEW/'adversarial-initial/known-loss-with-unknown-member.json')['case'];c['record_audit'].update(source_sha256='',operative_sha256='');out=v.validate(c)
ck('original known mismatch retained with unknown dependency',out['required_scope_status']=='unverified' and out['effective_mappings']['g']=='unknown' and 'g' in out['required_defects'] and out['known_required_defects']['g']=='mismatched')
(H/'known-loss-result.json').write_text(json.dumps(out,indent=2)+'\n')
c['mappings']['g'].update(status='missing',refs=[]);del c['operative']['g'];out=v.validate(c)
ck('known missing retained with unknown dependency',out['required_scope_status']=='unverified' and out['effective_mappings']['g']=='unknown' and out['known_required_defects']['g']=='missing' and 'g' in out['required_defects'])
c=copy.deepcopy(byid['conditional_advisory_positive']);c['inventory'][0]['uncertainty']='Source force unresolved';c['operative']['i']['modality']='mandatory';c['mappings']['i']['status']='mismatched';refresh_source(c);out=v.validate(c)
ck('known mismatch retained with own source uncertainty',out['required_scope_status']=='unverified' and out['known_required_defects']=={'i':'mismatched'})
# Freshly bind audit BEFORE independent same-ref/source mutations.
base=copy.deepcopy(byid['complete_positive']);audit(base);ck('bound reviewed positive',v.validate(base)['record_fidelity']=='reviewer_attestation_only')
c=copy.deepcopy(base);c['operative']['d']['value']='June 1';c['mappings']['d']['status']='mismatched';reject('same-ref changed deadline invalidates review',c,'record_audit_hash')
c=copy.deepcopy(base);c['source']+=' Additional source background.';refresh_source(c);reject('source mutation invalidates reverse audit',c,'record_audit_hash')
for field in ('source_sha256','operative_sha256'):
 c=copy.deepcopy(base);c['record_audit'][field]='0'*64;reject('stale '+field,c,'record_audit_hash')
 c=copy.deepcopy(base);del c['record_audit'][field];reject('absent '+field,c,'wrong keys')
c=copy.deepcopy(base);c['operative']=dict(reversed(list(c['operative'].items())));ck('canonical key reorder preserves bound audit',v.validate(c)['record_fidelity']=='reviewer_attestation_only')
c=copy.deepcopy(byid['complete_positive']);c['record_audit']['operative_sha256']=v.digest(c['operative']);reject('not-run audit cannot certify hash',c,'not-run audit')
# All declared contradictory category/basis combinations reject, not just the old example.
policy=read(P/'policy.json')
for category,basis in policy['scope_basis_by_category'].items():
 scope_base=byid['atomic_rule_transitions_positive'] if category=='identifying_context' else base
 candidates=[u for u in scope_base['inventory'] if category in policy['allowed_scope_by_kind'][u['kind']]];uid=candidates[0]['id']
 for other in policy['scope_bases']:
  if other==basis:continue
  c=copy.deepcopy(scope_base);c['scopes'][uid].update(category=category,basis=other);refresh_source(c);reject('category/basis '+category+'/'+other,c,'scope basis/category')
c=copy.deepcopy(base);c['scopes']['d'].update(category='unresolved_scope',basis='uncertain_source_function');refresh_source(c);ck('consistent unresolved scope blocks positive',v.validate(c)['required_scope_status']=='unverified')
# Exercise malformed unmapped facets without relying on a stale/absent audit error.
valid={'kind':'endpoint','value':'extra@example.test','modality':'descriptive','condition':'unconditional','qualifications':[]}
changes=[{'kind':'bad'},{'value':None},{'modality':'bad'},{'condition':[]},{'qualifications':False},{'qualifications':['x','x']},{'kind':'endpoint_role','value':{'endpoint':'e','purpose':['questions']}},{'kind':'endpoint_role','value':{'endpoint':False,'purpose':'questions'}},{'kind':'endpoint_role','value':{'endpoint':'e','purpose':'questions','extra':True}},{'kind':'relationship','value':{'members':['r'],'purpose':'view_material','semantics':'substitution'}},{'kind':'relationship','value':{'members':['r','r'],'purpose':'view_material','semantics':'substitution'}},{'kind':'relationship','value':{'members':['r','s'],'purpose':'view_material','semantics':'bad'}},{'kind':'relationship','value':{'members':['r','s'],'purpose':'view_material','semantics':'substitution','equivalence_evidence':[]}}]
for i,change in enumerate(changes):
 c=copy.deepcopy(base);c['operative']['unmapped']={**valid,**change};audit(c);reject('malformed unmapped operative facet '+str(i),c,'operative')
c=copy.deepcopy(base);c['operative']['unmapped']=valid;audit(c);c['record_audit']['unsupported_refs']=['unmapped'];out=v.validate(c);ck('well-formed unsupported addition stays reverse-audit defect',out['required_scope_status']=='all_required_inventoried_units_matched' and out['record_fidelity']=='not_faithful' and out['unsupported_record_refs']==['unmapped'])
c['record_audit']['unsupported_refs']=[];c['record_audit']['unknown_refs']=['unmapped'];ck('well-formed unknown addition blocks fidelity',v.validate(c)['record_fidelity']=='unverified')
for name,key,want in [('background_missing_not_participation_defect','required_scope_status','all_required_inventoried_units_matched'),('split_mixed_paragraph_deadline_missing','required_scope_status','not_complete'),('same_endpoint_two_atomic_purposes','required_scope_status','all_required_inventoried_units_matched'),('shared_contact_ambiguous_scope','required_scope_status','unverified'),('independent_view_permissions_no_group_required','required_scope_status','all_required_inventoried_units_matched'),('glyph_and_reference_closure_unknown','required_scope_status','unverified')]:ck('material semantic anchor '+name,v.validate(byid[name])[key]==want)
plan=read(P/'comparison-plan.json')
ck('plan remains unapproved preparation',plan['status']=='unfunded_preparation_only' and not plan['dispatch_authorized'] and not plan['budget']['pilot_dispatch_authorized'])
ck('human assisted unequal comparison disclosed','human-assisted' in plan['comparison_type'] and 'not an automated ordering test' in plan['comparison_type'])
ck('distinct operational and held-out roles stated','Disjoint' in plan['human_boundaries']['operational_annotator'] and 'sealed' in plan['reference'].lower())
ck('provider cost separately labeled and human effort accounted','provider-only' in plan['cost_per_correct_case'].lower() and set(plan['human_effort_accounting'])=={'operational_scope','reference_and_evaluation','comparison_reporting'})
ck('pins unchanged before and after',intact() and sha(P/'READY.json')==readyhash)
report={'status':'passed' if all(x['passed'] for x in checks) else 'blocked','protocol_ready_sha256':readyhash,'preserved_initial_ready_sha256':sha(OLD/'READY.json'),'initial_review_ready_sha256':sha(REVIEW/'READY-initial.json'),'current_protocol_file_pins':len(ready['files']),'consulted_input_pins':len(ready['consulted_inputs']),'initial_candidate_file_pins':len(oldready['files']),'checks_passed':sum(x['passed'] for x in checks),'checks_failed':sum(not x['passed'] for x in checks),'checks':checks,'owner_fixtures':35,'owner_test_methods':res.testsRun,'provider_calls':0,'credentials_read':False,'prior_files_edited':False,'model_evaluation_performed':False}
(H/'RESULT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:x for k,x in report.items() if k!='checks'}));print('failures',[x['name'] for x in checks if not x['passed']])
