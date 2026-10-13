"""Bounded independent offline counterexamples; no fixture authoring or provider use."""
import copy,hashlib,importlib.util,io,json,sys,unittest
from pathlib import Path
H=Path(__file__).resolve().parent;REVIEW=H.parent;ROUND=REVIEW.parent;P=ROUND/'protocol';REPO=ROUND.parents[3]
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
ready=read(P/'READY.json');readyhash=sha(P/'READY.json');pins={str(P/f):row for f,row in ready['files'].items()};pins.update({str(REPO/f):row for f,row in ready['consulted_inputs'].items()})
def verify():return all(sha(Path(f))==x['sha256'] and Path(f).stat().st_size==x['bytes'] for f,x in pins.items())
assert verify()
sys.path.insert(0,str(P));import validator as v
fixtures=v.strict_load((P/'fixtures.json').read_text());byid={f['id']:f['case'] for f in fixtures};owner=v.run_fixtures();assert all(x['pass'] for x in owner)
spec=importlib.util.spec_from_file_location('r11_owner_tests',P/'test_validator.py');tests=importlib.util.module_from_spec(spec);spec.loader.exec_module(tests);stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests));(H/'owner-tests.txt').write_text(stream.getvalue())
observations=[]
def probe(name,case,expected,criterion):
 try:actual={'accepted':True,'result':v.validate(case)}
 except ValueError as exc:actual={'accepted':False,'error':str(exc)}
 row={'name':name,'expected':expected,'actual':actual,'expectation_met':criterion(actual)};observations.append(row);(H/(name+'.json')).write_text(json.dumps({'case':case,**row},indent=2)+'\n')
base=copy.deepcopy(byid['complete_positive'])
# A known incomplete full substitution relation and unresolved endpoint recovery coexist.
c=copy.deepcopy(byid['substitution_with_qualifications_positive'])
c['mappings']['e0']['status']='unknown';c['mappings']['r0']['status']='unknown';c['operative']['g']['value']['members']=['r1','r2'];c['mappings']['g']['status']='mismatched';c['mappings']['g']['reason']='Known full-member omission; Zoom recovery also unresolved.'
probe('known-loss-with-unknown-member',c,'Scope unverified AND known g mismatch explicitly retained in defect diagnostics.',lambda x:x['accepted'] and x['result']['required_scope_status']=='unverified' and 'g' in x['result']['required_defects'])
# The record review is made against one projection, then that value changes at same ref.
c=copy.deepcopy(base);c['record_audit']={'status':'reviewed','reviewed_refs':list(c['operative']),'unsupported_refs':[],'unknown_refs':[]};before=copy.deepcopy(c)
assert v.validate(before)['record_fidelity']=='reviewer_attestation_only'
c['operative']['d']['value']='June 1';c['mappings']['d']['status']='mismatched';c['mappings']['d']['reason']='Changed deadline: source May 3, record June 1.'
probe('stale-reverse-audit',c,'Changed operative projection invalidates prior audit; reject or record_fidelity unverified.',lambda x:not x['accepted'] or x['result']['record_fidelity']=='unverified')
(H/'stale-reverse-audit-before.json').write_text(json.dumps(before,indent=2)+'\n')
# Explicit unresolved-function basis cannot coexist with a positive scope gate.
c=copy.deepcopy(base);c['scopes']['d']['basis']='uncertain_source_function';c['scopes']['d']['reason']='Source-relative function unresolved; category accidentally remains required.';c['source_review']['scopes_sha256']=v.digest(c['scopes'])
probe('unresolved-basis-positive-category',c,'Reject inconsistent category/basis or block scoped coverage as unverified.',lambda x:not x['accepted'] or x['result']['required_scope_status']=='unverified')
# Reverse audits must not implicitly validate malformed operative facets.
c=copy.deepcopy(base);c['operative']['malformed']={'kind':'not_a_kind','value':None,'modality':'not_a_modality','condition':[],'qualifications':False};c['record_audit']={'status':'reviewed','reviewed_refs':list(c['operative']),'unsupported_refs':[],'unknown_refs':[]}
probe('malformed-operative-facet',c,'Reject malformed operative facet independently of mapping coverage.',lambda x:not x['accepted'])
# Positive/negative semantic anchors against actual synthetic text.
for name in ('background_missing_not_participation_defect','split_mixed_paragraph_deadline_missing','same_endpoint_two_atomic_purposes','shared_contact_ambiguous_scope','conditional_advisory_positive','independent_view_permissions_no_group_required','glyph_and_reference_closure_unknown','unsupported_addition_separate_reviewed_audit'):
 c=copy.deepcopy(byid[name]);expected=next(f['expected'] for f in fixtures if f['id']==name)
 probe('anchor-'+name,c,expected,lambda x,expected=expected:x['accepted'] and all(x['result'][k]==val for k,val in expected.items() if k!='valid'))
# Binding and totality controls already specified; independent mutations must reject.
for name,mut in [('deleted-scope',lambda c:c['scopes'].pop('b')),('deleted-mapping',lambda c:c['mappings'].pop('d')),('stale-source',lambda c:c.update(source=c['source']+' A new hearing occurs.')),('stale-inventory',lambda c:c['inventory'][0].update(value='different')),('nonoperative-ref',lambda c:c['mappings']['d'].update(refs=['evidence/deadline']))]:
 c=copy.deepcopy(base);mut(c);probe(name,c,'Reject inconsistent supplied annotation.',lambda x:not x['accepted'])
assert verify() and sha(P/'READY.json')==readyhash
report={'protocol_ready_sha256':readyhash,'protocol_pins':len(ready['files']),'consulted_input_pins':len(ready['consulted_inputs']),'all_pins_unchanged_before_after':True,'owner_fixtures_passed':sum(x['pass'] for x in owner),'owner_fixtures_total':len(owner),'owner_tests_run':result.testsRun,'owner_tests_passed':result.wasSuccessful(),'independent_probes':len(observations),'independent_expectations_met':sum(x['expectation_met'] for x in observations),'counterexamples':[x for x in observations if not x['expectation_met']],'provider_calls':0,'credentials_read':False,'prior_files_edited':False,'synthetic_model_accuracy_claim':False}
(H/'RESULT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:val for k,val in report.items() if k!='counterexamples'}));print('Counterexamples:',[x['name'] for x in report['counterexamples']])
