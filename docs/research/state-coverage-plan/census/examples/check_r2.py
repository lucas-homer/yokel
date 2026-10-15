#!/usr/bin/env python3
"""Reproduce r2 broken fixtures in temporary copies; never change source/state runs."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HOME = Path(__file__).resolve().parent

def case(name, mutate, expected, stage='manifest'):
    with tempfile.TemporaryDirectory(prefix='census-r2-') as tmp:
        target = Path(tmp)
        shutil.copytree(HOME, target, dirs_exist_ok=True)
        run = json.loads((target/'run.json').read_text())
        mutate(run)
        (target/'run.json').write_text(json.dumps(run))
        cmd = [sys.executable, str(HOME.parent/'validate.py'), tmp, '--stage', stage]
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(f'$ python3 validate.py <temporary:{name}> --stage {stage}')
        print(result.stdout, end='')
        assert result.returncode == (1 if expected else 0), result.stderr
        assert not result.stderr, result.stderr
        for message in expected:
            assert message in result.stdout, message


def coverage(run):
    return run['processes'][0]['coverage']


def full(run):
    c = coverage(run)
    c['mode'] = 'independent_full'
    c['checks'][0]['scope'] = 'full'
    c['checks'][0]['expected_unit_ids'].append('sx-2')
    c['checks'][0]['matched_unit_ids'].append('sx-2')
    c['completeness'] = 'established'


def unfrozen(run):
    run['brief_sha256'] = run['brief_frozen_at'] = None
    run['audit']['seed'] = run['audit']['frame_hash'] = None
    run['audit']['frozen_before_seed'] = False


if __name__ == '__main__':
    case('partial-as-full', lambda r: coverage(r).update(mode='independent_full'),
         ['C03: agency-x/rulemaking independent_full requires a whole-universe independent source'])
    case('partial-established', lambda r: coverage(r).update(completeness='established'),
         ['C03: agency-x/rulemaking partial/uncovered or discrepant coverage requires completeness not_established'])
    case('outside-agency-claim', lambda r: coverage(r).update(claim_agency_ids=['agency-y']),
         ['C03: agency-x/rulemaking claim agencies exceed corroborated subset'])
    case('missing-outcome', lambda r: coverage(r)['checks'][0].update(matched_unit_ids=[]),
         ['C03: agency-x/rulemaking coverage outcomes must partition expected subset of universe'])
    case('full-scope-subset', lambda r: coverage(r)['checks'][0].update(scope='full'),
         ['C03: agency-x/rulemaking full source scope must cover whole universe'])
    case('legacy-independent', lambda r: r['processes'][0].pop('coverage'),
         ['C03: agency-x/rulemaking independent claim requires explicit coverage'])
    case('same-lineage-edge', lambda r: coverage(r)['checks'][0].update(against_entry_id='m1'),
         ['C03: agency-x/rulemaking coverage check lacks retrieved different-lineage manifest edge'])
    case('whole-source', full, [])
    case('unfrozen-manifest', unfrozen, [])
    case('audit-unfrozen-passes', lambda r: r['audit'].update(seed=None, frame_hash=None, frozen_before_seed=False), [], 'passes')
    case('unfrozen-passes', unfrozen, ['C05: brief hash/frozen time required at passes/final stage'], 'passes')
    case('unfrozen-final', unfrozen, ['C08: audit seed/frame hash/freeze required at final stage'], 'final')
    print('PASS all r2 fixture assertions (7 broken coverage cases, full coverage, and 4 freeze-stage cases).')
