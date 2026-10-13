"""Compile only synthetic fixtures; type-check live branch without emitting a binary."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='partition-repair-fixtures-') as temporary:
    binary=Path(temporary)/'fixtures'
    common=['/usr/bin/xcrun','clang','-fobjc-arc','-Wno-deprecated-declarations','-framework','Foundation','-framework','Security']
    subprocess.run(common+['-DSYNTHETIC_FIXTURES',str(HERE/'repair.m'),'-o',str(binary)],check=True,capture_output=True)
    r=subprocess.run([str(binary),'--synthetic-fixtures'],check=True,capture_output=True,text=True,timeout=10);result=json.loads(r.stdout)
    assert result['state']=='passed' and not result['keychain_access'] and not result['live_mutation']
    denied=subprocess.run([str(binary),'--repair-known-partition'],capture_output=True,text=True,timeout=10);assert denied.returncode==1
    subprocess.run(common+['-fsyntax-only',str(HERE/'repair.m')],check=True,capture_output=True)
    installed=Path('/Users/home/.local/libexec/yokel/research-credentials-stable-v1')
    assert hashlib.sha256(installed.read_bytes()).hexdigest()=='821f91b67f4c0c2d2a7f333e1381fab9aec1f9d8a9b8be8c34a0ee135494547e'
    result.update(source_sha256=hashlib.sha256((HERE/'repair.m').read_bytes()).hexdigest(),live_branch_syntax='passed',synthetic_binary_denies_live_mode=True,installed_reader_unchanged=True,production_helper_built=False,provider_calls=0)
    (HERE/'TEST-RESULT.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,sort_keys=True))
