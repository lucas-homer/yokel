"""Read-only postrun audit of the primary-frozen single exact-ID probe."""
import base64,hashlib,importlib.util,json,math,sys
from decimal import Decimal,ROUND_CEILING
from pathlib import Path
HERE=Path(__file__).resolve().parent;REVIEW=HERE.parent;ROOT=REVIEW.parent;BENCH=ROOT.parent
FROZEN=ROOT/'execution/freeze.json';RUN=ROOT/'execution/run'
EXPECTED_FREEZE='3d02ea5ef6395960125ffeada047d64bf1a0658939d59fc295c6ca273f860143'
EXPECTED_MANIFEST='c2d7cf16857124c921c6472bd877b9301624d3a6c4564798465304ee1c11cbbc'
EXPECTED_EXE='821f91b67f4c0c2d2a7f333e1381fab9aec1f9d8a9b8be8c34a0ee135494547e'
checks=[]
def guard(event,args):
 if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise AssertionError('offline audit forbids network/process')
 if event=='open' and isinstance(args[0],(str,bytes)):
  p=Path(args[0]).resolve();mode=args[1];flags=args[2]
  if any(x in p.parts for x in ('.ssh','.aws','Keychains')) or p.name=='.env' or p.suffix in ('.pem','.key'):raise AssertionError('private credential/signing file denied')
  writing=(isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags & 3 in (1,2))
  if writing and not p.is_relative_to(HERE):raise AssertionError('postrun-only writes')
