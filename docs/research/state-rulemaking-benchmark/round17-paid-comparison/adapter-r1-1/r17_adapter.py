"""R17 P3: one cell, one POST, durable accounting. Stdlib; no credential access.

The native host injects credential-owning callbacks; this module never resolves a key.
All imports of benchmark executables execute verified bytes, never an unpinned reopen.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import sys
import time
from contextlib import contextmanager

HERE = Path(__file__).resolve().parent
R17 = HERE.parent
BENCH = R17.parent
DESIGN = R17 / 'design-r3-1'
RECON_SHA = '5295a66700fee54b2e03344003e5638a5728b1949eedf0945062950cc40e33ff'
WIRE_SHA = '662268ba0774d7ef5a121ec4af90003a3836c07e4ce5a5ae551a413fe8375ab1'
CALLS = [f'S{i}-OPQ' for i in (1, 2, 3)] + [f'S{i}-FULL' for i in (1, 2, 3)]
NAMESPACE = 'r17.paid-comparison.v1'
POST_URL = 'https://openrouter.ai/api/v1/chat/completions'
KEY_URL = 'https://openrouter.ai/api/v1/key'
KEY_LABEL = 'yokel-r17-paid-comparison'
MAX_RAW = 2_000_000
HEADER_NAMES = {'content-type', 'date', 'x-request-id', 'x-openrouter-request-id',
                'x-openai-request-id', 'openai-request-id'}
FLAGS = dict(automatic_retry=False, production_eligible=False, action_ready=False,
             invoice_verified=False)


class Refused(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise Refused(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


class Number(str):
    """The exact raw JSON decimal token, distinct from a JSON string."""


def strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate_json_key')
            result[key] = value
        return result
    def constant(_):
        raise Refused('nonfinite_json')
    return json.loads(raw, object_pairs_hook=pairs, parse_float=Number,
                      parse_constant=constant)


def read(path):
    return strict(Path(path).read_bytes())


def filter_headers(headers):
    """Only response metadata crosses the receipt boundary; never echo bearer/cookies."""
    result = {}
    for name, value in headers.items():
        if not isinstance(name, str) or not isinstance(value, str):
            continue
        name = name.lower()
        if name not in HEADER_NAMES and not re.fullmatch(r'x-ratelimit-[a-z0-9-]+', name):
            continue
        if re.search(r'sk-or-|bearer\s|authorization|set-cookie', value, re.I):
            continue
        if '\r' in value or '\n' in value:
            continue
        result[name] = value[:1024]
    return result


def receipt(path, repair=False, valid=None):
    """A torn receipt is evidence, never a reason to repeat an uncertain GET."""
    path = Path(path)
    if not path.exists():
        return None
    raw = path.read_bytes()
    try:
        value = strict(raw)
        require(isinstance(value, dict), 'receipt_object')
        require(valid is None or valid(value), 'receipt_shape')
        return value
    except (ValueError, TypeError, UnicodeError):
        if repair:
            sidecar = path.with_name(path.name + '.torn-' + sha(raw) + '.bin')
            if not sidecar.exists():
                put(sidecar, raw)
            else:
                require(sidecar.read_bytes() == raw, 'receipt_sidecar_mismatch')
            path.unlink()
            fsync_dir(path.parent)
        return None


def recovery_calls(ledger):
    resolved = {e['call'] for e in ledger.entries if e['type'] == 'RESOLVE' and e['dispatched']}
    reconciled = {e['call'] for e in ledger.entries if e['type'] == 'RECONCILED'}
    needed = set(recon.pending(ledger.entries))
    for e in ledger.entries:
        if e['type'] != 'DISPATCH_MARK':
            continue
        folder = ledger.root / e['attempt_dir']
        finals = [final_receipt(folder, n, e['call'])
                  for n in ('completed.json', 'stop.json', 'recovered.json')]
        final = any(v is not None for v in finals)
        normally_stopped = (finals[1] is not None or finals[2] is not None) and e['call'] in resolved
        if not final or e['call'] not in reconciled and not normally_stopped:
            needed.add(e['call'])
    return needed


def final_receipt(folder, name, cell, repair=False):
    def valid(v):
        if name == 'recovered.json':
            return (v.get('call') == cell and type(v.get('dispatched')) is bool
                    and type(v.get('debit')) is int and v['debit'] >= 0)
        return (isinstance(v.get('files'), dict) and bool(v['files'])
                and type(v.get('state')) is int and 'halt' in v)
    return receipt(folder / name, repair=repair, valid=valid)


def load_pinned(name, path, expected):
    path = Path(path)
    raw = path.read_bytes()
    require(sha(raw) == expected, 'dependency_pin:' + name)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def dependencies():
    primary = read(DESIGN / 'READY.primary.json')['sha256']
    require(primary['fixtures/r17recon.py'] == RECON_SHA, 'primary_recon_pin')
    require(read(R17 / 'sources-r2/READY.json')['upstream']['wire']['sha256'] == WIRE_SHA,
            'source_wire_pin')
    return (load_pinned('r17_exact_recon', DESIGN / 'fixtures/r17recon.py', RECON_SHA),
            load_pinned('r17_exact_wire', BENCH / 'round16-wire-compat/protocol-w2-1/wire.py', WIRE_SHA))


recon, wire = dependencies()


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def put(path, value):
    path = Path(path)
    raw = value if isinstance(value, bytes) else encode(value)
    with path.open('xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    fsync_dir(path.parent)


def claim(path):
    path = Path(path)
    path.mkdir(exist_ok=False)
    fsync_dir(path.parent)


class Clock:
    def now(self):
        return time.time()

    def wait_until(self, deadline):
        while self.now() < deadline:
            time.sleep(max(0, min(60, deadline - self.now())))


def ledger_shapes(entries):
    """Reject well-hashed but impossible entry sequences before applying the pure rules."""
    required = entries[0].get('required_calls', [])
    pending, marked, completed, reconciled, jobs = {}, set(), set(), set(), set()
    for entry in entries:
        kind, call = entry['type'], entry.get('call')
        if kind in ('RESERVE', 'DISPATCH_MARK', 'RESOLVE', 'RECONCILED', 'SKIP'):
            require(call in required, 'ledger_unknown_call')
        if kind in ('RESERVE', 'DISPATCH_MARK', 'RESOLVE'):
            name = entry.get('attempt_dir')
            require(isinstance(name, str) and name not in ('.', '..')
                    and re.fullmatch(r'[A-Za-z0-9_.-]+', name), 'ledger_attempt_path')
        if kind == 'RESERVE':
            require(not pending and call not in completed and entry.get('job_id') not in jobs,
                    'ledger_impossible_reserve')
            require(isinstance(entry.get('job_id'), str) and re.fullmatch(r'[A-Za-z0-9_-]{1,100}',
                    entry['job_id']) and entry.get('floor') == recon.FLOOR, 'ledger_reserve_fields')
            jobs.add(entry.get('job_id'))
            pending[call] = entry['attempt_dir']
        elif kind == 'DISPATCH_MARK':
            require(pending.get(call) == entry['attempt_dir'] and call not in marked,
                    'ledger_impossible_dispatch')
            marked.add(call)
        elif kind == 'RESOLVE':
            require(pending.get(call) == entry['attempt_dir'] and type(entry.get('dispatched')) is bool,
                    'ledger_impossible_resolve')
            require((entry['dispatched'] and entry['debit'] >= recon.FLOOR) or
                    (not entry['dispatched'] and entry['debit'] == 0 and call not in marked),
                    'ledger_dispatch_debit')
            require(entry.get('reported') is None or type(entry['reported']) is int
                    and entry['reported'] >= 0, 'ledger_reported_cost')
            pending.pop(call)
            if entry['dispatched']:
                completed.add(call)
        elif kind == 'RECONCILED':
            require(call in completed and call not in reconciled and type(entry.get('U')) is int
                    and entry['U'] >= 0, 'ledger_impossible_reconciliation')
            reconciled.add(call)
        elif kind == 'SKIP':
            require(not pending and call not in completed and entry.get('rule_id') in (
                'D1', 'D5', 'T6', 'OPQ-semantic-futility', 'FULL-semantic-futility'), 'ledger_impossible_skip')
            completed.add(call)


class Ledger:
    def __init__(self, root, clock=None):
        self.root = Path(root)
        self.path = self.root / 'ledger.jsonl'
        self.clock = clock or Clock()
        self.locked = False
        self.entries = []
        self.offset = None
        self.tail_hash = None

    @contextmanager
    def lock(self, run_id):
        require(not self.locked, 'nested_lock')
        # No stale-lock guessing or automatic unlink, even if the PID is gone.
        put(self.root / 'ledger.lock', dict(pid=os.getpid(), host=socket.gethostname(),
                                           started=str(self.clock.now()), run_id=run_id))
        self.locked = True
        crashed = False
        try:
            yield self
        except BaseException as exc:
            crashed = not isinstance(exc, Exception)
            raise
        finally:
            self.locked = False
            if not crashed:
                (self.root / 'ledger.lock').unlink()
                fsync_dir(self.root)

    def load(self, repair_tail=False, lock_evidence_sha256=None):
        require(self.locked, 'ledger_requires_lock')
        raw = self.path.read_bytes()
        lines = raw.splitlines(keepends=True)
        entries, offset, torn = [], 0, False
        for index, line in enumerate(lines):
            try:
                require(line.endswith(b'\n'), 'unterminated_ledger_line')
                entry = read_line = strict(line[:-1])
            except (ValueError, TypeError):
                require(index == len(lines) - 1 and repair_tail, 'ledger_corrupt')
                tail = raw[offset:]
                sidecar = self.root / ('ledger-torn-' + sha(tail) + '.bin')
                if not sidecar.exists():
                    put(sidecar, tail)
                else:
                    require(sidecar.read_bytes() == tail, 'torn_sidecar_mismatch')
                with self.path.open('r+b') as handle:
                    handle.truncate(offset)
                    handle.flush()
                    os.fsync(handle.fileno())
                fsync_dir(self.root)
                torn = True
                break
            require(isinstance(entry, dict) and encode(read_line) == line[:-1], 'ledger_noncanonical')
            require(entry.get('type') in {'INIT', 'BIND_RELEASE', 'RESERVE', 'DISPATCH_MARK',
                    'RESOLVE', 'RECONCILED', 'SKIP', 'RECONCILE_UP', 'RECOVER',
                    'LOCK_RECOVERED', 'HALT'}, 'ledger_entry_type')
            if entries:
                require(entry.get('prev_sha256') == sha(encode(entries[-1])), 'ledger_chain')
                require(entry['type'] != 'INIT', 'duplicate_init')
            else:
                require(entry['type'] == 'INIT' and 'prev_sha256' not in entry, 'ledger_init')
            if entry['type'] in ('RESOLVE', 'RECONCILE_UP'):
                require(type(entry.get('debit')) is int and entry['debit'] >= 0, 'ledger_debit')
            entries.append(entry)
            offset += len(line)
        require(entries, 'empty_ledger')
        ledger_shapes(entries)
        self.entries = entries
        self.offset = offset
        self.tail_hash = sha(encode(entries[-1]))
        if lock_evidence_sha256 is not None:
            self.append('LOCK_RECOVERED', evidence_sha256=lock_evidence_sha256)
        if torn:
            self.append('RECOVER', torn_sha256=sha(tail), torn_length=len(tail))
        return torn

    def append(self, kind, **fields):
        require(self.locked, 'append_requires_lock')
        entry = dict(type=kind, **fields)
        if self.entries:
            entry['prev_sha256'] = sha(encode(self.entries[-1]))
        raw = encode(entry) + b'\n'
        with self.path.open('a+b') as handle:
            self.assert_tail(handle)
            handle.write(raw)
            handle.flush()
            # Track bytes actually written even if the following durability step fails.
            # A failure is recovered conservatively, never resolved as unmarked.
            self.entries.append(entry)
            self.offset += len(raw)
            self.tail_hash = sha(raw[:-1])
            os.fsync(handle.fileno())
        fsync_dir(self.root)
        return entry

    def assert_tail(self, handle=None):
        require(self.locked, 'tail_requires_lock')
        if handle is None:
            with self.path.open('rb') as opened:
                return self.assert_tail(opened)
        require(os.fstat(handle.fileno()).st_size == self.offset, 'ledger_tail_changed')
        last = encode(self.entries[-1]) + b'\n'
        handle.seek(self.offset - len(last))
        actual = handle.read(len(last))
        require(actual.endswith(b'\n') and sha(actual[:-1]) == self.tail_hash,
                'ledger_tail_changed')
        handle.seek(0, os.SEEK_END)

    def verify(self, expected=None):
        before = copy.deepcopy(self.entries)
        before_tail = self.offset, self.tail_hash
        try:
            self.load()
            require(before == self.entries, 'AD7_ledger_changed')
            if expected is not None:
                require(recon.aggregate(self.entries) == expected, 'AD7_aggregate')
        except Exception:
            self.entries = before
            self.offset, self.tail_hash = before_tail
            raise


def artifact(root, release, name):
    item = release['artifacts'][name]
    path = (Path(root) / item['path']).resolve()
    require(not Path(item['path']).is_absolute() and path.is_relative_to(Path(root).resolve()),
            'artifact_path')
    raw = path.read_bytes()
    require(sha(raw) == item['sha256'], 'artifact_pin:' + name)
    return path, raw


def freeze(root, path, raw):
    """Verify the transitive files enumerated by a freeze, not just its manifest hash."""
    ready = strict(raw)
    pins = ready.get('sha256', ready.get('files'))
    require(isinstance(pins, dict) and pins, 'freeze_files')
    for name, pin in pins.items():
        target = (path.parent / name).resolve()
        require(not Path(name).is_absolute() and target.is_relative_to(Path(root).resolve()), 'freeze_path')
        expected = pin['sha256'] if isinstance(pin, dict) else pin
        require(sha(target.read_bytes()) == expected, 'freeze_pin')
    return ready


REQUIRED_ARTIFACTS = {'protocol', 'budget', 'reference_spec', 'adjudication_spec', 'scorer',
    'recon', 'cases', 'cases_src', 'check', 'A1_fixture_gate', 'A2_fixture_gate', 'sources_ready',
    'reference_ready', 'scoring_manifest', 'policy_evidence', 'key_attestation', 'machine_check',
    'roles_auth', 'adapter', 'tests', 'adapter_ready', 'design_ready', 'design_primary'}


def release_gate(ledger, release_path, cell, source, root=BENCH):
    release_raw = Path(release_path).read_bytes()
    release = strict(release_raw)
    init = ledger.entries[0]
    policy = release.get('release_policy')
    require(policy in recon.RELEASE_POLICIES, 'release_policy_unset')
    require(release.get('schema_version') == 'r17.release.v1', 'release_schema')
    require(init.get('release_policy') == policy, 'release_init_policy')
    require(init.get('namespace') == NAMESPACE and init.get('key_label') == KEY_LABEL,
            'init_namespace_key')
    require(all(init.get(k) == v for k, v in {'CAP': recon.CAP, 'OPERATING': recon.OPERATING,
            'FLOOR': recon.FLOOR, 'KEY_MAX': recon.KEY_MAX, 'key_initial_usage': 0,
            'key_limit_reset': None}.items()), 'init_constants')
    calls = release.get('required_calls')
    require(type(release.get('typed_testable')) is bool, 'typed_testable')
    require(calls == (CALLS if release['typed_testable'] else CALLS[:3])
            and init.get('required_calls') == calls, 'required_calls')
    require(recon.key_limit_ok(init.get('key_limit'), len(calls)), 'key_limit')
    require(release.get('init_sha256') == sha(encode(init)), 'release_init_hash')
    binds = [e for e in ledger.entries if e['type'] == 'BIND_RELEASE']
    require(len(binds) == 1 and binds[0].get('release_sha256') == sha(release_raw)
            and binds[0].get('release_policy') == policy, 'BIND_RELEASE')
    require(not any(e['type'] == 'RESERVE' for e in ledger.entries[:ledger.entries.index(binds[0])]),
            'reserve_before_binding')
    require(release.get('model') == 'openai/gpt-6.1-sol' and release.get('provider') == 'OpenAI',
            'release_identity')
    require(REQUIRED_ARTIFACTS <= set(release.get('artifacts', {})), 'release_missing_artifacts')
    artifacts = {name: artifact(root, release, name) for name in release['artifacts']}
    budget = artifacts['budget'][1].decode('utf-8')
    require(re.search(r'^RELEASE_POLICY\s*=\s*' + re.escape(policy) + r'\b', budget, re.M),
            'budget_policy_unset_or_mismatch')
    design_path = artifacts['design_primary'][0]
    require(design_path == artifacts['protocol'][0].parent / 'READY.primary.json'
            and artifacts['design_ready'][0] == design_path.parent / 'READY.json', 'design_ready_path')
    design_ready = strict(artifacts['design_primary'][1])
    require(design_ready.get('release_policy') == policy
            and strict(artifacts['design_ready'][1]).get('release_policy') == policy, 'design_ready_policy')
    for name in ('protocol', 'budget', 'reference_spec', 'adjudication_spec', 'scorer',
                 'recon', 'cases', 'cases_src', 'check'):
        path, raw = artifacts[name]
        relative = path.relative_to(design_path.parent).as_posix()
        require(design_ready['sha256'].get(relative) == sha(raw), 'design_freeze_pin')
    require(sha(artifacts['recon'][1]) == RECON_SHA, 'release_recon_pin')
    require(init.get('budget_sha256') == sha(artifacts['budget'][1])
            and init.get('recon_sha256') == RECON_SHA, 'init_static_pins')
    for role in ('A1', 'A2'):
        gate = strict(artifacts[role + '_fixture_gate'][1])
        require(gate.get('role') == role and gate.get('failures') == 0
                and gate.get('all_gold_packets') is True and gate.get('accepted_by_primary') is True
                and gate.get('cases_sha256') == sha(artifacts['cases'][1])
                and gate.get('check_sha256') == sha(artifacts['check'][1]),
                'P5_fixture_gate')
    reference_ready = freeze(root, *artifacts['reference_ready'])
    require(reference_ready.get('accepted_by_primary') is True, 'P6_reference_freeze')
    adapter_ready = freeze(root, *artifacts['adapter_ready'])
    require(adapter_ready.get('status') == 'READY_OFFLINE_IMPLEMENTATION', 'P3_adapter_freeze')
    require(artifacts['adapter'][1] == Path(__file__).read_bytes(), 'adapter_self_pin')
    require(artifacts['tests'][1] == (HERE / 'test_adapter.py').read_bytes(), 'test_self_pin')
    evidence = strict(artifacts['policy_evidence'][1])
    expected_name = 'ENFORCEMENT-EVIDENCE.json' if policy == 'P-HARD' else 'CAP-ACCEPTANCE.json'
    require(artifacts['policy_evidence'][0].name == expected_name
            and evidence.get('accepted_by_primary') is True, 'policy_evidence')
    if policy == 'P-HARD':
        require(evidence.get('enforcement') in ('E-1', 'E-2')
                and evidence.get('cross_provider_review_accepted') is True
                and evidence.get('documentation') and evidence.get('review_sha256'), 'hard_enforcement')
        require(isinstance(evidence['documentation'], list), 'enforcement_documentation')
        for document in evidence['documentation']:
            require(isinstance(document, dict) and document.get('url') and document.get('retrieved_utc'),
                    'enforcement_documentation')
            artifact(root, dict(artifacts=dict(document=document)), 'document')
        _, review_raw = artifact(root, dict(artifacts=dict(review=evidence['review'])), 'review')
        require(sha(review_raw) == evidence['review_sha256'], 'enforcement_review_pin')
        if evidence['enforcement'] == 'E-2':
            require(type(evidence.get('all_in_upper_bound_nano')) is int
                    and 0 <= evidence['all_in_upper_bound_nano'] <= recon.FLOOR
                    and evidence.get('established') == dict(CN1=True, CN2=True, CN3=True, CN4=True),
                    'E2_bound')
    else:
        require(evidence.get('date') and evidence.get('verbatim_acceptance')
                and evidence.get('residual_risk_accepted') is True, 'conditional_acceptance')
    attestation = strict(artifacts['key_attestation'][1])
    require(attestation.get('key_label') == KEY_LABEL and attestation.get('used_only_for_R17') is True
            and attestation.get('creation_date') and attestation.get('release_policy') == policy
            and attestation.get('limit') == init['key_limit']
            and attestation.get('limit_reset') is None, 'K3_attestation')
    machine = strict(artifacts['machine_check'][1])
    require(machine.get('endpoint') == KEY_URL and machine.get('documentation_confirmed') is True
            and machine.get('usage_units') == 'USD' and machine.get('usage_field') == 'usage'
            and machine.get('response_sha256') and machine.get('accepted_by_primary') is True
            and machine.get('usage') == 0 and machine.get('limit') == init['key_limit']
            and machine.get('limit_remaining') == init['key_limit']
            and machine.get('limit_reset') is None, 'K3_machine_check')
    auth = strict(artifacts['roles_auth'][1])
    require(auth.get('authMethod') == 'claude.ai' and auth.get('anthropic_api_key_override') is False
            and auth.get('reference_reviewer') == 'gpt-6-astra'
            and auth.get('reviewer_provider') == 'codex' and auth.get('accepted_by_primary') is True,
            'P8_roles_auth')
    manifest = strict(artifacts['scoring_manifest'][1])
    require(manifest.get('typed_testable') == release['typed_testable']
            and set(manifest.get('sources', {})) == {'S1', 'S2', 'S3'}, 'manifest_slots')
    counts = [len(manifest['sources'][s]['relations']) for s in ('S1', 'S2', 'S3')]
    nc = sum(len(manifest['sources'][s]['compounds']) for s in ('S1', 'S2', 'S3'))
    require(all(type(flag) is bool for s in ('S1', 'S2', 'S3') for group in ('relations', 'compounds')
                for flag in manifest['sources'][s][group].values()), 'manifest_critical_flags')
    critical = [sum(manifest['sources'][s]['relations'].values()) for s in ('S1', 'S2', 'S3')]
    critical_compounds = sum(sum(manifest['sources'][s]['compounds'].values()) for s in ('S1', 'S2', 'S3'))
    require(min(counts) >= 2 and sum(counts) >= 12 and release['typed_testable'] == (nc >= 5),
            'P6_E8_counts')
    require(release.get('thresholds') == dict(N=sum(counts), n_s=counts, N_c=nc,
            D2=(9 * sum(counts) + 9) // 10, D3_correct=(3 * sum(counts) + 3) // 4,
            D3_acceptable=(9 * sum(counts) + 9) // 10,
            D2_source=[(3 * n + 3) // 4 for n in counts], T4=(9 * nc + 9) // 10,
            critical=sum(critical), critical_per_source=critical,
            critical_compounds=critical_compounds), 'threshold_table')
    sources_ready = strict(artifacts['sources_ready'][1])
    slots = [manifest['sources'][s]['source_id'] for s in ('S1', 'S2', 'S3')]
    require(slots == sorted(slots) and len(set(slots)) == 3, 'source_order')
    for s in ('S1', 'S2', 'S3'):
        src = manifest['sources'][s]
        require(sources_ready['files'][src['source_id'] + '/parsed-body.txt']['sha256']
                == src['source_sha256'], 'source_freeze_hash')
    require(cell in calls and set(release.get('calls', {})) == set(calls), 'release_call_set')
    slot = manifest['sources'][cell.split('-')[0]]
    require(sha(source.encode('utf-8')) == slot['source_sha256'], 'source_input_hash')
    return release, sha(release_raw), sha(artifacts['reference_ready'][1]), manifest


def done_calls(entries):
    return {e['call'] for e in entries if e['type'] == 'SKIP'
            or e['type'] == 'RESOLVE' and e['dispatched']}


def last_usage(entries):
    return next((e['U'] for e in reversed(entries) if e['type'] == 'RECONCILED'), 0)


def staged_gate(ledger, cell, release_hash, reference_hash, gate_path=None, opq_freeze=None):
    """P7 primary's accepted, pinned scorer report; no new adjudication inside adapter."""
    done = done_calls(ledger.entries)
    remaining = [c for c in ledger.entries[0]['required_calls'] if c not in done]
    require(remaining and cell == remaining[0], 'wrong_cell_order')
    require(not any(e['type'] == 'SKIP' for e in ledger.entries), 'futility_ended_run')
    if not done:
        return
    require(gate_path is not None, 'adjudication_pause')
    raw = Path(gate_path).read_bytes()
    if recon.pending(ledger.entries):
        reservation = next(e for e in reversed(ledger.entries) if e['type'] == 'RESERVE')
        require(sha(raw) == reservation.get('staged_gate_sha256'), 'staged_gate_changed')
    gate = strict(raw)
    require(gate.get('accepted_by_primary') is True and gate.get('release_sha256') == release_hash
            and gate.get('reference_ready_sha256') == reference_hash, 'staged_gate_binding')
    completed = {e['call']: e for e in ledger.entries if e['type'] == 'RESOLVE' and e['dispatched']}
    require(set(gate.get('calls', {})) == set(completed), 'staged_gate_call_set')
    for call, entry in completed.items():
        folder = ledger.root / entry['attempt_dir']
        result_raw = (folder / 'result.json').read_bytes()
        result = strict(result_raw)
        g = gate['calls'][call]
        require(g.get('result_sha256') == sha(result_raw) and result['state'] == 13
                and result['halt'] is None and result['completion_tokens'] <= 13926,
                'staged_result_binding')
        require(g.get('A1_sha256') and g.get('A2_sha256'), 'both_adjudicators_required')
    pins = gate.get('files')
    require(isinstance(pins, dict) and pins, 'staged_gate_files')
    for name, want in pins.items():
        path = (Path(gate_path).parent / name).resolve()
        require(path.is_relative_to(ledger.root.resolve()), 'staged_gate_path')
        require(sha(path.read_bytes()) == want, 'staged_gate_pin')
    required_pins = {g[k] for g in gate['calls'].values() for k in ('A1_sha256', 'A2_sha256')}
    require(required_pins <= set(pins.values()) and gate.get('scorer_report_sha256') in pins.values(),
            'staged_gate_report_pins')
    report_path = next((Path(gate_path).parent / n for n, h in pins.items()
                        if h == gate['scorer_report_sha256']))
    report = read(report_path)
    require(report.get('state', {}).get('halted_phase') is None, 'staged_report_halted')
    arm = cell.split('-')[1]
    states = report.get('state', {}).get(arm.lower())
    opq_states = report.get('state', {}).get('opq')
    stopped = (states is not None and any(s in ('unreachable', 'fail') for s in states.values())
               or arm == 'FULL' and opq_states != {'A1': 'pass', 'A2': 'pass'})
    if stopped:
        require(report.get('outcome') in (None, 'O1', 'O3', 'O4'), 'staged_stop_outcome')
        require(not recon.pending(ledger.entries), 'staged_gate_changed')
        for skipped in remaining:
            ledger.append('SKIP', call=skipped, reason='not run, pre-registered futility',
                          rule_id='OPQ-semantic-futility' if arm == 'OPQ'
                          or opq_states != {'A1': 'pass', 'A2': 'pass'} else 'FULL-semantic-futility')
        raise Refused('semantic_futility_stop')
    require(report.get('outcome') is None and states in (
        {'A1': 'reachable', 'A2': 'reachable'}, {'A1': 'pass', 'A2': 'pass'}), 'staged_report_state')
    if arm == 'FULL':
        require(report['state'].get('opq') == {'A1': 'pass', 'A2': 'pass'} and opq_freeze,
                'FULL_requires_frozen_OPQ_pass')
        freeze_raw = Path(opq_freeze).read_bytes()
        frozen = strict(freeze_raw)
        require(frozen.get('accepted_by_primary') is True
                and frozen.get('release_sha256') == release_hash
                and frozen.get('opq') == {c: gate['calls'][c] for c in CALLS[:3]}, 'OPQ_freeze_binding')
        marks = [e for e in ledger.entries if e['type'] == 'DISPATCH_MARK' and e['call'].endswith('FULL')]
        require(not marks or all(e.get('opq_freeze_sha256') == sha(freeze_raw) for e in marks),
                'OPQ_freeze_changed')


