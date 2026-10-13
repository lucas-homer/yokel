"""Pinned bounded offline inputs and strict canonical JSON. No transports or approvals."""
import hashlib,importlib.util,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent;ROUND=ROOT.parent;PROTO=ROUND/'protocol'
READY_SHA='613b372963791f54f7afa3160a48cf15d1750e454f126a9b75c5b1ec4d4db2f1'
APPROVAL_SHA='5682a7a621cd36b54b7736001799395dc9dd21d0c73010cb773f9e6a567c8f99'
class InvalidInput(ValueError):pass
def encode(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def digest(value):return hashlib.sha256(encode(value)).hexdigest()
def file_hash_bytes(raw):return hashlib.sha256(raw).hexdigest()
def file_hash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def strict(raw):
    def pairs(values):
        result={}
        for key,value in values:
            if key in result:raise InvalidInput('duplicate raw JSON key: '+key)
            result[key]=value
        return result
    def floating(value):
        number=float(value)
        if not math.isfinite(number):raise InvalidInput('nonfinite numeric overflow')
        return number
    try:return json.loads(raw,object_pairs_hook=pairs,parse_float=floating,parse_constant=lambda _:(_ for _ in ()).throw(InvalidInput('nonstandard numeric constant')))
    except (json.JSONDecodeError,UnicodeDecodeError,TypeError) as e:raise InvalidInput('invalid raw JSON') from e

def read(path):return strict(Path(path).read_bytes())
def verify_inputs():
    if file_hash(PROTO/'READY.json')!=READY_SHA:raise InvalidInput('protocol release drift')
    release=read(ROUND/'implementation-release.json')
    if release['state']!='approved_offline_implementation' or release['protocol_ready_sha256']!=READY_SHA or release['approved_development_audits_sha256']!=APPROVAL_SHA or file_hash(ROUND/'approved-development-audits.json')!=APPROVAL_SHA:raise InvalidInput('external approval binding drift')
    for name,want in read(PROTO/'READY.json')['artifacts'].items():
        path=(PROTO/name).resolve()
        if not path.is_relative_to(PROTO.resolve()) or file_hash(path)!=want:raise InvalidInput('protocol artifact drift: '+name)
    pins=read(ROOT/'input-pins.json')['files']
    for path,want in pins.items():
        if file_hash(path)!=want:raise InvalidInput('read-only dependency drift: '+path)
    return len(pins)
verify_inputs()
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
p=load('r9_frozen_r7_pipeline',ROUND.parent/'round7/pipeline/pipeline.py')
codec=load('r9_frozen_quote_table',ROUND.parent/'round8-evidence-table/runtime/codec.py')
