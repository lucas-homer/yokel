#!/usr/bin/env python3
"""Replay retained research fixtures and assemble one candidate-observation stream.

Uses Python's standard library only. No network, dependency installation, or
production database. Input source artifacts are verified before and after replay.
"""

import hashlib
import json
import os
import pathlib
import subprocess
import sys

sys.dont_write_bytecode = True
from validate import validate_lane

ROOT = pathlib.Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    lanes = [ROOT / name for name in ['ct', 'wa', 'pdf']]
    combined, artifacts, lane_reports = [], [], []
    for lane in lanes:
        before_validation = validate_lane(lane)
        if not before_validation['passed']:
            raise ValueError('Pre-replay validation failed: ' + json.dumps(before_validation))
        before = digest(lane / 'observations.json')
        child = subprocess.run(
            [sys.executable, str(lane / 'normalize.py')],
            cwd=lane, check=True, text=True, capture_output=True, timeout=30,
            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
        )
        after_validation = validate_lane(lane)
        after = digest(lane / 'observations.json')
        if not after_validation['passed'] or before != after:
            raise ValueError('Replay changed output or failed evidence checks: ' + lane.name)
        lane_reports.append({
            **after_validation, 'offline_replay_identical': True,
            'normalizer_sha256': digest(lane / 'normalize.py'),
            'observations_sha256': after, 'normalizer_stdout': child.stdout.strip(),
        })
        combined.extend(json.loads((lane / 'observations.json').read_text()))
        for a in json.loads((lane / 'manifest.json').read_text()):
            artifacts.append({**a, 'path': lane.name + '/' + a['path'], 'lane': lane.name})
    observation_ids = [o['observation_id'] for o in combined]
    artifact_ids = [a['artifact_id'] for a in artifacts]
    if len(set(observation_ids)) != len(observation_ids):
        raise ValueError('Cross-lane observation ID collision')
    if len(set(artifact_ids)) != len(artifact_ids):
        raise ValueError('Cross-lane artifact ID collision')
    for o in combined:
        if any(ev['artifact_id'] not in artifact_ids for ev in o['evidence']):
            raise ValueError('Dangling evidence reference')
    (ROOT / 'observations.json').write_text(json.dumps(combined, indent=2) + '\n')
    (ROOT / 'artifacts.json').write_text(json.dumps(artifacts, indent=2) + '\n')
    report = {
        'research_date': '2026-10-05', 'schema_version': 'state-spike-v1',
        'passed': True, 'observation_count': len(combined), 'artifact_count': len(artifacts),
        'method_counts': {k: sum(o['method']['kind'] == k for o in combined)
                          for k in ['deterministic', 'manual_visual', 'manual_text', 'model']},
        'predicate_counts': {k: sum(o['predicate'] == k for o in combined)
                             for k in sorted({o['predicate'] for o in combined})},
        'lanes': lane_reports,
        'checks': ['artifact hashes', 'envelope types', 'temporal shape',
                   'canonical vocabulary', 'exact text quote presence',
                   'explicit manual visual provenance', 'deterministic offline replay',
                   'cross-lane identity uniqueness', 'evidence reference integrity'],
        'limitations': ['No blanket semantic-entailment guarantee.',
                        'No statewide discovery or completeness result.',
                        'No production projection or publication approval.',
                        'No blinded accuracy or vendor-comparison benchmark.'],
    }
    (ROOT / 'validation-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['passed', 'observation_count', 'artifact_count', 'method_counts']}))


if __name__ == '__main__':
    main()
