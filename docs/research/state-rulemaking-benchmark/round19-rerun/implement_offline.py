"""One-time offline R18 + A7 build; writes only beneath this R19 directory."""
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
R18 = BENCH / 'round18-rerun'
FOLDERS = ('wire', 'recon', 'adapter', 'keycheck', 'release-prep')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen():
    return {p.relative_to(BENCH).as_posix(): sha(p)
            for round_no in range(14, 19)
            for root in sorted(BENCH.glob('round' + str(round_no) + '-*'))
            for p in sorted(root.rglob('*')) if p.is_file()}


def sentence():
    lines = (HERE / 'amendments/A7.md').read_text().splitlines()
    quoted = [line[3:-1] for line in lines if line.startswith('> "') and line.endswith('"')]
    assert len(quoted) == 1, 'A7 must have exactly one normative quoted sentence'
    return quoted[0]


def write(rel, text):
    path = HERE / rel
    assert path.is_relative_to(HERE) and rel != 'amendments/A7.md'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def edit(rel, pairs):
    text = (HERE / rel).read_text()
    for old, new in pairs:
        assert old in text, (rel, old)
        text = text.replace(old, new)
    write(rel, text)


def retarget(text):
    return text.replace('round18-rerun', 'round19-rerun').replace('R18', 'R19').replace('r18', 'r19')


def update_docs():
    write('wire/SPEC.md', """# r16.w2.3 / r16.e4

Copy of R18 wire; only revision/envelope labels and the conditional A7 append
change in wire.py. A7 plus newline follows A5 only for opaque. Full prompt is
byte-identical to R18; schema/codec/validator/guards/dependency pins are fixed.
test_r18.py retains the A5 mechanical regression and tests the exact allowed
R18-to-R19 source transformation. test_a7.py checks all three frozen sources-r2
under both profiles, comparing every body field and reporting guarded sizes.
No output is scored. The independent suite retains its one historical expected
source-envelope assertion failure (54/55); no unexpected failure is permitted.
""")
    text = retarget((R18 / 'adapter/SPEC.md').read_text())
    text = text.replace('# Adapter r1.5', '# Adapter r1.6')
    text = text.replace('Copy of R17 adapter-r1-4. Namespace r19.paid-rerun.v1; new wire/recon pins.',
        'Copy of R18 adapter r1.5. Namespace r19.paid-rerun.v1; new wire pin.\nFrozen R18 recon path and pin are reused directly.')
    write('adapter/SPEC.md', text)
    write('recon/SPEC.md', """# A6 recon reused from frozen R18

No R19 recon executable copy. Adapter loads ../round18-rerun/recon/r17recon.py
by SHA256 64794fdda2f345559a5399ccd8e83142a93e621fcb5c6e79842209a4d4c27140.
Its original READY is pinned and staged alongside the engine. R19 tests differ
only in the engine path; the three original tests and all A6 behavior remain.
NOTE.md is the unchanged historical A4 note inherited by R18, not the A6 pin.
""")
    edit('release-prep/README.md', [('recon artifact to R19 recon', 'recon artifact to frozen R18 recon')])
    edit('release-prep/SPEC.md', [
        ('active stage/run/adapter/wire/recon point to R19.', 'active stage/run/adapter/wire point to R19.\nRecon points to the unchanged frozen R18 engine and READY.'),
        ('A5/A6 and DESIGN-NOTE are pinned.', 'A5/A6, A7 and DESIGN-NOTE are pinned.')])


