#!/usr/bin/env python3
"""Read-only R8 failure diagnosis. Writes new analysis only; never repairs inventory or calls providers."""
import copy,hashlib,importlib.util,json,math,re,sys
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def put(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def main():
    def guard(event,args):
        if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('network/process forbidden in failure analysis')
        if event=='open' and isinstance(args[0],(str,bytes)):
            name=str(args[0]).lower()
            if '/.env' in name or '/library/keychains/' in name or '/.aws/' in name or Path(name).name in ('credentials','credentials.json'):raise RuntimeError('credential access forbidden')
    sys.addaudithook(guard)
    freeze=ROOT/'execution/freeze-E.json';want='ef9891fca1a9aa6e0eeeafcdfee22d46b7d6dab8c79ff39099c3e00ef4f2c996';assert digest(freeze)==want
    entries=json.loads(freeze.read_bytes())['files'];before={row['path']:digest(ROOT/row['path']) for row in entries}
    assert len(entries)==20 and all(before[row['path']]==row['sha256'] and (ROOT/row['path']).stat().st_size==row['bytes'] for row in entries)
    op=next((ROOT/'execution/run/operations').iterdir());raw=(op/'response.body').read_bytes();response=json.loads(raw);choice=response['choices'][0];content=choice['message']['content'];usage=response['usage']
    adapter_path=ROOT.parent/'round7/runtime/provider_adapters.py';implementation=json.loads((ROOT/'runtime/implementation.json').read_bytes());assert digest(adapter_path)==implementation['code'][str(adapter_path.resolve())];spec=importlib.util.spec_from_file_location('frozen_r7_parser_diagnosis',adapter_path);a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    result={}
    try:a.parse_or(raw);result['frozen_parse']={'accepted':True}
    except Exception as error:result['frozen_parse']={'accepted':False,'exception_type':type(error).__name__,'reason':str(error)}
    try:a.loads(content);result['content_json']={'valid':True}
    except json.JSONDecodeError as error:result['content_json']={'valid':False,'reason':error.msg,'line':error.lineno,'column':error.colno,'character_index':error.pos}
    except Exception as error:result['content_json']={'valid':False,'reason':str(error),'exception_type':type(error).__name__}
    checks=dict(wrapper_object=isinstance(response,dict),wrapper_error_absent=not response.get('error'),model_allowed=response.get('model') in a.RESPONSE_MODELS,provider_allowed=response.get('provider') in (None,'OpenAI'),exactly_one_choice=isinstance(response.get('choices'),list) and len(response['choices'])==1,choice_error_absent=not choice.get('error'),finish_reason_stop=choice.get('finish_reason')=='stop',refusal_absent=not choice['message'].get('refusal'),tool_calls_absent=not choice['message'].get('tool_calls'),content_is_string=isinstance(content,str),usage_object=isinstance(usage,dict),prompt_tokens_valid=type(usage.get('prompt_tokens')) is int and usage['prompt_tokens']>=0,completion_tokens_valid=type(usage.get('completion_tokens')) is int and usage['completion_tokens']>=0,cost_valid=type(usage.get('cost')) in (int,float) and math.isfinite(usage['cost']) and usage['cost']>=0)
    # Synthetic valid parser transport only. No artifact is called a source inventory or repaired response.
    synthetic=dict(model=a.MODEL,provider='OpenAI',choices=[dict(finish_reason='stop',message=dict(content='{"development_control":true}'))],usage=dict(prompt_tokens=100,completion_tokens=100,cost=.0012))
    controls=[]
    for model in sorted(a.RESPONSE_MODELS):
        value=copy.deepcopy(synthetic);value['model']=model
        controls.append(dict(name='allowed_model_'+model,expected='accept_parser_transport_only',passed=a.parse_or(json.dumps(value).encode())['structured']=={'development_control':True}))
    for name,alter in [('length',lambda v:v['choices'][0].update(finish_reason='length')),('unknown_model',lambda v:v.update(model='unsupported-model')),('wrong_provider',lambda v:v.update(provider='Other')),('missing_usage_cost',lambda v:v['usage'].pop('cost')),('bool_usage_count',lambda v:v['usage'].update(completion_tokens=True)),('truncated_json',lambda v:v['choices'][0]['message'].update(content='{"x":"unterminated'))]:
        value=copy.deepcopy(synthetic);alter(value)
        try:a.parse_or(json.dumps(value).encode());passed=False;reason='accepted unexpectedly'
        except Exception as error:passed=True;reason=type(error).__name__+': '+str(error)
        controls.append(dict(name=name,expected='reject',passed=passed,reason=reason))
    cf=copy.deepcopy(response);cf['choices'][0]['finish_reason']='stop'
    try:a.parse_or(json.dumps(cf).encode());counterfactual={'accepted':True}
    except Exception as error:counterfactual={'accepted':False,'exception_type':type(error).__name__,'reason':str(error)}
    quotes=[]
    for match in re.finditer(r'"quote"\s*:\s*("(?:[^"\\]|\\.)*")',content):
        try:quotes.append(json.loads(match[1]))
        except json.JSONDecodeError:pass
    counts=Counter(quotes);inside=False;escaped=False;space=0
    for character in content:
        if inside:
            if escaped:escaped=False
            elif character=='\\':escaped=True
            elif character=='"':inside=False
        elif character=='"':inside=True
        elif character.isspace():space+=1
    budget=[]
    for notices in (8,7,5,1):
        for cap in (6144,8192,12288,16384):
            bound=notices*(2*35000*a.PRICES['prompt']+cap*a.PRICES['completion']+4096*a.PRICES['completion']+64000*a.PRICES['jev'])
            budget.append(dict(notices=notices,inventory_completion=cap,max_calls=3*notices,nominal_worst_case_usd=round(bound,6),fits_new_2_usd_envelope=bound<=2))
    metadata=dict(document_id=json.loads((op/'identity.json').read_bytes())['identity']['document_id'],http_status=json.loads((op/'status.json').read_bytes())['http_status'],response_sha256=digest(op/'response.body'),request_sha256=digest(op/'request.json'),parser_sha256=digest(adapter_path),model=response['model'],provider=response['provider'],allowed_models=sorted(a.RESPONSE_MODELS),finish_reason=choice['finish_reason'],native_finish_reason=choice.get('native_finish_reason'),configured_completion_cap=json.loads((op/'request.json').read_bytes())['max_tokens'],content_codepoints=len(content),usage=usage,provider_reported_usd=usage['cost'],invoice_verified=False,usage_rate_estimated_usd=usage['prompt_tokens']*a.PRICES['prompt']+usage['completion_tokens']*a.PRICES['completion'])
    report=dict(schema_version='round8.offline_failure_diagnosis.v1',metadata=metadata,parser_checks=checks,observed_rejection=result,diagnostic_only_finish_reason_override=counterfactual,synthetic_parser_controls=controls,partial_lexical_diagnostics_not_inventory=dict(closed_quote_fields=len(quotes),distinct_quote_values=len(counts),quote_value_chars=sum(map(len,quotes)),repeated_quote_value_chars=sum((n-1)*len(q) for q,n in counts.items()),outside_string_whitespace_chars=space,content_chars=len(content)),budget_scenarios=budget,inventory_record_created=False,verifier_calls=0,new_provider_calls=0,credentials_read=False,source_labels_read=False,freeze_E_verified=True,parser_matches_frozen_implementation=True,frozen_files=20,frozen_bytes_unchanged_during_analysis=all(digest(ROOT/rel)==want for rel,want in before.items()),analysis_control_passed=all(c['passed'] for c in controls),limitations=['Partial lexical counts are descriptive only; no missing-tail length or final semantic completeness is known.','Transport parser acceptance is not assembly or semantic acceptance.','Reported charge is response-reported, not invoice verified; stopped parser did not create result.json.','Any new higher-cap or compact transport requires separately authorized reviewed version, not retrying this frozen operation.'])
    put(HERE/'diagnosis.json',report)
    print(json.dumps(dict(frozen_rejection=result['frozen_parse'],latent_content_json=result['content_json'],model_identity_allowed=checks['model_allowed'],usage_fields_valid=all(checks[k] for k in ('usage_object','prompt_tokens_valid','completion_tokens_valid','cost_valid')),synthetic_controls=len(controls),controls_passed=report['analysis_control_passed'],frozen_unchanged=report['frozen_bytes_unchanged_during_analysis']),indent=2))
if __name__=='__main__':main()
