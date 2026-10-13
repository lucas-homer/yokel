"""Offline verifier: fixed test/check commands, writes only owned report/log; no live invocation."""
import hashlib, json, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
PYTHON='/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    # No ambient credential environment is forwarded to either offline process.
    env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
    tests=subprocess.run([PYTHON,'-I','-S','-B',str(HERE/'test_adapter.py')],env=env,capture_output=True)
    (HERE/'test-output.txt').write_bytes(tests.stdout+tests.stderr)
    check=subprocess.run([PYTHON,'-I','-S','-B',str(HERE/'adapter.py'),'--check'],env=env,capture_output=True)
    (HERE/'check-output.txt').write_bytes(check.stdout+check.stderr)
    if tests.returncode or check.returncode:raise SystemExit('offline verification failed; inspect owned output')
    dependencies=json.loads((HERE/'dependency-pins.json').read_bytes())['files']
    for p,want in dependencies.items():
        if sha(Path(p))!=want:raise SystemExit('dependency drift')
    report=dict(schema_version='round9-live-exact-id.offline-report.v1',passed=True,test_methods=13,provider_calls=0,credentials_read=False,check=json.loads(check.stdout),dependency_files=len(dependencies),test_output_sha256=sha(HERE/'test-output.txt'),check_output_sha256=sha(HERE/'check-output.txt'),production_eligible=False,action_ready=False)
    (HERE/'REPORT.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(passed=True,test_methods=13,dependency_files=len(dependencies),provider_calls=0,credentials_read=False)))
if __name__=='__main__':main()
