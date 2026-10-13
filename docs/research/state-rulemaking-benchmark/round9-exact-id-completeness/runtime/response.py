"""Exact-key wire schema, explicit local-ref expansion and lossless legacy host validation."""
import copy
import common as c
WIRE_VERSION='round9.exact-id.record_verdict.v1'
CATEGORIES=('events','routes','requirements','identities','uncertainties','alternative_groups')
DEFS=c.read(c.PROTO/'wi70-response.schema.json')['$defs']
ALLOWED={'type','properties','required','additionalProperties','enum','pattern','minimum','maximum','minLength','maxLength','items','minItems','maxItems','$schema','title','$defs','$ref'}
def schedule(record,payload_sha256):
    items=[]
    for category in CATEGORIES:
        if not isinstance(record.get(category),list):raise c.InvalidInput('invalid item category')
        for n,item in enumerate(record[category]):
            pointer=f'/{category}/{n}';items.append({'item_id':item.get('id'),'pointer':pointer,'kind':category})
            nested='timing' if category=='events' else 'components' if category=='routes' else None
            if nested:
                if not isinstance(item.get(nested),list):raise c.InvalidInput('invalid nested category')
                for k,child in enumerate(item[nested]):items.append({'item_id':child.get('id'),'pointer':f'{pointer}/{nested}/{k}','kind':nested})
    ids=[item['item_id'] for item in items]
    if not 1<=len(ids)<=1000 or any(not isinstance(i,str) or not i.strip() or i=='coverage' for i in ids) or len(set(ids))!=len(ids):raise c.InvalidInput('invalid/colliding/reserved/empty schedule IDs')
    return {'schema_version':'round9.exact-id.schedule.v1','document_id':record['document_id'],'record_sha256':c.digest(record),'payload_sha256':payload_sha256,'expected_item_count':len(ids),'items':items,'sorted_ids':sorted(ids)}

def schema_for(schedule):
    ids=schedule['sorted_ids']
    if not isinstance(ids,list) or not 1<=len(ids)<=1000 or any(not isinstance(i,str) or not i.strip() or i=='coverage' for i in ids) or ids!=sorted(set(ids)):raise c.InvalidInput('schema requires a checked exact sorted schedule')
    schema=copy.deepcopy(c.p.VERDICT_SCHEMA)
    # Each evidence array is exactly the approved shared definition before substitution.
    def pool(node):
        if isinstance(node,dict):
            for key,value in list(node.items()):
                if key=='evidence':
                    if value!=DEFS['e']:raise c.InvalidInput('unreviewed evidence schema')
                    node[key]={'$ref':'#/$defs/e'}
                else:pool(value)
        elif isinstance(node,list):
            for value in node:pool(value)
    pool(schema)
    schema['properties']['schema_version']['enum']=[WIRE_VERSION]
    schema['properties']['document_id']['enum']=[schedule['document_id']]
    schema['properties']['payload_sha256']['enum']=[schedule['payload_sha256']]
    schema['properties']['assessments']={'type':'object','properties':{i:{'$ref':'#/$defs/a'} for i in ids},'required':ids,'additionalProperties':False}
    schema['properties']['contradictions']['items']['properties']['item_ids']['items']['enum']=ids
    schema['$defs']=copy.deepcopy(DEFS);return schema

def expand(schema):
    if not isinstance(schema,dict) or schema.get('$defs')!=DEFS:raise c.InvalidInput('definitions must be exact approved a/e definitions')
    def walk(node,depth=0,chain=()):
        if not isinstance(node,dict):raise c.InvalidInput('schema node must be object')
        if '$ref' in node:
            ref=node['$ref']
            if set(node)!={'$ref'} or ref not in ('#/$defs/a','#/$defs/e') or ref in chain or depth>8 or len(chain)>=8:raise c.InvalidInput('unsupported/sibling/cyclic/deep local reference')
            return walk(schema['$defs'][ref.rsplit('/',1)[1]],depth,chain+(ref,))
        if set(node)-ALLOWED:raise c.InvalidInput('unreviewed schema keyword')
        out={}
        for key,value in node.items():
            if key=='$defs':
                if depth!=0:raise c.InvalidInput('nested definitions unsupported')
                continue
            if key=='properties':out[key]={name:walk(child,depth+2,chain) for name,child in value.items()}
            elif key=='items':out[key]=walk(value,depth+1,chain)
            else:out[key]=copy.deepcopy(value)
        return out
    return walk(schema)

def validate_response(raw,source,assembled):
    try:
        if not isinstance(source,dict) or not isinstance(assembled,dict) or not isinstance(assembled.get('record'),dict):raise c.InvalidInput('source/assembled input shape')
        common=c.p.verification_payload(source,assembled);registry=schedule(assembled['record'],common['payload_sha256'])
        wire=c.strict(raw);errors=c.p.schema_errors(wire,expand(schema_for(registry)))
        if errors:return {'structural_valid':False,'errors':errors,'legacy_verdict':None,'semantic_status':'unverified','production_eligible':False,'action_ready':False}
        legacy=copy.deepcopy(wire);legacy['schema_version']='round7.record_verdict.v1';legacy['assessments']=[{'item_id':i,**copy.deepcopy(wire['assessments'][i])} for i in registry['sorted_ids']]
        checked=c.p.validate_verdict(source,assembled,legacy);valid=checked['valid']
        return {'structural_valid':valid,'errors':checked['errors'],'legacy_verdict':legacy if valid else None,'normalized_verdict':checked['normalized_verdict'],'semantic_status':'unverified','review_required':True,'production_eligible':False,'action_ready':False}
    except (ValueError,KeyError,TypeError,AttributeError,IndexError) as error:return {'structural_valid':False,'errors':[str(error)],'legacy_verdict':None,'semantic_status':'unverified','production_eligible':False,'action_ready':False}
