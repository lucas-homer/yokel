import hashlib,io,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT))
def guard(event,args):
    if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('candidate offline guard')
    if event=='open' and isinstance(args[0],(str,bytes)):
        name=str(args[0]).lower()
        if '/.env' in name or '/library/keychains/' in name or '/.aws/' in name or Path(name).name in ('credentials','credentials.json'):raise RuntimeError('credential paths forbidden')
sys.addaudithook(guard)
log=io.StringIO();suite=unittest.defaultTestLoader.discover(str(ROOT),pattern='test_adapter.py');result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite);(ROOT/'test-output.txt').write_text(log.getvalue());report={'status':'unapproved_pending_final_credential_review_and_primary_release_signing','tests':result.testsRun,'passed':result.wasSuccessful(),'provider_calls':0,'real_credentials_read':False,'live_intent_created_in_task':False,'native_builds':0,'log_sha256':hashlib.sha256((ROOT/'test-output.txt').read_bytes()).hexdigest()};(ROOT/'TEST-REPORT.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps(report));raise SystemExit(0 if result.wasSuccessful() else 1)
