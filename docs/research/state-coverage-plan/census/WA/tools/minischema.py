"""Minimal Draft 2020-12 subset validator (type/enum/const/required/properties/additionalProperties/
items/pattern/minLength/minimum/maximum/minItems/uniqueItems/anyOf/allOf/if-then-else). Formats: date-time."""
import json, re, sys
from datetime import datetime
T={'object':dict,'array':list,'string':str,'boolean':bool,'null':type(None)}
def is_type(v,t):
    if t=='integer': return isinstance(v,int) and not isinstance(v,bool)
    if t=='number': return isinstance(v,(int,float)) and not isinstance(v,bool)
    return isinstance(v,T[t])
def errs(s,v,path=''):
    out=[]
    if 'type' in s:
        ts=s['type'] if isinstance(s['type'],list) else [s['type']]
        if not any(is_type(v,t) for t in ts): return [f'{path}: type {ts} got {type(v).__name__}']
    if 'const' in s and v!=s['const']: out.append(f'{path}: const {s["const"]!r}')
    if 'enum' in s and v not in s['enum']: out.append(f'{path}: enum {v!r}')
    if isinstance(v,str):
        if len(v)<s.get('minLength',0): out.append(f'{path}: minLength')
        if 'pattern' in s and not re.search(s['pattern'],v): out.append(f'{path}: pattern')
        if s.get('format')=='date-time':
            try: datetime.fromisoformat(v.replace('Z','+00:00'))
            except ValueError: out.append(f'{path}: date-time')
    if is_type(v,'number'):
        if 'minimum' in s and v<s['minimum']: out.append(f'{path}: minimum')
        if 'maximum' in s and v>s['maximum']: out.append(f'{path}: maximum')
    if isinstance(v,dict):
        for r in s.get('required',[]):
            if r not in v: out.append(f'{path}: missing {r}')
        props=s.get('properties',{})
        for k,x in v.items():
            if k in props: out+=errs(props[k],x,f'{path}.{k}')
            elif s.get('additionalProperties') is False: out.append(f'{path}: extra {k}')
            elif isinstance(s.get('additionalProperties'),dict): out+=errs(s['additionalProperties'],x,f'{path}.{k}')
    if isinstance(v,list):
        if len(v)<s.get('minItems',0): out.append(f'{path}: minItems')
        if s.get('uniqueItems') and len({json.dumps(x,sort_keys=True) for x in v})!=len(v): out.append(f'{path}: uniqueItems')
        if 'items' in s:
            for i,x in enumerate(v): out+=errs(s['items'],x,f'{path}[{i}]')
    if 'anyOf' in s and not any(not errs(x,v,path) for x in s['anyOf']): out.append(f'{path}: anyOf')
    for x in s.get('allOf',[]): out+=errs(x,v,path)
    if 'if' in s:
        out+=errs(s['then'],v,path) if not errs(s['if'],v,path) and 'then' in s else (errs(s['else'],v,path) if errs(s['if'],v,path) and 'else' in s else [])
    return out
if __name__=='__main__':
    schema=json.load(open(sys.argv[1])); n=0
    for f in sys.argv[2:]:
        recs=[json.loads(l) for l in open(f) if l.strip()] if f.endswith('.jsonl') else [json.load(open(f))]
        for i,r in enumerate(recs):
            for e in errs(schema,r): n+=1; print(f'{f}[{i}] {e}') if n<30 else None
    print('schema errors:',n)
