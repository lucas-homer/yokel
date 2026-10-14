"""Q7: the ordered release steps in release-prep/README.md still carry r1.3 values; r1.4 refuses them.

Also: the evidence files pinned in the A4 stage manifest (run/KEY-ATTESTATION.json,
run/CAP-ACCEPTANCE.json) are refused by r1.4's release_gate as they stand, and a gate reused
across cells is refused. Every refusal happens before any POST. Synthetic Harness only.
"""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _load as L
a = L.a
results = []


def check(name, ok, detail=''):
    results.append(ok)
    print(('ok   ' if ok else 'FAIL ') + name + ('  ' + detail if detail else ''))


readme = (L.R17 / 'release-prep/README.md').read_text()
readme_a4 = (L.R17 / 'release-prep-a4/README.md').read_text()
print('# release-prep/README.md (the only document with the ordered release steps) vs r1.4 constants')
for needle, meaning in (("KEY_MAX:1730000000", 'INIT KEY_MAX $1.73'), ("key_label:'yokel-r17-paid-comparison'", 'INIT key_label'),
                        ('5295a66700fee54b2e03344003e5638a5728b1949eedf0945062950cc40e33ff', 'INIT recon_sha256 (design engine)'),
                        ('$1.73 key', 'human key step'), ('adapter-r1-3', 'artifact mapping to r1.3')):
    check('release-prep/README.md still says %s (%s)' % (needle, meaning), needle in readme)
check('release-prep-a4/README.md has no ordered release steps of its own (defers: "Update INIT constants, label and recon hash")',
      'Exact primary release order' not in readme_a4 and 'Update INIT constants' in readme_a4)
check('release-prep-a4/README.md does not state the r1.4 INIT values (KEY_MAX 50000000000 / recon 8c98fab...)',
      '50000000000' not in readme_a4 and '8c98fabdc73fad10336698fa695869966a631d5a7d99b797725f2c711b1b6bb0' not in readme_a4)


def fresh():
    tmp = L.tempdir('readme')
    h = L.Harness(tmp.name)
    h.release['required_calls'] = h.init['required_calls'] = a.CALLS[:3]
    h.release['calls'] = {c: h.release['calls'][c] for c in a.CALLS[:3]}
    h.release['typed_testable'] = False
    man = a.read(h.root / h.release['artifacts']['scoring_manifest']['path'])
    man['typed_testable'] = False
    for s in man['sources'].values():
        s['compounds'] = {}
    h.release['artifacts']['scoring_manifest'] = h.write(h.release['artifacts']['scoring_manifest']['path'], man)
    h.release['thresholds'].update(N_c=0, T4=0)
    return tmp, h


def bind(h):
    h.release['init_sha256'] = a.sha(a.encode(h.init))
    h.save_release()
    h.rewrite_ledger([h.init, dict(type='BIND_RELEASE', release_policy=h.init['release_policy'],
                                 release_sha256=a.sha(h.release_path.read_bytes()))])


def refused(h, label, expect):
    expect = expect if isinstance(expect, tuple) else (expect,)
    try:
        h.execute('S1-OPQ', 'j')
        check(label, False, 'executed!')
    except a.Refused as exc:
        check(label + ' -> refused ' + str(exc) + ', 0 POST', str(exc) in expect and h.posts == [])


print('# r1.4 refuses INIT written with the README\'s r1.3 values (fail closed)')
tmp, h = fresh(); h.init['KEY_MAX'] = 1_730_000_000; h.init['key_limit'] = 1_730_000_000; bind(h); refused(h, 'INIT KEY_MAX 1730000000', 'init_constants'); tmp.cleanup()
tmp, h = fresh(); h.init['key_label'] = 'yokel-r17-paid-comparison'; bind(h); refused(h, 'INIT key_label yokel-r17-paid-comparison', 'init_namespace_key'); tmp.cleanup()
tmp, h = fresh(); h.init['recon_sha256'] = '5295a66700fee54b2e03344003e5638a5728b1949eedf0945062950cc40e33ff'; bind(h); refused(h, 'INIT recon_sha256 = design engine', 'init_static_pins'); tmp.cleanup()
tmp, h = fresh()
old_recon = (L.R17 / 'design-r3-1/fixtures/r17recon.py').read_bytes()
h.release['artifacts']['recon'] = h.write('design/fixtures/r17recon.py', old_recon)
bind(h); refused(h, 'RELEASE.json recon artifact = design-r3-1 engine', 'release_recon_pin'); tmp.cleanup()
tmp, h = fresh()
h.release['artifacts']['adapter'] = h.write('adapter/r17_adapter.py', (L.R17 / 'adapter-r1-3/r17_adapter.py').read_bytes())
bind(h); refused(h, 'RELEASE.json adapter artifact mapped to adapter-r1-3', ('freeze_pin', 'adapter_self_pin')); tmp.cleanup()

