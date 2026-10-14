#!/usr/bin/env python3
"""P5 fixture gate under amendment A1 (batched sessions). See AMENDMENT.md.

  python3 -I -S -B gate_batched.py                       # pins, frozen checks, BATCHES.json fresh
  python3 -I -S -B gate_batched.py --write-batches       # (re)write BATCHES.json, then run
  python3 -I -S -B gate_batched.py --adjudications DIR   # batched P5 gate: DIR/A1/<pid>.json, DIR/A2/<pid>.json
      [--excluded-sessions FILE]                         # optional JSON list of reference author/reviewer sessions

This is NOT a fork of the frozen scorer. It verifies the frozen design-r3-1 files against the
sha256 pins in design-r3-1/READY.primary.json, imports the frozen fixtures/check.py by path (which
loads r17score.py and r17recon.py), and replaces exactly one rule: check.py's "one fresh session
per packet" becomes "one fresh session per (role, batch)". Every other check (exactly A1 and A2,
one file per gold packet, role/model/effort, echoed bindings, mapping == gold on
(target, unit, form), compare_case) is check.py's own adjudicator_gate, unchanged.
Stdlib only.
"""
import collections
import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R17 = HERE.parents[1]
FROZEN = R17 / 'design-r3-1'
PACKETS = R17 / 'gate' / 'packets'
BATCHES_JSON = HERE / 'BATCHES.json'

READY_PRIMARY_SHA256 = '35b19756602aac89746f373313315a23c24d28b65d6318683a78ad1d4dceb9ed'
# The frozen files this gate executes or reads; each must match READY.primary.json.
PINNED = ('ADJUDICATION-SPEC.md', 'fixtures/check.py', 'fixtures/r17score.py', 'fixtures/r17recon.py',
          'fixtures/cases.json', 'fixtures/cases.src.json')
BATCH_SIZE = 10
AMENDMENT = 'A1-p5-batching'


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_pins():
    raw = (FROZEN / 'READY.primary.json').read_bytes()
    if _sha(raw) != READY_PRIMARY_SHA256:
        raise SystemExit('design-r3-1/READY.primary.json changed')
    pins = json.loads(raw.decode('utf-8'))['sha256']
    for rel in PINNED:
        if _sha((FROZEN / rel).read_bytes()) != pins[rel]:
            raise SystemExit(f'frozen file changed: design-r3-1/{rel}')
    return {rel: pins[rel] for rel in PINNED}


