"""Pin/verify only this preparation and frozen metadata; no runner or body reads."""
import argparse
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
R17 = HERE.parent


def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def payload():
    return {p.relative_to(HERE).as_posix(): pin(p) for p in sorted(HERE.rglob('*'))
            if p.is_file() and '_out' not in p.relative_to(HERE).parts and p.name != 'READY.json'}


def frozen():
    return {str(p.relative_to(R17)): pin(p)['sha256']
            for folder in ('release-prep-a4', 'adapter-r1-4', 'recon-a4')
            for p in sorted((R17/folder).rglob('*')) if p.is_file()}


def verify_frozen():
    baseline = json.loads((HERE/'_out/frozen-before-r2.json').read_bytes())
    assert frozen() == baseline, 'frozen inputs changed'
    return baseline


def write():
    verify_frozen()
    log = HERE/'_out/r2-tests.txt'
    output = log.read_text()
    assert re.findall(r'^Ran (\d+) tests', output, re.M) == ['21']
    assert re.findall(r'^OK$', output, re.M) == ['OK']
    assert not re.search(r'^FAILED|^ERROR:|^FAIL:', output, re.M)
    evidence = {}
    for name in ('KEY-ATTESTATION.json', 'CAP-ACCEPTANCE.json'):
        data = json.loads((HERE/'evidence'/name).read_bytes())
        evidence[name] = dict(output=pin(HERE/'evidence'/name), source_sha256=data['source_sha256'])
    ready = dict(schema_version='r17.release-prep-a4-r2-ready.v1',
        status='READY_OFFLINE_IMPLEMENTATION', revision='A4-r2',
        files=payload(), evidence=evidence,
        tests=dict(executable='/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12',
            flags=['-I','-S','-B'], run=21, passed=21, failed=0,
            output='_out/r2-tests.txt', output_pin=pin(log)),
        frozen_baseline=dict(path='_out/frozen-before-r2.json', pin=pin(HERE/'_out/frozen-before-r2.json')),
        frozen_inputs_unchanged=True, normalized_evidence_adapter_validation='PASS: frozen adapter-r1-4 release_gate, synthetic full release, no dispatch',
        dispositions=dict(S7='fixed',S8='fixed',S9='fixed',S10='fixed',N33='fixed',N36='documented primary pre-release check',N29='documented arithmetic; live measured bootstrap margin pending'),
        release_policy='P-ACCEPT', required_calls=['S1-OPQ','S2-OPQ','S3-OPQ'],
        key_label='DocketClock', key_max_nanousd=50000000000,
        CAP=2000000000, OPERATING=1800000000, FLOOR=270000000,
        manifest_status='prospective normalized run pins; primary installation and additional release evidence required',
        network_calls=0, provider_calls=0, credentials_accessed=False,
        runner_executor_release_check_job_commands_run=False, production_staged=False,
        source_bodies_read=False, reference_contents_read=False, committed=False,
        production_eligible=False, paid_release_authorized=False,
        self_pin='READY excludes itself; primary pins exact hash externally')
    (HERE/'READY.json').write_text(json.dumps(ready,sort_keys=True,indent=2)+'\n')


def verify():
    ready = json.loads((HERE/'READY.json').read_bytes())
    assert ready['files'] == payload(), 'prep payload drift'
    assert pin(HERE/ready['tests']['output']) == ready['tests']['output_pin']
    assert pin(HERE/ready['frozen_baseline']['path']) == ready['frozen_baseline']['pin']
    verify_frozen()
    print('READY inventory, test log, frozen baseline and frozen input bytes verified')
    print('READY sha256: '+pin(HERE/'READY.json')['sha256'])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--verify',action='store_true')
    args=p.parse_args()
    if not args.verify:
        write()
    verify()
