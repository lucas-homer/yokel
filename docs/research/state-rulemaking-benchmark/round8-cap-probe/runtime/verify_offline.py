#!/usr/bin/env python3
"""Guarded author controls and code receipt preparation; no source/credential/provider execution."""
import contextlib,hashlib,importlib.util,io,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
    def guard(event,args):
        if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('network/process disabled during mock controls')
        if event=='open' and isinstance(args[0],(str,bytes)):
            name=str(args[0]).lower()
            if '/.env' in name or '/library/keychains/' in name or '/.aws/' in name or Path(name).name in ('credentials','credentials.json'):raise RuntimeError('credential access disabled during mock controls')
    sys.addaudithook(guard)
    log=io.StringIO();counts=[]
    for folder,pattern in ((ROOT,'offline_checks.py'),(ROOT.parent/'execution/service-account','test_adapter.py')):
        with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
            suite=unittest.defaultTestLoader.discover(str(folder),pattern=pattern)
            result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
        counts.append(dict(suite=str(folder),tests=result.testsRun,passed=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors)))
    (ROOT/'offline-test-output.txt').write_text(log.getvalue())
    report=dict(schema_version='round8-cap-probe.mock_runtime_report.v1',controls=counts,passed=all(x['passed'] for x in counts),provider_calls=0,credentials_read=False,network_process_guard='Python audit hook active; explicit mock transport only',development_only=True,action_ready=False,production_eligible=False,log_sha256=hashlib.sha256((ROOT/'offline-test-output.txt').read_bytes()).hexdigest(),command='PYTHONDONTWRITEBYTECODE=1 /Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 '+str(Path(__file__).resolve()))
    (ROOT/'offline-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=report['passed'],tests=sum(x['tests'] for x in counts),provider_calls=0)))
    if not report['passed']:raise SystemExit(1)
if __name__=='__main__':main()
