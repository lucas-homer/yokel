"""Standalone offline inventory contract. No provider, credentials or execution adapter."""
import copy
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
VERSION='r13.1'
KINDS=['identity','rule_transition','phase','timing','endpoint','endpoint_role','instruction','relationship','background']
MODALITIES=['informational','mandatory','advisory','optional','prohibited','unknown','not_applicable']
UNCERTAINTIES=['none','source_ambiguous','reference_unresolved','function_unresolved']
UNIT_KEYS=['i','k','s','m','c','d','b','e','q','r']

def require(ok,message):
    if not ok:raise ValueError(message)
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def source_hash(source):return hashlib.sha256(source.encode('utf-8')).hexdigest()
def closed(obj,keys):require(isinstance(obj,dict) and set(obj)==set(keys),'closed keys')
def strict_load(raw):
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'duplicate key');result[key]=value
        return result
    def constant(value):raise ValueError('nonfinite constant')
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=constant);canonical(value);return value

def span_table(source):
    require(isinstance(source,str) and bool(source.strip()),'nonempty source')
    # Python splitlines preserves each exact line separator with keepends=True.
    parts=source.splitlines(keepends=True);rows=[];start=0
    for index,part in enumerate(parts,1):
        rows.append([f's{index}',start,start+len(part),part]);start+=len(part)
    require(start==len(source),'partition coverage')
    return dict(v='r13.spans.1',h=source_hash(source),rows=rows)

def validate_table(source,table):
    require(table==span_table(source) and canonical(table)==canonical(span_table(source)),'exact host span table')

def reconstruct(source,table):
    validate_table(source,table)
    result=''.join(source[start:end] for _,start,end,_ in table['rows'])
    require(result==source and result.encode()==source.encode(),'source reconstruction')
    return result

def schema(source,table):
    validate_table(source,table)
    def text(cap,empty=False):return dict(type='string',minLength=0 if empty else 1,maxLength=cap)
    def obj(props):return dict(type='object',properties=props,required=list(props),additionalProperties=False)
    unit=obj({'i':dict(type='integer',minimum=1,maximum=160),'k':dict(type='integer',minimum=0,maximum=8),'s':text(280),'m':dict(type='integer',minimum=0,maximum=6),'c':text(180,True),'d':dict(type='array',items=dict(type='integer',minimum=1,maximum=160),maxItems=16),'b':dict(type='array',items=dict(type='integer',minimum=1,maximum=160),maxItems=16),'e':dict(type='array',items=dict(type='string',enum=[row[0] for row in table['rows']]),minItems=1,maxItems=6),'q':dict(type='integer',minimum=0,maximum=3),'r':text(180,True)})
    return obj({'v':dict(type='string',enum=[VERSION]),'h':dict(type='string',enum=[source_hash(source)]),'t':dict(type='string',enum=[digest(table)]),'u':dict(type='array',items=unit,minItems=1,maxItems=160),'z':dict(type='string',enum=['END'])})

def validate(value,source,table,finish_reason='stop'):
    require(finish_reason=='stop','non-stop/truncated response')
    validate_table(source,table);closed(value,['v','h','t','u','z'])
    require(value['v']==VERSION and value['h']==source_hash(source) and value['t']==digest(table),'binding/version')
    require(value['z']=='END','terminal marker')
    require(isinstance(value['u'],list) and 1<=len(value['u'])<160,'inventory bound/capacity reached')
    evidence_ids={row[0] for row in table['rows']};units={}
    for unit in value['u']:
        closed(unit,UNIT_KEYS)
        for key,maximum in [('i',160),('k',8),('m',6),('q',3)]:
            require(type(unit[key]) is int and (1 if key=='i' else 0)<=unit[key]<=maximum,'integer code/ID')
        require(unit['i'] not in units,'duplicate unit ID');units[unit['i']]=unit
        for key,cap,empty in [('s',280,False),('c',180,True),('r',180,True)]:
            require(isinstance(unit[key],str) and len(unit[key])<=cap and ((empty and unit[key]=='') or bool(unit[key].strip())),'text bound')
        for key,cap in [('d',16),('b',16),('e',6)]:
            arr=unit[key];require(isinstance(arr,list) and len(arr)<=cap,'list bound')
            if key in ['d','b']:require(all(type(i) is int and 1<=i<=160 for i in arr),'dependency IDs')
            else:require(bool(arr) and all(isinstance(i,str) and i in evidence_ids for i in arr),'unknown evidence ID')
            require(len(arr)==len(set(arr)),'duplicate references')
        require((unit['q']==0)==(unit['r']==''),'uncertainty/reason contradiction')
        require(unit['m']!=5 or unit['q']!=0,'unknown modality without uncertainty')
    done=set();visiting=set()
    def visit(uid):
        require(uid not in visiting,'dependency cycle')
        if uid in done:return
        visiting.add(uid)
        for dep in units[uid]['d']:
            require(dep in units,'unknown dependency');visit(dep)
        visiting.remove(uid);done.add(uid)
    for uid,unit in units.items():
        visit(uid)
        if unit['k']==5:require(bool(unit['d']) and units[unit['d'][0]]['k']==4,'role endpoint dependency')
        if unit['k']==7:require(len(unit['b'])>=2 and all(member in units and member!=uid for member in unit['b']),'relationship members')
        else:require(unit['b']==[],'members on nonrelationship')
    return value