def dispatched(plan):
    body = copy.deepcopy(plan['body'])
    require(body['max_tokens'] == 8192, 'plan_output_cap_changed')
    body['max_tokens'] = 16384
    raw = encode(body)
    require(len(raw) + 1024 <= 40000, 'dispatched_body_overflow')
    require(sha(encode(plan['body'])) == plan['request_sha256'], 'plan_request_hash')
    return raw


def money(value):
    require(type(value) is int or isinstance(value, Number), 'money_not_numeric_token')
    return recon.parse_usd(str(value))


def recover_terms(value):
    """Recover billing from successful AND error envelopes, including nested usage."""
    usages = []
    def walk(item):
        if isinstance(item, dict):
            if isinstance(item.get('usage'), dict):
                usages.append(item['usage'])
            for child in item.values():
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)
    walk(value)
    costs, rates = [], []
    for usage in usages:
        try:
            costs.append(money(usage.get('cost')))
        except (ValueError, TypeError, ArithmeticError):
            pass
        p, c = usage.get('prompt_tokens'), usage.get('completion_tokens')
        if type(p) is int and p >= 0 and type(c) is int and c >= 0:
            rates.append((p * 2500 + c * 10000, p, c))
    rate, p, c = max(rates, default=(0, None, None))
    return dict(reported=max(costs) if costs else None, prompt_tokens=p, completion_tokens=c,
                rate=rate)


