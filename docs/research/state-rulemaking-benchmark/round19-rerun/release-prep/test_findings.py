"""Offline regressions: frozen adapter validators, verbatim provenance, single-cell jobs."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
OUT = HERE / '_out'

def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

n = load('normalize_test', HERE / 'normalize_evidence.py')
p = load('proposals_test', HERE / 'make_proposals.py')
# Use the frozen adapter's synthetic Harness without writing into its _out.
fixture = HERE.parent / 'adapter/test_adapter.py'
t = types.ModuleType('frozen_fixture')
t.__file__ = str(fixture)
source = fixture.read_text().replace("OUT = HERE / '_out'", 'OUT = Path(' + repr(str(OUT)) + ')')
exec(compile(source, str(fixture), 'exec'), t.__dict__)
a = t.a

def original(name):
    return base64.b64decode(json.loads((HERE/'evidence'/name).read_bytes())['source_bytes_base64'])


class FindingTests(unittest.TestCase):
    def test_verbatim_strings_and_exact_original_bytes(self):
        def strings(v):
            if isinstance(v, str):
                yield v
            elif isinstance(v, dict):
                for x in v.values():
                    yield from strings(x)
            elif isinstance(v, list):
                for x in v:
                    yield from strings(x)
        for name in n.NAMES:
            raw = original(name)
            normalized = n.normalize(raw, name)
            value = json.loads(normalized)
            self.assertEqual(value['source_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(base64.b64decode(value['source_bytes_base64']), raw)
            self.assertEqual(value['source_record'], json.loads(raw))
            for statement in strings(json.loads(raw)):
                self.assertIn(statement.encode('utf-8'), [x.encode('utf-8') for x in strings(value)])
            self.assertEqual((HERE / 'evidence' / name).read_bytes(), normalized)
        cap = json.loads(n.normalize(original(n.NAMES[1]), n.NAMES[1]))
        self.assertEqual(cap['verbatim_acceptance'].encode(), b'accept re residual risk statement.')
        self.assertEqual(cap['user_statement_verbatim'].encode(), b'$3 is fine')

    def test_frozen_adapter_release_gate_accepts_both_normalized_files(self):
        with tempfile.TemporaryDirectory(dir=OUT) as tmp:
            h = t.Harness(tmp)
            h.init['release_policy'] = h.release['release_policy'] = 'P-ACCEPT'
            h.init['required_calls'] = h.release['required_calls'] = a.CALLS[:3]
            h.release['calls'] = {c: h.release['calls'][c] for c in a.CALLS[:3]}
            h.release['typed_testable'] = False
            budget = (h.root / h.release['artifacts']['budget']['path']).read_bytes().replace(b'RELEASE_POLICY = P-HARD', b'RELEASE_POLICY = P-ACCEPT')
            h.release['artifacts']['budget'] = h.write('design/BUDGET.md', budget)
            dp = a.read(h.root / h.release['artifacts']['design_primary']['path'])
            dp['release_policy'] = 'P-ACCEPT'
            dp['sha256']['BUDGET.md'] = a.sha(budget)
            h.release['artifacts']['design_primary'] = h.write('design/READY.primary.json', dp)
            h.release['artifacts']['design_ready'] = h.write('design/READY.json', {'release_policy': 'P-ACCEPT'})
            man = a.read(h.root / h.release['artifacts']['scoring_manifest']['path'])
            man['typed_testable'] = False
            for s in man['sources'].values():
                s['compounds'] = {}
            h.release['artifacts']['scoring_manifest'] = h.write('manifest.json', man)
            h.release['thresholds'].update(N_c=0, T4=0)
            for role, name in zip(('key_attestation', 'policy_evidence'), n.NAMES):
                h.release['artifacts'][role] = h.write('run/' + name, (HERE / 'evidence' / name).read_bytes())
            h.init['budget_sha256'] = a.sha(budget)
            h.release['init_sha256'] = a.sha(a.encode(h.init))
            h.save_release()
            h.rewrite_ledger([h.init, dict(type='BIND_RELEASE', release_policy='P-ACCEPT', release_sha256=a.sha(h.release_path.read_bytes()))])
            ledger = a.Ledger(h.run)
            with ledger.lock('offline-evidence-test'):
                ledger.load()
                result = a.release_gate(ledger, h.release_path, 'S1-OPQ', t.SOURCE, root=h.root)
                self.assertEqual(result[0]['release_policy'], 'P-ACCEPT')
                self.assertEqual(h.posts, [])
                self.assertEqual(h.key_reads, [])
                # Originals fail through those same validators: demonstrate test sensitivity.
                for role, name, reason in (('key_attestation', n.NAMES[0], 'K3_attestation'), ('policy_evidence', n.NAMES[1], 'policy_evidence')):
                    old = h.release['artifacts'][role]
                    h.release['artifacts'][role] = h.write('original/' + name, original(name))
                    h.save_release()
                    h.rewrite_ledger([h.init, dict(type='BIND_RELEASE', release_policy='P-ACCEPT', release_sha256=a.sha(h.release_path.read_bytes()))])
                    ledger.load()
                    with self.assertRaisesRegex(a.Refused, reason):
                        a.release_gate(ledger, h.release_path, 'S1-OPQ', t.SOURCE, root=h.root)
                    h.release['artifacts'][role] = old

    def test_no_or_multiple_live_cells_refused_before_any_write(self):
        with tempfile.TemporaryDirectory(dir=OUT) as tmp:
            root = Path(tmp)
            for cells in (p.CELLS, [], ['S1-OPQ', 'S2-OPQ'], ['S2-OPQ', 'S2-OPQ']):
                with self.assertRaises(ValueError):
                    p.generate(root, root/'out', {}, {}, draft=False, scope='test', batch='test', expires=1, prior=0, cells=cells)
                self.assertFalse((root/'out').exists())
            for args in ([], ['--cell','S1-OPQ','--cell','S2-OPQ']):
                result = subprocess.run([sys.executable,'-I','-S','-B',str(HERE/'make_proposals.py'),'--output',str(root/'out')] + args, capture_output=True)
                self.assertEqual(result.returncode, 2)
                self.assertIn(b'exactly one --cell', result.stderr)

    def test_signed_recovery_args_forbidden(self):
        for arg in ('--lock-evidence', '--lock-evidence=x', '--opq-freeze', '--opq-freeze=x'):
            with self.assertRaisesRegex(ValueError, 'forbidden'):
                p.validate_cell_args(['--cell', 'S1-OPQ', arg])
        p.validate_cell_args(['--cell', 'S1-OPQ'])

    def test_manifest_uses_normalized_run_pins_and_installation_guard(self):
        m = load('manifest_test', HERE/'prepare_manifest.py')
        manifest = m.build()
        for name in n.NAMES:
            self.assertEqual(manifest['files'][p.R17+'/run/'+name], p.st.digest((HERE/'evidence'/name).read_bytes()))
        read = m.st.read_regular
        with patch.object(m.st, 'read_regular', lambda path: b'{}' if Path(path).parent == HERE.parent / 'run' else read(path)):
            with self.assertRaisesRegex(ValueError, 'not installed'):
                m.build(require_installed=True)

    def test_normalization_idempotent_after_primary_install(self):
        for name in n.NAMES:
            raw = (HERE/'evidence'/name).read_bytes()
            self.assertEqual(n.normalize(raw, name), raw)

    def test_release_record_init_matches_frozen_a4_constants(self):
        records = load('records_test', HERE/'release_records.py')
        value = records.init_record(a, b'synthetic budget', 59_408_500)
        self.assertEqual(value['KEY_MAX'], a.recon.KEY_MAX)
        self.assertEqual(value['recon_sha256'], a.RECON_SHA)
        self.assertEqual(value['key_label'], a.KEY_LABEL)
        self.assertEqual(value['required_calls'], a.CALLS[:3])

    def test_wrong_per_cell_gate_refused(self):
        with tempfile.TemporaryDirectory(dir=OUT) as tmp:
            root = Path(tmp)
            release = root/'RELEASE.json'
            artifact = root/'evidence.json'
            artifact.write_text('{}')
            roles = a.REQUIRED_ARTIFACTS | {'host_driver'}
            release.write_bytes(p.st.canonical(dict(schema_version='r17.release.v1', required_calls=p.CELLS, typed_testable=False, release_policy='P-ACCEPT', artifacts={r:dict(path='evidence.json',sha256=p.st.digest(artifact.read_bytes())) for r in roles})))
            gate = root/'gate.json'
            gate.write_bytes(p.st.canonical(dict(accepted_by_primary=True,calls={'S1-OPQ':{}},release_sha256=p.st.digest(release.read_bytes()),files={})))
            p.release_pins(root,release,cell='S2-OPQ',gate=gate)
            with self.assertRaisesRegex(ValueError, 'per-cell gate call set'):
                p.release_pins(root,release,cell='S3-OPQ',gate=gate)

if __name__ == '__main__':
    unittest.main(verbosity=2)
