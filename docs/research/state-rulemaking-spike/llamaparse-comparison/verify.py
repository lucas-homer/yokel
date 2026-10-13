"""Replay this bounded comparison offline; not a semantic or JSON Schema engine."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
TRIAL = ROOT / 'trial'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, cwd):
    result = subprocess.run([sys.executable, '-B', *map(str, args)], cwd=cwd,
                            text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    return {'arguments': list(map(str, args)), 'exit_code': result.returncode,
            'stdout': result.stdout, 'stderr': result.stderr}


def main():
    baseline = json.loads((ROOT / 'baseline-manifest.json').read_text())
    for item in baseline['files']:
        assert digest(ROOT.parent / item['path']) == item['sha256'], item['path']
    copied = json.loads((ROOT / 'integration-copy.json').read_text())
    for item in copied['files']:
        assert digest(ROOT / item['path']) == item['sha256'], item['path']
    assert digest(TRIAL / 'source.pdf') == digest(ROOT.parent / 'pdf/raw/fresh.pdf')
    for raw, md in [('parse-response.json', 'parse.md'),
                    ('parse-plus-response.json', 'parse-plus.md')]:
        payload = json.loads((TRIAL / raw).read_text())
        assert payload['isError'] is False
        assert payload['content'][0]['text'] == (TRIAL / md).read_text()
    assert json.loads((TRIAL / 'extraction-response.json').read_text())['isError'] is True

    with tempfile.TemporaryDirectory(prefix='llamaparse-replay-') as tmp:
        dest = Path(tmp) / 'trial'
        shutil.copytree(TRIAL, dest, ignore=shutil.ignore_patterns('__pycache__'))
        names = ['observations.json', 'normalization-diagnostics.json', 'guard-test-results.json']
        before = {name: digest(dest / name) for name in names}
        commands = [run(['normalize.py'], dest), run(['test_guards.py'], dest)]
        assert before == {name: digest(dest / name) for name in names}
        validation = run([ROOT.parent / 'validate.py', dest], ROOT)
        report = json.loads(validation['stdout'])
        assert report['passed']
        lane = report['lanes'][0]
        assert (lane['observation_count'], lane['exact_quote_count'],
                lane['visual_evidence_count']) == (7, 9, 0)

    obs = json.loads((TRIAL / 'observations.json').read_text())
    by_predicate = {o['predicate']: o for o in obs}
    assert len(by_predicate) == len(obs) == 7
    assert all(o['review_state'] == 'needs_review' for o in obs)
    assert not {'filing_date', 'comment_close', 'effective_date'} & by_predicate.keys()
    hearing = by_predicate['hearing_request_duration']['value']
    comment = by_predicate['comment_duration']['value']
    assert hearing['duration'] == 20 and hearing['computed_close'] is None
    assert comment['duration'] == 25 and comment['anchor'] is None
    assert comment['day_basis'] is None and comment['computed_close'] is None
    assert len(by_predicate['hearing_request_duration']['evidence']) == 2
    result = {
        'passed': True,
        'scope': 'Source/copy integrity, raw-to-derived identity, offline replay, retained fixture assertions and three omission guards; not general semantic validation.',
        'baseline_files_unchanged': len(baseline['files']),
        'copied_files_verified': len(copied['files']),
        'source_byte_identity': True,
        'raw_markdown_exact': True,
        'replay_outputs_byte_identical': True,
        'commands': commands,
        'shared_validator': report,
        'full_json_schema_engine_executed': False,
        'extraction_result_available': False,
        'all_observations_require_review': True,
    }
    (ROOT / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in {'commands', 'shared_validator'}}, indent=2))


if __name__ == '__main__':
    main()