def raw_usage(raw):
    """Locate the root usage value with JSON decoding, preserving exact whitespace/tokens."""
    text = raw.decode('utf-8')
    decoder = json.JSONDecoder()
    pos = text.index('{') + 1
    while True:
        pos = re.match(r'\s*', text[pos:]).end() + pos
        if text[pos] == '}':
            return None
        key, pos = decoder.raw_decode(text, pos)
        pos = re.match(r'\s*:\s*', text[pos:]).end() + pos
        start = pos
        _, pos = decoder.raw_decode(text, pos)
        if key == 'usage':
            return text[start:pos].encode('utf-8')
        pos = re.match(r'\s*', text[pos:]).end() + pos
        if text[pos] == '}':
            return None
        require(text[pos] == ',', 'raw_usage_separator')
        pos += 1


def anomalies(value, guarded, release, ledger, expected):
    failures = []
    usage = value.get('usage')
    if not isinstance(usage, dict):
        usage = {}
    p, c = usage.get('prompt_tokens'), usage.get('completion_tokens')
    p_ok = type(p) is int and 1 <= p <= guarded
    c_ok = type(c) is int and 0 <= c <= 16384
    if not p_ok:
        failures.append('AD1')
    if not c_ok:
        failures.append('AD2')
    nested_ok = True
    for field in ('completion_tokens_details', 'prompt_tokens_details'):
        if field in usage and not isinstance(usage[field], dict):
            nested_ok = False
    cd, pd = usage.get('completion_tokens_details'), usage.get('prompt_tokens_details')
    cd = cd if isinstance(cd, dict) else {}
    pd = pd if isinstance(pd, dict) else {}
    r = cd.get('reasoning_tokens', usage.get('reasoning_tokens', 0))
    cached = pd.get('cached_tokens', usage.get('cached_tokens', 0))
    written = pd.get('cache_write_tokens', usage.get('cache_write_tokens', 0))
    # A present top-level alias must also be valid; conflicting aliases are unexpected.
    for key, detail, selected in (('reasoning_tokens', cd, r), ('cached_tokens', pd, cached),
                                   ('cache_write_tokens', pd, written)):
        if key in usage and key in detail and usage[key] != selected:
            nested_ok = False
    if not (nested_ok and type(r) is int and r >= 0 and c_ok and r <= c
            and all(type(v) is int and v >= 0 for v in (cached, written))
            and p_ok and cached + written <= p
            and ('total_tokens' not in usage or type(usage['total_tokens']) is int
                 and usage['total_tokens'] == p + c)):
        failures.append('AD3')
    try:
        cost = money(usage.get('cost'))
        require(p_ok and c_ok and cost <= p * 2500 + c * 10000 + 1000
                and cost <= 263840000, 'AD4')
    except (ValueError, TypeError, ArithmeticError):
        failures.append('AD4')
    if value.get('model') != release['model'] or value.get('provider') != release['provider']:
        failures.append('AD5')
    try:
        ledger.verify(expected)
    except (ValueError, TypeError, OSError):
        failures.append('AD7')
    return failures


