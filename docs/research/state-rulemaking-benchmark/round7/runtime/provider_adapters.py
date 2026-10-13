"""Offline request/response mechanics adapted from hash-pinned R6. No POST function or credentials."""
import hashlib,json,math,types
class Stop(ValueError): pass
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encode(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def loads(raw):
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out:raise Stop('duplicate JSON key')
            out[k]=v
        return out
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda x:(_ for _ in ()).throw(Stop('nonfinite JSON')))
j=types.SimpleNamespace(encode=encode,loads=loads,JEV_MODEL='jev-1.13.0')
MODEL='openai/gpt-6.1-sol'
CANONICAL_MODEL='openai/gpt-6.1-sol-20260929'
RESPONSE_MODELS={MODEL,CANONICAL_MODEL}
PRICES={'prompt':.000002,'completion':.000010,'jev':.000000042}
LIMITS={'documents':8,'PDF_pages':40,'native_codepoints':30000,'OR_input_estimate':35000,
        'inventory_completion':6144,'stronger_completion':4096,'Jev_input_estimate':64000,'Jev_state_longest_estimate':32000,
        'inventory_calls':8,'stronger_calls':8,'Jev_calls':8,'budget_usd':2.0}
MAX_RESERVATION=16*35000*PRICES['prompt']+8*6144*PRICES['completion']+8*4096*PRICES['completion']+8*64000*PRICES['jev']
assert MAX_RESERVATION<2


def estimate_input(payload):
    # Conservative byte upper bound plus transport/template allowance. Never crop input to fit.
    return len(j.encode(payload))+1024


def reserve(payload,stage):
    tokens=estimate_input(payload)
    if stage=='jev':
        if tokens>LIMITS['Jev_input_estimate']:raise Stop('Jev total input overlimit; no clipping')
        combined=len(j.encode(payload['state']))+max(len(j.encode(q)) for q in payload['questions'].values())+1024
        if combined>LIMITS['Jev_state_longest_estimate']:raise Stop('Jev state + longest question overlimit; no clipping')
        return tokens*PRICES['jev']
    if stage not in ('inventory','stronger'):raise Stop('unknown operation stage')
    if tokens>LIMITS['OR_input_estimate']:raise Stop('OpenRouter input overlimit; no clipping')
    expected=LIMITS[stage+'_completion']
    if payload.get('max_tokens')!=expected:raise Stop('completion reservation/cap mismatch')
    return tokens*PRICES['prompt']+expected*PRICES['completion']


def or_request(plan,stage):
    if stage not in ('inventory','stronger'):raise Stop('unsupported OpenRouter stage')
    if not isinstance(plan,dict) or not {'system','user','response_schema'}<=set(plan):raise Stop('pipeline provider plan missing fields')
    user=plan['user'] if not isinstance(plan['user'],str) else j.loads(plan['user'])
    if not isinstance(user,dict):raise Stop('pipeline user payload must be a JSON object')
    # A's schema is duplicated in its user wrapper; move the exact duplicate to response_format only.
    if 'response_schema' in user:
        if user['response_schema']!=plan['response_schema']:raise Stop('schema copies differ')
        user={k:v for k,v in user.items() if k!='response_schema'}
    body={'model':MODEL,'stream':False,'max_tokens':LIMITS[stage+'_completion'],
          'reasoning':{'effort':'low'},
          'provider':{'only':['openai'],'order':['openai'],'allow_fallbacks':False,'require_parameters':True,'max_price':{'prompt':2,'completion':10}},
          'messages':[{'role':'system','content':plan['system']},{'role':'user','content':j.encode(user).decode()}],
          'response_format':{'type':'json_schema','json_schema':{'name':'round7_'+stage,'strict':True,'schema':plan['response_schema']}}}
    reserve(body,stage)
    return body


def jev_request(payload,questions):
    if not isinstance(payload,dict) or not isinstance(questions,dict) or not questions or len(questions)>160:raise Stop('invalid bounded Jev question plan')
    for question in questions.values():
        if set(question)!={'type','instructions','criteria'} or question['type']!='choice' or not isinstance(question['criteria'],dict) or len(question['criteria'])<2:raise Stop('Jev needs explicit Choice questions, not generative JSON')
    body={'model':j.JEV_MODEL,'state':payload,'questions':questions};reserve(body,'jev')
    return body