def load_check():
    verify_pins()
    spec = importlib.util.spec_from_file_location('r17check', FROZEN / 'fixtures' / 'check.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


C = load_check()
S = C.S


def load_data():
    """Exactly check.py main(): build from cases.src.json and require cases.json to match."""
    src = json.loads((C.HERE / 'cases.src.json').read_bytes().decode('utf-8'))
    encoded = (json.dumps(C.build(src), indent=1, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')
    if (C.HERE / 'cases.json').read_bytes() != encoded:
        raise SystemExit('frozen cases.json does not match its build')
    return json.loads(encoded.decode('utf-8'))


# ---------------------------------------------------------------- the batch partition

def partition(data):
    """Gold packet ids sorted, split into consecutive batches of BATCH_SIZE (last may be smaller).
    Returns [(batch_number, [packet ids])], numbered from 1; identical for both roles."""
    ids = sorted(c['packet']['packet_id'] for c in data['cases'] if c['gold'])
    return [(i // BATCH_SIZE + 1, ids[i:i + BATCH_SIZE]) for i in range(0, len(ids), BATCH_SIZE)]


def batches_manifest(data, packets_dir=PACKETS):
    """BATCHES.json: the dispatch plan. Each packet is bound by its file's sha256, and the packet's
    echoed bindings are checked against the frozen build (a stale or edited packet dir fails)."""
    gold = {c['packet']['packet_id']: c['packet'] for c in data['cases'] if c['gold']}
    part_a_sha = S.sha_bytes(C.part_a().encode('utf-8'))
    on_disk = sorted(p.stem for p in packets_dir.glob('*.json'))
    if on_disk != sorted(gold):
        raise SystemExit(f'{packets_dir}: packet files differ from the gold packet ids')
    batches = []
    for b, ids in partition(data):
        entries = []
        for pid in ids:
            raw = (packets_dir / f'{pid}.json').read_bytes()
            pk, want = json.loads(raw.decode('utf-8')), gold[pid]
            if (pk.get('call_id') != pid or pk.get('part_a_sha256') != part_a_sha
                    or any(pk.get(k) != want[k] for k in ('source_id', 'output_sha256', 'reference_sha256'))
                    or 'mappings' in pk):
                raise SystemExit(f'{packets_dir}/{pid}.json: bindings differ from the frozen build')
            entries.append(dict(packet_id=pid, file=f'gate/packets/{pid}.json', sha256=_sha(raw)))
        batches.append(dict(batch=b, packets=entries))
    return dict(amendment=AMENDMENT, batch_size=BATCH_SIZE, gold_packets=len(gold),
                part_a_sha256=part_a_sha,
                cases_json_sha256=_sha((C.HERE / 'cases.json').read_bytes()),
                roles={r: dict(model=m, effort=S.ADJ_EFFORT) for r, m in sorted(S.ADJUDICATORS.items())},
                sessions_required=len(batches) * len(S.ADJUDICATORS),
                rule='one fresh session per (role, batch); session ids unique across batches and roles; '
                     'a batch session sees only its own packets',
                batches=batches)


def manifest_bytes(data):
    return (json.dumps(batches_manifest(data), indent=1, sort_keys=True) + '\n').encode('utf-8')


# ---------------------------------------------------------------- the amended session rule

def _session(adj):
    who = adj.get('adjudicator') if isinstance(adj, dict) else None
    s = who.get('session') if isinstance(who, dict) else None
    return s if isinstance(s, str) and s else None


def batch_session_check(data, adjs, excluded=()):
    """The one amended rule. Within (role, batch) every file carries the same session; that session
    is used by no other batch or role and is not excluded. Missing/invalid sessions and missing files
    are left to check.py's gate, which reports them."""
    fails, owner, excluded = [], {}, set(excluded)
    for role in sorted(set(adjs) & set(S.ADJUDICATORS)):
        for b, ids in partition(data):
            got = [(pid, _session(adjs[role][pid])) for pid in ids if pid in adjs[role]]
            valid = [s for _, s in got if s is not None]
            if not valid:
                continue
            counts = collections.Counter(valid)
            # The batch's session: the most common one; ties go to the earliest packet's.
            batch_sess = max(valid, key=lambda s: (counts[s], -valid.index(s)))
            for pid, s in got:
                if s is not None and s != batch_sess:
                    fails.append(f'{role} batch {b} {pid}: session {s!r} does not match the batch session {batch_sess!r}')
            for s in sorted(counts):
                if s in excluded:
                    fails.append(f'{role} batch {b}: session {s!r} is a reference author/reviewer session')
                if s in owner and owner[s] != (role, b):
                    fails.append(f'{role} batch {b}: session {s!r} reused (also {owner[s][0]} batch {owner[s][1]})')
                owner.setdefault(s, (role, b))
    return fails


def _per_packet_view(adjs):
    """Rewrite each valid session to an injective (role dir, session, packet) key so that check.py's
    per-packet uniqueness test is vacuous (batch_session_check owns that rule); everything else
    it checks sees the files unchanged."""
    out = copy.deepcopy(adjs)
    for role, files in out.items():
        for pid, adj in files.items():
            if _session(adj) is not None:
                adj['adjudicator']['session'] = json.dumps([role, adj['adjudicator']['session'], pid])
    return out


def batched_gate(data, adjs, excluded=()):
    """Returns (checks, failures). check.py's adjudicator_gate with the session rule amended."""
    if set(adjs) != set(S.ADJUDICATORS):
        return 1, [f'adjudicator directories must be exactly {sorted(S.ADJUDICATORS)}, got {sorted(adjs)}']
    fails = batch_session_check(data, adjs, excluded)
    n, gf = C.adjudicator_gate(data, _per_packet_view(adjs))
    return n, fails + gf


# ---------------------------------------------------------------- main

def main(argv):
    pins = verify_pins()
    data = load_data()
    fails = []
    if '--write-batches' in argv:
        BATCHES_JSON.write_bytes(manifest_bytes(data))
    elif not BATCHES_JSON.exists() or BATCHES_JSON.read_bytes() != manifest_bytes(data):
        fails.append('BATCHES.json is missing or stale; run with --write-batches')
    counts, f = C.run(data)
    fails += f
    gate = 'not run (P5 requires --adjudications)'
    if '--adjudications' in argv:
        excluded = []
        if '--excluded-sessions' in argv:
            path = Path(argv[argv.index('--excluded-sessions') + 1])
            excluded = json.loads(path.read_bytes().decode('utf-8'))
            if not isinstance(excluded, list) or not all(isinstance(s, str) for s in excluded):
                raise SystemExit('--excluded-sessions must be a JSON list of strings')
        k, f = batched_gate(data, C.load_adjs(argv[argv.index('--adjudications') + 1]), excluded)
        gate = dict(checked=k, failures=len(f), batches=len(partition(data)),
                    sessions_required=len(partition(data)) * len(S.ADJUDICATORS))
        fails += f
    for f in fails:
        print('FAIL', f)
    print(json.dumps(dict(amendment=AMENDMENT, frozen_checks=counts, batched_gate=gate, failures=len(fails),
                          frozen_pins=pins, batches_json_sha256=_sha(BATCHES_JSON.read_bytes())
                          if BATCHES_JSON.exists() else None), sort_keys=True))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
