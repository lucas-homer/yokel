"""Strict canonical JSON and explicitly bounded closed-schema validation; no I/O at import."""
import copy, hashlib, json, math, re
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROUND=HERE.parent; BENCH=ROUND.parent; PROTO=ROUND/'protocol'
READY_SHA='ea8675ff9ad1e7400aebfc0ea49e64bae194ccf2ef22e207f8c7f9ff48b57843'
BASELINE_SHA='33bb7e130c32d0b6528d319d6d103b50d007f7ecab48b1e4b69f244d61587a56'
class Denied(ValueError): pass
def require(ok):
    if not ok: raise Denied('bounded validation failed')
def encode(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(raw): return hashlib.sha256(raw).hexdigest()
def digest(v): return sha(encode(v))
def file_hash(p): return sha(Path(p).read_bytes())
def strict(raw):
    def pairs(rows):
        out={}
        for k,v in rows: require(k not in out); out[k]=v
        return out
    def floating(v):
        n=float(v); require(math.isfinite(n)); return n
    return json.loads(raw,object_pairs_hook=pairs,parse_float=floating,parse_constant=lambda _:(_ for _ in ()).throw(Denied()))
def read(p): return strict(Path(p).read_bytes())
def schema_errors(value,schema,path='$'):
    errors=[]; declared=schema.get('type'); types=declared if isinstance(declared,list) else [declared]
    actual=('null' if value is None else 'boolean' if type(value) is bool else 'integer' if type(value) is int else 'number' if type(value) is float else 'string' if isinstance(value,str) else 'array' if isinstance(value,list) else 'object' if isinstance(value,dict) else 'unknown')
    if declared and actual not in types and not(actual=='integer' and 'number' in types): return [path+': type']
    if 'enum' in schema and value not in schema['enum']: errors.append(path+': enum')
    if actual=='object':
        props=schema.get('properties',{}); errors += [path+': required '+k for k in schema.get('required',[]) if k not in value]
        if schema.get('additionalProperties') is False: errors += [path+': extra '+k for k in value if k not in props]
        for k in value:
            if k in props: errors += schema_errors(value[k],props[k],path+'.'+k)
    if actual=='array':
        if not schema.get('minItems',0)<=len(value)<=schema.get('maxItems',float('inf')): errors.append(path+': size')
        for i,v in enumerate(value): errors+=schema_errors(v,schema.get('items',{}),path+'/'+str(i))
    if actual=='string' and not schema.get('minLength',0)<=len(value)<=schema.get('maxLength',float('inf')): errors.append(path+': length')
    if actual in ('integer','number') and not schema.get('minimum',float('-inf'))<=value<=schema.get('maximum',float('inf')): errors.append(path+': range')
    return errors
def verify_pin(path,want):
    require(file_hash(path)==(want['sha256'] if isinstance(want,dict) else want))
    if isinstance(want,dict) and 'bytes' in want:require(Path(path).stat().st_size==want['bytes'])
def verify_protocol():
    require(file_hash(PROTO/'READY.json')==READY_SHA)
    for name,want in read(PROTO/'READY.json')['files'].items():
        path=(PROTO/name).resolve();require(path.is_relative_to(PROTO.resolve()));verify_pin(path,want)
    for path,want in read(HERE/'input-pins.json')['files'].items():verify_pin(path,want)
def check_schema(node,depth=0):
    allowed={'type','properties','required','additionalProperties','enum','minimum','maximum','minLength','maxLength','items','minItems','maxItems'}
    require(isinstance(node,dict) and depth<=16 and not set(node)-allowed)
    for child in node.get('properties',{}).values():check_schema(child,depth+1)
    if 'items' in node:check_schema(node['items'],depth+1)
def verify_release():
    verify_protocol();release=read(ROUND/'implementation-release.json')
    require(release['status']=='APPROVED_OFFLINE_IMPLEMENTATION' and release['max_provider_calls']==1 and release['prior_nanousd']==1505990718 and release['reservation_nanousd']==200000000 and release['ceiling_nanousd']==2000000000 and release['provider_calls_authorized_by_this_file'] is False)
    required={str(PROTO/'READY.json'),str(ROUND/'review/protocol/READY.json'),str(ROUND/'scope.json'),str(ROUND/'prior-baseline.json'),str(ROUND/'sizing-decision.json')};require(required<=set(release['files']))
    for path,want in release['files'].items():verify_pin(path,want)
    ready=read(ROUND/'review/protocol/READY.json');require(ready['implementation_approved'] is True and ready['paid_release_approved'] is False and ready['reviewed_protocol_ready_sha256']==READY_SHA and not ready['blocking_findings'])
    for name,want in ready['files'].items():
        path=(ROUND/'review/protocol'/name).resolve();require(path.is_relative_to((ROUND/'review/protocol').resolve()));verify_pin(path,want)
    decision=read(ROUND/'sizing-decision.json');require(decision['protocol_ready_sha256']==READY_SHA and decision['max_calls']==1 and decision['tokenizer_matched'] is False)
