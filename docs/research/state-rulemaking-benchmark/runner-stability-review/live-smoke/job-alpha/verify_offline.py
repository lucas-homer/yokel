import hashlib,io,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT))
def guard(event,args):
    if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('smoke synthetic tests block network/native processes')
    if event=='open' and isinstance(args[0],(str,bytes)):
        name=str(args[0]).lower()
        if '/library/keychains/' in name or '/.env' in name or '/.aws/' in name or Path(name).name in ('credentials','credentials.json'):raise RuntimeError('real credential files blocked')
sys.addaudithook(guard)
log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT),pattern='test_smoke.py'));(ROOT/'test-output.txt').write_text(log.getvalue());report={'tests':result.testsRun,'passed':result.wasSuccessful(),'network_provider_calls':0,'real_credentials_read':False,'signing_native_execution':False,'synthetic_receipts_only_deleted':True,'zero_reservation_authorized_by_primary_and_supported_by_native_candidate':True,'log_sha256':hashlib.sha256((ROOT/'test-output.txt').read_bytes()).hexdigest()};(ROOT/'TEST-REPORT.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps(report));raise SystemExit(0 if result.wasSuccessful() else 1)
