"""Released source-only inventory, exact span codec and operative whole-field guards."""
import copy
import common as c
CATEGORIES=('events','routes','requirements','identities','uncertainties','alternative_groups')
COLS=['id','kind','assertion','modality','applicability','uncertainty','uncertainty_reason','required_unit_ids','evidence']
SPAN=['start','end','occurrence']
WIRE='round12.inventory-span-tuples.v1'
def source_hash(text): c.require(isinstance(text,str) and text.strip()); return c.sha(text.encode())
def a_schema(text):
    return schema('a',text)
def starts(text,quote):
    c.require(isinstance(quote,str) and quote.strip()); positions=[]; start=0
    while True:
        pos=text.find(quote,start)
        if pos<0:return positions
        positions.append(pos); start=pos+1

def selector(text,e):
    c.require(isinstance(e,dict) and set(e)=={'quote','occurrence'} and type(e['occurrence']) is int)
    positions=starts(text,e['quote']); c.require(1<=e['occurrence']<=len(positions)); start=positions[e['occurrence']-1]
    return [start,start+len(e['quote']),e['occurrence']]
def validate_a(text,inventory):
    s=a_schema(text); c.require(not c.schema_errors(inventory,c.expand(s,s['$defs'])))
    units=inventory['units']; ids=[u['id'] for u in units]; c.require(len(ids)==len(set(ids)) and all(c.re.fullmatch('u00[1-9]|u0[1-5][0-9]|u06[0-4]',i) for i in ids))
    index={u['id']:u for u in units}; spans={}; done=set(); active=set()
    def visit(i):
        c.require(i not in active)
        if i in done:return
        active.add(i)
        for dep in index[i]['required_unit_ids']:visit(dep)
        active.remove(i); done.add(i)
    for u in units:
        c.require(u['assertion'].strip() and u['applicability'].strip())
        c.require((u['uncertainty']=='none' and u['uncertainty_reason']=='') or (u['uncertainty']!='none' and bool(u['uncertainty_reason'].strip())))
        deps=u['required_unit_ids']; c.require(len(deps)==len(set(deps)) and u['id'] not in deps and set(deps)<=set(ids))
        spans[u['id']]=[selector(text,e) for e in u['evidence']]
    for i in ids:visit(i)
    return {'structural_valid':True,'source_text_sha256':source_hash(text),'inventory_sha256':c.digest(inventory),'unit_count':len(units),'evidence_spans':spans,'source_inventory_completeness':'unverified','semantic_status':'unverified','production_eligible':False,'action_ready':False}
def wire_encode(text,inventory):
    checked=validate_a(text,inventory)
    return {'schema_version':WIRE,'source_text_sha256':source_hash(text),'columns':COLS[:],'evidence_columns':SPAN[:],'units':[[copy.deepcopy(u[k]) if k!='evidence' else checked['evidence_spans'][u['id']] for k in COLS] for u in inventory['units']]}
def wire_decode(text,wire,frozen):
    c.require(isinstance(wire,dict) and set(wire)=={'schema_version','source_text_sha256','columns','evidence_columns','units'} and wire['schema_version']==WIRE and wire['source_text_sha256']==source_hash(text) and wire['columns']==COLS and wire['evidence_columns']==SPAN and isinstance(wire['units'],list))
    units=[]
    for row in wire['units']:
        c.require(isinstance(row,list) and len(row)==9); u=dict(zip(COLS,copy.deepcopy(row))); c.require(isinstance(u['evidence'],list)); evidence=[]
        for span in u['evidence']:
            c.require(isinstance(span,list) and len(span)==3 and all(type(n) is int for n in span)); start,end,occ=span
            c.require(0<=start<end<=len(text) and occ>=1); e={'quote':text[start:end],'occurrence':occ}; c.require(selector(text,e)==span); evidence.append(e)
        u['evidence']=evidence; units.append(u)
    restored={'schema_version':'round12.source-inventory.v1','source_text_sha256':source_hash(text),'units':units}
    validate_a(text,restored); c.require(c.encode(restored)==c.encode(frozen) and c.digest(restored)==c.digest(frozen)); return restored

def fields(record):
    result={}
    def visit(item,pointer):
        for k,v in item.items():
            if k in ('id','evidence'):continue
            p=pointer+'/'+k.replace('~','~0').replace('/','~1')
            if k in ('timing','components'):
                for n,child in enumerate(v):visit(child,p+'/'+str(n))
            else:result[p]=v
    for category in CATEGORIES:
        for n,item in enumerate(record[category]):visit(item,f'/{category}/{n}')
    return result

def projection(node):
    if isinstance(node,dict):return {k:projection(v) for k,v in node.items() if k not in ('evidence','coverage')}
    if isinstance(node,list):return [projection(v) for v in node]
    return copy.deepcopy(node)
