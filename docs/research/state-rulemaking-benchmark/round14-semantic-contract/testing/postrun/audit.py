"""Local postrun integrity audit only: no network, credentials, signer or executor."""
import ast, hashlib, json, os, subprocess, sys, datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
RUNTIME=ROOT/'runtime'
sys.path.insert(0,str(RUNTIME))
import adapter as A
C=A.c; K=A.k

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_bytes())
def verify(root,items):
    for n,w in items.items():
        p=(root/n).resolve(); h=w['sha256'] if isinstance(w,dict) else w
        assert sha(p)==h, str(p)
        if isinstance(w,dict) and 'bytes' in w: assert p.stat().st_size==w['bytes']
    return len(items)

def main():
    run=ROOT/'execution/run'; frozen=load(ROOT/'execution/READY.json')
    counts={'execution_frozen_files':verify(run,frozen['files'])}
    raw=(run/'response.body').read_bytes(); body=(run/'content.body').read_text()
    response=load(run/'response.body'); content,meta=A.native(raw)
    assert content==(run/'content.body').read_bytes()
    source=(ROOT/'source/parsed-body.txt').read_text(); table=load(run/'span-table.json')
    checked=K.validate_response(body,meta['finish_reason'],source,table)
    compact=load(run/'validated.json'); expanded=load(run/'expanded.json')
    assert checked=={'compact':compact,'expanded':expanded}
    assert K.protocol().contract(expanded,source,table)==compact
    assert C.encode(compact)==(run/'validated.json').read_bytes()
    assert C.encode(expanded)==(run/'expanded.json').read_bytes()
    assert K.protocol().reconstruct(source,table)==source
    result=load(run/'result.json'); done=load(run/'completed.json'); ledger=load(run/'ledger.json'); intent=load(run/'intent.json'); request=load(run/'request.json')
    assert done['state']=='validated_frozen' and ledger['state']=='charge_recorded'
    counts['completed_attestation_files']=verify(run,done['files'])
    assert not os.path.lexists(run/'stop.json')
    assert result['request_sha256']==intent['request_sha256']==sha(run/'request.json')==sha(RUNTIME/'source-request.json')
    assert request==load(RUNTIME/'source-request.json')
    assert result['response_sha256']==sha(run/'response.body')==load(run/'status.json')['response_sha256']
    assert load(run/'status.json')['http_status']==200
    assert result['content_sha256']==sha(run/'content.body')
    assert result['compact_sha256']==sha(run/'validated.json')
    assert result['expanded_sha256']==sha(run/'expanded.json')
    assert result['source_sha256']==K.protocol().source_hash(source)
    assert result['span_table_sha256']==sha(run/'span-table.json')==C.digest(table)
    assert result['source_ready_sha256']==sha(ROOT/'source/READY.json')
    assert result['finish_reason']==meta['finish_reason']=='stop'
    assert result['usage']==meta['usage']==response['usage']
    assert result['budget_charge_nanousd']==meta['budget_charge_nanousd']==ledger['budget_charge_nanousd']==200000000
    assert ledger['prior_nanousd']==1705990718 and ledger['reserved_nanousd']==200000000 and ledger['attempts_claimed']==1
    assert ledger['cumulative_budget_charge_nanousd']==result['cumulative_budget_charge_nanousd']==1905990718<=ledger['ceiling_nanousd']==2000000000
    assert ledger['budget_charge_nanousd']==max(ledger['reserved_nanousd'],result['reported_cost_nanousd'],result['usage_rate_estimated_nanousd'])
    assert intent['automatic_retry'] is False and intent['output_cap']==8192 and intent['prior_nanousd']==ledger['prior_nanousd']
    assert result['model']=='openai/gpt-6.1-sol' and result['provider']=='OpenAI' and result['provider_identity_verified'] is True
    assert result['unit_count']==len(compact['u'])==len(expanded['units'])==110
    user=json.loads(request['messages'][1]['content'])
    assert set(user)=={'source_text','source_text_sha256','span_table','span_table_sha256'} and user['source_text']==source and user['span_table']==table
    counts['runtime_frozen_files']=verify(RUNTIME,load(RUNTIME/'READY.json')['files'])
    for filename in ['code-pins.json','input-pins.json','dependency-pins.json']:
        counts[filename]=verify(Path('/'),load(RUNTIME/filename)['files'])
    counts['reference_frozen_files']=verify(ROOT/'reference',load(ROOT/'reference/READY.json')['artifacts'])
    for directory in ['testing','testing/revised','testing/runtime','testing/execution-stop','testing/recovery-review']:
        counts[directory]=verify(ROOT/directory,load(ROOT/directory/'READY.json')['files'])
    stop=load(ROOT/'execution/STOP.json'); assert sha(ROOT/'execution/STOP.json')==load(ROOT/'testing/execution-stop/READY.json')['primary_stop_receipt_sha256']
    assert stop['native_runner_exit_code']==1 and stop['source_only_provider_request_dispatched'] is False
    core=load(ROOT.parent/'runner-stability-review/deployment/core.json'); native=[]
    signature_code="""import sys,json,base64
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
core=json.loads(Path(sys.argv[1]).read_bytes())
key=ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(),base64.b64decode(core['public_key_base64']))
key.verify(Path(sys.argv[3]).read_bytes(),b'yokel.research-job.v1\\0'+Path(sys.argv[2]).read_bytes(),ec.ECDSA(hashes.SHA256()))
print('public-key signature valid')
"""
    for job in ['round14-semantic-contract-initial','round14-semantic-contract-recovery']:
        manifest=Path(core['registry_dir'])/(job+'.json'); sig=manifest.with_suffix('.sig'); claim=Path(core['journal_dir'])/job
        m=load(manifest); raw_m=manifest.read_bytes()
        assert C.encode(m)==raw_m and claim.read_bytes().decode()==sha(manifest)
        verified=subprocess.run([str(A.PYTHON),'-I','-B','-c',signature_code,str(ROOT.parent/'runner-stability-review/deployment/core.json'),str(manifest),str(sig)],env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,timeout=30)
        assert verified.returncode==0,verified.stderr.decode()
        native.append({'job_id':job,'manifest_sha256':sha(manifest),'claim_sha256':sha(claim),'claim_matches_manifest':True,'public_key_signature_valid':True,'signature_sha256':sha(sig),'manifest_pins':verify(Path('/'),m['job']['files'])})
    assert native[0]['claim_sha256']==load(ROOT/'testing/execution-stop/READY.json')['files'].get('claim',{}).get('sha256',load(ROOT/'testing/execution-stop/AUDIT.json')['independently_verified']['claim_file_sha256'])
    assert native[1]['manifest_sha256']==load(ROOT/'recovery/RELEASE-RECEIPT.json')['manifest_sha256']
    output={'status':'PASSED_LOCAL_ACTUAL_RECEIPT_AUDIT','author':'Codex/GPT deterministic local verification; no Fable runtime approval','execution_READY_sha256':sha(ROOT/'execution/READY.json'),'counts':counts,'native_jobs':native,'roundtrip_exact':True,'raw_content_and_attestations_concordant':True,'source_only_request_input_verified':True,'model':result['model'],'provider':result['provider'],'finish_reason':'stop','unit_count':110,'completion_tokens':result['usage']['completion_tokens'],'reasoning_tokens':result['usage']['completion_tokens_details']['reasoning_tokens'],'reported_cost_usd':result['reported_cost_usd'],'reported_cost_nanousd':result['reported_cost_nanousd'],'rate_estimated_nanousd':result['usage_rate_estimated_nanousd'],'new_conservative_charge_nanousd':200000000,'prior_nanousd':1705990718,'cumulative_nanousd':1905990718,'ceiling_nanousd':2000000000,'invoice_verified':False,'initial_pre_dispatch_STOP_unchanged':True,'source_reference_unchanged':True,'research_provider_calls_by_audit':0,'claude_bridge_calls_by_audit':0,'credentials_read':False,'native_executor_invocations':0,'signer_invocations':0,'semantic_status':'pending_Fable_assessment','limits':'Integrity and receipt reconciliation only; provider billing is not independently invoiced; signed manifests/claim attestations plus one adapter execution are observed, not an external exhaustive network-traffic proof.','verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (HERE/'RESULT.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))
if __name__=='__main__':main()
