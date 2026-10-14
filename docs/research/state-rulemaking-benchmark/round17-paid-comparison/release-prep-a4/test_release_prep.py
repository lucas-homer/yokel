"""Offline staging/proposal tests: temporary synthetic trees only, no executor calls."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

HERE = Path(__file__).resolve().parent
OUT = HERE / '_out'
OUT.mkdir(exist_ok=True)
spec = importlib.util.spec_from_file_location('r17_proposal_tests', HERE / 'make_proposals.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
st = p.st


class PrepTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=OUT)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.parent = self.root / 'allowed/.r17-stage'
        self.allowed = [str(self.root)]
        self.m = {'schema_version': 'r17.stage.v1', 'files': {}}
        def put(name, raw):
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            self.m['files'][name] = st.digest(raw)
        put(p.ADAPTER + '/native_entry.py', st.read_regular(st.BENCH / p.ADAPTER / 'native_entry.py'))
        put(p.ADAPTER + '/host_driver.py', b'# SYNTHETIC offline host; never invoked\n')
        put(p.ADAPTER + '/SPEC.md', b'SYNTHETIC review fixture\n')
        put(p.R17 + '/sources-r2/synthetic/parsed-body.txt', b'SYNTHETIC source text\n')
        put(p.R17 + '/reference/synthetic.json', b'{"SYNTHETIC":true}')
        put(p.R17 + '/evidence.json', b'{"files":{}}')
        self.core = json.loads(st.read_regular(st.CORE))
        self.core['adapter_roots'] = self.allowed
        self.core['dependency_roots'] = self.allowed + [str(Path(self.core['python_path']).parent.parent)]
        self.now = int(time.time())

    def staged(self):
        return st.stage(self.source, self.parent, self.m, allowed_roots=self.allowed)

    def test_exact_copy_layout_hashes_and_no_extras(self):
        (self.source / 'unused.txt').write_text('not copied')
        stage = self.staged()
        st.verify_stage(stage, self.m)
        self.assertFalse((stage / 'unused.txt').exists())
        self.assertEqual(stage.name, st.content_id(self.m))
        self.assertEqual({x.relative_to(stage).as_posix() for x in stage.rglob('*') if x.is_file()}, set(self.m['files']) | {'STAGE-MANIFEST.json'})
        for name, h in self.m['files'].items():
            self.assertEqual(st.digest(st.read_regular(stage / name)), h)

    def test_full_100_file_layout_imports_pinned_adapter_and_wire_offline(self):
        real = st.load_manifest()
        synthetic = {'schema_version': 'r17.stage.v1', 'files': {}}
        fixture = self.root / 'full-source'
        fixture.mkdir()
        for name in real['files']:
            # Never open actual source/reference bodies. Replace the entire
            # reference tree (including metadata) with synthetic fixture bytes.
            if name.startswith(p.R17 + '/reference/') or name.endswith('/parsed-body.txt'):
                raw = b'SYNTHETIC frozen member\n'
            else:
                raw = st.read_regular(st.BENCH / name)
            dst = fixture / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(raw)
            synthetic['files'][name] = st.digest(raw)
        stage = st.stage(fixture, self.root / 'full-stage', synthetic, allowed_roots=self.allowed)
        code = ("import importlib.util; from pathlib import Path; "
            "p=Path(" + repr(str(stage / p.ADAPTER / 'r17_adapter.py')) + "); "
            "s=importlib.util.spec_from_file_location('staged_offline',p); "
            "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
            "assert m.recon.FLOOR == 270000000; assert m.recon.KEY_MAX == 50000000000; assert m.KEY_LABEL == 'DocketClock'; "
            "assert m.wire.build('Operators must file notices.','opaque')['request_sha256']; "
            "print('staged pinned adapter/recon/wire import and synthetic build OK')")
        result = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', code],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env={}, check=False)
        self.assertEqual(result.returncode, 0, result.stdout.decode())
        self.assertIn(b'synthetic build OK', result.stdout)
        self.assertEqual(len(synthetic['files']), len(real['files']))

    def test_a4_manifest_pins_new_authorities_and_inherits_reference_hashes(self):
        manifest = st.load_manifest()
        frozen = json.loads(st.read_regular(st.BENCH / p.R17 / 'release-prep/STAGE-MANIFEST.json'))
        refs = lambda m: {n: h for n, h in m['files'].items() if n.startswith(p.R17 + '/reference/')}
        self.assertEqual(refs(manifest), refs(frozen))
        for name in ('recon-a4/r17recon.py', 'recon-a4/READY.json',
                     'adapter-r1-4/r17_adapter.py', 'adapter-r1-4/native_entry.py',
                     'adapter-r1-4/READY.json', 'run/KEY-ATTESTATION.json'):
            rel = p.R17 + '/' + name
            self.assertEqual(manifest['files'][rel], st.digest(st.read_regular(st.BENCH / rel)))
        self.assertFalse(any(n.startswith(p.R17 + '/adapter-r1-3/') for n in manifest['files']))
        self.assertIn(p.R17 + '/design-r3-1/fixtures/r17recon.py', manifest['files'])

    def test_existing_target_refused(self):
        stage = self.staged()
        with self.assertRaises(FileExistsError):
            self.staged()
        st.verify_stage(stage, self.m)

    def test_source_file_symlink_refused(self):
        path = self.source / p.ADAPTER / 'SPEC.md'
        path.unlink()
        path.symlink_to(self.source / p.ADAPTER / 'host_driver.py')
        with self.assertRaises((ValueError, OSError)):
            self.staged()

    def test_source_ancestor_symlink_refused(self):
        path = self.root / 'source-link'
        path.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises((ValueError, OSError)):
            st.stage(path, self.parent, self.m, allowed_roots=self.allowed)

    def test_destination_ancestor_symlink_refused(self):
        self.parent.parent.mkdir()
        self.parent.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises((ValueError, OSError)):
            self.staged()

    def test_changed_bytes_refuse_and_partial_stage_is_not_reused(self):
        (self.source / p.ADAPTER / 'SPEC.md').write_text('drift')
        with self.assertRaisesRegex(ValueError, 'source hash mismatch'):
            self.staged()
        with self.assertRaises(FileExistsError):
            self.staged()

    def test_traversal_and_outside_roots_refuse(self):
        with self.assertRaises(ValueError):
            st.relative('../escape')
        with self.assertRaises(ValueError):
            st.relative('/absolute')
        with self.assertRaises(ValueError):
            st.stage(self.source, self.root / 'outside', self.m, allowed_roots=[str(self.source)])

    def proposals(self, stage, output, *, draft, cells=p.CELLS, **kwargs):
        return p.generate(stage, output, self.m, self.core, draft=draft, scope='r17-test-scope',
            batch='synthetic-20261014', expires=self.now + 86400, prior=0, cells=cells, **kwargs)

    def test_three_draft_proposals_exact_shape_and_reservations(self):
        stage = self.staged()
        proposals = self.proposals(stage, self.root / 'draft', draft=True)
        self.assertEqual(len(proposals), 3)
        values = [json.loads(x.read_bytes()) for x in proposals]
        self.assertEqual([x['budget']['prior_nanousd'] for x in values], [0, 270_000_000, 540_000_000])
        self.assertEqual(len({x['job_id'] for x in values}), 3)
        self.assertIn('UNSIGNED DRAFT', (self.root / 'draft/UNSIGNED.txt').read_text())
        for value in values:
            self.assertTrue(p.validate(value, self.core, now=self.now, check_files=False))
            self.assertEqual(value['provider_variables'], ['OPENROUTER_API_KEY'])
            self.assertEqual(value['job']['timeout_seconds'], 1800)
            self.assertEqual(st.canonical(value), (self.root / 'draft' / (value['job_id'] + '.json')).read_bytes())

    def final_release(self, stage):
        evidence = {'path': p.R17 + '/evidence.json', 'sha256': self.m['files'][p.R17 + '/evidence.json']}
        roles = {'protocol', 'budget', 'reference_spec', 'adjudication_spec', 'scorer', 'recon',
            'cases', 'cases_src', 'check', 'A1_fixture_gate', 'A2_fixture_gate', 'sources_ready',
            'reference_ready', 'scoring_manifest', 'policy_evidence', 'key_attestation', 'machine_check',
            'roles_auth', 'adapter', 'tests', 'adapter_ready', 'design_ready', 'design_primary', 'host_driver'}
        release = stage / p.R17 / 'run/RELEASE.json'
        release.parent.mkdir()
        release.write_bytes(st.canonical({'schema_version': 'r17.release.v1', 'required_calls': p.CELLS,
            'typed_testable': False, 'release_policy': 'P-ACCEPT', 'artifacts': {r: evidence for r in roles}}))
        gate = release.parent / 'gate.json'
        gate.write_bytes(st.canonical({'files': {'RELEASE.json': st.digest(release.read_bytes())}}))
        return release, gate

    def test_temp_staged_final_proposals_validate_actual_files_all_cells(self):
        stage = self.staged()
        release, gate = self.final_release(stage)
        paths = self.proposals(stage, self.root / 'final', draft=False, release=release, gate=gate,
            review=stage / p.ADAPTER / 'SPEC.md')
        for path in paths:
            value = json.loads(path.read_bytes())
            self.assertTrue(p.validate(value, self.core, now=self.now, check_files=True))
            self.assertIn(str(release), value['job']['files'])
            self.assertIn(str(Path(value['job']['argv'][4]).parent / 'arguments.json'), value['job']['files'])
            self.assertNotIn(str(release.parent / 'ledger.jsonl'), value['job']['files'])
        # Synthetic release above verifies native admission, NOT production adapter gates.

    def test_invalid_native_semantics_rejected(self):
        stage = self.staged()
        value = json.loads(self.proposals(stage, self.root / 'draft', draft=True)[0].read_bytes())
        mutations = [lambda m: m.update(expires_unix=0),
            lambda m: m['job'].update(timeout_seconds=1801),
            lambda m: m['job']['argv'].append('--cell'),
            lambda m: m['job']['argv'].__setitem__(4, str(self.source / 'host_driver.py')),
            lambda m: m.update(provider_variables=['TYPESAFE_API_KEY']),
            lambda m: m['budget'].update(reservation_nanousd=True),
            lambda m: m['budget'].update(prior_nanousd=2_000_000_000),
            lambda m: m.update(extra='UNSIGNED'),
            lambda m: m['review'].update(sha256='0'*64)]
        for mutation in mutations:
            bad = copy.deepcopy(value)
            mutation(bad)
            with self.assertRaises(ValueError):
                p.validate(bad, self.core, now=self.now, check_files=False)

    def test_missing_release_gate_and_expiry_fail_closed(self):
        stage = self.staged()
        with self.assertRaises(ValueError):
            self.proposals(stage, self.root / 'missing', draft=False)
        release, _ = self.final_release(stage)
        with self.assertRaisesRegex(ValueError, 'prior-cell'):
            self.proposals(stage, self.root / 'missing-gate', draft=False, cells=['S2-OPQ'],
                release=release, review=stage / p.ADAPTER / 'SPEC.md')


if __name__ == '__main__':
    unittest.main(verbosity=2)