def response_state(status, raw, release, ledger, expected, source, profile, plan, folder):
    value, parse_ok = {}, False
    try:
        require(len(raw) <= MAX_RAW, 'response_body_overflow')
        raw.decode('utf-8')  # JSON's UTF-16/32 autodetection is outside the wire contract.
        parsed = strict(raw)
        if isinstance(parsed, dict):
            value, parse_ok = parsed, True
    except (ValueError, UnicodeError, TypeError):
        pass
    terms = recover_terms(value)
    checks = anomalies(value, len(dispatched(plan)) + 1024, release, ledger, expected)
    try:
        usage_bytes = raw_usage(raw) if parse_ok else None
    except (ValueError, UnicodeError, IndexError, TypeError, AttributeError):
        usage_bytes, parse_ok = None, False
    if usage_bytes is not None:
        put(folder / 'usage.raw.json', usage_bytes)
    choice = None
    choices = value.get('choices')
    if isinstance(choices, list) and len(choices) == 1 and isinstance(choices[0], dict):
        choice = choices[0]
    message = choice.get('message') if choice else None
    message = message if isinstance(message, dict) else {}
    content = message.get('content')
    if isinstance(content, str):
        put(folder / 'content.body', content.encode('utf-8'))
    finish = choice.get('finish_reason') if choice else None
    native_finish = choice.get('native_finish_reason') if choice else None
    # Error bodies need not use OpenRouter's usual {error: ...} JSON envelope.
    # For an HTTP error, inspect the entire retained body, including plain text.
    error_text = ((json.dumps(value, ensure_ascii=False) if parse_ok else
                   raw.decode('utf-8', errors='replace')) if status is not None and status >= 400
                  else json.dumps(value.get('error', {}), ensure_ascii=False)).lower()
    validation, wire_error = None, None
    if status is None:
        state = 2
    elif status in (401, 403):
        state = 3
    elif status == 402 or re.search(r'(credit|key)[ _-]*limit', error_text):
        state = 4
    elif status == 429:
        state = 5
    elif status in (400, 422) and re.search(r'response_format|schema|parameter|unsupported keyword', error_text):
        state = 6
    elif status != 200:
        state = 7
    elif not parse_ok or len(raw) > MAX_RAW or choice is None:
        state = 8
    elif checks:
        state = 9
    elif (finish not in ('stop', 'length') or message.get('refusal') or message.get('tool_calls')
          or message.get('function_call') or choice.get('error') or not isinstance(content, str)
          or not content.strip()):
        state = 10
    elif finish == 'length':
        state = 11
    else:
        try:
            validation = wire.validate_response(content, finish, source, plan['table'], profile, plan=plan)
            state = 13
            put(folder / 'expanded.json', validation)
        except ValueError as exc:
            state, wire_error = 12, getattr(exc, 'code', 'ValueError')
    usage = value.get('usage') if isinstance(value.get('usage'), dict) else {}
    reported_token = usage.get('cost')
    return dict(state=state, checks=checks, wire_error=wire_error, validated=validation is not None,
                content_sha256=sha(content.encode('utf-8')) if isinstance(content, str) else None,
                usage_raw_sha256=sha(usage_bytes) if usage_bytes is not None else None,
                finish_reason=finish, native_finish_reason=native_finish, model=value.get('model'),
                provider=value.get('provider'), completion_tokens=terms['completion_tokens'],
                reported_cost_decimal=str(reported_token) if type(reported_token) is int
                or isinstance(reported_token, Number) else None, debit_basis=terms)