def parse_or(raw):
    obj=j.loads(raw)
    if not isinstance(obj,dict) or obj.get('error') or obj.get('model') not in RESPONSE_MODELS or obj.get('provider') not in (None,'OpenAI'):raise Stop('OpenRouter model/provider mismatch or error')
    choices=obj.get('choices')
    if not isinstance(choices,list) or len(choices)!=1 or choices[0].get('finish_reason')!='stop' or choices[0].get('error'):raise Stop('incomplete structured completion; never retry')
    message=choices[0].get('message',{})
    if message.get('refusal') or message.get('tool_calls'):raise Stop('refusal or tool invocation')
    text=message.get('content')
    if not isinstance(text,str):raise Stop('missing structured response text')
    value=j.loads(text)
    if not isinstance(value,dict):raise Stop('structured response must be an object')
    usage=obj.get('usage')
    if not isinstance(usage,dict) or any(type(usage.get(k)) is not int or usage[k]<0 for k in ('prompt_tokens','completion_tokens')):raise Stop('missing/invalid usage')
    cost=usage.get('cost')
    if type(cost) not in (int,float) or not math.isfinite(cost) or cost<0:raise Stop('missing/invalid reported cost; stop without retry')
    estimate=usage['prompt_tokens']*PRICES['prompt']+usage['completion_tokens']*PRICES['completion']
    return {'structured':value,'usage':usage,'provider':obj.get('provider'),'provider_identity_verified':obj.get('provider')=='OpenAI','model':obj['model'],
            'reported_cost_usd':cost,'usage_rate_estimated_usd':estimate,'observed_cost_usd':cost,
            'cost_basis':'OpenRouter response-reported usage.cost; estimate separate, not invoice verified',
            'production_eligible':False,'operation_status':'completed'}


def parse_jev(raw,questions):
    obj=j.loads(raw)
    if not isinstance(obj,dict) or obj.get('model')!=j.JEV_MODEL or set(obj.get('answers',{}))!=set(questions):raise Stop('Jev model/question mismatch')
    answers={}
    for key,question in questions.items():
        answer=obj['answers'][key];probs=answer.get('probabilities');choice=answer.get('choice');confidence=answer.get('confidence')
        criteria=question['criteria']
        if answer.get('type')!='choice' or choice not in criteria or not isinstance(probs,dict) or set(probs)!=set(criteria):raise Stop('invalid Choice schema')
        if any(type(p) not in (int,float) or not math.isfinite(p) or not 0<=p<=1 for p in probs.values()) or abs(sum(probs.values())-1)>.02 or type(confidence) not in (int,float) or not math.isfinite(confidence) or not 0<=confidence<=1:raise Stop('invalid Choice probabilities/confidence')
        highest=max(probs.values())
        if probs[choice]<highest-.000001:raise Stop('Choice is not highest probability')
        tied=sum(abs(p-highest)<.000001 for p in probs.values())>1
        answers[key]={'label':None if tied else choice,'raw_label':choice,'probabilities':probs,'confidence':confidence,'abstained_on_tie':tied}
    usage=obj.get('usage')
    if not isinstance(usage,dict) or any(type(usage.get(k)) is not int or usage[k]<0 for k in ('input_tokens','output_tokens')):raise Stop('invalid Jev usage')
    cost=usage['input_tokens']*PRICES['jev']
    return {'answers':answers,'usage':usage,'model':obj['model'],'observed_cost_usd':cost,
            'usage_rate_estimated_usd':cost,'reported_cost_usd':None,'cost_basis':'reported usage × pinned input rate; output free',
            'generative_explanations_available':False,'production_eligible':False,'operation_status':'completed'}



def admission(body,stage):
    measured=estimate_input(body)
    longest=None
    if stage=='jev':longest=len(encode(body['state']))+max(len(encode(q)) for q in body['questions'].values())+1024
    try:reservation=reserve(body,stage);reason=None
    except Stop as e:reservation=None;reason=str(e)
    return dict(schema_version='round7.admission.v1',stage=stage,body_sha256=sha(encode(body)),body_utf8_bytes=len(encode(body)),estimate=measured,cap=LIMITS['Jev_input_estimate' if stage=='jev' else 'OR_input_estimate'],state_longest_estimate=longest,state_longest_cap=LIMITS['Jev_state_longest_estimate'] if stage=='jev' else None,admitted=reason is None,reason=reason,reservation_usd=reservation)

def or_body(plan,stage):
    # Construct exact final request even when overlimit, then retain a receipt instead of clipping.
    user=loads(plan['user']) if isinstance(plan['user'],str) else plan['user']
    if 'response_schema' in user:
        if user['response_schema']!=plan['response_schema']:raise Stop('schema copies differ')
        user={k:v for k,v in user.items() if k!='response_schema'}
    return {'model':MODEL,'stream':False,'max_tokens':LIMITS[stage+'_completion'],'reasoning':{'effort':'low'},'provider':{'only':['openai'],'order':['openai'],'allow_fallbacks':False,'require_parameters':True,'max_price':{'prompt':2,'completion':10}},'messages':[{'role':'system','content':plan['system']},{'role':'user','content':encode(user).decode()}],'response_format':{'type':'json_schema','json_schema':{'name':'round7_'+stage,'strict':True,'schema':plan['response_schema']}}}