def main():
    assert not any((HERE / f).exists() for f in FOLDERS), 'one-time build: refuse existing components'
    a7_before = sha(HERE / 'amendments/A7.md')
    write('_out/frozen-before.json', json.dumps(frozen(), sort_keys=True, indent=2) + '\n')
    # Copy the reviewed offline payload inventory, not live records or old logs.
    for folder in FOLDERS:
        ready = json.loads((R18 / folder / 'READY.json').read_bytes())
        for name in ready['files']:
            if name == 'STAGE-MANIFEST.json' or (folder == 'recon' and name == 'r17recon.py'):
                continue
            src, dst = R18 / folder / name, HERE / folder / name
            assert sha(src) == ready['files'][name]['sha256'], str(src)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
        (HERE / folder / '_out').mkdir(exist_ok=True)
    write('amendments/A5-A6.md', (R18 / 'amendments/A5-A6.md').read_text())

    edit('wire/wire.py', [
        ('r16.w2.2', 'r16.w2.3'), ('r16.e3', 'r16.e4'),
        ('    return prompt\n', "    if profile == 'opaque':\n        prompt += " + repr(sentence() + '\n') + '\n    return prompt\n')])
    a7_literal = repr(sentence() + '\n')
    old_assert = "self.assertEqual(after, before.replace(old, new) + "
    text = (HERE / 'wire/test_wire.py').read_text()
    lines = text.splitlines(True)
    for i, line in enumerate(lines):
        if old_assert in line:
            lines[i] = line.rstrip()[:-1] + " + (" + a7_literal + " if profile == 'opaque' else ''))\n"
        if '82 + len(' in line:
            lines[i] = line.rstrip()[:-1] + " + (len(common.encode(" + a7_literal + ")) - 2 if profile == 'opaque' else 0))\n"
    write('wire/test_wire.py', ''.join(lines))
    # Retain the A5 mechanical regression; compare the prompt delta to frozen R18.
    edit('wire/test_r18.py', [
        ('A5 prompt-only proof', 'A7 prompt-only proof'),
        ("w.BENCH/'round16-wire-compat/protocol-w2-1/wire.py'", "w.BENCH/'round18-rerun/wire/wire.py'"),
        ("original.replace('r16.w2.1', 'r16.w2.2').replace('r16.e2', 'r16.e3')", "original.replace('r16.w2.2', 'r16.w2.3').replace('r16.e3', 'r16.e4')"),
        ("'    prompt += '+repr(SENTENCE+'\\n')+'\\n    return prompt\\n'", repr("    if profile == 'opaque':\n        prompt += " + a7_literal + '\n    return prompt\n')),
        ("before['body']['messages'][0]['content'] + SENTENCE+'\\n'", "before['body']['messages'][0]['content'] + (" + a7_literal + " if profile == 'opaque' else '')")])

    edit('adapter/r17_adapter.py', [
        ('R18 = HERE.parent\nBENCH = R18.parent', "R19 = HERE.parent\nBENCH = R19.parent\nR18 = BENCH / 'round18-rerun'"),
        ("R18 / 'wire/", "R19 / 'wire/"),
        ("'r18_wire_pin'", "'r19_wire_pin'"),
        ("NAMESPACE = 'r18.paid-rerun.v1'", "NAMESPACE = 'r19.paid-rerun.v1'"),
        ("WIRE_SHA = '" + sha(R18 / 'wire/wire.py') + "'", "WIRE_SHA = '" + sha(HERE / 'wire/wire.py') + "'")])
    # R18 recon code and READY stay at their frozen path with their exact old pins.
    edit('recon/test_recon.py', [("HERE / 'r17recon.py'", "HERE.parent.parent / 'round18-rerun/recon/r17recon.py'")])
    for rel in ('adapter/pin_ready.py', 'adapter/verify_ready.py', 'adapter/run_tests.sh',
                'release-prep/pin_ready.py', 'keycheck/README.md'):
        write(rel, retarget((HERE / rel).read_text()))
    # Keep keycheck.py and its failure grammar byte-identical; only job/stage IDs move.
    edit('keycheck/make_keycheck_proposal.py', [('r18-keycheck-v3-', 'r19-keycheck-v3-'),
                                              ('r18.keycheck-stage.v3', 'r19.keycheck-stage.v3')])
    for name in ('stage.py', 'prepare_manifest.py', 'make_proposals.py', 'release_records.py',
                 'test_release_prep.py', 'test_findings.py', 'test_a6.py', 'README.md', 'SPEC.md'):
        rel = 'release-prep/' + name
        write(rel, retarget((HERE / rel).read_text()))
    edit('release-prep/prepare_manifest.py', [("('amendments/A5-A6.md', 'DESIGN-NOTE.md'", "('amendments/A5-A6.md', 'amendments/A7.md', 'DESIGN-NOTE.md'")])
    edit('release-prep/test_a6.py', [
        ("self.assertIn('round19-rerun/recon/r17recon.py',manifest)", "self.assertIn('round18-rerun/recon/r17recon.py',manifest)\n        self.assertIn('round19-rerun/amendments/A7.md',manifest)")])
    edit('release-prep/test_release_prep.py', [
        ("for name in ('recon/r17recon.py', 'recon/READY.json',", "for name in ('recon/READY.json',"),
        ("self.assertIn('round17-paid-comparison/design-r3-1/fixtures/r17recon.py', manifest['files'])", "self.assertIn('round17-paid-comparison/design-r3-1/fixtures/r17recon.py', manifest['files'])\n        for name in ('r17recon.py', 'READY.json'):\n            rel = 'round18-rerun/recon/' + name\n            self.assertEqual(manifest['files'][rel], st.digest(st.read_regular(st.BENCH / rel)))")])

    write('offline_tests.py', retarget((R18 / 'offline_tests.py').read_text()))
    pins = retarget((R18 / 'pin_ready.py').read_text())
    pins = pins.replace("wire='r16.w2.2'", "wire='r16.w2.3'").replace("adapter='r1.5'", "adapter='r1.6'")
    pins = pins.replace("envelope_version='r16.e3'", "envelope_version='r16.e4'")
    pins = pins.replace("for root in (BENCH/'round16-wire-compat', BENCH/'round17-paid-comparison')", "for round_no in range(14,19)\n        for root in sorted(BENCH.glob('round'+str(round_no)+'-*'))")
    pins = pins.replace('frozen R16/R17 bytes', 'frozen R14–R18 bytes').replace('frozen_R16_R17_unchanged', 'frozen_R14_R18_unchanged')
    pins = pins.replace("'round19-rerun/recon/r17recon.py','round19-rerun/recon/READY.json'", "'round18-rerun/recon/r17recon.py','round18-rerun/recon/READY.json'")
    pins = pins.replace("    if folder == 'adapter':", "    if folder == 'recon':\n        names += ['round18-rerun/recon/r17recon.py','round18-rerun/recon/READY.json']\n    if folder == 'adapter':", 1)
    pins = pins.replace("['round19-rerun/amendments/A5-A6.md', 'round19-rerun/DESIGN-NOTE.md']", "['round19-rerun/amendments/A5-A6.md', 'round19-rerun/amendments/A7.md', 'round19-rerun/DESIGN-NOTE.md']")
    pins = pins.replace("roots.update({'amendments/A5-A6.md':pin(HERE/'amendments/A5-A6.md')})", "roots.update({n:pin(HERE/n) for n in ('amendments/A5-A6.md','amendments/A7.md','review/REVIEW.md')})")
    write('pin_ready.py', pins)
    update_docs()
    assert sha(HERE / 'amendments/A7.md') == a7_before, 'A7 changed'
    assert frozen() == json.loads((HERE / '_out/frozen-before.json').read_bytes()), 'frozen input drift'
    print('R18 payload copied; A7 applied; frozen R14–R18 inventory unchanged.')