sys.addaudithook(guard)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def enc(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def pairs(rows):
 out={}
 for k,v in rows:
  if k in out:raise ValueError('duplicate raw member')
  out[k]=v
 return out
def strict(raw,decimal=False):
 def floating(v):
  n=float(v)
  if not math.isfinite(n):raise ValueError('nonfinite')
  return Decimal(v) if decimal else n
 return json.loads(raw,object_pairs_hook=pairs,parse_float=floating,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite')))
def read(p):return strict(Path(p).read_bytes())
def check(name,ok,detail=None):
 checks.append(dict(name=name,passed=bool(ok),detail=detail))
 if not ok:raise AssertionError(name)
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
check('Primary freeze exact bytes',sha(FROZEN)==EXPECTED_FREEZE)
freeze=read(FROZEN);paths=[]
for row in freeze['files']:
 p=(ROOT/row['path']).resolve();paths.append(p)
 check('Execution artifact '+row['path'],p.is_relative_to(ROOT) and sha(p)==row['sha256'] and p.stat().st_size==row['bytes'])
check('Six distinct frozen execution artifacts',len(paths)==len(set(paths))==6)
check('Execution run has exactly frozen artifacts',set(RUN.iterdir())==set(paths))
prior_review=read(REVIEW/'READY.json')
check('Signed preflight review READY unchanged',sha(REVIEW/'READY.json')=='9a009653cefc6ee9bec499fb3812224470182ed455599e4a0ae91b59a13056ef')
check('Every signed review artifact unchanged',all(sha(REVIEW/name)==want for name,want in prior_review['files'].items()),{'files':len(prior_review['files'])})
pre=read(REVIEW/'FINAL-REVIEW.json')
check('Stopped runtime READY unchanged',sha(ROOT/'runtime/READY.json')==pre['runtime_ready_sha256'])
check('All reviewed runtime files unchanged',all(sha(p)==want for p,want in pre['runtime_files'].items()))
core=read(BENCH/'runner-stability-review/deployment/core.json');registry=Path(core['registry_dir']);job='round9-exact-id-initial'
manifest_path=registry/(job+'.json');sig_path=registry/(job+'.sig');raw_manifest=manifest_path.read_bytes();manifest=strict(raw_manifest)
check('Signed manifest exact canonical bytes',sha(manifest_path)==EXPECTED_MANIFEST and enc(manifest)==raw_manifest)
check('Manifest matches reviewed unsigned proposal',manifest==read(ROOT/'runtime/UNSIGNED-JOB-PROPOSAL.json'))
check('Release receipt binds exact manifest',read(ROOT/'release-receipt.json')['manifest_sha256']==EXPECTED_MANIFEST and read(ROOT/'primary-release-verification.json')['manifest_canonical_sha256']==EXPECTED_MANIFEST)
check('Only injected OpenRouter variable and fixed adapter argv',manifest['provider_variables']==['OPENROUTER_API_KEY'] and manifest['job']['argv']==[core['python_path'],'-I','-S','-B',str(ROOT/'runtime/adapter.py'),'--live-initial'])
check('Manifest budget matches authorization',manifest['budget']==dict(prior_nanousd=696390718,reservation_nanousd=161920000,ceiling_nanousd=2000000000))
files=manifest['job']['files'];bad=[p for p,want in files.items() if sha(p)!=want]
check('All signed release file pins unchanged',len(files)==6672 and not bad,{'files':len(files),'mismatches':bad})
check('Final review path and digest signed',manifest['review']['path']==str(REVIEW/'FINAL-REVIEW.md') and manifest['review']['sha256']==sha(REVIEW/'FINAL-REVIEW.md'))
# Public-only ECDSA verification; never import or invoke the release signer/runner.
site=Path(core['python_path']).parent.parent/'lib/python3.12/site-packages';sys.path.insert(0,str(site))
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
public=ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(),base64.b64decode(core['public_key_base64'],validate=True))
public.verify(sig_path.read_bytes(),b'yokel.research-job.v1\0'+raw_manifest,ec.ECDSA(hashes.SHA256()))
check('Public-key signature verifies',True)
claim=Path(core['journal_dir'])/job
check('Native consumed job claim binds exact manifest',claim.read_text()==EXPECTED_MANIFEST)
exe=Path('/Users/home/.local/libexec/yokel/research-credentials-stable-v1')
check('Installed executor unchanged',sha(exe)==EXPECTED_EXE)
deployment=read(BENCH/'runner-stability-review/deployment/FREEZE.json')['files']
check('Deployment provenance unchanged',all(sha(p)==want for p,want in deployment.items()),{'files':len(deployment)})
baseline=read(ROOT/'prior-baseline.json')['files'];bad=[]
for row in baseline:
 p=(BENCH/row['path']).resolve()
 if not p.is_relative_to(BENCH) or sha(p)!=row['sha256'] or p.stat().st_size!=row['bytes']:bad.append(row['path'])
check('Frozen prior baseline unchanged',len(baseline)==5055 and not bad,{'files':len(baseline),'mismatches':bad})
request_raw=(RUN/'request.json').read_bytes();request=strict(request_raw);intent=read(RUN/'intent.json');native_raw=(RUN/'response.body').read_bytes();native=strict(native_raw);status=read(RUN/'status.json');result=read(RUN/'result.json');completed=read(RUN/'completed.json')
fixture=read(BENCH/'round9-exact-id-completeness/protocol/wi70-offline-request.fixture.json')
check('Exact canonical frozen provider request',request==fixture and request_raw==enc(request) and sha(RUN/'request.json')=='093b205a1c01bc0f2f2d6640944d3e0854e88ba34ffc0ad4c2b5f9f4e4b812f5')
check('Unchanged input/output guards',len(request_raw)==38432 and len(request_raw)+1024==39456<=40000 and request['max_tokens']==intent['output_cap']==8192 and intent['input_guard']==40000)
check('Fixed model/reasoning/no-fallback routing',request['model']=='openai/gpt-6.1-sol' and request['reasoning']=={'effort':'low'} and request['provider']=={'only':['openai'],'order':['openai'],'allow_fallbacks':False,'require_parameters':True,'max_price':{'prompt':2,'completion':10}})
check('Exactly one stronger intent with no retry',len(list(RUN.glob('intent.json')))==1 and intent['operation_id']=='doc-92211b8c7ba0-stronger-exact-id' and intent['kind']=='stronger' and intent['automatic_retry'] is False and intent['request_sha256']==sha(RUN/'request.json'))
check('HTTP 200 binds exact raw response',status['http_status']==200 and status['response_sha256']==sha(RUN/'response.body'))
check('Native model/provider identity',native['model']=='openai/gpt-6.1-sol' and native['provider']=='OpenAI')
check('One completed native choice',len(native['choices'])==1 and native['choices'][0]['finish_reason']=='stop' and not native.get('error') and not native['choices'][0].get('error'))
choice=native['choices'][0];message=choice['message'];check('No refusal or tool call',not message.get('refusal') and not message.get('tool_calls'))
wire=strict(message['content']);assessment=wire['assessments'];expected=request['response_format']['json_schema']['schema']['properties']['assessments']['required']
check('Exactly all 70 IDs and no coverage assessment',isinstance(assessment,dict) and len(assessment)==len(expected)==70 and set(assessment)==set(expected) and 'coverage' not in assessment)
a=load('postrun_review_adapter',ROOT/'runtime/adapter.py');planned,frozen_request,frozen_response,prior=a.preflight()
a.verify_live_bindings()
check('Actual late binding and authorization verification',True)
rebuilt=a.parse_native(native_raw,frozen_request,frozen_response)
check('Reparsed native result equals retained result',rebuilt==result)
checked=frozen_response.validate_response(message['content'],frozen_request.ASSEMBLED['source'],frozen_request.ASSEMBLED)
check('Frozen host validator reproduces exact retained validation',checked==result['structural_validation'] and checked['structural_valid'] is True and checked['errors']==[])
legacy=checked['legacy_verdict'];check('Lossless keyed normalization',len(legacy['assessments'])==70 and {row['item_id']:{k:v for k,v in row.items() if k!='item_id'} for row in legacy['assessments']}==assessment)
check('Global sections preserved',all(legacy[k]==v for k,v in wire.items() if k not in ('schema_version','assessments')))
usage=strict(native_raw,decimal=True)['usage'];reported=usage['cost'];rate=Decimal(usage['prompt_tokens'])*Decimal('.000002')+Decimal(usage['completion_tokens'])*Decimal('.000010')
reported_nano=int((reported*Decimal(1000000000)).to_integral_value(rounding=ROUND_CEILING));rate_nano=usage['prompt_tokens']*2000+usage['completion_tokens']*10000
charge=max(161920000,reported_nano,rate_nano);cumulative=696390718+charge
check('Independent conservative cost accounting',reported==Decimal('.0826585') and charge==161920000 and cumulative==858310718 and result['new_budget_charge_nanousd']==charge and result['budget_charge_nanousd']==cumulative)
check('Rate estimate matches retained value',abs(Decimal(str(result['usage_rate_estimated_usd']))-rate)<Decimal('.000000000001'))
check('Completion receipt accurately reports parsed result',completed==dict(state='completed',structural_valid=True,model_completeness_label=wire['completeness']['label'],independent_audit_agreement='unverified',semantic_status='unverified',production_eligible=False,action_ready=False))
check('Model incomplete remains separate from semantic audit',result['model_completeness_label']==wire['completeness']['label']=='incomplete' and result['semantic_status']=='unverified' and result['independent_audit_agreement']=='unverified' and result['production_eligible'] is False and result['action_ready'] is False)
check('No failure stop artifact',not (RUN/'stop.json').exists())
check('Execution freeze still unchanged after audit',sha(FROZEN)==EXPECTED_FREEZE and all(sha(ROOT/row['path'])==row['sha256'] for row in freeze['files']))
report=dict(schema_version='round9-live-exact-id.postrun-operational-audit.v1',state='passed',checks=checks,check_count=len(checks),freeze_sha256=EXPECTED_FREEZE,manifest_sha256=EXPECTED_MANIFEST,signature_verified=True,native_claim_verified=True,request_sha256=sha(RUN/'request.json'),response_sha256=sha(RUN/'response.body'),http_status=status['http_status'],provider=native['provider'],model=native['model'],finish_reason=choice['finish_reason'],native_finish_reason=choice.get('native_finish_reason'),structural_valid=True,expected_id_count=70,returned_id_count=len(assessment),model_completeness_label=wire['completeness']['label'],semantic_status='unverified',independent_audit_agreement='unverified',costs={'reported_usd':str(reported),'usage_rate_estimated_usd':str(rate),'prior_nanousd':696390718,'reserved_nanousd':161920000,'new_conservative_charge_nanousd':charge,'cumulative_conservative_nanousd':cumulative,'ceiling_nanousd':2000000000,'invoice_verified':False},usage_tokens={k:usage[k] for k in ('prompt_tokens','completion_tokens','total_tokens')},retained_attempts=1,provider_calls_by_auditor=0,credentials_read=False,runner_invoked=False,production_eligible=False,action_ready=False,limitations=['One retained intent/response plus reviewed exclusive claim and signed native consumed job support one attempt; no independent network capture exists.','A valid schema response supports compatibility for this single observed provider call, not general compatibility.','Source semantic correctness is outside this operational audit; model incomplete is an assertion, not an audit conclusion.','Native runner exit 0/no prompts are primary observations; retained completion is independently checked.'])
(HERE/'RESULT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('checks','limitations')}))