def key_read(key_info):
    """Callback drops identifying fields BEFORE returning. Only these fields cross the boundary."""
    packet = key_info(KEY_URL)
    require(set(packet) == {'fields', 'response_sha256'}, 'key_packet_fields')
    require(isinstance(packet['fields'], bytes)
            and re.fullmatch(r'[0-9a-f]{64}', packet['response_sha256']), 'key_packet_hash')
    fields = strict(packet['fields'])
    require(set(fields) == {'usage', 'limit', 'limit_remaining', 'limit_reset'}, 'key_permitted_fields')
    try:
        u = money(fields['usage'])
    except (ValueError, TypeError, ArithmeticError):
        u = None  # A returned but invalid usage is an immediate reference-engine halt.
    try:
        limit = None if fields['limit'] is None else money(fields['limit'])
    except (ValueError, TypeError, ArithmeticError):
        limit = None
    remaining = None if fields['limit_remaining'] is None else money(fields['limit_remaining'])
    if limit is not None and u is not None:
        require(remaining is not None and abs(remaining - (limit - u)) <= 1000, 'key_remaining_mismatch')
    return dict(usage=u, limit=limit, limit_reset=fields['limit_reset']), dict(
        permitted_fields=fields, response_sha256=packet['response_sha256'],
        permitted_fields_sha256=sha(packet['fields']))