def identities(node,p=''):
    found={}
    if isinstance(node,dict):
        if 'id' in node: found[node['id']]=p
        for k,v in node.items():
            child=identities(v,p+'/'+k.replace('~','~0').replace('/','~1')); c.require(not found.keys()&child.keys()); found.update(child)
    elif isinstance(node,list):
        for n,v in enumerate(node):
            child=identities(v,p+'/'+str(n)); c.require(not found.keys()&child.keys()); found.update(child)
    return found

def resolve(record,pointer):
    c.require(isinstance(pointer,str) and pointer.startswith('/')); node=record
    for token in pointer.split('/')[1:]:
        c.require(not c.re.search('~(?![01])',token)); token=token.replace('~1','/').replace('~0','~')
        if isinstance(node,list): c.require(c.re.fullmatch('0|[1-9][0-9]*',token) is not None and int(token)<len(node)); node=node[int(token)]
        else: c.require(isinstance(node,dict) and token in node); node=node[token]
    return node

def operative(record):
    out=projection(record); values=fields(record)
    c.require(fields(out)==values and identities(out)==identities(record))
    for p,v in values.items(): c.require(resolve(record,p)==v and resolve(out,p)==v)
    return out,values


import scope_codec as sc
FLAGS={'source_inventory_completeness':'unverified','whole_record_fidelity':'unverified','semantic_status':'unverified','production_eligible':False,'action_ready':False}
def schema(stage,text,record=None,inventory=None,scope=None):
    s=c.read(c.PROTO/f'stage-{stage}.schema.template.json')
    replacements={'__SOURCE_SHA256__':source_hash(text)}
    if record is not None:
        projected,_=operative(record);replacements.update(__RECORD_SHA256__=c.digest(record),__OPERATIVE_SHA256__=c.digest(projected))
    if inventory is not None:replacements['__INVENTORY_SHA256__']=c.digest(inventory)
    if scope is not None:replacements['__SCOPE_SHA256__']=c.digest(scope)
    def substitute(v):
        if isinstance(v,dict):return {k:substitute(x) for k,x in v.items()}
        if isinstance(v,list):return [substitute(x) for x in v]
        if isinstance(v,str):return replacements.get(v,v)
        return v
    s=substitute(s)
    if stage in ('c','b'):
        c.require(inventory is not None);ids=[u['id'] for u in inventory['units']];field,ref=('scopes','s') if stage=='c' else ('mappings','m')
        s['properties'][field]={'type':'object','properties':{i:{'$ref':'#/$defs/'+ref} for i in ids},'required':ids,'additionalProperties':False}
    c.require('__' not in c.encode(s).decode());c.expand(s,s['$defs']);return s
def validate_scope(text,inventory,scope):
    validate_a(text,inventory);s=schema('c',text,inventory=inventory);c.require(not c.schema_errors(scope,c.expand(s,s['$defs'])))
    ids=[u['id'] for u in inventory['units']];sc.validate_c(scope,text,c.digest(inventory),ids)
    policy=c.read(c.PROTO/'policy.json')
    for u in inventory['units']:
        x=scope['scopes'][u['id']];c.require(x['category'] in policy['allowed_scope_by_kind'][u['kind']] and policy['scope_basis_by_category'][x['category']]==x['basis'])
    return {'structural_valid':True,'scope_sha256':c.digest(scope),'inventory_sha256':c.digest(inventory),'unit_count':len(ids),**FLAGS}
def scope_wire(text,inventory,scope):
    validate_scope(text,inventory,scope);ids=[u['id'] for u in inventory['units']];wire=sc.encode(scope,text,c.digest(inventory),ids)
    restored=sc.decode(wire,text,c.digest(inventory),ids,scope);c.require(c.encode(restored)==c.encode(scope) and c.digest(restored)==c.digest(scope));return wire