def diff_reports():
    summaries = {}
    for folder in FOLDERS:
        src, dst = R18 / folder, HERE / folder
        names = set(json.loads((src / 'READY.json').read_bytes())['files'])
        names |= {p.relative_to(dst).as_posix() for p in dst.rglob('*') if p.is_file()
                  and p.name != 'READY.json' and '_out' not in p.relative_to(dst).parts}
        combined = []
        for name in sorted(names):
            if name == 'STAGE-MANIFEST.json':
                continue  # Derived pin closure gets its own diff after final pinning.
            before = (src / name).read_text() if (src / name).exists() else ''
            after = (dst / name).read_text() if (dst / name).exists() else ''
            if before == after:
                continue
            if folder == 'recon' and name == 'r17recon.py':
                summaries[folder + '/' + name] = dict(action='referenced, not copied',
                    path='round18-rerun/recon/r17recon.py', sha256=sha(src / name), hunks=[])
                continue
            diff = list(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                fromfile=(src / name).relative_to(BENCH).as_posix(),
                tofile=(dst / name).relative_to(BENCH).as_posix()))
            combined.extend(diff)
            summaries[folder + '/' + name] = dict(
                added=sum(x.startswith('+') and not x.startswith('+++') for x in diff),
                removed=sum(x.startswith('-') and not x.startswith('---') for x in diff),
                hunks=[x.rstrip() for x in diff if x.startswith('@@')],
                changes=[x.rstrip() for x in diff if x[:1] in ('+','-') and not x.startswith(('+++','---'))])
        write('_out/' + folder + '.diff', ''.join(combined))
    before = (R18 / 'release-prep/STAGE-MANIFEST.json').read_text()
    after = (HERE / 'release-prep/STAGE-MANIFEST.json').read_text()
    diff = list(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
        fromfile='round18-rerun/release-prep/STAGE-MANIFEST.json', tofile='round19-rerun/release-prep/STAGE-MANIFEST.json'))
    write('_out/stage-manifest.diff', ''.join(diff))
    summaries['release-prep/STAGE-MANIFEST.json'] = dict(
        reason='Derived hash closure: R19 paths/payload pins/A7; R18 recon pins reused; frozen R17 evidence unchanged.',
        hunks=[x.rstrip() for x in diff if x.startswith('@@')])
    for group, names in (
        ('root', ('SPEC.md', 'DESIGN-NOTE.md', 'implement_offline.py', 'offline_tests.py', 'pin_ready.py', 'FILES-WRITTEN.txt')),
        ('ready', tuple(folder + '/READY.json' for folder in FOLDERS))):
        combined = []
        for name in names:
            before = (R18 / name).read_text()
            after = (HERE / name).read_text()
            diff = list(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                fromfile='round18-rerun/' + name, tofile='round19-rerun/' + name))
            combined.extend(diff)
            summaries[name] = dict(reason=('Derived payload/dependency/test pins and R19 revision/namespace metadata.'
                if group == 'ready' else 'Offline build/verification/documentation/inventory retargeted to R19 + A7; frozen inputs expanded to R14–R18.'),
                added=sum(x.startswith('+') and not x.startswith('+++') for x in diff),
                removed=sum(x.startswith('-') and not x.startswith('---') for x in diff),
                hunks=[x.rstrip() for x in diff if x.startswith('@@')])
        write('_out/' + group + '.diff', ''.join(combined))
    summaries['_policy'] = dict(
        runtime_deltas='wire: revision/envelope + opaque-only A7; adapter: roots/wire pin/namespace; keycheck proposal: job/stage labels; release-prep: R19 roots/scope/A7 pin closure',
        unchanged_executables=['adapter/host_driver.py','adapter/native_entry.py','keycheck/keycheck.py',
                               'keycheck/measure_bootstrap.py','release-prep/normalize_evidence.py'],
        recon='Frozen R18 engine referenced by unchanged hash; no copied executable.',
        beyond_listed_dispatch_ledger_key_changes=False,
        root_READY='Pins final roots/component READY/amendments/review/_out; intentionally excluded from its own diffs to avoid hash recursion.')
    for name in summaries['_policy']['unchanged_executables']:
        assert (R18 / name).read_bytes() == (HERE / name).read_bytes(), name
    assert (R18 / 'amendments/A5-A6.md').read_bytes() == (HERE / 'amendments/A5-A6.md').read_bytes()
    for name in ('KEY-ATTESTATION.json','CAP-ACCEPTANCE.json'):
        assert (R18 / 'release-prep/evidence' / name).read_bytes() == (HERE / 'release-prep/evidence' / name).read_bytes()
    write('_out/diff-summary.json', json.dumps(summaries, sort_keys=True, indent=2) + '\n')


if __name__ == '__main__':
    main()
