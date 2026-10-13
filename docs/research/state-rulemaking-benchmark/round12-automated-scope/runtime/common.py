"""Strict canonical JSON and explicitly bounded closed-schema validation; no I/O at import."""
import copy, hashlib, json, math, re
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROUND=HERE.parent; BENCH=ROUND.parent; PROTO=ROUND/'protocol'
READY_SHA='be674e8d2dc1240bc445acccdd4e70f52319584017e52ccb7649938cc679a7a9'
BASELINE_SHA='37fce781c7477b80a38dfcd323e2b44851837cfbd0e14bcface0846a91c3a205'
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
ALLOWED={'type','properties','required','additionalProperties','enum','minimum','maximum','minLength','maxLength','items','minItems','maxItems','$defs','$ref'}
def expand(schema,definitions):
    require(isinstance(schema,dict) and schema.get('$defs')==definitions and set(definitions)<= {'e','u','m','s','d'})
    def walk(n,depth=0,chain=()):
        require(isinstance(n,dict) and depth<=32 and not set(n)-ALLOWED)
        if '$ref' in n:
            ref=n['$ref']; require(set(n)=={'$ref'} and ref in {'#/$defs/'+k for k in definitions} and ref not in chain and len(chain)<8)
            return walk(definitions[ref.rsplit('/',1)[1]],depth+1,chain+(ref,))
        out={}
        for k,v in n.items():
            if k=='$defs': require(depth==0)
            elif k=='properties': require(isinstance(v,dict)); out[k]={x:walk(y,depth+1,chain) for x,y in v.items()}
            elif k=='items': out[k]=walk(v,depth+1,chain)
            else: out[k]=copy.deepcopy(v)
        return out
    # Check unused definitions too: no unsupported keyword can be silently ignored.
    for name,node in definitions.items(): walk(node,1,('#/$defs/'+name,))
    return walk(schema)
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
    if isinstance(want,dict) and 'bytes' in want: require(Path(path).stat().st_size==want['bytes'])
def verify_package(folder,ready,kind='files'):
    value=read(folder/ready)
    for n,want in value[kind].items():
        p=(folder/n).resolve(); require(p.is_relative_to(folder.resolve()) and 'reference' not in p.relative_to(ROUND).parts); verify_pin(p,want)
def verify_release():
    require(file_hash(PROTO/'READY.json')==READY_SHA)
    release=read(ROUND/'implementation-release.json')
    require(release['state']=='approved_offline_implementation' and release['protocol_ready_sha256']==READY_SHA and release['scope_sha256']==file_hash(ROUND/'scope.json'))
    for name,key in [('protocol/SOURCE-READY.json','source_binding_ready_sha256'),('review/protocol-revised/READY.json','protocol_review_ready_sha256'),('candidate/READY.json','candidate_ready_sha256'),('pre-evaluation-freeze.json','pre_evaluation_freeze_sha256')]:require(file_hash(ROUND/name)==release[key])
    verify_package(PROTO,'READY.json'); verify_package(PROTO,'SOURCE-READY.json'); verify_package(ROUND/'review/protocol-revised','READY.json')
    verify_package(ROUND/'candidate','READY.json','artifacts')
    source=read(ROUND/'source/READY.json'); binding=read(PROTO/'SOURCE-BINDING.json')
    verify_pin(ROUND/'source/READY.json',binding['source_archive_ready']);verify_pin(ROUND/'source/FRAME.json',binding['source_archive_frame'])
    for want in source['artifacts'].values():
        p=(ROUND/'source'/want['path']).resolve();require(p.is_relative_to((ROUND/'source').resolve()));verify_pin(p,want)
    for p,h in read(HERE/'input-pins.json')['files'].items():require('reference' not in Path(p).relative_to(ROUND).parts if Path(p).is_relative_to(ROUND) else True);verify_pin(p,h)