def reported_sum(entries, current=None):
    amounts = [e.get('reported') for e in entries if e['type'] == 'RESOLVE' and e['dispatched']]
    if current is not None:
        amounts.append(current.get('reported'))
    return None if any(a is None for a in amounts) else sum(amounts)


def poll(ledger, cell, folder, key_info, clock, resolved_at, terms, already_resolved=False):
    entries = ledger.entries
    i = sum(e['type'] == 'DISPATCH_MARK' for e in entries)
    # A torn dispatch mark still counts as a possibly-dispatched attempt.
    if not any(e['type'] == 'DISPATCH_MARK' and e['call'] == cell for e in entries):
        i += 1
    cumulative = reported_sum(entries, None if already_resolved else terms)
    previous = last_usage([e for e in entries if e['type'] != 'RECONCILED' or e['call'] != cell])
    reads, highest = [], previous
    pinned = dict(limit=entries[0]['key_limit'], limit_reset=entries[0]['key_limit_reset'])
    verdict = ('HALT', 'KEY_USAGE_UNRECONCILED')
    for due in recon.READ_SCHEDULE_S:
        path = folder / f'recon-{due}.json'
        read_claim = folder / f'recon-{due}.intent.json'
        if path.exists():
            def valid(v):
                p = v.get('parsed')
                return (type(v.get('elapsed_s')) is int and v['elapsed_s'] >= due
                        and 'parsed' in v and (p is None or isinstance(p, dict)
                        and set(p) == {'usage', 'limit', 'limit_reset'}
                        and all(p[k] is None or type(p[k]) is int and p[k] >= 0
                                for k in ('usage', 'limit'))))
            saved = receipt(path, repair=True, valid=valid)
            if saved is None:
                elapsed, parsed = due, None
                put(path, dict(elapsed_s=elapsed, scheduled_s=due, parsed=None,
                               read_failed=True, recovered_read_uncertain=True))
            else:
                elapsed, parsed = saved['elapsed_s'], saved['parsed']
        elif read_claim.exists():
            # The GET might already have happened. Consume this slot as a failed read;
            # a restart must not silently add a fifth read to the bounded schedule.
            saved = receipt(read_claim, repair=True, valid=lambda v:
                            type(v.get('elapsed_s')) is int and v['elapsed_s'] >= due)
            elapsed, parsed = saved.get('elapsed_s', due) if saved else due, None
            put(path, dict(elapsed_s=elapsed, scheduled_s=due, parsed=None,
                           read_failed=True, recovered_read_uncertain=True))
        else:
            clock.wait_until(resolved_at + due)
            require(clock.now() >= resolved_at + due, 'clock_returned_early')
            elapsed = max(due, int(clock.now() - resolved_at))
            put(read_claim, dict(elapsed_s=elapsed, scheduled_s=due))
            try:
                parsed, meta = key_read(key_info)
            except Exception:
                parsed, meta = None, dict(read_failed=True)
            saved = dict(elapsed_s=elapsed, scheduled_s=due, parsed=parsed, **meta)
            put(path, saved)
        reads.append((elapsed, parsed))
        if parsed is not None and type(parsed['usage']) is int:
            highest = max(highest, parsed['usage'])
        verdict = recon.reconcile(i, cumulative, previous, pinned, reads)
        if verdict[0] == 'RECONCILED' or verdict[1] != 'KEY_USAGE_UNRECONCILED':
            break
    put_name = folder / 'reconciliation.json'
    if not put_name.exists():
        put(put_name, dict(verdict=list(verdict), reads=len(reads), cumulative_reported=cumulative,
                           highest_usage=highest, previous_usage=previous))
    return verdict, highest, max(0, highest - previous)


def close(ledger, highest):
    upward = recon.close_debit(ledger.entries, highest)
    if upward:
        ledger.append('RECONCILE_UP', debit=upward, highest_usage=highest)
    return recon.aggregate(ledger.entries)


def completion(folder, result):
    put(folder / 'result.json', {**result, **FLAGS})
    pins = {p.name: sha(p.read_bytes()) for p in sorted(folder.iterdir()) if p.is_file()}
    put(folder / ('completed.json' if result['state'] == 13 and not result['halt']
                  else 'stop.json'), dict(files=pins, state=result['state'], halt=result['halt'], **FLAGS))


