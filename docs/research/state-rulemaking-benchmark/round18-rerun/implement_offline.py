"""One-time offline copy/amendment utility; writes only beneath this R18 directory."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
R17 = BENCH / 'round17-paid-comparison'
SENTENCE = ('If a unit has several conditions of the same role (if, onlyif, unless or obj), '
    'emit a single link of that role to one L leaf whose fragments cover each condition in '
    'source order (up to 8). Never emit two links of the same role on one unit.')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def frozen():
    return {p.relative_to(BENCH).as_posix(): sha(p)
        for root in (BENCH/'round16-wire-compat', R17)
        for p in sorted(root.rglob('*')) if p.is_file()}

def edit(rel, pairs):
    p = HERE/rel
    text = p.read_text()
    for old, new in pairs:
        assert old in text, (rel, old)
        text = text.replace(old, new)
    p.write_text(text)

def main():
    out = HERE/'_out'
    out.mkdir(exist_ok=True)
    (out/'frozen-before.json').write_text(json.dumps(frozen(), sort_keys=True, indent=2)+'\n')
    for src, dst in ((BENCH/'round16-wire-compat/protocol-w2-1', 'wire'),
                     (R17/'adapter-r1-4', 'adapter'), (R17/'recon-a4', 'recon'),
                     (R17/'keycheck-job-v2', 'keycheck'), (R17/'release-prep-a4-r2', 'release-prep')):
        shutil.copytree(src, HERE/dst, ignore=shutil.ignore_patterns(
            '__pycache__', 'evidence-*', 'proposals-*', 'primary-review*', 'LIVE-VARS.txt'))
        # Keep the adapter's copied, byte-identical review repros; discard prior logs.
        history = HERE/dst/'_out'
        if history.exists():
            for p in history.iterdir():
                if p.name != 'round2-repros':
                    shutil.rmtree(p) if p.is_dir() else p.unlink()
        else:
            history.mkdir()
    edit('wire/wire.py', [
        ('Offline r16.w2.1 revision: unchanged r16.w1 response, r16.e2 request envelope.',
         'Offline r16.w2.2 revision: unchanged r16.w1 response, r16.e3 request envelope.'),
        ("REVISION = 'r16.w2.1'", "REVISION = 'r16.w2.2'"),
        ("ENVELOPE_VERSION = 'r16.e2'", "ENVELOPE_VERSION = 'r16.e3'"),
        ('    return prompt\n', '    prompt += '+repr(SENTENCE+'\n')+'\n    return prompt\n')])
    edit('wire/test_wire.py', [
        ("ROOT.parent / 'protocol/wire.py'", "BENCH / 'round16-wire-compat/protocol/wire.py'"),
        ("ROOT.parent / 'design", "BENCH / 'round16-wire-compat/design"),
        ('self.assertEqual(after, before.replace(old, new))',
         'self.assertEqual(after, before.replace(old, new) + '+repr(SENTENCE+'\n')+')'),
        ('self.assertEqual(len(common.encode(after)) - len(common.encode(before)), 82)',
         'self.assertEqual(len(common.encode(after)) - len(common.encode(before)), 82 + len('+repr(SENTENCE)+') + 2)')])
    # verify.inputs remains scoped to frozen R16, including in its synthetic scope test.
    edit('wire/verify.py', [("ROOT.parent / name", "tests.BENCH / 'round16-wire-compat' / name")])
    edit('recon/r17recon.py', [
        ('def key_limit_ok(limit, required_calls):', 'def key_limit_ok(limit, required_calls, initial_usage=0):'),
        ('return type(limit) is int and required_calls * FLOOR <= limit <= KEY_MAX',
         'return (type(limit) is int and type(initial_usage) is int and initial_usage >= 0\n'
         '            and required_calls * FLOOR <= limit - initial_usage and limit <= KEY_MAX)'),
        ('prev_usage: last reconciled usage (0 at INIT).', 'prev_usage: last reconciled usage (U0 at INIT).'),
        ("    tol, floor = i * TOL_PER_CALL, prev_usage", "    baseline = pinned.get('key_initial_usage', 0)\n    tol, floor = i * TOL_PER_CALL, prev_usage"),
        ('if u > cumulative_reported + tol:', 'if u > baseline + cumulative_reported + tol:'),
        ('if abs(u - cumulative_reported) <= tol:', 'if abs(u - (baseline + cumulative_reported)) <= tol:'),
        ('highest key usage since zero', 'highest key usage above INIT baseline U0'),
        ('return max(0, highest_usage - total)', "return max(0, highest_usage - entries[0].get('key_initial_usage', 0) - total)")])
    edit('adapter/r17_adapter.py', [
        ('R17 = HERE.parent\nBENCH = R17.parent\nDESIGN = R17',
         "R18 = HERE.parent\nBENCH = R18.parent\nR17 = BENCH / 'round17-paid-comparison'\nDESIGN = R17"),
        ("NAMESPACE = 'r17.paid-comparison.v1'", "NAMESPACE = 'r18.paid-rerun.v1'"),
        ("R17 / 'recon-a4/", "R18 / 'recon/"),
        ("BENCH / 'round16-wire-compat/protocol-w2-1/wire.py'", "R18 / 'wire/wire.py'"),
        ("== WIRE_SHA,\n            'source_wire_pin'", "== '662268ba0774d7ef5a121ec4af90003a3836c07e4ce5a5ae551a413fe8375ab1',\n            'source_wire_pin'"),
        ("    return (load_pinned('r17_exact_recon'", "    require(read(R18 / 'wire/READY.json')['sha256']['wire.py'] == WIRE_SHA, 'r18_wire_pin')\n    return (load_pinned('r17_exact_recon'"),
        ("'FLOOR': recon.FLOOR, 'KEY_MAX': recon.KEY_MAX, 'key_initial_usage': 0,", "'FLOOR': recon.FLOOR, 'KEY_MAX': recon.KEY_MAX,"),
        ("    calls = release.get('required_calls')", "    require(type(init.get('key_initial_usage')) is int and init['key_initial_usage'] >= 0,\n            'init_constants')\n    calls = release.get('required_calls')"),
        ("recon.key_limit_ok(init.get('key_limit'), len(calls))", "recon.key_limit_ok(init.get('key_limit'), len(calls), init['key_initial_usage'])"),
        ("machine.get('usage') == 0", "type(machine.get('usage')) is int and machine['usage'] == init['key_initial_usage']"),
        ("machine.get('limit_remaining') == init['key_limit']", "type(machine.get('limit_remaining')) is int\n            and machine['limit_remaining'] == init['key_limit'] - init['key_initial_usage']"),
        ("if e['type'] == 'RECONCILED'), 0)", "if e['type'] == 'RECONCILED'), entries[0]['key_initial_usage'])"),
        ("pinned = dict(limit=entries[0]['key_limit'], limit_reset=entries[0]['key_limit_reset'])",
         "pinned = dict(limit=entries[0]['key_limit'], limit_reset=entries[0]['key_limit_reset'],\n                  key_initial_usage=entries[0]['key_initial_usage'])"),
        ("abs(pre['usage'] - cumulative) <= count * 1000", "abs(pre['usage'] - (ledger.entries[0]['key_initial_usage'] + cumulative)) <= count * 1000"),
        ("RECON_SHA = '8c98fabdc73fad10336698fa695869966a631d5a7d99b797725f2c711b1b6bb0'", "RECON_SHA = '"+sha(HERE/'recon/r17recon.py')+"'"),
        ("WIRE_SHA = '662268ba0774d7ef5a121ec4af90003a3836c07e4ce5a5ae551a413fe8375ab1'", "WIRE_SHA = '"+sha(HERE/'wire/wire.py')+"'")])
    edit('adapter/native_entry.py', [("'adapter-r1-4/host_driver.py'", "'adapter/host_driver.py'")])
    edit('adapter/test_native.py', [("'adapter-r1-4/host_driver.py'", "'adapter/host_driver.py'")])
    edit('adapter/test_adapter.py', [("a.R17 / 'recon-a4/r17recon.py'", "a.R18 / 'recon/r17recon.py'")])
    edit('adapter/test_a4.py', [('def test_nonzero_initial_usage_refused', 'def test_negative_initial_usage_refused'),
                             ("self.refused_init('key_initial_usage', 1,", "self.refused_init('key_initial_usage', -1,")])
    edit('adapter/test_repros.py', [("REVIEW = HERE.parent / 'adapter-review'", "REVIEW = HERE.parent.parent / 'round17-paid-comparison/adapter-review'")])
    edit('adapter/test_round2.py', [("original = HERE.parent / 'adapter-review-r2'", "original = HERE.parent.parent / 'round17-paid-comparison/adapter-review-r2'")])
    edit('keycheck/keycheck.py', [
        ("'r17.keycheck-failure.v2'", "'r18.keycheck-failure.v3'"),
        ("'limit_remaining': decimal.Decimal('50.00'), 'limit_reset': None,\n            'usage': decimal.Decimal('0')", "'limit_remaining': None, 'limit_reset': None,\n            'usage': None"),
        ("checks['label'] = label_check", "checks['usage'] = fields['usage'] is not None and numeric(fields['usage'])\n    if fields['limit'] is not None and fields['usage'] is not None:\n        with decimal.localcontext() as ctx:\n            span = max(fields['limit'].adjusted(), fields['usage'].adjusted(), 0) - min(\n                fields['limit'].as_tuple().exponent, fields['usage'].as_tuple().exponent, 0) + 2\n            typed(span <= MAX_RAW, 'limit_remaining', None)\n            ctx.prec = max(28, span)\n            checks['limit_remaining'] = fields['limit_remaining'] == fields['limit'] - fields['usage']\n    else:\n        checks['limit_remaining'] = False\n    checks['label'] = label_check"),
        ("metadata = {'label_kind'", "metadata = {'key_initial_usage_candidate_usd': fields['usage'],\n        'label_kind'")])
    edit('keycheck/test_keycheck.py', [("'r17.keycheck-failure.v2'", "'r18.keycheck-failure.v3'")])
    for name in ('stage.py', 'make_proposals.py', 'release_records.py', 'test_release_prep.py', 'test_findings.py'):
        p = HERE/'release-prep'/name
        text = p.read_text().replace('adapter-r1-4', 'adapter')
        # Active run/stage namespace is R18; historical evidence paths handled separately.
        text = text.replace('round17-paid-comparison', 'round18-rerun')
        text = text.replace('recon-a4/', 'recon/')
        p.write_text(text)
    edit('release-prep/release_records.py', [
        ('def init_record(a, budget):', 'def init_record(a, budget, key_initial_usage):\n    a.require(type(key_initial_usage) is int and key_initial_usage >= 0, "key_initial_usage")'),
        ('key_initial_usage=0,', 'key_initial_usage=key_initial_usage,'),
        ("init.add_argument('--budget', type=Path, required=True)", "init.add_argument('--budget', type=Path, required=True)\n    init.add_argument('--key-initial-usage', type=int, required=True, help='machine-checked U0 in integer nanoUSD')"),
        ('init_record(a, args.budget.read_bytes())', 'init_record(a, args.budget.read_bytes(), args.key_initial_usage)')])
    edit('release-prep/make_proposals.py', [("'r17-s1-opq-'", "'r18-s1-opq-'"),
        ("job_id = 'r17-'", "job_id = 'r18-'"),
        ("default='r17-paid-comparison'", "default='docketclock-research-r18-authorized-20261014'"),
        (".r17-stage", ".r18-stage")])
    edit('release-prep/stage.py', [(".r17-stage", ".r18-stage")])
    # A4 evidence is reused verbatim. No new human or machine acceptance is fabricated.
    edit('release-prep/normalize_evidence.py', [("RUN = HERE.parent / 'run'", "RUN = HERE.parent.parent / 'round17-paid-comparison/run'")])
    edit('release-prep/test_findings.py', [('records.init_record(a, b\'synthetic budget\')', "records.init_record(a, b'synthetic budget', 59_408_500)")])
    for src, dst in ((BENCH/'round16-wire-compat/protocol-w2-1/wire.py', HERE/'wire/wire.py'),
                     (R17/'recon-a4/r17recon.py', HERE/'recon/r17recon.py')):
        (out/(dst.parent.name+'.diff')).write_text(''.join(difflib.unified_diff(
            src.read_text().splitlines(True), dst.read_text().splitlines(True),
            fromfile=src.relative_to(BENCH).as_posix(), tofile=dst.relative_to(BENCH).as_posix())))

if __name__ == '__main__':
    main()
