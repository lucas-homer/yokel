"""Benign stable-runner credential smoke. Stdlib only; no network/provider operation."""
import json,os,sys
from pathlib import Path
JOB_ID='job-alpha'
HERE=Path(__file__).resolve().parent
PYTHON=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12')
class Denied(Exception):pass
def require(value):
    if not value:raise Denied()
def check_and_record(environment,receipt_path):
    # Check receipt first. No key, key hash, key length or value is retained or emitted.
    require(not receipt_path.exists())
    key=environment.get('OPENROUTER_API_KEY')
    checks={'job_id':JOB_ID,'openrouter_nonempty':isinstance(key,str) and bool(key.strip()),'service_account_token_absent':'OP_SERVICE_ACCOUNT_TOKEN' not in environment,'typesafe_key_absent':'TYPESAFE_API_KEY' not in environment,'network_called':False,'provider_called':False}
    require(checks['openrouter_nonempty'] and checks['service_account_token_absent'] and checks['typesafe_key_absent'])
    raw=(json.dumps(checks,sort_keys=True,separators=(',',':'))+'\n').encode()
    fd=os.open(receipt_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    fd=os.open(receipt_path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
    return checks
def main():
    try:
        require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and Path(sys.executable).resolve()==PYTHON.resolve())
        require(len(sys.argv)==2 and sys.argv[1]=='--live-initial')
        check_and_record(os.environ,HERE/'receipt.json')
        print('Credential smoke checks completed.');return 0
    except BaseException:
        print('Credential smoke rejected.');return 1
if __name__=='__main__':sys.exit(main())