def execute_once(*, cell, source, release_path, run_root, attempt_dir, job_id,
                 post, key_info, clock=None, artifact_root=BENCH, staged_path=None,
                 opq_freeze=None, hook=None):
    """post(url, exact_bytes) -> {status, raw, headers}; invoked at most ONCE.

    key_info(url) -> {fields: sanitized exact JSON bytes, response_sha256: original hash}.
    No callback receives a credential from this module. Clock and hook are offline test seams.
    """
    clock = clock or Clock()
    ledger = Ledger(run_root, clock)
    folder = Path(attempt_dir).resolve()
    root = Path(run_root).resolve()
    require(folder.parent == root and re.fullmatch(r'[A-Za-z0-9_-]{1,100}', job_id), 'claim_path_or_id')
    require(not folder.exists(), 'existing_run_dir')
    with ledger.lock(job_id):
        ledger.load()
        require(not recovery_calls(ledger), 'recovery_required')
        release, release_hash, reference_hash, _ = release_gate(
            ledger, release_path, cell, source, artifact_root)
        staged_gate(ledger, cell, release_hash, reference_hash, staged_path, opq_freeze)
        gate_hash = sha(Path(staged_path).read_bytes()) if staged_path else None
        require(not any(e.get('job_id') == job_id for e in ledger.entries), 'claim_id_reused')
        ok, reason = recon.admit(ledger.entries, cell, last_usage(ledger.entries))
        require(ok, 'admission:' + str(reason))
        claim(folder)
        reserved, marked = False, False
        expected = recon.aggregate(ledger.entries)
        try:
            pre, meta = key_read(key_info)
            require(pre['limit'] == ledger.entries[0]['key_limit'] and pre['limit_reset'] is None
                    and type(pre['usage']) is int,
                    'pre_key_limit')
            previous = last_usage(ledger.entries)
            count = sum(e['type'] == 'DISPATCH_MARK' for e in ledger.entries)
            cumulative = reported_sum(ledger.entries)
            require(cumulative is not None and pre['usage'] >= previous
                    and abs(pre['usage'] - cumulative) <= count * 1000, 'pre_key_usage')
            put(folder / 'key-preflight.json', dict(parsed=pre, **meta))
            ledger.append('RESERVE', call=cell, job_id=job_id, attempt_dir=folder.name,
                          floor=recon.FLOOR, staged_gate_sha256=gate_hash)
            reserved = True
            expected += recon.FLOOR
            if hook:
                hook('after_reserve', ledger, folder)
            profile = 'opaque' if cell.endswith('OPQ') else 'full'
            plan = wire.build(source, profile)
            original = copy.deepcopy(plan)
            raw_body = dispatched(plan)
            call_pin = release['calls'][cell]
            require(call_pin == dict(plan_request_sha256=plan['request_sha256'],
                                    dispatched_body_sha256=sha(raw_body)), 'release_body_hashes')
            put(folder / 'plan.json', plan)
            put(folder / 'request.json', raw_body)
            put(folder / 'span-table.json', plan['table'])
            opq_hash = sha(Path(opq_freeze).read_bytes()) if opq_freeze else None
            intent = dict(call=cell, job_id=job_id, release_sha256=release_hash,
                          reference_ready_sha256=reference_hash,
                          plan_request_sha256=plan['request_sha256'], dispatched_body_sha256=sha(raw_body),
                          source_sha256=sha(source.encode('utf-8')), guarded_bytes=len(raw_body) + 1024,
                          reserve=recon.FLOOR, opq_freeze_sha256=opq_hash, **FLAGS)
            put(folder / 'intent.json', intent)
            if hook:
                hook('before_mark', ledger, folder)
            # Re-read immutable exact bytes and rebuild originating plan.
            ledger.verify(expected)
            require(plan == original == wire.build(source, profile), 'plan_changed')
            require(read(folder / 'intent.json') == intent and
                    sha(Path(release_path).read_bytes()) == release_hash, 'intent_changed')
            # Reverify all release and adjudication pins after receipt creation.
            release_gate(ledger, release_path, cell, source, artifact_root)
            require((sha(Path(staged_path).read_bytes()) if staged_path else None) == gate_hash,
                    'staged_gate_changed')
            staged_gate(ledger, cell, release_hash, reference_hash, staged_path, opq_freeze)
            # Final guard uses the immutable byte object handed to the transport.
            actual = (folder / 'request.json').read_bytes()
            require(actual == dispatched(plan) and sha(actual) == intent['dispatched_body_sha256']
                    and len(actual) + 1024 <= 40000, 'immediate_transport_guard')
            require((sha(Path(staged_path).read_bytes()) if staged_path else None) == gate_hash
                    and (sha(Path(opq_freeze).read_bytes()) if opq_freeze else None) == opq_hash,
                    'staged_gate_changed')
            ledger.assert_tail()
            marked = True  # An append/fsync failure is possibly marked until recovery proves otherwise.
            ledger.append('DISPATCH_MARK', call=cell, job_id=job_id, attempt_dir=folder.name,
                          opq_freeze_sha256=opq_hash)
            # Exactly one call site; no redirects/retries may be implemented by the callback.
            try:
                response = post(POST_URL, actual)
                require(set(response) == {'status', 'raw', 'headers'}, 'transport_packet')
                status, raw, headers = response['status'], response['raw'], response['headers']
                require(type(status) is int and isinstance(raw, bytes) and isinstance(headers, dict),
                        'transport_packet_types')
                headers = filter_headers(headers)
            except Exception:
                status, raw, headers = None, b'', {}
            resolved_at = clock.now()
            put(folder / 'response.body', raw)
            put(folder / 'status.json', dict(http_status=status, response_sha256=sha(raw),
                                           headers=headers, resolved_at=str(resolved_at)))
            result = response_state(status, raw, release, ledger, expected, source, profile, plan, folder)
            try:
                require((folder / 'response.body').read_bytes() == raw
                        and read(folder / 'status.json')['response_sha256'] == sha(raw)
                        and read(folder / 'status.json')['http_status'] == status
                        and (folder / 'request.json').read_bytes() == actual
                        and read(folder / 'plan.json') == plan
                        and read(folder / 'span-table.json') == plan['table'], 'post_receipt_integrity')
                if result['content_sha256'] is not None:
                    require(sha((folder / 'content.body').read_bytes()) == result['content_sha256'],
                            'post_content_integrity')
                if result['state'] == 13:
                    expanded = wire.validate_response((folder / 'content.body').read_text('utf-8'),
                        result['finish_reason'], source, plan['table'], profile, plan=plan)
                    require(encode(expanded) == (folder / 'expanded.json').read_bytes(), 'post_inverse_integrity')
                release_gate(ledger, release_path, cell, source, artifact_root)
            except Exception:
                result['checks'].append('POST_INTEGRITY')
                if result['state'] >= 9:
                    result['state'] = 9
            put(folder / 'post-checks.json', result)
            verdict, highest, delta = poll(ledger, cell, folder, key_info, clock, resolved_at,
                                          result['debit_basis'])
            basis = result['debit_basis']
            debit = recon.debit(basis['reported'], basis['prompt_tokens'], basis['completion_tokens'], delta)
            halt = ('response_state_' + str(result['state'])) if result['state'] <= 9 else None
            if verdict[0] == 'HALT':
                halt = str(verdict[1])
            if debit > recon.FLOOR:
                halt = 'debit_exceeds_floor'
            ledger.append('RESOLVE', call=cell, dispatched=True, debit=debit,
                          reported=basis['reported'], attempt_dir=folder.name)
            if hook:
                hook('after_resolve', ledger, folder)
            if verdict[0] == 'RECONCILED':
                ledger.append('RECONCILED', call=cell, U=verdict[1])
            if hook:
                hook('after_reconciled', ledger, folder)
            if halt:
                ledger.append('HALT', call=cell, reason=halt)
            elif result['state'] in (10, 11, 12) or result['completion_tokens'] > 13926:
                for skipped in ledger.entries[0]['required_calls']:
                    if skipped not in done_calls(ledger.entries):
                        ledger.append('SKIP', call=skipped, reason='not run, pre-registered futility',
                                      rule_id='D1' if result['state'] != 13 else 'D5')
            elif cell.endswith('FULL'):
                tokens = {}
                for entry in ledger.entries:
                    if entry['type'] == 'RESOLVE' and entry['dispatched']:
                        if entry['call'] == cell:
                            tokens[cell] = result['completion_tokens']
                        else:
                            tokens[entry['call']] = read(root / entry['attempt_dir'] / 'result.json')['completion_tokens']
                if 2 * sum(v for c, v in tokens.items() if c.endswith('FULL')) > 3 * sum(
                        v for c, v in tokens.items() if c.endswith('OPQ')):
                    for skipped in ledger.entries[0]['required_calls']:
                        if skipped not in done_calls(ledger.entries):
                            ledger.append('SKIP', call=skipped, reason='not run, pre-registered futility', rule_id='T6')
            close_up = recon.close_debit(ledger.entries, highest)
            aggregate = close(ledger, highest)
            ledger.verify(expected - recon.FLOOR + debit + close_up)
            result.update(halt=halt, debit=debit, key_usage_delta=delta,
                          aggregate=aggregate, response_sha256=sha(raw), **intent)
            put(folder / 'ledger-snapshot.json', ledger.entries)
            completion(folder, result)
            return result
        except Exception:
            if not marked:
                if reserved:
                    try:
                        ledger.append('RESOLVE', call=cell, dispatched=False, debit=0,
                                      reported=None, attempt_dir=folder.name)
                    except (ValueError, TypeError, OSError):
                        raise Refused('recovery_required') from None
                completion(folder, dict(call=cell, state=1, halt=None, debit=0))
            else:
                # This sentinel also covers a crash after RESOLVE/RECONCILED but before
                # final receipts. Never allow a later cell to cross this failure boundary.
                fault = folder / 'unexpected-halt.json'
                if not fault.exists():
                    put(fault, dict(call=cell, reason='unexpected_post_dispatch_failure', **FLAGS))
                try:
                    ledger.verify()
                    ledger.append('HALT', call=cell, reason='unexpected_post_dispatch_failure')
                except (ValueError, TypeError, OSError):
                    pass  # Do not append to a corrupt chain; preserve the sidecar instead.
            # Post-mark unexpected failures keep the lock-free unresolved reservation.
            # The next dispatch is refused; explicit recover() reconciles, debits and HALTs.
            raise Refused('pre_dispatch_pause' if not marked else 'recovery_required') from None


