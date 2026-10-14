"""Offline proposal generation for an already staged standalone adapter.py."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import time
import uuid

HERE = Path(__file__).resolve().parent
PYTHON = Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12')


def need(value):
    if not value:
        raise ValueError('proposal rejected')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def within(path, roots):
    return path.is_absolute() and path.resolve() == path and any(
        path != Path(root) and path.is_relative_to(Path(root)) for root in roots)


def runtime_files(python):
    # Match prior stable smoke's conservative stdlib/extensions/dylib closure.
    lib = python.parent.parent / 'lib'
    std = lib / 'python3.12'
    need(std.is_dir())
    files = {python.resolve()}
    # -B forbids writes, not reads: existing cached bytecode must also be pinned.
    files.update(p.resolve() for p in std.rglob('*') if p.is_file()
                 and 'site-packages' not in p.parts)
    files.update(p.resolve() for p in lib.glob('*.dylib') if p.is_file())
    return files


def prepare(core, stage, scope_id, expires_unix, prior_nanousd, ceiling_nanousd,
            *, now=None, dependencies=None):
    now = int(time.time()) if now is None else now
    stage = Path(stage)
    adapter, review = stage / 'adapter.py', stage / 'REVIEW.md'
    need(core['python_path'] == str(PYTHON))
    need(within(adapter, core['adapter_roots']) and within(review, core['dependency_roots']))
    need(stage.is_dir() and set(p.name for p in stage.iterdir()) == {'adapter.py', 'REVIEW.md'})
    need(adapter.is_file() and review.is_file() and review.stat().st_size > 0)
    need(digest(adapter) == digest(HERE / 'keycheck.py'))
    # An implementation SPEC is not independent primary-accepted review evidence.
    need(review.read_bytes() != (HERE / 'SPEC.md').read_bytes())
    need(isinstance(scope_id, str) and re.fullmatch(r'[a-z][a-z0-9-]{0,63}', scope_id))
    need(type(expires_unix) is int and now < expires_unix <= now + 7 * 86400)
    need(type(prior_nanousd) is int and type(ceiling_nanousd) is int
         and 0 <= prior_nanousd <= ceiling_nanousd <= 4503599627370495 and ceiling_nanousd > 0)
    need('OPENROUTER_API_KEY' in core['base_policy']['references'])
    pins = runtime_files(PYTHON) if dependencies is None else set(dependencies)
    pins |= {PYTHON, adapter, review}
    need(0 < len(pins) <= 10000 and core['timeout_max_seconds'] >= 30)
    need(all(within(p, core['dependency_roots']) and p.is_file() for p in pins))
    files = {str(p): digest(p) for p in sorted(pins)}
    job_id = 'r18-keycheck-v3-' + time.strftime('%Y%m%d%H%M%S', time.gmtime(now)) + '-' + uuid.uuid4().hex[:12]
    proposal = {'schema_version': 'yokel.research-job.v1', 'job_id': job_id,
        'scope_id': scope_id, 'project': 'yokel.docketclock.research',
        'expires_unix': expires_unix, 'provider_variables': ['OPENROUTER_API_KEY'],
        'job': {'argv': [str(PYTHON), '-I', '-S', '-B', str(adapter), '--live-initial'],
                'files': files, 'timeout_seconds': 30},
        'budget': {'prior_nanousd': prior_nanousd, 'reservation_nanousd': 0,
                   'ceiling_nanousd': ceiling_nanousd},
        'review': {'path': str(review), 'sha256': files[str(review)]}}
    manifest = {'schema_version': 'r18.keycheck-stage.v3', 'job_id': job_id,
        'stage': str(stage), 'files': [
            {'source': str(HERE / 'keycheck.py'), 'staged': str(adapter), 'sha256': files[str(adapter)]},
            {'role': 'primary-accepted-independent-review', 'staged': str(review), 'sha256': files[str(review)]}],
        'external_runtime_pins': {p: h for p, h in files.items() if p not in {str(adapter), str(review)}},
        'outputs_not_staged_or_pinned': ['KEY-MACHINE.json', 'BOOTSTRAP-TIMING.json', 'FAILURE.json'],
        'approval': 'unsigned; primary must review before signing'}
    need(len(json.dumps(proposal).encode()) <= 4 * 1024 * 1024)
    return proposal, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core', required=True, type=Path)
    parser.add_argument('--stage', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--scope-id', required=True)
    parser.add_argument('--expires-unix', required=True, type=int)
    parser.add_argument('--prior-nanousd', required=True, type=int)
    parser.add_argument('--ceiling-nanousd', required=True, type=int)
    args = parser.parse_args()
    proposal, manifest = prepare(json.loads(args.core.read_bytes()), args.stage,
        args.scope_id, args.expires_unix, args.prior_nanousd, args.ceiling_nanousd)
    args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
    for name, value in [('UNSIGNED-ZERO-COST-PROPOSAL.json', proposal), ('STAGE-MANIFEST.json', manifest)]:
        with (args.output / name).open('x') as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write('\n')
    print(proposal['job_id'])


if __name__ == '__main__':
    main()
