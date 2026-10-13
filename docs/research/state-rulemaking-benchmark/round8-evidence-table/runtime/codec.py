"""Exact-quote evidence table. Restoration is bound to an independently pinned payload hash."""
import copy,hashlib,json
VERSION='round8-evidence-table.wire.v1'
class InvalidWire(ValueError):pass
def encode_json(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(value):return hashlib.sha256(encode_json(value)).hexdigest()
def require(ok,message):
    if not ok:raise InvalidWire(message)
def encode(payload):
    out=copy.deepcopy(payload);table=[];index={}
    require(isinstance(out,dict) and isinstance(out.get('record'),dict),'payload/record shape')
    text=out.get('source_text');require(isinstance(text,str) and hashlib.sha256(text.encode()).hexdigest()==out.get('source_text_sha256'),'source hash')
    def walk(node):
        if isinstance(node,dict):
            for key,item in list(node.items()):
                if key=='evidence':
                    require(isinstance(item,list),'evidence array');refs=[]
                    for ev in item:
                        validate_entry(ev,text);identity=encode_json(ev)
                        if identity not in index:index[identity]=len(table);table.append(copy.deepcopy(ev))
                        refs.append(index[identity])
                    node[key]=refs
                else:walk(item)
        elif isinstance(node,list):
            for item in node:walk(item)
    walk(out['record']);return {'schema_version':VERSION,'payload':out,'evidence_table':table}
def validate_entry(ev,text):
    require(isinstance(ev,dict) and set(ev)=={'start','end','quote'},'exact evidence shape')
    require(type(ev['start']) is int and type(ev['end']) is int and 0<=ev['start']<=ev['end']<=len(text),'codepoint span')
    require(isinstance(ev['quote'],str) and text[ev['start']:ev['end']]==ev['quote'],'quote/source mismatch')
def restore(wire,expected_payload_sha256):
    require(isinstance(expected_payload_sha256,str) and len(expected_payload_sha256)==64,'independent payload hash required')
    require(isinstance(wire,dict) and set(wire)=={'schema_version','payload','evidence_table'} and wire['schema_version']==VERSION,'wire envelope shape/version')
    out=copy.deepcopy(wire['payload']);table=wire['evidence_table'];require(isinstance(table,list) and isinstance(out,dict) and isinstance(out.get('record'),dict),'payload/table shape')
    text=out.get('source_text');require(isinstance(text,str) and hashlib.sha256(text.encode()).hexdigest()==out.get('source_text_sha256'),'source hash')
    for ev in table:validate_entry(ev,text)
    def walk(node):
        if isinstance(node,dict):
            for key,item in list(node.items()):
                if key=='evidence':
                    require(isinstance(item,list),'reference array');evidence=[]
                    for ref in item:
                        require(type(ref) is int and 0<=ref<len(table),'reference type/bounds');evidence.append(copy.deepcopy(table[ref]))
                    node[key]=evidence
                else:walk(item)
        elif isinstance(node,list):
            for item in node:walk(item)
    walk(out['record']);require(digest(out)==expected_payload_sha256,'restored payload hash differs from independent original')
    require(encode_json(encode(out))==encode_json(wire),'noncanonical evidence table/reference order')
    return out