def recover(*, run_root, key_info, clock=None, lock_evidence=None):
    """Accounting-only recovery. NEVER calls post, and NEVER reuses an attempt directory."""
    clock = clock or Clock()
    ledger = Ledger(run_root, clock)
    with ledger.lock('recovery'):
        # LOCK_RECOVERED must be the next appended entry after a human removes the lock.
        evidence_hash = None
        if lock_evidence:
            require(read(lock_evidence).get('owner_gone') is True, 'lock_recovery_evidence')
            evidence_hash = sha(Path(lock_evidence).read_bytes())
        torn = ledger.load(repair_tail=True, lock_evidence_sha256=evidence_hash)
        recovered = []
        for cell in sorted(recovery_calls(ledger)):
            reservation = next(e for e in reversed(ledger.entries) if e['type'] == 'RESERVE' and e['call'] == cell)
            folder = ledger.root / reservation['attempt_dir']
            marked = torn or any(e['type'] == 'DISPATCH_MARK' and e['call'] == cell for e in ledger.entries)
            if not marked:
                ledger.append('RESOLVE', call=cell, dispatched=False, debit=0, reported=None,
                              attempt_dir=folder.name)
                put(folder / 'recovered.json', dict(call=cell, dispatched=False, debit=0, **FLAGS))
                recovered.append(cell)
                continue
            raw = (folder / 'response.body').read_bytes() if (folder / 'response.body').exists() else b''
            try:
                require(len(raw) <= MAX_RAW, 'response_body_overflow')
                value = strict(raw)
            except (ValueError, UnicodeError):
                value = {}
            terms = recover_terms(value)
            resolved = next((e for e in reversed(ledger.entries) if e['type'] == 'RESOLVE'
                             and e['call'] == cell and e['dispatched']), None)
            status = receipt(folder / 'status.json', repair=True, valid=lambda v:
                             isinstance(v.get('resolved_at'), str)
                             and re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', v['resolved_at']) is not None) or {}
            verdict, highest, delta = poll(ledger, cell, folder, key_info, clock,
                float(status.get('resolved_at', clock.now())), terms, already_resolved=resolved is not None)
            debit = recon.debit(terms['reported'], terms['prompt_tokens'], terms['completion_tokens'], delta)
            if not resolved:
                ledger.append('RESOLVE', call=cell, dispatched=True, debit=debit,
                              reported=terms['reported'], attempt_dir=folder.name)
            elif debit > resolved['debit']:
                ledger.append('RECONCILE_UP', debit=debit - resolved['debit'], call=cell)
            if verdict[0] == 'RECONCILED' and not any(e['type'] == 'RECONCILED' and e['call'] == cell
                                                    for e in ledger.entries):
                ledger.append('RECONCILED', call=cell, U=verdict[1])
            if not any(e['type'] == 'HALT' and e.get('call') == cell for e in ledger.entries):
                ledger.append('HALT', call=cell, reason='recovered_possibly_dispatched')
            close(ledger, highest)
            if final_receipt(folder, 'recovered.json', cell, repair=True) is None:
                put(folder / 'recovered.json', dict(call=cell, dispatched=True, debit=debit,
                                                   reconciliation=list(verdict), **FLAGS))
            recovered.append(cell)
        return recovered


def _main(argv=None, recover_first=False):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--cell', choices=CALLS, required=True)
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--run-root', type=Path, required=True)
    parser.add_argument('--attempt-dir', type=Path, required=True)
    parser.add_argument('--job-id', required=True)
    parser.add_argument('--driver', type=Path, required=True)
    parser.add_argument('--driver-sha256', required=True)
    parser.add_argument('--staged-gate', type=Path)
    parser.add_argument('--opq-freeze', type=Path)
    args = parser.parse_args(argv)
    require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, 'python_flags')
    # No built-in networking or credential lookup. P7 must pin/review the host driver.
    release = read(args.release)
    require(release.get('release_policy') in recon.RELEASE_POLICIES, 'release_policy_unset')
    require(release.get('driver_sha256') == args.driver_sha256, 'driver_release_pin')
    driver_path, driver_raw = artifact(BENCH, release, 'host_driver')
    require(driver_path == args.driver.resolve() and sha(driver_raw) == args.driver_sha256,
            'driver_artifact_pin')
    driver = load_pinned('r17_host_driver', args.driver, args.driver_sha256)
    require(all(callable(getattr(driver, n, None)) for n in ('source', 'post_once', 'key_info')),
            'driver_exports')
    # The probe owns the same exclusive lock discipline. execute_once re-checks all
    # state under its own lock after recovery, so a competing invocation cannot bypass it.
    probe = Ledger(args.run_root)
    with probe.lock('recovery-check'):
        try:
            probe.load()
            needed = bool(recovery_calls(probe))
        except Refused as exc:
            if str(exc) != 'ledger_corrupt':
                raise
            needed = True  # recover alone may repair a torn last line.
    if needed:
        require(recover_first, 'recovery_required')
        recover(run_root=args.run_root, key_info=driver.key_info)
    # A recovered marked cell is terminal: refuse before reading any source.
    with probe.lock('admission-check'):
        probe.load()
        require(not recovery_calls(probe), 'recovery_required')
        ok, reason = recon.admit(probe.entries, args.cell, last_usage(probe.entries))
        require(ok, 'admission:' + str(reason))
    result = execute_once(cell=args.cell, source=driver.source(args.cell), release_path=args.release,
        run_root=args.run_root, attempt_dir=args.attempt_dir, job_id=args.job_id,
        post=driver.post_once, key_info=driver.key_info, staged_path=args.staged_gate,
        opq_freeze=args.opq_freeze)
    print(encode(dict(call=result['call'], state=result['state'], halt=result['halt'],
                      debit=result['debit'])).decode())
    return 0 if result['state'] == 13 and not result['halt'] else 1


def main(argv=None, recover_first=False):
    try:
        return _main(argv, recover_first)
    except FileExistsError:
        print('R17 lock/claim exists; no lock was broken. No retry.', file=sys.stderr)
        return 3
    except Refused as exc:
        # Never print arbitrary exception text or untrusted artifact names.
        safe = {'python_flags', 'release_policy_unset', 'driver_release_pin',
                'driver_artifact_pin', 'driver_exports', 'existing_run_dir',
                'claim_path_or_id', 'pre_dispatch_pause', 'recovery_required',
                'wrong_cell_order', 'semantic_futility_stop', 'adjudication_pause'}
        code = str(exc) if str(exc) in safe else 'gate_refused'
        print('R17 refusal: ' + code + '. No retry.', file=sys.stderr)
        return 2
    except Exception:
        print('R17 stopped: internal_failure; inspect nonsecret receipts. No retry.', file=sys.stderr)
        return 4


if __name__ == '__main__':
    sys.exit(main())
