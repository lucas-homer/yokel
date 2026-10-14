"""Offline repro (R19 review Q4): release-prep constants, cell set/order, scope, and the frozen R17
P-ACCEPT reuse. Rebuilds the staging manifest in memory (read-only) and compares it with the committed
STAGE-MANIFEST.json, the R18 manifest and the accepted R17 RELEASE.json artifact pins."""
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[1]
R19 = BENCH / 'round19-rerun'


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    sys.modules[name] = m
    s.loader.exec_module(m)
    return m


a = load('r19_adapter_rp', R19 / 'adapter/r17_adapter.py')
rr = load('r19_release_records', R19 / 'release-prep/release_records.py')
mp = load('r19_make_proposals', R19 / 'release-prep/make_proposals.py')
pm = load('r19_prepare_manifest', R19 / 'release-prep/prepare_manifest.py')

# Cells, order, no FULL.
assert mp.CELLS == ['S1-OPQ', 'S2-OPQ', 'S3-OPQ'] and mp.R17 == 'round19-rerun'
assert a.CALLS[:3] == mp.CELLS
init = rr.init_record(a, b'synthetic budget', 118_819_500)
assert init['required_calls'] == ['S1-OPQ', 'S2-OPQ', 'S3-OPQ']
assert init['namespace'] == 'r19.paid-rerun.v1'
assert (init['FLOOR'], init['OPERATING'], init['CAP']) == (270_000_000, 1_800_000_000, 2_000_000_000)
assert (a.recon.FLOOR, a.recon.OPERATING, a.recon.CAP) == (270_000_000, 1_800_000_000, 2_000_000_000)
assert init['KEY_MAX'] == init['key_limit'] == 50_000_000_000 and init['key_limit_reset'] is None
assert init['release_policy'] == 'P-ACCEPT' and init['key_label'] == 'DocketClock'
assert init['recon_sha256'] == '64794fdda2f345559a5399ccd8e83142a93e621fcb5c6e79842209a4d4c27140'
for bad in (-1, True, 1.5, '1', None):
    try:
        rr.init_record(a, b'x', bad)
    except a.Refused:
        pass
    else:
        raise AssertionError(bad)
# Default scope and job-id prefix in make_proposals (argparse default + generate()).
src = (R19 / 'release-prep/make_proposals.py').read_text()
assert "default='docketclock-research-r19-authorized-20261014'" in src
assert "job_id = 'r19-' + cell.lower() + '-' + batch" in src
assert "identifier('r19-s1-opq-' + batch)" in src
assert 'r18' not in src and 'R18' not in src
# Source slots: manifest S1/S2/S3 -> 039/041/106 in order.
scoring = json.loads((BENCH / 'round17-paid-comparison/scoring-manifest/MANIFEST.json').read_bytes())
slots = [scoring['sources'][s]['source_id'] for s in ('S1', 'S2', 'S3')]
assert slots == ['26-19-039', '26-19-041', '26-19-106'], slots
assert scoring['typed_testable'] is False

# Staging manifest: rebuilt == committed; frozen R17 reuse identical to R18.
built = pm.build()
committed_raw = (R19 / 'release-prep/STAGE-MANIFEST.json').read_bytes()
assert pm.st.canonical(built) == committed_raw, 'rebuilt manifest differs from committed STAGE-MANIFEST.json'
m19 = built['files']
m18 = json.loads((BENCH / 'round18-rerun/release-prep/STAGE-MANIFEST.json').read_bytes())['files']
def frozen_part(m):
    return {k: v for k, v in m.items() if not k.startswith(('round18-rerun/', 'round19-rerun/'))}
assert frozen_part(m18) == frozen_part(m19), 'frozen R14–R17 closure differs between R18 and R19 manifests'
r18_only = sorted(k for k in m19 if k.startswith('round18-rerun/'))
assert r18_only == ['round18-rerun/recon/READY.json', 'round18-rerun/recon/r17recon.py'], r18_only
assert m19['round18-rerun/recon/r17recon.py'] == '64794fdda2f345559a5399ccd8e83142a93e621fcb5c6e79842209a4d4c27140'
assert 'round19-rerun/amendments/A7.md' in m19 and 'round19-rerun/amendments/A5-A6.md' in m19
assert m19['round19-rerun/wire/wire.py'] == 'f17af0190dbc35eeeeeb1df00afe594f555f0a4df80aa9cb842083d9713c0ffb'
assert not any('/run-live/' in k or k.endswith('/KEY-MACHINE.json') or k.endswith('/content.body') for k in m19)
assert not any('adapter-r1-4' in k or 'recon-a4' in k for k in m19)
# Every frozen R17 artifact the accepted R17 release pinned (design, references, gates, scoring
# manifest, sources READY, attestation, CAP-ACCEPTANCE) is present with the identical hash.
rel17 = json.loads((BENCH / 'round17-paid-comparison/run-live/stage-run/RELEASE.json').read_bytes())
reused, excluded = [], []
for role, item in rel17['artifacts'].items():
    p = item['path']
    if role in ('adapter', 'adapter_ready', 'tests', 'host_driver', 'recon', 'machine_check'):
        assert p not in m19, p
        excluded.append(role)
        continue
    key = p
    if p.startswith('round17-paid-comparison/run/'):
        # R18/R19 install normalized copies under release-prep/evidence (same bytes required).
        key = 'round19-rerun/release-prep/evidence/' + Path(p).name
    assert m19.get(key) == item['sha256'], (role, p, key)
    reused.append(role)
assert set(reused) >= {'protocol', 'budget', 'reference_spec', 'adjudication_spec', 'scorer', 'cases', 'cases_src',
                       'check', 'design_primary', 'design_ready', 'A1_fixture_gate', 'A2_fixture_gate',
                       'reference_ready', 'scoring_manifest', 'sources_ready', 'key_attestation', 'policy_evidence'}
print('reused R17 release artifacts with identical hash:', sorted(reused))
print('deliberately not reused (fresh in R19 or superseded):', sorted(excluded))
print('round18-rerun entries in R19 manifest:', r18_only)
print('OK: cells S1/S2/S3-OPQ = 039/041/106, no FULL; FLOOR/OPERATING/CAP 270000000/1800000000/2000000000;',
      'scope docketclock-research-r19-authorized-20261014; frozen R17 P-ACCEPT closure identical to R18')
