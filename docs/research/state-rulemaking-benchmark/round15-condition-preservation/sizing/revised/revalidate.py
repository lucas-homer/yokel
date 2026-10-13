"""Small exact R15.1 sizing revalidation; no providers, runtime changes or old writes."""
import ast,copy,hashlib,importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;SIZING=HERE.parent;ROUND=SIZING.parent;BENCH=ROUND.parent;OLD=ROUND/'protocol';NEW=ROUND/'protocol-revised'
sys.path.insert(0,str(SIZING))
from measure_baseline import freeze_check
from measure_candidate import old_checker,schema_inventory
READY_SHA='dd2bb510254e198589ed50caa6f9a171194a0971c11ae92bde996006267f1f50'
def enc(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def load(directory,name):
    spec=importlib.util.spec_from_file_location(name,directory/'compact.py');k=importlib.util.module_from_spec(spec);spec.loader.exec_module(k);return k

def measure():
    r14count=freeze_check();prior=read(SIZING/'CHECKS.json')
    for name,want in prior['files'].items():assert h(SIZING/name)==want['sha256'] and (SIZING/name).stat().st_size==want['bytes']
    assert h(NEW/'READY.json')==READY_SHA
    for directory in (OLD,NEW):
        for name,want in read(directory/'READY.json')['sha256'].items():assert h(directory/name)==want
    oldready=read(NEW/'READY.json')['original_ready_sha256'];assert h(OLD/'READY.json')==oldready
    oldast=ast.parse((OLD/'compact.py').read_bytes());newast=ast.parse((NEW/'compact.py').read_bytes())
    def functions(tree):return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
    of,nf=functions(oldast),functions(newast);assert of.keys()==nf.keys();changed=sorted(name for name in of if of[name]!=nf[name]);assert changed==['contract','validate'],changed
    def rest(tree):
        keep=[]
        for node in tree.body:
            if isinstance(node,ast.FunctionDef) and node.name in changed:continue
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'VERSION','SPAN_VERSION','EXPANDED_VERSION'} for t in node.targets):continue
            keep.append(node)
        return ast.dump(ast.Module(body=keep,type_ignores=[]),include_attributes=False)
    assert rest(oldast)==rest(newast),'unexpected shape/constants/schema/build change'
    assert (OLD/'stage-a.system.txt').read_text().replace('r15.0','r15.1')==(NEW/'stage-a.system.txt').read_text()
    assert (OLD/'request-settings.json').read_bytes()==(NEW/'request-settings.json').read_bytes()
    assert (OLD/'bound-policy.json').read_bytes()==(NEW/'bound-policy.json').read_bytes()
    # Verify unchanged validate prefix/suffix around the graph walk, and no other inverse edits.
    def validator_regions(tree):
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='validate')
        start=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='depths' for t in n.targets))
        end=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='reached' for t in n.targets))
        return ast.dump(ast.Module(body=fn.body[:start],type_ignores=[])),ast.dump(ast.Module(body=fn.body[end:],type_ignores=[]))
    assert validator_regions(oldast)==validator_regions(newast)
    oldk=load(OLD,'r15_revision_original_protocol');k=load(NEW,'r15_revision_exact_protocol');assert oldk.VERSION=='r15.0' and k.VERSION=='r15.1'
    source_path=BENCH/'round14-semantic-contract/source/parsed-body.txt';source=source_path.read_bytes().decode();oldplan=oldk.build(source);plan=k.build(source)
    def translate_schema(schema,source,table):
        out=copy.deepcopy(schema);out['properties']['v']['enum']=[k.VERSION];out['properties']['h']['enum']=[k.source_hash(source)];out['properties']['t']['enum']=[k.digest(table)];return out
    assert translate_schema(oldk.schema(source,oldplan['table']),source,plan['table'])==k.schema(source,plan['table'])
    checker=old_checker();schema=plan['body']['response_format']['json_schema']['schema'];inventory=schema_inventory(schema)
    try:checker['check_schema'](schema);accepted=True
    except checker['Denied']:accepted=False
    assert not accepted
    original=read(SIZING/'CANDIDATE.json');original_rows={r['id']:r for r in original['profiles']};profiles=read(SIZING/'authored-profiles.json')['profiles'];paired=[];controls=[]
    for name in ('paired-opaque-complete-clause','paired-typed-complete-clause'):
        p=next(p for p in profiles if p['id']==name);src=p['source'];wire=copy.deepcopy(p['wire']);table=k.span_table(src);wire.update(v=k.VERSION,h=k.source_hash(src),t=k.digest(table))
        restored=copy.deepcopy(wire);restored.update(v=oldk.VERSION,h=p['wire']['h'],t=p['wire']['t']);assert restored==p['wire']
        raw=k.canonical(wire);checked=k.validate_response(raw.decode(),'stop',src,table);expanded=checked['expanded'];inverse=k.contract(expanded,src,table);assert inverse==wire and k.canonical(inverse)==raw
        oldchecked=oldk.validate_response(oldk.canonical(p['wire']).decode(),'stop',src,oldk.span_table(src));normalized=copy.deepcopy(expanded);normalized['schema_version']=oldk.EXPANDED_VERSION;normalized['span_table_sha256']=oldchecked['expanded']['span_table_sha256'];assert normalized==oldchecked['expanded']
        for u,v in zip(inverse['u'],expanded['units']):assert u['d'] is not v['required_unit_ids'] and u['b'] is not v['relationship_member_ids']
        for n,e in zip(inverse['g'],expanded['nodes']):assert n['a'] is not e['args']
        pairplan=k.build(src);oldpairplan=oldk.build(src);assert translate_schema(oldk.schema(src,oldpairplan['table']),src,pairplan['table'])==k.schema(src,pairplan['table'])
        row={'id':name,'label':'Translated authored exact-clause sizing control; not model output/semantic performance','source_sha256':k.source_hash(src),'wire_sha256':k.digest(wire),'bytes':len(raw),'original_bytes':original_rows[name]['R15_compact_bytes'],'byte_delta':len(raw)-original_rows[name]['R15_compact_bytes'],'guarded_request_bytes':pairplan['guarded_bytes'],'guarded_request_delta':pairplan['guarded_bytes']-original_rows[name]['guarded_request_bytes'],'request_sha256':pairplan['request_sha256'],'inverse_exact':True,'expanded_equal_after_only_version_hash_translation':True,'inverse_lists_detached':True}
        assert row['byte_delta']==row['guarded_request_delta']==0;paired.append(row);controls.append({'id':name,'source':src,'wire':wire})
    assert paired[0]['source_sha256']==paired[1]['source_sha256']
    # One focused behavioural control, not the original 19-profile matrix.
    deep=copy.deepcopy(controls[0]);deep['id']='authored-399-node-chain-recursion-limit600';leaf=copy.deepcopy(deep['wire']['g'][0]);leaf['i']='c399'
    deep['wire']['g']=[dict(i=f'c{i}',o='NOT',a=[f'c{i+1}'],x=[],g='',q=0,r='') for i in range(1,399)]+[leaf]
    old_limit=sys.getrecursionlimit()
    try:
        sys.setrecursionlimit(600)
        try:k.validate_response(k.canonical(deep['wire']).decode(),'stop',deep['source'],k.span_table(deep['source']));raise AssertionError('depth399 accepted')
        except ValueError as exc:assert str(exc)=='graph_depth';deep_outcome={'recursion_limit':600,'nodes':399,'expected_depth_nodes':399,'error_type':'ValueError','error_code':str(exc),'partial_expansion_emitted':False,'old_error_not_retested':'Earlier Opus/GPT hardening evidence reports RecursionError; this small check verifies only revised controlled stop.'}
    finally:sys.setrecursionlimit(old_limit)
    controls.append(deep)
    pins=[HERE/'revalidate.py',SIZING/'CANDIDATE.json',SIZING/'CANDIDATE.md',SIZING/'CHECKS.json',SIZING/'BASELINE.json',SIZING/'BASELINE.md',SIZING/'measure_baseline.py',SIZING/'measure_candidate.py',SIZING/'profile_recipe.py',SIZING/'authored-profiles.json',SIZING/'exposed-R14-input-request.json',ROUND/'primary/R14-FREEZE.json',source_path,OLD/'READY.json',NEW/'READY.json']+[NEW/name for name in read(NEW/'READY.json')['sha256']]
    original_input=original['exposed_R14_source_input_overhead_only'];public={'label':'Same outcome-exposed7208-byte R14 source; request sizing only, no reference/output migration or provider experiment','source_sha256':k.source_hash(source),'source_bytes':len(source.encode()),'span_count':len(plan['table']['rows']),'full_request_bytes':plan['body_bytes'],'guarded_request_bytes':plan['guarded_bytes'],'guard_max_bytes':40000,'residual_guard_bytes':40000-plan['guarded_bytes'],'original_R15_guarded_bytes':original_input['guarded_request_bytes'],'guarded_byte_delta':plan['guarded_bytes']-original_input['guarded_request_bytes'],'schema_bytes':len(k.canonical(schema)),'schema_byte_delta':len(k.canonical(schema))-original_input['schema_bytes'],'request_sha256':plan['request_sha256'],'prior_request_sha256':original_input['full_request_sha256'],'schema_equal_after_only_version_hash_translation':True,'source_text_and_span_rows_unchanged':plan['table']['rows']==oldplan['table']['rows']}
    assert public['guarded_byte_delta']==public['schema_byte_delta']==0
    report={'schema_version':'round15.revised-small-sizing.v1','status':'OFFLINE_SMALL_REVALIDATION_NOT_RELEASED','protocol_ready_sha256':READY_SHA,'protocol_version':k.VERSION,'span_version':k.SPAN_VERSION,'expanded_version':k.EXPANDED_VERSION,'source_pins':{str(p.relative_to(BENCH)):{'sha256':h(p),'bytes':p.stat().st_size} for p in sorted(set(pins))},'actual_diff':{'changed_functions':changed,'all_other_functions_constants_schema_build_AST_unchanged_except_three_version_constants':True,'validate_prefix_suffix_unchanged_except_graph_walk':True,'inverse_delta':'deepcopy unit d/b and node a lists; wire unchanged','prompt_delta':'only r15.0 -> r15.1 envelope version','settings_and_bound_policy_unchanged':True,'full_matrix_rerun_needed_for_wire_shape_change':False,'full_original_matrix_rerun':False},'public_R14_source_request':public,'paired_authored_controls':paired,'typed_minus_opaque_bytes':paired[1]['bytes']-paired[0]['bytes'],'typed_over_opaque_fraction':paired[1]['bytes']/paired[0]['bytes']-1,'focused_behavioural_control':deep_outcome,'compatibility':{'actual_source_bound_schema_old_checker_admitted':accepted,'schema_inventory':inventory,'provider_structured_schema_support':'UNVERIFIED_NO_PROVIDER_CALL','minimal_new_runtime_support_required':['$schema dialect metadata','positional prefixItems and Boolean items=false closure','anyOf branch semantics','pattern constraints','same strict keyword/resource/type checks'],'alternative':'A separately reviewed object-fragment wire/schema redesign would require new codecs, pins, independent equivalence/negative checks and complete sizing. Do not assume provider support for either route.','runtime_adapter_or_native_runner_changed':False},'budget':original['budget'],'observed_tokens':'Only R14 observed7231/8192; no R15/R15.1 model or tokenizer measurement','limits':['Authored translated controls do not establish semantic equivalence, source completeness, model compression, accuracy or future output fit.','Wire/schema shapes are checked unchanged after version/hash translation; behavioural hardening is a controlled host stop and detached inverse lists, not improved extraction.','Complete source/request/controls retained; no clipping, narrowing, retry, fallback, signing or budget changes.'],'verification':{'new_READY_files_verified':len(read(NEW/'READY.json')['sha256']),'old_READY_files_verified':len(read(OLD/'READY.json')['sha256']),'original_sizing_manifest_files_verified':len(prior['files']),'original_candidate_sha256':h(SIZING/'CANDIDATE.json'),'R14_freeze_files_verified':r14count,'paired_inverses_exact':True,'provider_calls':0,'credentials_read':False,'signer_executor_invoked':False,'prior_artifacts_changed':False,'production_eligible':False,'action_ready':False}}
    assert freeze_check()==r14count
    for name,want in prior['files'].items():assert h(SIZING/name)==want['sha256']
    return report,{'label':'Authored translated pair and focused chain control, not model outputs','controls':controls},plan['body']
