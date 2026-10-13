"""Released source-only inventory, exact span codec and operative whole-field guards."""
import copy
import common as c
CATEGORIES=('events','routes','requirements','identities','uncertainties','alternative_groups')
COLS=['id','kind','assertion','modality','applicability','uncertainty','uncertainty_reason','required_unit_ids','evidence']
SPAN=['start','end','occurrence']
WIRE='round10.inventory-span-tuples.v1'
def source_hash(text): c.require(isinstance(text,str) and text.strip()); return c.sha(text.encode())
def a_schema(text):
    s=c.read(c.PROTO/'stage-a.schema.json'); s['properties']['source_text_sha256']['enum']=[source_hash(text)]; c.expand(s,s['$defs']); return s
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
    restored={'schema_version':'round10.source-inventory.v1','source_text_sha256':source_hash(text),'units':units}
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

def b_schema(text,record,inventory):
    validate_a(text,inventory); s=c.read(c.PROTO/'stage-b.schema.template.json')
    s['properties']['source_text_sha256']['enum']=[source_hash(text)]; s['properties']['record_sha256']['enum']=[c.digest(record)]; s['properties']['inventory_sha256']['enum']=[c.digest(inventory)]
    ids=[u['id'] for u in inventory['units']]; s['properties']['mappings']={'type':'object','properties':{i:{'$ref':'#/$defs/m'} for i in ids},'required':ids,'additionalProperties':False}; c.expand(s,s['$defs']); return s

def validate_b(text,record,inventory,value):
    s=b_schema(text,record,inventory); c.require(not c.schema_errors(value,c.expand(s,s['$defs'])))
    _,allow=operative(record); mappings=value['mappings']; diagnostics=[]; effective={}; values={}
    for u in inventory['units']:
        i=u['id']; m=mappings[i]; pointers=m['operative_pointers']; c.require(m['reason'].strip() and len(pointers)==len(set(pointers)))
        c.require(set(pointers)<=set(allow)); values[i]=[{'pointer':p,'value':resolve(record,p),'value_sha256':c.digest(resolve(record,p))} for p in pointers]
        for p in pointers:c.require(resolve(record,p)==allow[p])
        if m['disposition']=='missing': c.require(not pointers)
        if m['disposition']=='matched':
            c.require(pointers and any(allow[p] not in (None,'',[],{}) for p in pointers) and u['uncertainty']=='none' and u['modality']!='unknown')
            c.require(all(mappings[d]['disposition']=='matched' for d in u['required_unit_ids']))
    index={u['id']:u for u in inventory['units']}
    def visit(i):
        if i in effective:return effective[i]
        u=index[i]; m=mappings[i]['disposition']; deps=[visit(d) for d in u['required_unit_ids']]
        if m=='unknown' or u['uncertainty']!='none' or u['modality']=='unknown' or 'unknown' in deps: status='unknown'
        elif any(d!='matched' for d in deps): status='incomplete'
        else: status=m
        effective[i]=status
        if status!=m:diagnostics.append({'unit_id':i,'model_disposition':m,'effective_disposition':status,'dependencies':u['required_unit_ids']})
        return status
    for i in index:visit(i)
    statuses=set(effective.values()); summary='unverified' if 'unknown' in statuses else 'not_complete' if statuses-{'matched'} else 'all_inventoried_units_matched'
    return {'structural_valid':True,'mapping_status':summary,'effective_dispositions':effective,'dependency_diagnostics':diagnostics,'known_defects':[i for i,m in mappings.items() if m['disposition'] in ('missing','mismatched')],'operative_values':values,'source_inventory_completeness':'unverified','whole_record_fidelity':'unverified','semantic_status':'unverified','production_eligible':False,'action_ready':False}

def request(settings,system,user,schema,name):
    body=copy.deepcopy(settings); body.update(messages=[{'role':'system','content':system},{'role':'user','content':c.encode(user).decode()}],response_format={'type':'json_schema','json_schema':{'name':name,'strict':True,'schema':schema}})
    size=len(c.encode(body)); return {'body':body,'body_bytes':size,'guarded_bytes':size+1024,'request_sha256':c.digest(body),'fits':size+1024<=40000}
def build_a(text):
    # Deliberately accepts only text, not record/audits/assembly/fixtures.
    return request(c.read(c.PROTO/'request-settings.json'),(c.PROTO/'stage-a.system.txt').read_text(),{'source_text':text,'source_text_sha256':source_hash(text)},a_schema(text),'source_inventory')
def build_b(text,record,inventory):
    c.require(record['source_text_sha256']==source_hash(text)); projected,_=operative(record); wire=wire_encode(text,inventory); wire_decode(text,wire,inventory)
    user={'source_text':text,'source_text_sha256':source_hash(text),'record_sha256':c.digest(record),'operative_record':projected,'operative_record_sha256':c.digest(projected),'inventory_wire':wire,'inventory_sha256':c.digest(inventory)}
    return request(c.read(c.PROTO/'request-settings.json'),(c.PROTO/'stage-b.system.txt').read_text(),user,b_schema(text,record,inventory),'source_mapping')
