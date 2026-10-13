"""Read-only verification of R14 and the R15 design/protocol freezes."""
import hashlib
import json
from pathlib import Path

ROUND = Path(__file__).resolve().parents[1]
BENCH = ROUND.parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify():
    old = json.loads((ROUND / 'primary/R14-FREEZE.json').read_text())['files']
    for name, expected in old.items():
        assert sha(BENCH / name) == expected, name
    result = {'r14_unchanged_files': len(old), 'r15': {}}
    for folder in ['design', 'design-review', 'protocol', 'protocol-revised', 'implementation-review', 'revised-review', 'testing', 'testing/execution', 'testing/revised']:
        ready = ROUND / folder / 'READY.json'
        receipt = json.loads(ready.read_text())
        if folder in ['testing', 'testing/execution', 'testing/revised']:
            pins = {name: entry['sha256'] for name, entry in receipt['files'].items()}
        else:
            pins = receipt['sha256']
        for name, expected in pins.items():
            assert sha(ready.parent / name) == expected, (folder, name)
        result['r15'][folder] = {'verified_files': len(pins), 'ready_sha256': sha(ready)}
    result['paid_provider_calls'] = 0
    result['dispatch_approved'] = False
    return result

if __name__ == '__main__':
    print(json.dumps(verify(), sort_keys=True))