def markdown(m):
    q=m['public_R14_source_request'];pairs=m['paired_authored_controls'];rows='\n'.join(f"| {r['id']} | {r['bytes']} | {r['byte_delta']:+d} | {r['guarded_request_bytes']} | {r['guarded_request_delta']:+d} |" for r in pairs)
    return f'''# R15.1 small sizing revalidation

Pinned revised READY `{m['protocol_ready_sha256']}` ({m['verification']['new_READY_files_verified']} artifact pins; primary protocol evidence reports31 tests). All {m['verification']['old_READY_files_verified']} original protocol pins, {m['verification']['original_sizing_manifest_files_verified']} original sizing-manifest files and {m['verification']['R14_freeze_files_verified']} frozen R14 files verify unchanged. Original CANDIDATE SHA256 remains `{m['verification']['original_candidate_sha256']}`.

The actual compact.py AST diff changes only validate/contract and three version constants. validate prefix/suffix is unchanged around its recursive-to-iterative graph walk; contract deep-copies unit d/b and node a. All other functions/constants/schema/build AST are identical. Prompt changes only the envelope version; settings/bound-policy bytes are identical. Full source-bound schemas and paired wire/expanded objects match after only version/hash translation. No wire-shape change was found, so the19-profile original matrix was not rerun. This is host behavioural revalidation, not model extraction or semantic improvement.

## Exact request and paired bytes

Same outcome-exposed public R14 source: {q['source_bytes']} bytes/{q['span_count']} spans, with all text and row ranges unchanged. Exact revised schema={q['schema_bytes']} bytes; full request={q['full_request_bytes']} plus1024={q['guarded_request_bytes']} guarded bytes. Delta from R15.0: request {q['guarded_byte_delta']:+d}, schema {q['schema_byte_delta']:+d}; residual under40000={q['residual_guard_bytes']}. New request SHA256 `{q['request_sha256']}`; prior `{q['prior_request_sha256']}`. Hash changes reflect explicit versions/bindings; byte sizes stay equal. source-request.json preserves the entire source-only request. This is exposed-input sizing, not a new performance test.

| Translated authored pair | Compact bytes | Delta from R15.0 | Guarded request bytes | Delta |
| --- | ---: | ---: | ---: | ---: |
{rows}

Typed minus opaque remains **{m['typed_minus_opaque_bytes']} bytes ({100*m['typed_over_opaque_fraction']:.2f}% more)**. Both share the same complete fictional clause/source; typed grouping is authored interpretation, while opaque representation defers it. Exact imported inverse succeeds and expanded fields/evidence match after only version/hash translation. New inverse unit d/b and node a lists are detached from expanded lists. These are labelled authored controls, not model output, semantic-equivalence proof, compression, accuracy or future-fit claims.

## Controlled behavioural stop

One complete399-node authored chain at Python recursion limit600 rejects with **ValueError graph_depth**, with no partial expansion. Prior RecursionError was reported by the separate hardening evidence and is not re-tested here. The complete chain object is retained in authored-controls.json. No cap relaxation, source narrowing, partial-output repair or extra model call follows this stop.

## Compatibility and limits

The unchanged R14 runtime checker still rejects the actual source-bound revised schema. Unsupported forms remain $schema/prefixItems/anyOf/pattern and Boolean items=false; positional tuple/union/pattern semantics require a new reviewed runtime checker. An alternative object-fragment wire redesign would need new codecs/pins, independent equivalence/negative checks and renewed complete sizing. Neither route has demonstrated provider compatibility, and no runtime adapter/native runner/binding changes occurred.

Only R14 observed7231/8192 completion tokens are known; R15.1 model/output-token use is unmeasured. Guard admission does not establish full-output fit, condition completeness or semantic validity. The remaining conservative$0.094009282 still cannot fit an unchanged$0.20 reserve; no paid release or budget change is authorized.

## Read-only reproduction

```sh
/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12 -I -S -B /Users/home/.codex/worktrees/e8f4/yokel/docs/research/state-rulemaking-benchmark/round15-condition-preservation/sizing/revised/revalidate.py
```

Default mode rechecks exact pins/diff/controls/request without writes. --record creates revised artifacts exclusively and refuses existing files. No credentials, provider calls, signer/executor invocation or prior writes. production_eligible/action_ready=false.
'''
def main():
    if sys.argv[1:] not in ([],['--record']):raise SystemExit('no args verify; --record once')
    names=['CANDIDATE.json','CANDIDATE.md','authored-controls.json','source-request.json'];paths=[HERE/n for n in names]
    if sys.argv[1:]==['--record'] and any(p.exists() for p in paths):raise SystemExit('preserve revised artifacts')
    report,controls,body=measure();report['authored_controls_sha256']=hashlib.sha256(enc(controls)).hexdigest();doc=markdown(report)
    if sys.argv[1:]==['--record']:
        with paths[0].open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
        with paths[1].open('x') as f:f.write(doc)
        with paths[2].open('xb') as f:f.write(enc(controls))
        with paths[3].open('xb') as f:f.write(enc(body))
    else:assert read(paths[0])==report and paths[1].read_text()==doc and paths[2].read_bytes()==enc(controls) and paths[3].read_bytes()==enc(body),'recorded revised sizing differs'
    assert h(paths[2])==report['authored_controls_sha256'] and h(paths[3])==report['public_R14_source_request']['request_sha256']
    print(json.dumps({'passed':True,'protocol_ready_sha256':READY_SHA,'guarded_request_bytes':report['public_R14_source_request']['guarded_request_bytes'],'request_byte_delta':report['public_R14_source_request']['guarded_byte_delta'],'opaque_bytes':report['paired_authored_controls'][0]['bytes'],'typed_bytes':report['paired_authored_controls'][1]['bytes'],'typed_minus_opaque_bytes':report['typed_minus_opaque_bytes'],'deep_stop':'ValueError graph_depth at recursion600','old_checker_admitted':False,'original_candidate_unchanged':True,'provider_calls':0,'revised_candidate_sha256':h(paths[0])}))
if __name__=='__main__':main()
