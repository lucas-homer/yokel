"""Round-3 review repro: every benchmark file opened while verify.py runs must be in frozen-inputs.json."""
import io
import json
import os
import runpy
import sys
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
OWNED = HERE.parent / 'protocol-w2-1'
BENCH = HERE.parents[1]
opened = set()


def hook(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        try:
            opened.add(Path(os.fsdecode(args[0])).resolve())
        except (OSError, ValueError, TypeError):
            pass


sys.addaudithook(hook)
sys.argv = [str(OWNED / 'verify.py')]
buf = io.StringIO()
code = 0
try:
    with redirect_stdout(buf):
        runpy.run_path(str(OWNED / 'verify.py'), run_name='__main__')
except SystemExit as exc:
    code = exc.code
print('verify.py exit code under audit (with review-w2-1/ present as a new sibling):', code)
manifest = json.loads((OWNED / 'frozen-inputs.json').read_bytes())
scoped = {(BENCH / key).resolve() for key in manifest}
bench_files = {p for p in opened if p.is_relative_to(BENCH) and p.is_file()}
outside_owned = {p for p in bench_files if not p.is_relative_to(OWNED) and not p.is_relative_to(HERE)}
missing = sorted(outside_owned - scoped)
print('files opened under the benchmark, outside the owned folder:', len(outside_owned))
print('  ... of which NOT pinned in frozen-inputs.json:', len(missing))
for p in missing:
    print('   UNPINNED:', p.relative_to(BENCH))
print('files opened in the owned folder (pinned by READY.json instead):', sorted(str(p.relative_to(OWNED)) for p in bench_files if p.is_relative_to(OWNED) and 'tmp' not in str(p))[:20])
print('pinned-but-never-opened files (frozen for provenance only):', len(scoped - outside_owned))
print('pin constants:', {k: (BENCH / v).exists() for k, v in {'R15 READY.json': 'round15-condition-preservation/protocol-revised/READY.json', 'R14 common.py': 'round14-semantic-contract/runtime/common.py'}.items()})
