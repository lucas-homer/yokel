"""Check retained comparison inputs before the separate reference freeze."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from pypdf import PdfReader

CALIBRATION = 'ac95c240653690261eb7a6fef83bd80a04310cf49c15c37256569bbc70315955'
IDS = [f'{lane}{n:02d}' for lane in 'AB' for n in range(1, 11)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(root):
    fixtures, failures = [], []
    for fid in IDS:
        directory = root / ('source-a' if fid.startswith('A') else 'source-b') / fid
        path = directory / 'fixture.json'
        if not path.exists():
            failures.append({'fixture_id': fid, 'error': 'fixture.json not ready'})
            continue
        try:
            d = json.loads(path.read_text())
            assert d['fixture_id'] == fid
            assert sha(directory / 'input.pdf') == d['input_sha256']
            assert sha(directory / 'original.pdf') == d['original_sha256']
            assert d['original_sha256'] != CALIBRATION
            pages = len(PdfReader(directory / 'input.pdf').pages)
            original_pages = len(PdfReader(directory / 'original.pdf').pages)
            assert pages == d['input_page_count'] and 1 <= pages <= 4
            assert original_pages == d['original_page_count']
            mapping = d['original_physical_pages']
            assert len(mapping) == pages
            assert all(isinstance(n, int) and 1 <= n <= original_pages for n in mapping)
            assert mapping == list(range(mapping[0], mapping[0] + pages))
            assert (directory / 'native.txt').exists()
            fields = d['reference_fields']
            assert 6 <= len(fields) <= 10
            assert len({f['field_id'] for f in fields}) == len(fields)
            for f in fields:
                assert {'field_id', 'question', 'expected_value', 'answerability', 'critical',
                        'original_page', 'input_page', 'region', 'source_quote', 'basis'} <= f.keys()
                assert f['answerability'] in {'present', 'explicit_negative', 'not_stated', 'uncertain'}
                assert isinstance(f['critical'], bool)
                assert f['basis'] in {'source_text', 'visual_mark', 'full_scope_absence'}
                assert 1 <= f['input_page'] <= pages
                assert mapping[f['input_page'] - 1] == f['original_page']
            fixtures.append({
                'fixture_id': fid, 'directory': str(directory.relative_to(root)),
                'input_path': str((directory / 'input.pdf').resolve()),
                'input_sha256': d['input_sha256'], 'input_bytes': (directory / 'input.pdf').stat().st_size,
                'input_page_count': pages, 'original_sha256': d['original_sha256'],
                'original_page_count': original_pages, 'original_physical_pages': mapping,
                'state': d['state'], 'bucket': d['bucket'],
                'source_url': d['source_url'], 'fixture_metadata_sha256': sha(path),
                'native_sha256': sha(directory / 'native.txt'),
                'reference_fields': len(fields),
                'collector_critical_fields': sum(f['critical'] for f in fields),
            })
        except (AssertionError, KeyError, OSError, ValueError, TypeError) as exc:
            failures.append({'fixture_id': fid, 'error': f'{type(exc).__name__}: {exc}'})
    states = Counter(f['state'] for f in fixtures)
    pages = sum(f['input_page_count'] for f in fixtures)
    if len(fixtures) == 20:
        if len(states) < 6 or max(states.values()) > 4:
            failures.append({'error': 'state quota violation'})
        if len({f['input_sha256'] for f in fixtures}) != 20:
            failures.append({'error': 'duplicate input-byte hashes'})
        if pages > 80:
            failures.append({'error': 'input-page cap exceeded'})
    return {'checked_at': datetime.now(timezone.utc).isoformat(),
            'scope': 'Structure, source/input hashes, physical pages, reference shape; semantic reference review is separate.',
            'passed': len(fixtures) == 20 and not failures, 'fixtures': fixtures,
            'state_counts': dict(states), 'bucket_counts': dict(Counter(f['bucket'] for f in fixtures)),
            'input_page_count': pages, 'distinct_original_pdfs': len({f['original_sha256'] for f in fixtures}),
            'failures': failures}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    result = check(args.root.resolve())
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'fixtures'}, indent=2))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
