"""Direct use of exact-pinned R14 protocol; no competing compact schema or defaults."""
import importlib.util
import common as c
MODULE=None
FLAGS={'source_inventory_completeness':'unverified','semantic_status':'unverified','production_eligible':False,'action_ready':False}
def protocol():
    global MODULE
    path=c.PROTO/'compact.py';c.verify_pin(path,c.read(c.PROTO/'READY.json')['sha256']['compact.py'])
    if MODULE is None:
        spec=importlib.util.spec_from_file_location('r14_frozen_compact',path);MODULE=importlib.util.module_from_spec(spec);spec.loader.exec_module(MODULE)
    return MODULE
def build(source):
    k=protocol();plan=k.build(source);c.require(k.reconstruct(source,plan['table'])==source)
    user=c.strict(plan['body']['messages'][1]['content']);c.require(set(user)=={'source_text','source_text_sha256','span_table','span_table_sha256'} and user['source_text']==source)
    c.check_schema(k.schema(source,plan['table']));c.require(plan['body']['response_format']['json_schema']['schema']==k.schema(source,plan['table']))
    c.require(plan['guarded_bytes']==len(c.encode(plan['body']))+1024<=40000 and plan['request_sha256']==c.digest(plan['body']))
    return plan
def validate_response(content,finish_reason,source,table):
    k=protocol();result=k.validate_response(content,finish_reason,source,table);compact=result['compact'];expanded=result['expanded']
    schema=k.schema(source,table);c.check_schema(schema);c.require(not c.schema_errors(compact,schema))
    inverse=k.contract(expanded,source,table);c.require(inverse==compact and c.encode(inverse)==c.encode(compact) and c.digest(inverse)==c.digest(compact))
    c.require(expanded==k.expand(compact,source,table) and k.reconstruct(source,table)==source)
    return result