print('# the evidence files pinned by release-prep-a4/STAGE-MANIFEST.json, as they stand')
tmp, h = fresh()
h.release['artifacts']['key_attestation'] = h.write('run/KEY-ATTESTATION.json', (L.R17 / 'run/KEY-ATTESTATION.json').read_bytes())
bind(h); refused(h, 'run/KEY-ATTESTATION.json (limit_usd string, used_only_for_r17 string, no creation_date, limit_reset "none")', 'K3_attestation'); tmp.cleanup()
tmp, h = fresh()
h.init['release_policy'] = 'P-ACCEPT'; h.release['release_policy'] = 'P-ACCEPT'
raw = (h.root / h.release['artifacts']['budget']['path']).read_bytes().replace(b'RELEASE_POLICY = P-HARD', b'RELEASE_POLICY = P-ACCEPT')
h.release['artifacts']['budget'] = h.write(h.release['artifacts']['budget']['path'], raw)
dp = a.read(h.root / h.release['artifacts']['design_primary']['path']); dp['release_policy'] = 'P-ACCEPT'; dp['sha256']['BUDGET.md'] = a.sha(raw)
h.release['artifacts']['design_primary'] = h.write(h.release['artifacts']['design_primary']['path'], dp)
h.release['artifacts']['design_ready'] = h.write(h.release['artifacts']['design_ready']['path'], dict(release_policy='P-ACCEPT'))
att = a.read(h.root / h.release['artifacts']['key_attestation']['path']); att['release_policy'] = 'P-ACCEPT'
h.release['artifacts']['key_attestation'] = h.write(h.release['artifacts']['key_attestation']['path'], att)
h.init['budget_sha256'] = a.sha(raw)
h.release['artifacts']['policy_evidence'] = h.write('run/CAP-ACCEPTANCE.json', (L.R17 / 'run/CAP-ACCEPTANCE.json').read_bytes())
bind(h); refused(h, 'run/CAP-ACCEPTANCE.json as policy_evidence under P-ACCEPT (no accepted_by_primary/verbatim_acceptance/residual_risk_accepted)', 'policy_evidence'); tmp.cleanup()
print('   -> the A4 stage manifest pins evidence bytes the adapter will refuse; after normalization the manifest, stage and proposals must be regenerated.')

print('# a prior-cell gate reused for a later cell')
tmp, h = fresh(); bind(h)
h.queue = [L.packet(0), L.packet(10_000_000)]
r1 = h.execute('S1-OPQ', 'j1'); gate1 = h.stage()
h.queue = [L.packet(10_000_000), L.packet(20_000_000)]
r2 = h.execute('S2-OPQ', 'j2', staged_path=gate1)
check('S1 and S2 completed (2 POSTs)', r1['state'] == 13 and r2['state'] == 13 and len(h.posts) == 2)
try:
    h.execute('S3-OPQ', 'j3', staged_path=gate1)
    check('S3 with S2\'s gate executed?!', False)
except a.Refused as exc:
    check('S3 with the gate that admitted S2 (lists only S1) -> refused ' + str(exc) + ', still 2 POSTs', str(exc) == 'staged_gate_call_set' and len(h.posts) == 2)
try:
    h.execute('S3-OPQ', 'j4')
    check('S3 with no gate executed?!', False)
except a.Refused as exc:
    check('S3 with no gate -> refused ' + str(exc), str(exc) == 'adjudication_pause' and len(h.posts) == 2)
tmp.cleanup()

print('SUMMARY readme/evidence values:', sum(results), 'of', len(results), 'checks held')
sys.exit(0 if all(results) else 1)
