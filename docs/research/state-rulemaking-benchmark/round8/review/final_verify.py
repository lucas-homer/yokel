"""Independent R8 final review; writes only review receipts, uses synthetic sources/transports."""
import contextlib,copy,hashlib,importlib.util,io,json,sys,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent;R=HERE.parent

def guard(event,args):
    if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('network/process blocked')
    if event=='open' and isinstance(args[0],(str,bytes)):
        name=str(args[0]).lower()
        if '/.env' in name or '/library/keychains/' in name or '/.aws/' in name or Path(name).name in ('credentials','credentials.json'):raise RuntimeError('credential access blocked')
sys.addaudithook(guard)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(n,p):
    s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
c=load('r8_final_independent_helpers',R/'runtime/offline_checks.py');r=c.r
pins=r.code_pins();before={name:sha(Path(name)) for name in pins['code']}
log=io.StringIO();counts=[]
for directory,pattern in [(R/'runtime','offline_checks.py'),(R/'execution/service-account','test_adapter.py'),(R/'protocol','test_evaluate.py')]:
    with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        suite=unittest.TestLoader().discover(str(directory),pattern=pattern)
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    counts.append(dict(suite=str(directory.relative_to(R)),tests=result.testsRun,passed=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors)))
assert all(x['passed'] for x in counts)
checks=[]
for stage in ('inventory','stronger'):
    with tempfile.TemporaryDirectory() as temporary:
        root=Path(temporary);sources,manifest,freeze,auth,inv,verdict=c.fixture(root,documents=2);calls=[];normal=c.transport_for(inv,verdict,calls)
        def transport(provider,body,key):
            status,raw=normal(provider,body,key)
            if calls[-1]==stage:
                value=r.j.loads(raw);value['usage']['cost']=3;raw=r.j.encode(value)
            return status,raw
        with contextlib.redirect_stdout(log):out=r.run(manifest,sources,freeze,root/'run',live=True,authorization=auth,source_labels_freeze_sha256='a'*64,keys={'openrouter':'dummy-OR','jev':'dummy-jeV'},transport=transport)
        observed=r.j.loads(next((root/'run').glob('observed-*.json')).read_bytes());doc=observed['documents'][0]
        assert out['state']=='stopped_budget' and doc['runtime_gate']=='postresponse_budget_stop' and doc['inventory_sha256'] is not None
        assert observed['documents'][1]['runtime_gate']=='not_started' and r.audit_failure_receipts(observed,root/'run')
        assert calls==(['inventory'] if stage=='inventory' else ['inventory','jev','stronger'])
        if stage=='stronger':assert all(v['status']=='accepted_complete' for v in doc['arms'].values())
        count=len(calls)
        try:
            with contextlib.redirect_stdout(log):c.execute(root,(sources,manifest,freeze,auth,inv,verdict),calls)
        except r.Stop:pass
        else:raise AssertionError('budget latch resumed')
        assert len(calls)==count
        checks.append(dict(name='completed_'+stage+'_overrun_preserved',passed=True,gate=doc['runtime_gate'],arms={a:v['status'] for a,v in doc['arms'].items()},calls=calls,later_notice='not_started',resume_blocked=True))
with tempfile.TemporaryDirectory() as temporary:
    root=Path(temporary);data=c.fixture(root);calls=[];original=r.validate_observation
    def unavailable(value):raise ValueError('synthetic unavailable validator')
    r.validate_observation=unavailable
    try:
        with contextlib.redirect_stdout(log):c.execute(root,data,calls)
    except ValueError:pass
    else:raise AssertionError('unavailable validator ignored')
    finally:r.validate_observation=original
    assert calls==[];checks.append(dict(name='validator_unavailable_zero_dispatch',passed=True))
references=r.j.loads((R/'protocol/reuse-pins.json').read_bytes())['files']
assert all(str((R.parent/relative).resolve()) in pins['code'] for relative in references)
assert not any(Path(name).name in ('READY.json','implementation.json','offline-report.json','FINAL-VERIFICATION.json') for name in pins['code'])
assert r.code_pins()==pins
checks.append(dict(name='transitive_pins_complete_and_stable_without_generated_reports',passed=True))
with tempfile.TemporaryDirectory() as temporary:
    root=Path(temporary);data=c.fixture(root);calls=[]
    with contextlib.redirect_stdout(log):c.execute(root,data,calls,fail='jev')
    observed=r.j.loads(next((root/'run').glob('observed-*.json')).read_bytes());assert r.audit_failure_receipts(observed,root/'run')
    failure=observed['documents'][0]['failure'];op=next(folder for folder in (root/'run/operations').iterdir() if r.j.loads((folder/'identity.json').read_bytes())['kind']=='jev')
    cases=[]
    for name in ('stop.json','request.json'):
        path=op/name;original=path.read_bytes();path.write_bytes(original+b' ')
        try:r.audit_failure_receipts(observed,root/'run')
        except r.Stop:cases.append(name)
        else:raise AssertionError('referenced bytes tamper accepted: '+name)
        finally:path.write_bytes(original)
    bad=copy.deepcopy(observed);bad['documents'][0]['failure']['evidence_sha256']='0'*64
    try:r.audit_failure_receipts(bad,root/'run')
    except r.Stop:cases.append('receipt_hash')
    else:raise AssertionError('receipt hash tamper accepted')
    bad=copy.deepcopy(observed);bad['documents'][0]['failure']['operation_id']='doc-000000000002-jev'
    try:r.audit_failure_receipts(bad,root/'run')
    except r.Stop:cases.append('operation_identity')
    else:raise AssertionError('operation identity tamper accepted')
    checks.append(dict(name='receipt_to_ledger_tamper_rejected',passed=True,cases=cases))
baseline=R.parent/'round7/prior-round-baseline.json';files=json.loads(baseline.read_text())['files']
mismatches=[name for name,want in files.items() if sha(R.parent/name)!=want];assert not mismatches
changed=[name for name,want in before.items() if sha(Path(name))!=want];assert not changed
(HERE/'final-test-output.txt').write_text(log.getvalue())
receipt=dict(schema_version='round8.independent_final_review.v1',disposition='approved_for_primary_precollection_freeze',owner_tests=counts,independent_checks=checks,code_hashes=before,files_changed_during_verification=changed,prior_baseline=dict(sha256=sha(baseline),files_checked=len(files),mismatches=mismatches),provider_calls=0,fresh_sources_read=False,credentials_read=False,guard='Python audit hook blocks socket/process/credential-file access; explicit synthetic transports',log_sha256=sha(HERE/'final-test-output.txt'),production_eligible=False,action_ready=False)
(HERE/'FINAL-VERIFICATION.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'disposition':receipt['disposition'],'tests':sum(x['tests'] for x in counts),'independent_checks':len(checks),'prior_files_unchanged':len(files),'code_hashes':len(before)}))
