#!/usr/bin/env python3
"""Primary-delegated local release authority; no op/Keychain/provider access.

The release key is consciously primary-accessible, owner-only outside the repo.
This is artifact signing, not independent review or a bill-limiting broker.
"""
import argparse,base64,hashlib,json,os,stat,subprocess,time
from pathlib import Path
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import ec

DOMAIN=b'yokel.research-job.v1\0'
def need(value):
    if not value:raise ValueError('release denied')
def pairs(items):
    out={}
    for k,v in items:
        need(k not in out);out[k]=v
    return out
def read_json(path):return json.loads(Path(path).read_bytes(),object_pairs_hook=pairs)
def encode(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def owner_directory(path):
    p=Path(path);s=p.lstat();need(p.resolve()==p and stat.S_ISDIR(s.st_mode) and s.st_uid==os.getuid() and not s.st_mode&0o077);return p
def in_roots(path,roots):return Path(path).resolve()==Path(path) and any(Path(path).is_relative_to(Path(root)) and Path(path)!=Path(root) for root in roots)
def validate(core,m):
    need(set(m)=={'schema_version','job_id','scope_id','project','expires_unix','provider_variables','job','budget','review'})
    import re
    need(m['schema_version']=='yokel.research-job.v1' and m['project']=='yokel.docketclock.research')
    for field in ('job_id','scope_id'):need(isinstance(m[field],str) and re.fullmatch('[a-z][a-z0-9-]{0,63}',m[field]))
    need(type(m['expires_unix']) is int and int(time.time())<m['expires_unix']<=int(time.time())+7*24*3600)
    variables=m['provider_variables'];need(isinstance(variables,list) and 0<len(variables)<=2 and len(set(variables))==len(variables) and set(variables)<=set(core['base_policy']['references']))
    j=m['job'];need(set(j)=={'argv','files','timeout_seconds'} and isinstance(j['argv'],list) and len(j['argv'])==6)
    need(j['argv'][:4]==[core['python_path'],'-I','-S','-B'] and j['argv'][5]=='--live-initial' and j['argv'][4].endswith('/adapter.py') and in_roots(j['argv'][4],core['adapter_roots']))
    need(type(j['timeout_seconds']) is int and 1<=j['timeout_seconds']<=core['timeout_max_seconds'])
    files=j['files'];need(isinstance(files,dict) and 0<len(files)<=10000 and all(p in files for p in (j['argv'][0],j['argv'][4])))
    for p,want in files.items():need(in_roots(p,core['dependency_roots']) and re.fullmatch('[a-f0-9]{64}',want) and digest(p)==want)
    b=m['budget'];need(set(b)=={'prior_nanousd','reservation_nanousd','ceiling_nanousd'} and all(type(x) is int for x in b.values()))
    safe=4503599627370495 # JSON exact-number/arithmetic bound; not authorization.
    need(0<=b['prior_nanousd']<=safe and 0<=b['reservation_nanousd']<=safe and 0<b['ceiling_nanousd']<=safe and b['prior_nanousd']+b['reservation_nanousd']<=b['ceiling_nanousd'])
    review=m['review'];need(set(review)=={'path','sha256'} and files.get(review['path'])==review['sha256'])
    need(len(encode(m))<=4*1024*1024)
def read_key(core,path):
    p=Path(path);need(p.is_absolute() and p.resolve()==p);owner_directory(p.parent)
    repo=Path(__file__).resolve().parents[2];need(not p.is_relative_to(repo))
    need(not any(p.is_relative_to(Path(root)) for root in core['adapter_roots']+core['dependency_roots']))
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        s=os.fstat(fd);need(stat.S_ISREG(s.st_mode) and s.st_uid==os.getuid() and not s.st_mode&0o077 and 0<s.st_size<=4096)
        with os.fdopen(fd,'rb',closefd=False) as f:raw=f.read(4097)
    finally:os.close(fd)
    key=serialization.load_pem_private_key(raw,password=None)
    need(isinstance(key,ec.EllipticCurvePrivateKey) and isinstance(key.curve,ec.SECP256R1))
    public=key.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
    need(public==base64.b64decode(core['public_key_base64'],validate=True));return key
def publish(core,m,key):
    validate(core,m);registry=owner_directory(core['registry_dir']);raw=encode(m);sig=key.sign(DOMAIN+raw,ec.ECDSA(hashes.SHA256()))
    # Exclusive writes. A partial publication stays fail-closed and is never overwritten.
    for suffix,data in (('.json',raw),('.sig',sig)):
        fd=os.open(registry/(m['job_id']+suffix),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    fd=os.open(registry,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
    return hashlib.sha256(raw).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--core',type=Path,required=True);p.add_argument('--proposal',type=Path,required=True);p.add_argument('--key-file',type=Path,required=True);p.add_argument('--executor',type=Path,required=True);args=p.parse_args()
    try:
        core=read_json(args.core);m=read_json(args.proposal);validate(core,m)
        key=read_key(core,args.key_file);published=publish(core,m,key)
        result=subprocess.run([str(args.executor),'check-job',m['job_id']],env={'HOME':str(Path.home()),'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8'},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30)
        need(result.returncode==0)
        print(json.dumps({'state':'released','job_id':m['job_id'],'manifest_sha256':published,'credential_access':False,'provider_calls':0,'authority':'owner-delegated-primary'},sort_keys=True));return 0
    except Exception:
        print('Release failed; inspect nonsecret policy/pins/publication state. No credential access.');return 1
if __name__=='__main__':raise SystemExit(main())
