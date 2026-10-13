"""Authored offline sizing only. Requires exact protocol READY hash, never provider calls."""
import argparse,ast,copy,hashlib,importlib.util,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from profile_recipe import profiles
from measure_baseline import freeze_check
HERE=Path(__file__).resolve().parent;ROUND=HERE.parent;BENCH=ROUND.parent;PROTO=ROUND/'protocol'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def encoded(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def old_checker():
    path=BENCH/'round14-semantic-contract/runtime/common.py';tree=ast.parse(path.read_bytes());nodes=[n for n in tree.body if (isinstance(n,ast.ClassDef) and n.name=='Denied') or (isinstance(n,ast.FunctionDef) and n.name in ('require','check_schema','schema_errors'))];ns={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns);return ns

def schema_inventory(schema):
    keywords={};booleans=[];maxdepth=0
    def walk(node,path,depth):
        nonlocal maxdepth
        maxdepth=max(maxdepth,depth)
        if type(node) is bool:booleans.append(path);return
        assert isinstance(node,dict)
        for key in node:keywords.setdefault(key,[]).append(path)
        for key in ('properties','$defs','definitions'):
            for name,child in node.get(key,{}).items():walk(child,path+'/'+key+'/'+name,depth+1)
        for key in ('items','additionalProperties'):
            if key in node and (isinstance(node[key],dict) or key=='items'):walk(node[key],path+'/'+key,depth+1)
        for key in ('prefixItems','anyOf','oneOf','allOf'):
            for i,child in enumerate(node.get(key,[])):walk(child,path+'/'+key+'/'+str(i),depth+1)
    walk(schema,'$',0)
    allowed={'type','properties','required','additionalProperties','enum','minimum','maximum','minLength','maxLength','items','minItems','maxItems'}
    return {'keywords':{key:len(paths) for key,paths in sorted(keywords.items())},'unsupported_old_checker_keywords':{key:paths for key,paths in keywords.items() if key not in allowed},'boolean_schema_paths':booleans,'schema_node_depth':maxdepth,'old_schema_depth_cap':16}

def graph_depth(wire):
    nodes={n['i']:n for n in wire['g']};cache={}
    def depth(uid):
        if uid not in cache:cache[uid]=1+max((depth(child) for child in nodes[uid]['a']),default=0)
        return cache[uid]
    return max((depth(link['n']) for link in wire['l']),default=0)

def full_body(k,source,table):
    # Exact pinned build spelling; equality is checked whenever build admits a plan.
    user=dict(source_text=source,source_text_sha256=k.source_hash(source),span_table=table,span_table_sha256=k.digest(table))
    body=k.strict_load((PROTO/'request-settings.json').read_text());body.update(messages=[dict(role='system',content=(PROTO/'stage-a.system.txt').read_text()),dict(role='user',content=k.canonical(user).decode('utf-8'))],response_format=dict(type='json_schema',json_schema=dict(name='condition_inventory',strict=True,schema=k.schema(source,table))))
    return body

def measure(ready_sha):
    prior_count=freeze_check();assert sha(PROTO/'READY.json')==ready_sha,'actual frozen protocol READY required';ready=read(PROTO/'READY.json')
    hashes=ready.get('sha256',ready.get('files'));assert isinstance(hashes,dict) and 'compact.py' in hashes
    for name,want in hashes.items():
        p=(PROTO/name).resolve();assert p.is_relative_to(PROTO);assert sha(p)==(want['sha256'] if isinstance(want,dict) else want)
    spec=importlib.util.spec_from_file_location('r15_exact_candidate_protocol',PROTO/'compact.py');k=importlib.util.module_from_spec(spec);spec.loader.exec_module(k)
    authored=profiles(k);baseline=read(HERE/'BASELINE.json');old=old_checker();results=[]
    for profile in authored:
        source=profile['source'];wire=profile['wire'];table=k.span_table(source);raw=k.canonical(wire);prose=k.canonical(profile['repeated_text_fixture']);expanded=None;error=None
        try:
            checked=k.validate_response(raw.decode(),'stop',source,table);expanded=checked['expanded'];inverse=k.contract(expanded,source,table);assert inverse==wire and k.canonical(inverse)==raw and k.digest(inverse)==k.digest(wire);valid=True
        except ValueError as exc:valid=False;error=str(exc)
        assert valid==profile['expected_graph_admission'],(profile['id'],'unexpected protocol outcome',error)
        body=full_body(k,source,table);body_raw=k.canonical(body);guarded=len(body_raw)+1024
        try:
            plan=k.build(source);assert plan['body']==body and plan['table']==table and plan['body_bytes']==len(body_raw) and plan['guarded_bytes']==guarded and plan['request_sha256']==hashlib.sha256(body_raw).hexdigest();build_admitted=True;build_error=None
        except ValueError as exc:
            build_admitted=False;build_error=str(exc);assert guarded>40000 and build_error=='full_request_overflow',(profile['id'],build_error)
        schema=body['response_format']['json_schema']['schema'];inventory=schema_inventory(schema)
        try:old['check_schema'](schema);old_pass=True
        except old['Denied']:old_pass=False
        assert not old_pass,'expected tuple schema incompatibility not observed'
        fragments=[frag for node in wire['g'] for frag in node['x']]+[frag for link in wire['l'] for frag in link['x']]+[frag for unit in wire['u'] if unit['y'] is not None for dim in unit['y'].values() for frag in dim['x']]
        resolved=[k.resolve_fragment(fragment,source,table) for fragment in fragments]
        textbytes=sum(len(x['text'].encode()) for x in resolved)
        anchors=sum(len(fragment[1].encode())+len(fragment[4].encode()) for fragment in fragments)
        dims=sum(len(k.canonical(u['y']))-len(k.canonical(None)) for u in wire['u'])
        row={'id':profile['id'],'fixture_kind':'authored_dimensional_not_model_output','purpose':profile['purpose'],'source_bytes':len(source.encode()),'source_chars':len(source),'source_sha256':k.source_hash(source),'span_count':len(table['rows']),'graph_compact_sha256':k.digest(wire),'repeated_text_fixture_sha256':k.digest(profile['repeated_text_fixture']),'units':len(wire['u']),'nodes':len(wire['g']),'links':len(wire['l']),'DAG_depth_nodes':graph_depth(wire),'anchor_width':profile['anchor_width'],'fragments':len(fragments),'literal_anchor_utf8_bytes':anchors,'resolved_fragment_utf8_bytes_including_reuse_occurrences':textbytes,'R15_compact_bytes':len(raw),'authored_unbounded_repeated_text_bytes':len(prose),'R14_c180_admissible_by_length_only':profile['R14_c180_admissible_by_length_only'],'graph_minus_repeated_fixture_bytes':len(raw)-len(prose),'graph_to_repeated_fixture_byte_ratio':len(raw)/len(prose),'comparison_limit':'Long repeated-text fixture deliberately violates c180; version/envelope/state overhead differs. Ratios are serialization only, not actual R14 conversion, semantic equivalence or achievable model compression. Capacity/depth shapes do not assert source logical entailment.','unit_array_canonical_bytes':len(k.canonical(wire['u'])),'node_array_canonical_bytes':len(k.canonical(wire['g'])),'link_array_canonical_bytes':len(k.canonical(wire['l'])),'fragment_tuple_serialized_bytes':sum(len(k.canonical(fragment)) for fragment in fragments),'deadline_dimension_bytes_above_null':dims,'expanded_bytes':None if expanded is None else len(k.canonical(expanded)),'graph_admitted':valid,'graph_stop_reason':error,'inverse_exact':valid,'full_request_bytes':len(body_raw),'guarded_request_bytes':guarded,'request_guard_admitted':build_admitted,'request_guard_stop_reason':build_error,'schema_bytes':len(k.canonical(schema)),'response_format_bytes':len(k.canonical(body['response_format'])),'full_request_sha256':hashlib.sha256(body_raw).hexdigest(),'schema_inventory':inventory,'R14_runtime_checker_admitted':old_pass,'byte_estimates':{str(bpt):{'estimate_ceil_bytes_div_bpt_plus_256':math.ceil(len(raw)/bpt)+256,'residual_of_8192':8192-math.ceil(len(raw)/bpt)-256} for bpt in (2,3,4)},'provider_token_count':None,'provider_schema_compatibility':'unverified_no_provider_call','output_fit_guaranteed':False}
        results.append(row)
    # Same exposed public R14 source is input-overhead-only, never reference/model output migration.
    exposed_source=(BENCH/'round14-semantic-contract/source/parsed-body.txt').read_bytes().decode();exposed_table=k.span_table(exposed_source);exposed_body=full_body(k,exposed_source,exposed_table);exposed_bytes=len(k.canonical(exposed_body));exposed_guard=exposed_bytes+1024
    try:plan=k.build(exposed_source);assert plan['body']==exposed_body;exposed_admitted=True;exposed_stop=None
    except ValueError as exc:exposed_admitted=False;exposed_stop=str(exc);assert exposed_guard>40000 and exposed_stop=='full_request_overflow'
    pins=[HERE/'BASELINE.json',HERE/'BASELINE.md',HERE/'measure_baseline.py',HERE/'profile_recipe.py',HERE/'measure_candidate.py',ROUND/'primary/R14-FREEZE.json',ROUND/'design/DESIGN.md',ROUND/'design/READY.json',ROUND/'primary/acceptance.json',PROTO/'READY.json']+[PROTO/name for name in hashes]
    report={'schema_version':'round15.offline-authored-sizing.v1','status':'OFFLINE_SIZING_NOT_PROVIDER_RELEASE','protocol_version':k.VERSION,'protocol_ready_sha256':ready_sha,'source_pins':{str(p.relative_to(BENCH)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(set(pins))},'authored_profile_count':len(results),'observed_R14':{'unit_count':baseline['observed_output']['unit_count'],'canonical_bytes':baseline['observed_output']['canonical_compact_bytes'],'completion_tokens':baseline['observed_output']['observed_completion_tokens'],'output_cap':8192,'qualification_bytes':baseline['compact_text_fields']['c']['sum_utf8_bytes'],'duplicated_qualification_bytes_beyond_first':baseline['qualification_repetition']['literal_duplicate_utf8_bytes_beyond_first']},'profiles':results,'exposed_R14_source_input_overhead_only':{'label':'Outcome-exposed input size control, no R14 output converted or R15 provider extraction','source_sha256':k.source_hash(exposed_source),'source_bytes':len(exposed_source.encode()),'span_count':len(exposed_table['rows']),'schema_bytes':len(k.canonical(exposed_body['response_format']['json_schema']['schema'])),'full_request_bytes':exposed_bytes,'guarded_request_bytes':exposed_guard,'request_guard_admitted':exposed_admitted,'request_guard_stop_reason':exposed_stop,'full_request_sha256':hashlib.sha256(k.canonical(exposed_body)).hexdigest(),'prior_R14_guarded_bytes':baseline['input']['guarded_request_bytes'],'guarded_bytes_delta_from_R14':exposed_guard-baseline['input']['guarded_request_bytes']},'compatibility':{'old_runtime_checker_accepted_profiles':sum(row['R14_runtime_checker_admitted'] for row in results),'required_reviewed_checker_support':sorted({keyword for row in results for keyword in row['schema_inventory']['unsupported_old_checker_keywords']}),'boolean_schema_support_required':any(row['schema_inventory']['boolean_schema_paths'] for row in results),'maximum_observed_schema_node_depth':max(row['schema_inventory']['schema_node_depth'] for row in results),'tuple_positions_must_be_validated':True,'minimal_change':'A new reviewed runtime schema validator must support and enforce positional prefixItems, closed Boolean items, actual unions/pattern constraints and depth resource guard; retain failure on unsupported keywords. Do not edit R14/native runner or bypass validation. Source-bound codecs/import/pins/authorization must be distinct new versioned artifacts.','provider_schema_compatibility':'unverified; tuple-schema acceptance is not proved by local host validation'},'budget':baseline['budget'],'experiment_proposal':{'status':'OFFLINE_ONLY_NO_PAID_PROPOSAL_ADMITTED','provider_calls_authorized':False,'reason':'Remaining$0.094009282 is below unchanged$0.20 reserve; provider schema support and output token fit unverified.','next_allowed_work':'Primary/independent review of exact scope/evidence/deadline preservation using disjoint authored controls and negative cases; retain full-schema sizing and tuple checker gap. Any future paid proposal requires explicit new authorization and sufficient budget, exact request/source/schema pins and no clipping/retry/repair/fallback.'},'limits':['Authored fixtures are not model outputs or source gold and do not establish semantic/structural improvement.','Shared versus disjoint text changes source size; each within-profile serialization comparator uses exactly the same source and unit count.','The old-style long-c comparator is intentionally inadmissible under R14 c180 and is never reported as valid old output.','Byte/token sensitivities and256 allowance are illustrative, not a matched tokenizer, observed tokens or output guarantee.','A valid shorter graph may omit essential conditions or links; exact anchors and inverse do not prove completeness.'],'verification':{'prior_R14_freeze_files_verified':prior_count,'expected_graph_admission_matches_all_profiles':True,'admitted_graph_inverses_exact':True,'admitted_builds_match_full_accounted_body':True,'overflow_request_accounting_does_not_admit_build':True,'R14_source_or_outputs_modified':False,'runtime_adapter_or_release_binding_implemented':False,'provider_calls':0,'credentials_read':False,'signer_executor_invoked':False,'production_eligible':False,'action_ready':False}}
    assert freeze_check()==prior_count
    return report,{'label':'Authored dimensional fixtures only; not model output/gold/R14 migration','profiles':authored}
def markdown(m):
    rows=[]
    for row in m['profiles']:
        graph='pass' if row['graph_admitted'] else row['graph_stop_reason'];request='pass' if row['request_guard_admitted'] else 'overflow'
        rows.append(f"| {row['id']} | {row['units']}/{row['nodes']}/{row['links']} | {row['DAG_depth_nodes']} | {row['R15_compact_bytes']} | {row['authored_unbounded_repeated_text_bytes']} | {row['guarded_request_bytes']} | {graph} / {request} |")
    e=m['exposed_R14_source_input_overhead_only'];c=m['compatibility'];b=m['budget']
    return f'''# R15 offline candidate sizing

Exact frozen protocol {m['protocol_version']} READY `{m['protocol_ready_sha256']}`. {m['authored_profile_count']} authored dimensional profiles, never model outputs, source gold or a deterministic migration of R14 c text. CANDIDATE.json records full pins/component sizes, source/schema/request hashes, admission results and byte sensitivities; authored-profiles.json preserves complete labelled fixtures. All {m['verification']['prior_R14_freeze_files_verified']} prior R14 freeze hashes verify unchanged.

## Focused measurements

| Authored profile | Units/nodes/links | DAG depth | Graph bytes | Unbounded repeated-text fixture bytes | Full guarded request bytes | Graph / input admission |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
{chr(10).join(rows)}

Shared versus disjoint cases use complete160/600-character fictional clauses. Each within-profile comparator attaches the same clause text to the same units. Graph encoding stores source-backed fragments and typed links; the prose comparator repeats the authored complete clause.600-character (and multi-fragment) prose deliberately violates old c180. Its serialization cannot be called valid R14 output, model compression or a tested migration. Version/envelope/p/state/reference overhead differs and is included; exact graph-minus-fixture bytes are merely serialization deltas. Unary-depth and high-count duplicate-leaf profiles stress structure; they do not assert source logical entailment or meaningful condition counts. Deadline y overhead is measured as its JSON value minus null, rather than asserted to be semantically equivalent to a qualification-only prose fixture.

Every admitted graph passes the exact imported validator and byte/hash inverse; intended fragment/depth/node/link boundary controls reject complete objects. All bytes of failed profiles remain labelled fixtures; none are repaired or clipped. Request build overflow is separately recorded. The full accounted body equals the pinned builder on every admitted request; independently counting a rejected body's bytes does not admit or bypass the guard.

## Overheads and limits

CANDIDATE.json separates unit/node/link arrays, fragment tuples, literal anchor bytes, resolved source evidence bytes (including reuse occurrences), deadline dimensions, whole schema/response wrapper and entire guarded request.12-versus48-character anchors measure literal-copy cost. Fragment counts, DAG depth and399/400 sentinels are engineering limits, not full-output fit guarantees. Qualifiers/units/source are never dropped to make a profile pass.

The observed R14 output was110 units/22686 canonical bytes and7231 completion tokens at8192 cap, with4180 c bytes and only892 exact duplicated qualification bytes beyond first occurrences. Those are frozen observations. R15 profiles have **no observed provider tokens**.2/3/4-byte sensitivities plus an illustrative256-token allowance are assumptions, not a matched tokenizer, reasoning measurement or assurance of fit. Authored size deltas establish no semantic/structural improvement, source completeness, model behavior or generalization. Independent assessment must still reject scope leaks, missing final exceptions, wrong roles/connectives, ambiguous references made certain and omitted applicability links.

## Full-schema public R14 input control

The same outcome-exposed7208-byte public R14 source is measured for input overhead only, with no R14 output converted and no model extraction. The exact candidate schema is {e['schema_bytes']} bytes; full request {e['full_request_bytes']} +1024={e['guarded_request_bytes']} guarded bytes, versus29331 in R14 (delta {e['guarded_bytes_delta_from_R14']:+d}). Build admission: {e['request_guard_admitted']}; stop: {e['request_guard_stop_reason']}. This exposed source is not an unseen pilot. Its candidate request hash is `{e['full_request_sha256']}`.

## Runtime and provider compatibility

The old R14 closed-schema checker accepts {c['old_runtime_checker_accepted_profiles']}/{m['authored_profile_count']} candidate profile schemas. Actual unsupported keywords: {', '.join(c['required_reviewed_checker_support'])}. Boolean item schemas required: {c['boolean_schema_support_required']}; maximum observed schema-node depth {c['maximum_observed_schema_node_depth']} (old checker limit16).

The old checker only recurses into one homogeneous items dictionary and property schemas; schema_errors cannot enforce tuple positions, union alternatives or node-ID patterns. A NEW reviewed runtime validator must implement the actual schema's positional prefixItems, closed Boolean items and required union/pattern/depth behavior and reject unsupported keywords, or the protocol owner must choose an equally strict reviewed compatible schema/wire. Do not suppress keyword rejection, pretend positional constraints are homogeneous, bypass checker or edit the frozen R14/native runner. Exact source-bound codec/import/request/pins and primary late bindings must belong to distinct R15 artifacts. This child implemented no runtime adapter or release bindings.

**Provider structured-schema/tuple compatibility remains unverified.** Host validation and local schema rejection cannot establish provider acceptance; no provider/API/credential probe occurred.

## Experiment admission

Offline only. Remaining conservative budget${b['remaining_conservative_usd']} cannot fit the unchanged$0.20 reserve; no paid proposal is admitted. Do not reduce historical charges/reserve or change budget here. Future primary/user authorization and sufficient approved budget would need an exact reviewed source/request/schema, provider compatibility assessment, independent semantic rubric and intact stop conditions. No retries, clipping, source narrowing, fact dropping or fallback. Current allowed work is independent offline review of representation and negative controls; these profiles cannot substitute for new source-only model evidence.

## Reproduction

```sh
/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12 -I -S -B /Users/home/.codex/worktrees/e8f4/yokel/docs/research/state-rulemaking-benchmark/round15-condition-preservation/sizing/measure_candidate.py
```

Default mode verifies the recorded protocol hash, exact inputs and all measurements without writes. --record --protocol-ready-sha256 requires the actual frozen candidate hash and exclusively creates CANDIDATE.json/CANDIDATE.md/authored-profiles.json; existing artifacts refuse overwrite. No installs, provider calls, credentials, signer/executor invocation, prior edits or runtime binding changes. production_eligible/action_ready=false.
'''
def main():
    cli=argparse.ArgumentParser();cli.add_argument('--record',action='store_true');cli.add_argument('--protocol-ready-sha256');args=cli.parse_args();jp=HERE/'CANDIDATE.json';mp=HERE/'CANDIDATE.md';fp=HERE/'authored-profiles.json'
    ready_sha=args.protocol_ready_sha256 or (read(jp)['protocol_ready_sha256'] if jp.exists() else None)
    if not ready_sha or len(ready_sha)!=64:raise SystemExit('actual frozen protocol READY hash required before candidate measurement')
    if args.record and any(p.exists() for p in (jp,mp,fp)):raise SystemExit('preserve recorded candidate files')
    m,fixtures=measure(ready_sha);m['authored_profiles_sha256']=hashlib.sha256(encoded(fixtures)).hexdigest();doc=markdown(m)
    if args.record:
        with fp.open('xb') as f:f.write(encoded(fixtures))
        with jp.open('x') as f:json.dump(m,f,indent=2,sort_keys=True);f.write('\n')
        with mp.open('x') as f:f.write(doc)
    else:assert read(jp)==m and mp.read_text()==doc and fp.read_bytes()==encoded(fixtures),'recorded candidate mismatch'
    assert sha(fp)==m['authored_profiles_sha256'];freeze_check()
    print(json.dumps({'passed':True,'authored_profiles':m['authored_profile_count'],'graph_admitted':sum(x['graph_admitted'] for x in m['profiles']),'request_guard_admitted':sum(x['request_guard_admitted'] for x in m['profiles']),'old_runtime_checker_admitted':m['compatibility']['old_runtime_checker_accepted_profiles'],'public_R14_source_guarded_request_bytes':m['exposed_R14_source_input_overhead_only']['guarded_request_bytes'],'candidate_json_sha256':sha(jp),'provider_calls':0}))
if __name__=='__main__':main()
