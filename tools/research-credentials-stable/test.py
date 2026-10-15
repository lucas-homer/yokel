#!/usr/bin/env python3
"""Synthetic native integration. No real op, credentials, signing key or Keychain."""
import base64,copy,hashlib,importlib.util,json,os,signal,subprocess,tempfile,time
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

HERE=Path(__file__).resolve().parent;PYTHON=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12').resolve();ID='a'*26
spec=importlib.util.spec_from_file_location('stable_release',HERE/'release.py');release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)
checks=[]
def run(argv,want=0,env=None):
    r=subprocess.run(argv,capture_output=True,text=True,env=env,timeout=20)
    assert r.returncode==want,(argv[1:],r.returncode,r.stderr)
    assert 'ops_synthetic' not in r.stdout+r.stderr and 'synthetic-provider' not in r.stdout+r.stderr
    return r
def passed(name):checks.append({'name':name,'passed':True})
def stopped(pid):
    for _ in range(100):
        r=subprocess.run(['/bin/ps','-o','stat=','-p',str(pid)],capture_output=True,text=True)
        if r.returncode or r.stdout.strip().startswith('Z'):return
        time.sleep(.03)
    raise AssertionError('descendant still running')
with tempfile.TemporaryDirectory(prefix='yokel-stable-synthetic-') as temporary:
    root=Path(temporary).resolve();fixtures=root/'fixtures';fixtures.mkdir();keys=root/'keys';keys.mkdir(mode=0o700);registry=root/'jobs';registry.mkdir(mode=0o700);journal=root/'claims';journal.mkdir(mode=0o700)
    key=ec.generate_private_key(ec.SECP256R1());public=key.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
    keyfile=keys/'release-key.pem';keyfile.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()));keyfile.chmod(0o600)
    log=root/'fake-op-count';fake=root/'fake-op'
    fake.write_text('''#!/bin/sh
set -eu
[ "$OP_SERVICE_ACCOUNT_TOKEN" = ops_synthetic-only ]
[ "$OP_BIOMETRIC_UNLOCK_ENABLED" = false ] && [ "$OP_CACHE" = false ]
[ "${OP_CONNECT_HOST-unset}" = unset ] && [ "${OP_CONNECT_TOKEN-unset}" = unset ]
[ "${PYTHONPATH-unset}" = unset ] && [ "${DYLD_INSERT_LIBRARIES-unset}" = unset ]
printf 'called\\n' >> '''+str(log)+'''
if [ "$1" = user ]; then
  printf 'ID: aaaaaaaaaaaaaaaaaaaaaaaaaa\\nState: ACTIVE\\nType: SERVICE_ACCOUNT\\n'
  exit 0
fi
[ "$1" = run ] && [ "$2" = -- ]
if [ "${OPENROUTER_API_KEY-unset}" != unset ]; then export OPENROUTER_API_KEY=synthetic-provider-openrouter; fi
if [ "${TYPESAFE_API_KEY-unset}" != unset ]; then export TYPESAFE_API_KEY=synthetic-provider-typesafe; fi
shift 2
exec "$@"
''');fake.chmod(0o700)
    core=dict(schema_version='yokel.stable-core.v1',base_policy=dict(service_account_id=ID,vault_id=ID,op_path=str(fake),op_sha256=release.digest(fake),references={k:f'op://{ID}/{ID}/credential' for k in ('OPENROUTER_API_KEY','TYPESAFE_API_KEY')},jobs={}),public_key_base64=base64.b64encode(public).decode(),registry_dir=str(registry),journal_dir=str(journal),python_path=str(PYTHON),adapter_roots=[str(fixtures)],dependency_roots=[str(fixtures),str(PYTHON.parent.parent)],timeout_max_seconds=10)
    corefile=root/'core.json';corefile.write_bytes(release.encode(core));runner=root/'runner'
    compiled=subprocess.run([str(PYTHON),'-I','-S','-B',str(HERE/'build.py'),'--policy',str(corefile),'--output',str(runner),'--synthetic-tests'],capture_output=True,text=True)
    assert compiled.returncode==0,compiled.stderr
    binary=release.digest(runner);run([str(runner),'self-test']);passed('inherited-native-identity-environment-output-timeout-selftest')
    adapter_source='''import json,os,sys,time,subprocess
from pathlib import Path
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
assert sys.argv[1:]==['--live-initial']
settings=json.loads((Path(__file__).parent/'settings.json').read_bytes())
assert {k for k in os.environ if k.endswith('_API_KEY')}==set(settings['providers'])
assert 'OP_SERVICE_ACCOUNT_TOKEN' not in os.environ and 'OP_CONNECT_HOST' not in os.environ and 'PYTHONPATH' not in os.environ
if settings['mode']=='hang':
 child=subprocess.Popen(['/bin/sleep','20']);(Path(__file__).parent/'descendant.pid').write_text(str(child.pid));child.wait()
else:
 for k in settings['providers']:print(os.environ[k]);print(os.environ[k],file=sys.stderr)
'''
    def proposal(job,providers=('OPENROUTER_API_KEY',),mode='normal',timeout=5):
        folder=fixtures/job;folder.mkdir();adapter=folder/'adapter.py';adapter.write_text(adapter_source);settings=folder/'settings.json';settings.write_text(json.dumps({'mode':mode,'providers':list(providers)}));review=folder/'REVIEW.md';review.write_text('Synthetic review only. No independent authority.\n')
        return dict(schema_version='yokel.research-job.v1',job_id=job,scope_id='synthetic-authorized',project='yokel.docketclock.research',expires_unix=int(time.time())+3600,provider_variables=list(providers),job={'argv':[str(PYTHON),'-I','-S','-B',str(adapter),'--live-initial'],'files':{str(p):release.digest(p) for p in (PYTHON,adapter,settings,review)},'timeout_seconds':timeout},budget={'prior_nanousd':542976718,'reservation_nanousd':161920000,'ceiling_nanousd':2000000000},review={'path':str(review),'sha256':release.digest(review)})
    def raw_publish(m,raw=None,k=key):
        data=release.encode(m) if raw is None else raw
        from cryptography.hazmat.primitives import hashes
        for ext,value in (('.json',data),('.sig',k.sign(release.DOMAIN+data,ec.ECDSA(hashes.SHA256())))):
            p=registry/(m['job_id']+ext);p.write_bytes(value);p.chmod(0o600)
        return hashlib.sha256(data).hexdigest()
    noisy={'HOME':str(root),'PATH':'/synthetic','LANG':'en_US.UTF-8','OP_CONNECT_HOST':'synthetic','OP_CONNECT_TOKEN':'synthetic','PYTHONPATH':'/synthetic','OPENROUTER_API_KEY':'synthetic-inherited','TYPESAFE_API_KEY':'synthetic-inherited'}
    accepted=[]
    for job,providers in [('one-provider',('OPENROUTER_API_KEY',)),('two-providers',('OPENROUTER_API_KEY','TYPESAFE_API_KEY'))]:
        m=proposal(job,providers);loaded=release.read_key(core,keyfile);h=release.publish(core,m,loaded);run([str(runner),'check-job',job]);run([str(runner),'_test-auth-job',job],env=noisy);accepted.append({'job_id':job,'manifest_sha256':h,'executor_sha256':release.digest(runner)});passed(job+'-signed-fixed-grammar-subset-token-removal-output-suppression')
        run([str(runner),'_test-auth-job',job],1);passed(job+'-one-shot-replay')
    assert len({x['manifest_sha256'] for x in accepted})==2 and release.digest(runner)==binary
    run([str(runner),'enroll'],1);run([str(runner),'rotate-local'],1);run([str(runner),'identity'],1);passed('synthetic-binary-denies-keychain-enrollment-and-read')
    run([str(runner),'authorize-existing'],1);passed('authorize-existing-synthetic-rejected-before-any-keychain-api')
    run([str(runner),'_test-auth-smoke'],env=noisy);passed('synthetic-service-identity-and-core-smoke')
    m=proposal('zero-reserve-smoke');m['budget']['reservation_nanousd']=0;release.publish(core,m,key);run([str(runner),'check-job',m['job_id']]);run([str(runner),'_test-auth-job',m['job_id']]);passed('signed-zero-reservation-credential-smoke')
    m=proposal('synthetic-later-ceiling');m['budget']['ceiling_nanousd']=3000000000;release.publish(core,m,key);run([str(runner),'check-job',m['job_id']]);passed('signed-ceiling-change-does-not-rebuild-reader-synthetic-only')
    m=proposal('release-cli');proposalfile=root/'proposal.json';proposalfile.write_bytes(release.encode(m))
    bootstrap='import sys,runpy; sys.path.insert(0,'+repr(str(PYTHON.parent.parent/'lib/python3.12/site-packages'))+'); runpy.run_path('+repr(str(HERE/'release.py'))+',run_name="__main__")'
    output=run([str(PYTHON),'-I','-S','-B','-c',bootstrap,'--core',str(corefile),'--proposal',str(proposalfile),'--key-file',str(keyfile),'--executor',str(runner)])
    assert json.loads(output.stdout)['state']=='released';passed('protected-file-release-cli-and-native-noncredential-check')
    before=log.read_text()
    for name,change in [('project',lambda m:m.update(project='other')),('provider',lambda m:m.update(provider_variables=['LLAMA_CLOUD_API_KEY'])),('extra-argv',lambda m:m['job']['argv'].append('override')),('no-isolation',lambda m:m['job']['argv'].__setitem__(1,'-c')),('overspend',lambda m:m['budget'].update(reservation_nanousd=2000000000)),('boolean-budget',lambda m:m['budget'].update(prior_nanousd=True)),('expired',lambda m:m.update(expires_unix=0)),('key-override',lambda m:m.update(public_key='override')),('unpinned-adapter',lambda m:m['job']['files'].pop(m['job']['argv'][4]))]:
        m=proposal('reject-'+name);change(m);raw_publish(m);run([str(runner),'_test-auth-job',m['job_id']],1);passed(name+'-rejected-before-token-or-op')
    m=proposal('unsigned');raw_publish(m);(registry/'unsigned.sig').unlink();run([str(runner),'_test-auth-job','unsigned'],1);passed('unsigned-rejected')
    m=proposal('tampered');raw_publish(m);(registry/'tampered.json').write_bytes((registry/'tampered.json').read_bytes()+b' ');run([str(runner),'check-job','tampered'],1);passed('tamper-rejected')
    m=proposal('wrong-key');raw_publish(m,k=ec.generate_private_key(ec.SECP256R1()));run([str(runner),'check-job','wrong-key'],1);passed('wrong-key-rejected')
    m=proposal('duplicate');raw=release.encode(m);raw_publish(m,b'{"project":"yokel.docketclock.research",'+raw[1:]);run([str(runner),'check-job','duplicate'],1);passed('signed-duplicate-field-rejected')
    m=proposal('substituted');h=raw_publish(m);run([str(runner),'_test-check-boundary','substituted',h]);m['job']['timeout_seconds']=4;raw_publish(m);run([str(runner),'check-job','substituted']);run([str(runner),'_test-check-boundary','substituted',h],1);passed('validly-signed-cross-stage-substitution-rejected')
    m=proposal('drift');raw_publish(m);adapter=Path(m['job']['argv'][4]);adapter.write_text(adapter.read_text()+'\n# drift\n');run([str(runner),'_test-auth-job','drift'],1);passed('drifted-payload-rejected-before-token')
    assert log.read_text()==before;passed('all-invalid-job-controls-made-zero-fake-op-calls')
    m=proposal('timeout',mode='hang',timeout=1);release.publish(core,m,key);run([str(runner),'_test-auth-job','timeout'],1);stopped(int((fixtures/'timeout/descendant.pid').read_text()));passed('timeout-kills-job-and-descendant')
    m=proposal('cancelled',mode='hang',timeout=10);release.publish(core,m,key);p=subprocess.Popen([str(runner),'_test-auth-job','cancelled'],stdout=subprocess.PIPE,stderr=subprocess.PIPE);marker=fixtures/'cancelled/descendant.pid';deadline=time.monotonic()+5
    while not marker.exists() and time.monotonic()<deadline:time.sleep(.02)
    assert marker.exists();p.send_signal(signal.SIGTERM);stdout,stderr=p.communicate(timeout=5);assert p.returncode==1 and b'synthetic-provider' not in stdout+stderr;stopped(int(marker.read_text()));passed('cancellation-kills-job-and-descendant')
    keyfile.chmod(0o644)
    try:release.read_key(core,keyfile)
    except ValueError:passed('insecure-synthetic-signing-key-permissions-rejected')
    else:raise AssertionError('insecure key accepted')
    keyfile.chmod(0o600)
    invalid=proposal('invalid-release');invalid['budget']['reservation_nanousd']=2000000000
    try:release.publish(core,invalid,key)
    except ValueError:passed('release-denies-invalid-budget-before-publication')
    else:raise AssertionError('invalid release accepted')
    try:release.publish(core,m,key)
    except FileExistsError:passed('release-publication-never-overwrites')
    else:raise AssertionError('release overwrite accepted')
    assert release.digest(runner)==binary
    result={'schema_version':'stable.candidate-synthetic-tests.v1','state':'passed','checks':checks,'check_count':len(checks),'accepted_jobs':accepted,'executor_bytes_unchanged':True,'production_keys_generated':False,'keychain_access':False,'real_op_calls':0,'provider_calls':0,'production_ready':False,'keychain_continuity_tested':False}
    (HERE/'TEST-RESULT.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:result[k] for k in ('state','check_count','executor_bytes_unchanged','keychain_access','provider_calls','keychain_continuity_tested')}))
