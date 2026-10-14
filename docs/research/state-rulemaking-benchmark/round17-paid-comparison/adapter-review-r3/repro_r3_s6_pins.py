"""S6 against r1.2: does verification mutate anything that READY pins?

Snapshots every file (bytes) under adapter-r1-2 outside _out, and under every directory
READY.json lists as a dependency root (adapter, adapter-review, adapter-r1-1,
adapter-review-r2, design-r3-1 pins, sources-r2/READY.json ...). Verifies all pins, runs
`sh adapter-r1-2/run_tests.sh` (writes only to _out), re-verifies, and diffs the
snapshots. The suite output is kept in suite-output-r3.txt. Exit 0 = nothing pinned
changed and every pin verified before and after.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R17 = HERE.parent
BENCH = R17.parent
ADAPTER = R17 / 'adapter-r1-2'
problems = []


def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond:
        problems.append(what)


def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def payload_files():
    return {p.relative_to(ADAPTER).as_posix(): pin(p) for p in ADAPTER.rglob('*')
            if p.is_file() and '_out' not in p.relative_to(ADAPTER).parts and p.name != 'READY.json'}


def snapshot(roots):
    out = {}
    for root in roots:
        for p in root.rglob('*'):
            if p.is_file() and '_out' not in p.relative_to(R17).parts and '__pycache__' not in p.parts \
                    and not any(part.startswith('.review-') for part in p.parts):
                out[p.relative_to(BENCH).as_posix()] = pin(p)
    return out


ready = json.loads((ADAPTER / 'READY.json').read_bytes())
check(ready['revision'] == 'r1.2' and ready['excluded_paths'] == ['_out/**'], 'READY r1.2 excludes _out/**')
check(not any(n.startswith('_out/') or '/.review-' in n or '__pycache__' in n for n in ready['files']), 'no generated paths pinned')
check(all(not n.startswith('round17-paid-comparison/reference/') and not n.endswith(('parsed-body.txt', 'original.htm'))
          for n in ready['dependencies']), 'no reference/ or source-body dependency pins')


def verify(label):
    files = payload_files()
    check(set(files) == set(ready['files']), '%s: payload membership matches READY (%d files)' % (label, len(files)))
    bad = [n for n, v in files.items() if ready['files'].get(n) != v]
    check(not bad, '%s: every payload pin matches: %s' % (label, bad or 'all'))
    bad = [n for n, v in ready['dependencies'].items() if not (BENCH / n).is_file() or pin(BENCH / n) != v]
    check(not bad, '%s: every dependency pin matches (%d): %s' % (label, len(ready['dependencies']), bad or 'all'))
    return files


roots = [ADAPTER, R17 / 'adapter', R17 / 'adapter-review', R17 / 'adapter-r1-1', R17 / 'adapter-review-r2',
         R17 / 'design-r3-1']
before_files = verify('before')
before = snapshot(roots)
ready_before = pin(ADAPTER / 'READY.json')
out_before = {p.relative_to(ADAPTER).as_posix() for p in (ADAPTER / '_out').rglob('*') if p.is_file()}

print('     running sh adapter-r1-2/run_tests.sh (output -> suite-output-r3.txt) ...')
result = subprocess.run(['sh', str(ADAPTER / 'run_tests.sh')], cwd=str(ADAPTER),
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
(HERE / 'suite-output-r3.txt').write_bytes(result.stdout)
text = result.stdout.decode('utf-8', 'replace')
counts = [int(n) for n in re.findall(r'^Ran (\d+) tests', text, re.M)]
oks = len(re.findall(r'^OK$', text, re.M))
check(result.returncode == 0 and counts == [102, 26, 23, 9, 20] and oks == 5 and not re.search(r'^(FAILED|ERROR:|FAIL:)', text, re.M),
      'suite exit %d; Ran %s; OK x%d' % (result.returncode, counts, oks))

after_files = verify('after')
after = snapshot(roots)
changed = sorted(n for n in set(before) | set(after) if before.get(n) != after.get(n))
check(not changed, 'no pinned-root file changed or appeared outside _out: %s' % (changed or 'none'))
check(pin(ADAPTER / 'READY.json') == ready_before, 'READY.json bytes unchanged')
out_after = {p.relative_to(ADAPTER).as_posix() for p in (ADAPTER / '_out').rglob('*') if p.is_file()}
print('     _out files before/after:', len(out_before), len(out_after), '| new:', sorted(out_after - out_before) or 'none',
      '| gone:', sorted(out_before - out_after) or 'none')
stray = [p.relative_to(ADAPTER).as_posix() for p in ADAPTER.rglob('*') if p.is_file()
         and '_out' not in p.relative_to(ADAPTER).parts and p.relative_to(ADAPTER).as_posix() not in ready['files']
         and p.name != 'READY.json']
check(not stray, 'no stray files outside _out after the run: %s' % (stray or 'none'))

print()
print('problems:', problems)
sys.exit(0 if not problems else 1)
