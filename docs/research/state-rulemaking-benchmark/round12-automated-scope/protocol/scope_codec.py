"""Bounded C-only lossless transport probe. No provider/request runtime."""
import hashlib
import json
import re

C_VERSION = 'round12.source-scope.v1'
WIRE_VERSION = 'round12.scope-span-tuples.v1'
COLUMNS = ['id', 'category', 'basis', 'reason', 'evidence']
EVIDENCE_COLUMNS = ['start', 'end', 'occurrence']
CATEGORIES = ['required_participation', 'identifying_context', 'retained_background', 'unresolved_scope']
BASES = ['participation_function', 'identifies_proceeding', 'substantive_background_only', 'uncertain_source_function']

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def require(ok, message):
    if not ok:
        raise ValueError(message)

def closed(obj, keys):
    require(isinstance(obj,dict) and set(obj)==set(keys),'closed keys')

def text(value, cap):
    require(isinstance(value,str) and bool(value.strip()) and len(value)<=cap,'text bound')

def starts(source, quote):
    return [i for i in range(len(source)) if source.startswith(quote,i)]

def ids_valid(ids):
    require(isinstance(ids,list) and 1<=len(ids)<=64 and all(isinstance(i,str) and re.fullmatch(r'u00[1-9]|u0[1-5][0-9]|u06[0-4]',i) for i in ids) and len(set(ids))==len(ids),'ID schedule')

def validate_c(c, source, inventory_hash, ids):
    ids_valid(ids)
    closed(c,['schema_version','source_text_sha256','inventory_sha256','scopes'])
    require(isinstance(source,str) and source,'source text')
    require(isinstance(inventory_hash,str) and re.fullmatch('[0-9a-f]{64}',inventory_hash),'inventory hash')
    require(c['schema_version']==C_VERSION and c['source_text_sha256']==hashlib.sha256(source.encode()).hexdigest() and c['inventory_sha256']==inventory_hash,'C binding')
    require(isinstance(c['scopes'],dict) and set(c['scopes'])==set(ids),'scope totality')
    for scope in c['scopes'].values():
        closed(scope,['category','basis','reason','evidence'])
        require(scope['category'] in CATEGORIES,'category')
        require(scope['basis']==BASES[CATEGORIES.index(scope['category'])],'basis correspondence')
        text(scope['reason'],360)
        require(isinstance(scope['evidence'],list) and 1<=len(scope['evidence'])<=3,'evidence bound')
        for e in scope['evidence']:
            closed(e,['quote','occurrence']);text(e['quote'],320)
            require(type(e['occurrence']) is int and 1<=e['occurrence']<=10000,'occurrence')
            require(len(starts(source,e['quote']))>=e['occurrence'],'exact evidence')

def encode(c, source, inventory_hash, ids):
    validate_c(c,source,inventory_hash,ids)
    rows=[]
    for uid in ids:
        s=c['scopes'][uid];spans=[]
        for e in s['evidence']:
            start=starts(source,e['quote'])[e['occurrence']-1]
            spans.append([start,start+len(e['quote']),e['occurrence']])
        rows.append([uid,CATEGORIES.index(s['category']),BASES.index(s['basis']),s['reason'],spans])
    return dict(schema_version=WIRE_VERSION,source_text_sha256=c['source_text_sha256'],inventory_sha256=c['inventory_sha256'],columns=COLUMNS.copy(),evidence_columns=EVIDENCE_COLUMNS.copy(),scopes=rows)

def decode(wire, source, inventory_hash, ids, frozen_c):
    validate_c(frozen_c,source,inventory_hash,ids)
    closed(wire,['schema_version','source_text_sha256','inventory_sha256','columns','evidence_columns','scopes'])
    require(wire['schema_version']==WIRE_VERSION and wire['columns']==COLUMNS and wire['evidence_columns']==EVIDENCE_COLUMNS,'wire version/columns')
    require(wire['source_text_sha256']==frozen_c['source_text_sha256'] and wire['inventory_sha256']==inventory_hash,'wire binding')
    require(isinstance(wire['scopes'],list) and len(wire['scopes'])==len(ids),'wire totality')
    scopes={}
    for row,uid in zip(wire['scopes'],ids):
        require(isinstance(row,list) and len(row)==5 and row[0]==uid and uid not in scopes,'row schedule/width')
        require(type(row[1]) is int and 0<=row[1]<4 and type(row[2]) is int and 0<=row[2]<4,'enum codes')
        require(isinstance(row[4],list) and 1<=len(row[4])<=3,'span list')
        evidence=[]
        for span in row[4]:
            require(isinstance(span,list) and len(span)==3 and all(type(v) is int for v in span),'span integers')
            start,end,occurrence=span
            require(0<=start<end<=len(source) and 1<=occurrence<=10000,'span bound')
            quote=source[start:end];positions=starts(source,quote)
            require(len(positions)>=occurrence and positions[occurrence-1]==start,'span occurrence')
            evidence.append(dict(quote=quote,occurrence=occurrence))
        scopes[uid]=dict(category=CATEGORIES[row[1]],basis=BASES[row[2]],reason=row[3],evidence=evidence)
    c=dict(schema_version=C_VERSION,source_text_sha256=wire['source_text_sha256'],inventory_sha256=wire['inventory_sha256'],scopes=scopes)
    validate_c(c,source,inventory_hash,ids)
    require(c==frozen_c and canonical(c)==canonical(frozen_c) and digest(c)==digest(frozen_c),'frozen C equality/hash')
    return c