def recovery(text,record,inventory,scope,mappings):
    validate_scope(text,inventory,scope);_,allow=operative(record);index={u['id']:u for u in inventory['units']};c.require(set(mappings)==set(index))
    effective={};values={};diagnostics=[]
    for i,u in index.items():
        m=mappings[i];pointers=m['operative_pointers'];c.require(m['reason'].strip() and len(pointers)==len(set(pointers)) and set(pointers)<=set(allow))
        values[i]=[{'pointer':p,'value':resolve(record,p),'value_sha256':c.digest(resolve(record,p))} for p in pointers]
        for p in pointers:c.require(resolve(record,p)==allow[p])
        if m['disposition']=='missing':c.require(not pointers)
        if m['disposition']=='mismatched':c.require(bool(pointers))
        if m['disposition']=='matched':
            c.require(pointers and any(allow[p] not in (None,'',[],{}) for p in pointers) and u['uncertainty']=='none' and u['modality']!='unknown')
            c.require(all(mappings[d]['disposition']=='matched' for d in u['required_unit_ids']))
    def visit(i):
        if i in effective:return effective[i]
        u=index[i];raw=mappings[i]['disposition'];deps=[visit(d) for d in u['required_unit_ids']]
        status='unknown' if raw=='unknown' or u['uncertainty']!='none' or u['modality']=='unknown' or 'unknown' in deps else 'incomplete' if any(d!='matched' for d in deps) else raw
        effective[i]=status
        if status!=raw:diagnostics.append({'unit_id':i,'model_disposition':raw,'effective_disposition':status,'dependencies':u['required_unit_ids']})
        return status
    for i in index:visit(i)
    required=[i for i in index if scope['scopes'][i]['category'] in ('required_participation','identifying_context')]
    known=[i for i in index if mappings[i]['disposition'] in ('missing','mismatched')];required_known=[i for i in known if i in required]
    unresolved=[i for i in index if scope['scopes'][i]['category']=='unresolved_scope']
    status='unverified' if unresolved or any(effective[i]=='unknown' for i in required) else 'not_complete' if required_known or any(effective[i]!='matched' for i in required) else 'all_required_inventoried_units_matched'
    return {'structural_valid':True,'mapping_status':status,'effective_dispositions':effective,'dependency_diagnostics':diagnostics,'known_defects':known,'known_required_defects':required_known,'required_defects':required_known,'unresolved_scope_units':unresolved,'background_diagnostics':{i:effective[i] for i in index if scope['scopes'][i]['category']=='retained_background'},'operative_values':values,**FLAGS}
def validate_b(text,record,inventory,scope,value):
    validate_scope(text,inventory,scope);s=schema('b',text,record,inventory,scope);c.require(not c.schema_errors(value,c.expand(s,s['$defs'])))
    return recovery(text,record,inventory,scope,value['mappings'])
def validate_d(text,record,value):
    s=schema('d',text,record);c.require(not c.schema_errors(value,c.expand(s,s['$defs'])))
    inv={'schema_version':'round12.source-inventory.v1','source_text_sha256':source_hash(text),'units':[x['source_unit'] for x in value['units']]};validate_a(text,inv)
    scope={'schema_version':'round12.source-scope.v1','source_text_sha256':source_hash(text),'inventory_sha256':c.digest(inv),'scopes':{x['source_unit']['id']:x['scope'] for x in value['units']}}
    mappings={x['source_unit']['id']:x['mapping'] for x in value['units']};result=recovery(text,record,inv,scope,mappings)
    return {**result,'direct_inventory_sha256':c.digest(inv),'direct_scope_sha256':c.digest(scope)}
def validate(stage,text,record,inventory,scope,value):
    if stage=='D':return validate_d(text,record,value)
    if stage=='A':return validate_a(text,value)
    if stage=='C':return validate_scope(text,inventory,value)
    c.require(stage=='B');return validate_b(text,record,inventory,scope,value)

def request(stage,user,response_schema):
    fields=c.read(c.PROTO/'boundaries.json')['exact_user_fields'][stage];c.require(set(user)==set(fields))
    settings=c.read(c.PROTO/'request-settings.json');c.require(settings=={'model':'openai/gpt-6.1-sol','stream':False,'reasoning':{'effort':'low'},'max_tokens':8192,'provider':{'only':['openai'],'order':['openai'],'require_parameters':True,'allow_fallbacks':False,'max_price':{'prompt':2,'completion':10}}})
    names={'D':'direct_verification','A':'source_inventory','C':'source_scope','B':'source_mapping'}
    body=copy.deepcopy(settings);body.update(messages=[{'role':'system','content':(c.PROTO/f'stage-{stage.lower()}.system.txt').read_text()},{'role':'user','content':c.encode(user).decode()}],response_format={'type':'json_schema','json_schema':{'name':names[stage],'strict':True,'schema':response_schema}})
    size=len(c.encode(body));return {'body':body,'body_bytes':size,'guarded_bytes':size+1024,'request_sha256':c.digest(body),'fits':size+1024<=40000}
def source_user(text):return {'source_text':text,'source_text_sha256':source_hash(text)}
def candidate_user(text,record):
    c.require(record['source_text_sha256']==source_hash(text));projected,_=operative(record)
    return {**source_user(text),'record_sha256':c.digest(record),'operative_record':projected,'operative_record_sha256':c.digest(projected)}
def inventory_user(text,inventory):
    wire=wire_encode(text,inventory);wire_decode(text,wire,inventory)
    return {**source_user(text),'inventory_wire':wire,'inventory_sha256':c.digest(inventory)}
def build_a(text):return request('A',source_user(text),schema('a',text))
def build_d(text,record):return request('D',candidate_user(text,record),schema('d',text,record))
def build_c(text,inventory):return request('C',inventory_user(text,inventory),schema('c',text,inventory=inventory))
def build_b(text,record,inventory,scope):
    user={**candidate_user(text,record),**inventory_user(text,inventory),'scope_wire':scope_wire(text,inventory,scope),'scope_sha256':c.digest(scope)}
    return request('B',user,schema('b',text,record,inventory,scope))
