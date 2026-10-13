"""Read-only R14 measurements by default; --record exclusively creates R15 baseline."""
import ast,collections,hashlib,importlib.util,json,math,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROUND=HERE.parent;BENCH=ROUND.parent;R14=BENCH/'round14-semantic-contract';RUN=R14/'execution/run';PROTO=R14/'protocol-revised'
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def freeze_check():
    manifest=read(ROUND/'primary/R14-FREEZE.json')
    for name,want in manifest['files'].items():
        p=(BENCH/name).resolve();assert p.is_relative_to(R14) and sha(p)==want,(name,'R14 drift')
    return len(manifest['files'])
def object_sizes(obj):
    members={key:len(canonical(key))+1+len(canonical(value)) for key,value in obj.items()}
    punctuation=2+max(0,len(obj)-1);assert sum(members.values())+punctuation==len(canonical(obj))
    return {'member_key_colon_value_bytes':members,'braces_and_commas_bytes':punctuation,'total_canonical_bytes':len(canonical(obj))}
def measure():
    frozen_count=freeze_check()
    ready=read(PROTO/'READY.json')
    for name,want in ready['sha256'].items():assert sha(PROTO/name)==want
    spec=importlib.util.spec_from_file_location('r15_exact_r14_protocol',PROTO/'compact.py');k=importlib.util.module_from_spec(spec);spec.loader.exec_module(k)
    request=k.strict_load((RUN/'request.json').read_bytes());response=k.strict_load((RUN/'response.body').read_bytes());result=read(RUN/'result.json');ledger=read(RUN/'ledger.json');content=(RUN/'content.body').read_bytes();compact=k.strict_load(content);validated=(RUN/'validated.json').read_bytes();source=(R14/'source/parsed-body.txt').read_bytes().decode();table=read(RUN/'span-table.json')
    done=read(RUN/'completed.json');execution=read(R14/'execution/READY.json')
    for name,want in done['files'].items():assert sha(RUN/name)==want
    for name,want in execution['files'].items():assert sha(RUN/name)==want['sha256'] and (RUN/name).stat().st_size==want['bytes']
    assert result['finish_reason']=='stop' and response['choices'][0]['finish_reason']=='stop' and response['choices'][0]['message']['content'].encode()==content
    assert k.canonical(compact)==validated and compact==read(RUN/'validated.json')
    assert k.build(source)['body']==request and k.reconstruct(source,table)==source
    checked=k.validate_response(content.decode(),'stop',source,table);assert k.canonical(checked['expanded'])==(RUN/'expanded.json').read_bytes() and k.contract(checked['expanded'],source,table)==compact
    usage=response['usage'];assert usage==result['usage'] and usage['completion_tokens']==7231 and len(compact['u'])==result['unit_count']==110
    assert ledger['state']=='charge_recorded' and ledger['budget_charge_nanousd']==200000000 and ledger['cumulative_budget_charge_nanousd']==1905990718 and ledger['ceiling_nanousd']==2000000000
    units=compact['u'];schema=request['response_format']['json_schema']['schema'];uschema=schema['properties']['u']['items']['properties'];fields={}
    for key in ('s','c','r'):
        chars=[len(u[key]) for u in units];bytes_=[len(u[key].encode()) for u in units];vals=[len(canonical(u[key])) for u in units];cap=uschema[key]['maxLength']
        fields[key]={'schema_max_characters':cap,'measured_max_characters':max(chars),'measured_p95_characters_nearest_rank':sorted(chars)[math.ceil(.95*len(chars))-1],'measured_max_utf8_bytes':max(bytes_),'sum_characters':sum(chars),'sum_utf8_bytes':sum(bytes_),'sum_json_string_value_bytes':sum(vals),'sum_key_colon_value_bytes':sum(vals)+len(units)*4,'empty_unit_count':sum(x==0 for x in chars),'at_cap_unit_ids':[u['i'] for u in units if len(u[key])==cap],'at_or_above_90_percent_cap_unit_ids':[u['i'] for u in units if len(u[key])>=math.ceil(.9*cap)],'exceeding_cap_unit_ids':[u['i'] for u in units if len(u[key])>cap]}
    qualification_groups=collections.defaultdict(list)
    for u in units:
        if u['c']:qualification_groups[u['c']].append(u['i'])
    repeated=[{'value_sha256':hashlib.sha256(v.encode()).hexdigest(),'unit_ids':ids,'occurrences':len(ids),'characters_per_occurrence':len(v),'utf8_bytes_per_occurrence':len(v.encode()),'json_string_bytes_per_occurrence':len(canonical(v)),'utf8_bytes_total':len(ids)*len(v.encode()),'literal_duplicate_utf8_bytes_beyond_first':(len(ids)-1)*len(v.encode())} for v,ids in qualification_groups.items() if len(ids)>1]
    repeated.sort(key=lambda x:(-x['literal_duplicate_utf8_bytes_beyond_first'],x['value_sha256']))
    arrays={key:{'schema_max_items':uschema[key]['maxItems'],'measured_max_items':max(len(u[key]) for u in units),'sum_items':sum(len(u[key]) for u in units),'at_cap_unit_ids':[u['i'] for u in units if len(u[key])==uschema[key]['maxItems']]} for key in ('d','b','e')}
    user=k.strict_load(request['messages'][1]['content']);assert set(user)=={'source_text','source_text_sha256','span_table','span_table_sha256'} and user['source_text']==source and user['span_table']==table
    settings=read(PROTO/'request-settings.json');assert request['max_tokens']==8192 and settings['max_tokens']==8192
    input_sizes={'request_bytes':len((RUN/'request.json').read_bytes()),'guard_allowance_bytes':1024,'guarded_request_bytes':len(canonical(request))+1024,'guard_max_bytes':40000,'guard_residual_bytes':40000-len(canonical(request))-1024,'top_level_additive_accounting':object_sizes(request),'source_utf8_bytes':len(source.encode()),'source_characters':len(source),'span_count':len(table['rows']),'span_table_canonical_bytes':len(canonical(table)),'span_row_exact_text_utf8_sum':sum(len(row[3].encode()) for row in table['rows']),'source_text_json_string_bytes':len(canonical(source)),'inner_user_envelope_utf8_bytes':len(request['messages'][1]['content'].encode()),'outer_user_content_json_string_bytes':len(canonical(request['messages'][1]['content'])),'inner_user_envelope_additive_accounting':object_sizes(user),'system_content_utf8_bytes':len(request['messages'][0]['content'].encode()),'system_content_json_string_bytes':len(canonical(request['messages'][0]['content'])),'schema_canonical_bytes':len(canonical(schema)),'response_format_canonical_bytes':len(canonical(request['response_format'])),'schema_evidence_enum_count':len(uschema['e']['items']['enum']),'schema_evidence_enum_canonical_bytes':len(canonical(uschema['e']['items']['enum'])),'overhead_measurement_note':'Nested component sizes are separate measurement layers, not an additive total. source appears literally in source_text and exact span rows; outer JSON encoding adds escaping. No candidate/schema omission was performed.'}
    functions=[]
    for node in ast.parse((PROTO/'compact.py').read_bytes()).body:
        if isinstance(node,ast.FunctionDef):functions.append({'name':node.name,'signature':ast.unparse(node.args)})
    pins=[ROUND/'primary/R14-FREEZE.json',PROTO/'READY.json',R14/'execution/READY.json',R14/'execution/STOP.json',R14/'source/READY.json',R14/'source/parsed-body.txt',R14/'runtime/READY.json',R14/'runtime/adapter.py',R14/'runtime/common.py',R14/'runtime/contract.py',R14/'runtime/prepare_bindings.py']+[RUN/n for n in execution['files']]+[PROTO/n for n in ready['sha256']]
    prior_remaining=ledger['ceiling_nanousd']-ledger['cumulative_budget_charge_nanousd'];nominal=usage['prompt_tokens']*2000+usage['completion_tokens']*10000
    observed={'unit_count':len(units),'native_response_bytes':(RUN/'response.body').stat().st_size,'original_content_bytes':len(content),'canonical_compact_bytes':len(validated),'raw_minus_canonical_content_bytes':len(content)-len(validated),'expanded_inventory_bytes':(RUN/'expanded.json').stat().st_size,'finish_reason':'stop','observed_usage':usage,'completion_cap_tokens':8192,'observed_completion_tokens':usage['completion_tokens'],'observed_completion_fraction_of_cap':usage['completion_tokens']/8192,'observed_completion_cap_residual_tokens':8192-usage['completion_tokens'],'reasoning_tokens_reported':usage['completion_tokens_details']['reasoning_tokens'],'completion_minus_reasoning_arithmetic':usage['completion_tokens']-usage['completion_tokens_details']['reasoning_tokens'],'token_interpretation':'Observed provider usage for this single frozen R14 request; arithmetic subtraction is not a separately tokenized visible-content count or a future-fit guarantee.','observed_raw_content_bytes_per_reported_completion_token':len(content)/usage['completion_tokens'],'observed_canonical_bytes_per_reported_completion_token':len(validated)/usage['completion_tokens'],'bytes_per_token_interpretation':'Retrospective ratio including reported completion accounting; not a matched tokenizer or transferable conversion.'}
    sensitivities={str(bpt):{'canonical_bytes_per_token_assumption':bpt,'content_estimated_tokens_ceil':math.ceil(len(validated)/bpt),'illustrative_plus_256_allowance_tokens':math.ceil(len(validated)/bpt)+256,'residual_of_8192_after_illustrative_allowance':8192-math.ceil(len(validated)/bpt)-256} for bpt in (2,3,4)}
    m={'schema_version':'round15.r14-sizing-baseline.v1','status':'FROZEN_OBSERVED_BASELINE_OFFLINE_ONLY','measurement_script_sha256':sha(HERE/'measure_baseline.py'),'source_pins':{str(p.relative_to(BENCH)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(set(pins))},'prior_freeze_verified_files':frozen_count,'observed_output':observed,'compact_text_fields':fields,'compact_array_fields':arrays,'qualification_repetition':{'nonempty_occurrences':sum(bool(u['c']) for u in units),'distinct_nonempty_values':len(qualification_groups),'exact_repeated_value_groups':len(repeated),'repeated_nonempty_occurrences':sum(x['occurrences'] for x in repeated),'literal_duplicate_utf8_bytes_beyond_first':sum(x['literal_duplicate_utf8_bytes_beyond_first'] for x in repeated),'groups':repeated,'interpretation':'Exact text repetition measurement only. Duplicate bytes are not achievable savings, semantic redundancy or removable conditions; dictionary/reference/scope costs and meaning require separate evaluation.'},'input':input_sizes,'byte_sensitivities':{'kind':'illustrative byte estimates, not observed token usage or matched tokenizer','rows':sensitivities},'budget':{'prior_before_R14_nanousd':ledger['prior_nanousd'],'R14_reservation_and_charge_nanousd':ledger['budget_charge_nanousd'],'provider_reported_cost_usd':usage['cost'],'provider_reported_cost_nanousd':result['reported_cost_nanousd'],'nominal_usage_rate_estimated_nanousd':nominal,'provider_report_minus_nominal_estimate_nanousd':result['reported_cost_nanousd']-nominal,'cache_write_tokens_reported':usage['prompt_tokens_details']['cache_write_tokens'],'cache_write_premium_verified':False,'nominal_estimate_includes_cache_write_premium':False,'invoice_verified':False,'cumulative_conservative_charge_nanousd':ledger['cumulative_budget_charge_nanousd'],'ceiling_nanousd':ledger['ceiling_nanousd'],'remaining_conservative_nanousd':prior_remaining,'remaining_conservative_usd':f'{prior_remaining/1000000000:.9f}','another_200000000_reservation_fits':prior_remaining>=200000000,'shortfall_for_same_reservation_nanousd':max(0,200000000-prior_remaining),'budget_policy':'Do not replace conservative charges with lower reported/estimated costs or silently lower reservation. R15 is offline only; a new paid experiment requires explicit primary/user admission and sufficient approved budget.'},'protocol_interface':{'version':k.VERSION,'span_table_version':table['v'],'expanded_version':checked['expanded']['schema_version'],'required_compact_envelope_keys':list(compact),'unit_required_keys':k.UNIT_KEYS,'functions':functions,'settings':settings,'capacity_sentinel_units':160,'accepted_unit_count_max':159,'ID_max':160,'closed_schema_keyword_validator':'type/properties/required/additionalProperties/enum/minimum/maximum/minLength/maxLength/items/minItems/maxItems only; runtime check_schema fails unsupported keywords','build_result_keys':list(k.build(source)),'validate_response_result_keys':list(checked)},'integration_constraints':['Import the exact reviewed protocol after verifying READY/file pins; use its build, validate_response, expand and contract directly.','Preserve exact immutable source/UTF-8 hash and whole source-only envelope; regenerate source-instantiated request/schema/table and full guarded size for an R15 candidate.','Preserve condition/uncertainty evidence, literal strings, codes, ordering, explicit empties and exact compact-expanded inverse; any field/condition references require explicit schema/codec/review changes, no defaults or silently inferred scopes.','R14 c/r caps are180 characters and s cap280; bounds are characters, not UTF-8 bytes/tokens. Essential qualifiers cannot be clipped/dropped to fit.','Only complete stop output passes. Capacity160, truncation, malformed output or missing bindings stop intact; no retry, prefix repair, fallback or alternate representation.','Keep native executor/core unchanged; preserve primary late-binding CLI and yokel.research-job.v1 shape, isolated six-argument entry and explicit pinned dependency closure <=10000. R15 schemas/authorization/job ID require distinct prospectively reviewed bindings, not edits to R14.','Neutral charge ledger and separate completed/stop outcomes stay distinct; reserve and conservatively charge recoverable overruns, retain provider reports/usage/cache metadata without invoice or premium claims.','Use only separately labelled authored fixtures for transformed R14 outputs. A size delta cannot establish semantic/structural improvement, model behavior or unseen-source generalization.','No new provider experiment is authorized in this offline task; current remaining budget cannot admit another unchanged200000000 reserve.'],'verification':{'execution_and_completion_hashes_verified':True,'raw_content_matches_native_message':True,'canonical_content_matches_validated':True,'exact_current_source_build_matches_recorded_request':True,'expanded_inverse_roundtrip_exact':True,'all_prior_R14_freeze_hashes_rechecked':True,'provider_calls':0,'credentials_read':False,'signer_executor_invoked':False,'prior_artifacts_changed':False,'production_eligible':False,'action_ready':False}}
    assert freeze_check()==frozen_count
    return m
def markdown(m):
    o=m['observed_output'];q=m['qualification_repetition'];i=m['input'];b=m['budget'];f=m['compact_text_fields'];rows=[]
    for key,v in f.items():rows.append(f"| `{key}` | {v['schema_max_characters']} | {v['measured_max_characters']} | {v['measured_p95_characters_nearest_rank']} | {v['sum_utf8_bytes']} | {v['sum_key_colon_value_bytes']} | {v['empty_unit_count']} | {len(v['at_cap_unit_ids'])} |")
    estimates=[]
    for key,v in m['byte_sensitivities']['rows'].items():estimates.append(f"| {key} | {v['content_estimated_tokens_ceil']} | {v['illustrative_plus_256_allowance_tokens']} | {v['residual_of_8192_after_illustrative_allowance']} |")
    interfaces='\n'.join(f"- `{x['name']}({x['signature']})`" for x in m['protocol_interface']['functions'] if x['name'] in ('build','schema','span_table','reconstruct','validate','validate_response','expand','contract','canonical','digest','source_hash'))
    return f'''# R15 sizing baseline: frozen R14.2 observations

Measured from the unchanged R14.2 request and completed provider receipts. BASELINE.json contains exact pins, additive byte accounting, cap distributions, repeated-qualification groups and integration constraints. This is an offline observed baseline, not an R15 candidate or an improvement claim. All {m['prior_freeze_verified_files']} files in the primary R14-FREEZE manifest verify before and after measurement. No provider calls, credentials, signing, runner invocation, installs or prior writes.

## Exact observed output and usage

| Measurement | Observed value |
| --- | ---: |
| Units | {o['unit_count']} |
| Original provider content UTF-8 bytes | {o['original_content_bytes']} |
| Canonical compact bytes | {o['canonical_compact_bytes']} |
| Original minus canonical bytes | {o['raw_minus_canonical_content_bytes']} |
| Native response-envelope bytes | {o['native_response_bytes']} |
| Expanded inventory bytes | {o['expanded_inventory_bytes']} |
| Provider-reported prompt tokens | {o['observed_usage']['prompt_tokens']} |
| Provider-reported completion tokens | {o['observed_completion_tokens']} |
| Output cap | {o['completion_cap_tokens']} |
| Completion fraction of cap | {100*o['observed_completion_fraction_of_cap']:.4f}% |
| Observed completion residual | {o['observed_completion_cap_residual_tokens']} tokens |
| Reported reasoning tokens | {o['reasoning_tokens_reported']} |
| Finish reason | stop |

Original content is preserved separately from canonical JSON; both hash back to the immutable native/validated receipts. The exact source build matches the recorded request, and imported validate_response/expand/contract reproduce every expanded field/evidence and compact canonical bytes. Those checks establish provenance/structural roundtrip only. They do not establish complete or faithful conditions, semantic accuracy or future fit.

Completion minus reported reasoning is {o['completion_minus_reasoning_arithmetic']}; this is arithmetic, not a separately tokenized visible-content measurement. The raw-content/completion ratio is {o['observed_raw_content_bytes_per_reported_completion_token']:.6f} bytes/token and the canonical-content ratio is {o['observed_canonical_bytes_per_reported_completion_token']:.6f}. Both are retrospective ratios for this one request, not a matched tokenizer or a transferable conversion. No model call or authored replacement output was produced here.

## Qualifications and capped fields

| Field | Character cap | Observed max chars | P95 chars | Sum UTF-8 value bytes | Sum key/colon/JSON-value bytes | Empty units | Units at cap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(rows)}

`c` has {q['nonempty_occurrences']} nonempty occurrences and {q['distinct_nonempty_values']} distinct nonempty strings. {q['exact_repeated_value_groups']} exact repeated-string groups cover {q['repeated_nonempty_occurrences']} occurrences. Repetition beyond the first occurrence totals **{q['literal_duplicate_utf8_bytes_beyond_first']} literal UTF-8 bytes**. Group hashes and unit IDs in BASELINE.json make this count traceable without inventing a condition classification. These duplicated bytes are not achievable savings, semantically redundant conditions or permission to delete attachments: dictionary/reference/scope encoding overhead and semantic preservation require separate candidate evaluation.

Caps are Unicode character counts, not UTF-8 bytes or tokens. JSON-value bytes include quotes/escaping; key/colon/value contributions add the four bytes for each one-letter key. Unit commas/braces and other fields remain separate. Maximum observed list lengths are d={m['compact_array_fields']['d']['measured_max_items']}/16, b={m['compact_array_fields']['b']['measured_max_items']}/16, e={m['compact_array_fields']['e']['measured_max_items']}/6. The schema permits160 as a capacity sentinel; host validation accepts fewer than160 and IDs1..160. Neither count establishes a safe output fit or authorizes fact omission.

## Actual input and schema overhead

| Component or layer | UTF-8 bytes |
| --- | ---: |
| Full canonical request | {i['request_bytes']} |
| Guard allowance | {i['guard_allowance_bytes']} |
| Guarded request | {i['guarded_request_bytes']} |
| Residual under40000 guard | {i['guard_residual_bytes']} |
| Entire immutable source | {i['source_utf8_bytes']} |
| Source serialized as JSON string | {i['source_text_json_string_bytes']} |
| Exact span table ({i['span_count']} spans) | {i['span_table_canonical_bytes']} |
| Inner source-only user envelope | {i['inner_user_envelope_utf8_bytes']} |
| Outer serialized user-content string | {i['outer_user_content_json_string_bytes']} |
| System content | {i['system_content_utf8_bytes']} |
| Source-instantiated schema | {i['schema_canonical_bytes']} |
| Whole response_format wrapper | {i['response_format_canonical_bytes']} |
| Schema evidence-ID enum | {i['schema_evidence_enum_canonical_bytes']} |

Nested layers overlap; this table must not be summed. BASELINE.json separately proves exact additive top-level and inner-envelope accounting. Complete source text appears in source_text and exact span rows; double serialization adds escaping. Nothing was removed to produce a smaller request. An R15 candidate must regenerate the full source-instantiated schema/request/table and remeasure the complete guard.

## Estimates are separate from observations

The following are illustrative divisions of {o['canonical_compact_bytes']} canonical bytes by assumed bytes/token, with an optional256-token allowance inherited from sizing sensitivity work. They are not measured token counts or guaranteed bounds.

| Assumed bytes/token | Estimated content tokens (ceil) | Plus illustrative256 allowance | Residual under8192 |
| --- | ---: | ---: | ---: |
{chr(10).join(estimates)}

The actual provider reported {o['observed_completion_tokens']} completion tokens; the byte estimates can disagree materially. A candidate byte reduction cannot be reported as measured token reduction, semantic improvement, altered model behavior or generalization. Any edited R14 output must remain a separately labelled authored fixture with original output immutable.

## Budget and runtime integration

R14 reserve/conservative charge=${b['R14_reservation_and_charge_nanousd']/1e9:.2f}; reported provider cost=${b['provider_reported_cost_usd']:.7f}; nominal2/10 usage-rate estimate=${b['nominal_usage_rate_estimated_nanousd']/1e9:.7f}. Reported-minus-nominal=${b['provider_report_minus_nominal_estimate_nanousd']/1e9:.7f}. Usage reports {b['cache_write_tokens_reported']} cache-write prompt tokens. This difference is not independently verified cache-write premium or an invoice; preserve the reported usage/cost details and all three accounting quantities separately.

Cumulative conservative debit=${b['cumulative_conservative_charge_nanousd']/1e9:.9f} against$2, leaving **${b['remaining_conservative_usd']}**. Another unchanged$0.20 reservation does not fit; shortfall=${b['shortfall_for_same_reservation_nanousd']/1e9:.9f}. Do not retroactively substitute lower reported cost for conservative debit or silently reduce reservation. R15 is offline only. A future paid proposal requires explicit primary/user admission and sufficient approved budget; this baseline authorizes none.

The pure imported protocol is r14.2 (r14.spans.2; round14.expanded-inventory.v2). Relevant callable interfaces:

{interfaces}

Build returns body/table/body_bytes/guarded_bytes/request_sha256; validate_response returns compact/expanded. Preserve exact reviewed import pins and direct use of these functions. Unit fields i/k/s/m/c/d/b/e/q/r are closed and required; unknown modality requires uncertainty and q0 iff r empty. Essential conditions remain attached with exact evidence; new dictionary/reference/condition structures need explicit versioned schema/codec/scope validation and review, not inferred defaults or silent condition scopes. The runtime's closed-schema keyword checker must explicitly support any new schema form.

Keep Sol low/8192, OpenAI-only/no fallback and full40000 guard until a separately reviewed scope changes them. A complete stop output and exact inverse are required; truncation/capacity/bound failures stop intact. No clipping, retry, fallback, prefix repair or source/unit dropping. Preserve unchanged native executor/core, primary-only prepare_bindings --scope-id/--expires-unix/--review CLI, yokel.research-job.v1 manifest, isolated six-argument entry point and exact dependency closure<=10000. Neutral charge ledger and separate completion/stop outcomes stay distinct. R15 bindings/IDs/authorizations must be new artifacts rather than edits to R14. No live job or experiment proposal is released here.

## Reproduction

Run with the bundled interpreter, no installation:

```sh
/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12 -I -S -B /Users/home/.codex/worktrees/e8f4/yokel/docs/research/state-rulemaking-benchmark/round15-condition-preservation/sizing/measure_baseline.py
```

Default mode remeasures and compares BASELINE.json/BASELINE.md without writing. --record exclusively creates them and refuses existing baseline files. Exact source/code/receipt pins and the measurement script hash are in BASELINE.json. Future primary-supplied R15 implementations and offline sizing/experiment proposals remain pending; no semantic/structural improvement claim follows from this baseline.
'''
def main():
    if sys.argv[1:] not in ([],['--record']):raise SystemExit('use no args to verify or --record once')
    m=measure();doc=markdown(m);jp=HERE/'BASELINE.json';mp=HERE/'BASELINE.md'
    if sys.argv[1:]==['--record']:
        if jp.exists() or mp.exists():raise SystemExit('baseline already recorded; preserve frozen files')
        with jp.open('x') as f:json.dump(m,f,indent=2,sort_keys=True);f.write('\n')
        with mp.open('x') as f:f.write(doc)
    else:assert read(jp)==m and mp.read_text()==doc,'recorded baseline mismatch'
    freeze_check()
    print(json.dumps({'passed':True,'observed_units':m['observed_output']['unit_count'],'raw_content_bytes':m['observed_output']['original_content_bytes'],'canonical_bytes':m['observed_output']['canonical_compact_bytes'],'observed_completion_tokens':m['observed_output']['observed_completion_tokens'],'qualification_utf8_bytes':m['compact_text_fields']['c']['sum_utf8_bytes'],'duplicate_qualification_utf8_bytes_beyond_first':m['qualification_repetition']['literal_duplicate_utf8_bytes_beyond_first'],'request_schema_bytes':m['input']['schema_canonical_bytes'],'remaining_budget_usd':m['budget']['remaining_conservative_usd'],'prior_freeze_verified_files':m['prior_freeze_verified_files'],'baseline_json_sha256':sha(jp),'baseline_md_sha256':sha(mp),'provider_calls':0}))
if __name__=='__main__':main()