def expand(value,source,table,finish_reason='stop'):
    validate(value,source,table,finish_reason)
    spans={sid:(start,end) for sid,start,end,_ in table['rows']}
    units=[]
    for u in value['u']:
        evidence=[]
        for sid in u['e']:
            start,end=spans[sid];quote=source[start:end]
            occurrence=sum(source.startswith(quote,pos) for pos in range(start+1))
            evidence.append(dict(span_id=sid,start=start,end=end,quote=quote,occurrence=occurrence))
        units.append(dict(id=u['i'],kind=KINDS[u['k']],assertion=u['s'],modality=MODALITIES[u['m']],applicability=u['c'],required_unit_ids=copy.deepcopy(u['d']),relationship_member_ids=copy.deepcopy(u['b']),uncertainty=UNCERTAINTIES[u['q']],uncertainty_reason=u['r'],evidence=evidence))
    return dict(schema_version='round13.expanded-inventory.v1',source_text_sha256=value['h'],span_table_sha256=value['t'],units=units,terminal_marker=value['z'],source_inventory_completeness='unverified',production_eligible=False,action_ready=False)

def contract(value,source,table):
    # Public inverse verifies every expanded field and resolved evidence against source.
    closed(value,['schema_version','source_text_sha256','span_table_sha256','units','terminal_marker','source_inventory_completeness','production_eligible','action_ready'])
    require(value.get('schema_version')=='round13.expanded-inventory.v1','expanded version')
    units=[]
    for u in value['units']:
        closed(u,['id','kind','assertion','modality','applicability','required_unit_ids','relationship_member_ids','uncertainty','uncertainty_reason','evidence'])
        for e in u['evidence']:closed(e,['span_id','start','end','quote','occurrence'])
        units.append(dict(i=u['id'],k=KINDS.index(u['kind']),s=u['assertion'],m=MODALITIES.index(u['modality']),c=u['applicability'],d=u['required_unit_ids'],b=u['relationship_member_ids'],e=[e['span_id'] for e in u['evidence']],q=UNCERTAINTIES.index(u['uncertainty']),r=u['uncertainty_reason']))
    result=dict(v=VERSION,h=value['source_text_sha256'],t=value['span_table_sha256'],u=units,z=value['terminal_marker'])
    require(expand(result,source,table)==value and canonical(expand(result,source,table))==canonical(value),'expanded evidence/field equality')
    return result

def build(source):
    table=span_table(source)
    user=dict(source_text=source,source_text_sha256=source_hash(source),span_table=table,span_table_sha256=digest(table))
    settings=strict_load((ROOT/'request-settings.json').read_text())
    body=copy.deepcopy(settings)
    body.update(messages=[dict(role='system',content=(ROOT/'stage-a.system.txt').read_text()),dict(role='user',content=canonical(user).decode())],response_format=dict(type='json_schema',json_schema=dict(name='compact_inventory',strict=True,schema=schema(source,table))))
    raw=canonical(body)
    require(len(raw)+1024<=40000,'full request overflow')
    return dict(body=body,table=table,body_bytes=len(raw),guarded_bytes=len(raw)+1024,request_sha256=hashlib.sha256(raw).hexdigest())


def validate_response(raw_content,finish_reason,source,table):
    require(isinstance(raw_content,str),"raw content must be text")
    value=strict_load(raw_content)
    validate(value,source,table,finish_reason)
    return dict(compact=value,expanded=expand(value,source,table,finish_reason))
