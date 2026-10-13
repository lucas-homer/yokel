"""Frozen full-source/candidate artificial sizing; no request dispatch or semantic oracle."""
import copy
import hashlib
import json
from pathlib import Path
from scope_codec import canonical, decode, digest, encode

ROOT=Path(__file__).resolve().parent
ROUND=ROOT.parent
INITIAL=ROOT/'revisions/initial'
def load(path):return json.loads(path.read_text())
source=(ROUND/'source/26-19-016.txt').read_bytes().decode('utf-8')
record=load(ROUND/'candidate/candidate.json')
source_hash=hashlib.sha256(source.encode()).hexdigest()
def project(value):
    if isinstance(value,dict):return {k:project(v) for k,v in value.items() if k not in ('evidence','coverage')}
    if isinstance(value,list):return [project(v) for v in value]
    return value
operative=project(record)
base=dict(source_text=source,source_text_sha256=source_hash,record_sha256=digest(record),operative_record=operative,operative_record_sha256=digest(operative))
settings=load(ROOT/'request-settings.json')
wirecon=load(ROOT/'inventory-wire-contract.json')
def body(user,ids,folder):
    schema=load(folder/'stage-b.schema.template.json')
    for key,val in {'__SOURCE_SHA256__':source_hash,'__RECORD_SHA256__':digest(record),'__OPERATIVE_SHA256__':digest(operative),'__INVENTORY_SHA256__':user['inventory_sha256'],'__SCOPE_SHA256__':user['scope_sha256']}.items():
        schema=json.loads(json.dumps(schema).replace(key,val))
    schema['properties']['mappings'].update(properties={i:{'$ref':'#/$defs/m'} for i in ids},required=ids)
    req=copy.deepcopy(settings)
    req.update(messages=[dict(role='system',content=(folder/'stage-b.system.txt').read_text()),dict(role='user',content=canonical(user).decode())],response_format={'type':'json_schema','json_schema':dict(name='source_mapping',strict=True,schema=schema)})
    raw=canonical(req)
    return dict(body_bytes=len(raw),guarded_bytes=len(raw)+1024,fits=len(raw)+1024<=40000,request_sha256=hashlib.sha256(raw).hexdigest())
profiles=[]
for label,al,apl,rl,ql in [('concise',70,20,50,60),('modest',90,30,100,94),('longer',150,60,180,160)]:
    for n in [24,32,40,48,64]:
        ids=[f'u{i:03}' for i in range(1,n+1)];units=[];scopes={};spans=[]
        for j,uid in enumerate(ids):
            start=(j*59)%(len(source)-ql);quote=source[start:start+ql];occurrence=sum(source.startswith(quote,k) for k in range(start+1));ev=dict(quote=quote,occurrence=occurrence)
            units.append(dict(id=uid,kind='instruction',assertion='a'*al,modality='informational',applicability='a'*apl,uncertainty='none',uncertainty_reason='',required_unit_ids=[],evidence=[ev]))
            scopes[uid]=dict(category='required_participation',basis='participation_function',reason='r'*rl,evidence=[ev]);spans.append([[start,start+ql,occurrence]])
        inventory=dict(schema_version='round12.source-inventory.v1',source_text_sha256=source_hash,units=units)
        c=dict(schema_version='round12.source-scope.v1',source_text_sha256=source_hash,inventory_sha256=digest(inventory),scopes=scopes)
        awire=dict(schema_version=wirecon['schema_version'],source_text_sha256=source_hash,columns=wirecon['columns'],evidence_columns=wirecon['evidence_columns'],units=[[u[k] if k!='evidence' else spans[j] for k in wirecon['columns']] for j,u in enumerate(units)])
        cwire=encode(c,source,digest(inventory),ids);assert decode(cwire,source,digest(inventory),ids,c)==c
        common=base|dict(inventory_wire=awire,inventory_sha256=digest(inventory),scope_sha256=digest(c))
        profiles.append(dict(profile=label,units=n,assertion_chars=al,applicability_chars=apl,reason_chars=rl,quote_chars=ql,evidence_per_unit=1,dependencies_per_unit=0,C_exact_roundtrip=True,original_full_C=body(common|dict(scope=c),ids,INITIAL),revised_scope_wire=body(common|dict(scope_wire=cwire),ids,ROOT)))
result=dict(interpretation='Artificial schema/transport size profiles only, not semantic inventories, model performance or guaranteed actual fit. Complete same source and operative candidate retained; exact original/revised envelopes plus 1024 guard.',source_sha256=source_hash,candidate_raw_sha256=hashlib.sha256((ROUND/'candidate/candidate.json').read_bytes()).hexdigest(),record_canonical_sha256=digest(record),operative_canonical_sha256=digest(operative),operative_canonical_bytes=len(canonical(operative)),guard=40000,profiles=profiles)
print(json.dumps(result,indent=2))
