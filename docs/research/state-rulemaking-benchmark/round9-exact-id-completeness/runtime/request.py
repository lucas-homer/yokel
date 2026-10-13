"""Bounded WI offline request projection. Private audit/fixture bundles are never arguments."""
import copy
import common as c
import response
SIZES=c.read(c.PROTO/'wire-size-check.json')
BASELINE=c.read(SIZES['baseline_request_path'])
ASSEMBLED=c.read(next(x['path'] for x in c.read(c.PROTO/'PROVENANCE.json')['inputs'] if x['path'].endswith('/assembled.json')))
def build(source,assembled):
    common=c.p.verification_payload(source,assembled);wire=c.strict(BASELINE['messages'][1]['content'])['payload']
    if c.codec.restore(wire,common['payload_sha256'])!=common['payload']:raise c.InvalidInput('bounded baseline differs from selected source/record')
    registry=response.schedule(assembled['record'],common['payload_sha256']);schema=response.schema_for(registry);response.expand(schema)
    body={k:copy.deepcopy(BASELINE[k]) for k in ('model','stream','max_tokens','reasoning','provider')}
    body['messages']=[{'role':'system','content':BASELINE['messages'][0]['content']+'\n'+SIZES['added_neutral_instruction']},{'role':'user','content':BASELINE['messages'][1]['content']}]
    body['response_format']=copy.deepcopy(BASELINE['response_format']);body['response_format']['json_schema']['schema']=schema
    estimate=len(c.encode(body))+1024
    if estimate>40000:raise c.InvalidInput('full request over unchanged guard; no clipping/fallback')
    return {'body':body,'schedule':registry,'schema_bytes':len(c.encode(schema)),'body_bytes':len(c.encode(body)),'estimate':estimate,'guard':40000,'provider_compatibility':'unverified','provider_calls':0}
def wi():return build(ASSEMBLED['source'],ASSEMBLED)
