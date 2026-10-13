"""GPT-coded execution of frozen Fable requirements and primary qual disposition.
Authored fixture mappings only; no semantic extraction/model completeness oracle.
"""
import copy
import hashlib
import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('independent_r15_contract', ROOT / 'protocol/compact.py')
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)

PREFIX = 'Only if a district provides an accessible written notice, '
SUFFIX = ' AND no fee is charged to an eligible-but-unplaced child.'
PAD = 'all documented language-access safeguards remain required; '
LONG = PREFIX + (PAD * 20)[:697 - len(PREFIX) - len(SUFFIX)] + SUFFIX
assert len(LONG) == 697


def unit(i=1, p=0, q=0, m=0, k=6, sid='s1'):
    return dict(i=i, k=k, s='Authored synthetic assertion; no discovery claim.', m=m,
                p=p, y=None, d=[], b=[], e=[sid], q=q, r='Scope uncertain.' if q else '')


def envelope(source, units=None, nodes=None, links=None):
    table = C.span_table(source)
    return dict(v=C.VERSION, h=C.source_hash(source), t=C.digest(table),
                u=units or [unit()], g=nodes or [], l=links or [], z='END'), table


def fragment(source, start, end):
    """Authored range -> compact anchors; independent regex occurrence mapping."""
    rows = C.span_table(source)['rows']
    A = next(row for row in rows if row[1] <= start < row[2])
    Z = next(row for row in rows if row[1] <= end - 1 < row[2])
    h = source[start:min(end, A[2], start + 24)]
    t = source[max(start, Z[1], end - 24):end]
    heads = [m.start() for m in re.finditer('(?=' + re.escape(h) + ')', A[3])]
    head_occ = heads.index(start - A[1]) + 1
    tails = [m.start() for m in re.finditer('(?=' + re.escape(t) + ')', Z[3])
             if Z[1] + m.start() >= start and Z[1] + m.start() + len(t) >= start + len(h)]
    tail_occ = tails.index(end - len(t) - Z[1]) + 1
    return [A[0], h, head_occ, Z[0], t, tail_occ]


def phrase(source, needle, start=0):
    p = source.index(needle, start)
    return fragment(source, p, p + len(needle))


def leaf(i, x, q=0):
    return dict(i=i, o='L', a=[], x=x, g='', q=q, r='Unresolved interpretation.' if q else '')


def link(u=1, n='c1', w='onlyif', q=0):
    return dict(u=u, w=w, n=n, x=[], q=q, r='Applicability role unresolved.' if q else '')


def long_value(source=LONG):
    return envelope(source, [unit(p=1, m=3)], [leaf('c1', [fragment(source, 0, len(LONG))])], [link()])


class IndependentTests(unittest.TestCase):
    def check(self, value, source, table):
        expanded = C.expand(value, source, table)
        self.assertEqual(C.contract(expanded, source, table), value)
        self.assertEqual(C.validate_response(C.canonical(value).decode(), 'stop', source, table)['expanded'], expanded)
        return expanded

    def rejected(self, value, source, table, code=None):
        context = self.assertRaisesRegex(ValueError, code) if code else self.assertRaises(ValueError)
        with context:
            C.expand(value, source, table)

    def test_long_697_exact_fragment_and_no_clipped_qualification(self):
        value, table = long_value()
        before = copy.deepcopy(value)
        ex = self.check(value, LONG, table)
        ev = ex['nodes'][0]['evidence'][0]
        self.assertEqual((ev['start'], ev['end'], ev['text']), (0, 697, LONG))
        self.assertEqual(ev['text'].encode(), LONG.encode())
        self.assertEqual(value, before)
        self.assertEqual(ex['condition_coverage'], 'unverified')
        self.assertFalse(ex['production_eligible'])

    def test_short_exact_leaf_is_valid_but_authored_tail_omitted(self):
        value, table = long_value()
        cut = LONG.index(SUFFIX)
        value['g'][0]['x'] = [fragment(LONG, 0, cut)]
        ex = self.check(value, LONG, table)
        selected = ex['nodes'][0]['evidence'][0]['text']
        self.assertEqual(selected, LONG[:cut])
        self.assertNotIn('eligible-but-unplaced', selected)
        self.assertIn('eligible-but-unplaced', ex['units'][0]['evidence'][0]['quote'])
        # Known omitted condition vs authored full range; no host semantic rejection claimed.
        self.assertNotEqual(selected, LONG)
        self.assertEqual(ex['semantic_validity'], 'unverified')

    def test_link_omission_and_wrong_scope_can_pass_structural_validation(self):
        source = LONG + '\nQuestions go to the desk.'
        value, table = long_value(source)
        omitted = copy.deepcopy(value)
        omitted.update(g=[], l=[])
        omitted['u'][0]['p'] = 0
        ex = self.check(omitted, source, table)
        self.assertEqual(ex['units'][0]['applicability'], 'none_reported')
        self.assertEqual(ex['units'][0]['condition_links'], [])
        wrong = copy.deepcopy(value)
        wrong['u'][0]['p'] = 0
        wrong['u'].append(unit(i=2, p=1, sid='s2'))
        wrong['l'][0]['u'] = 2
        ex = self.check(wrong, source, table)
        self.assertEqual(ex['units'][0]['condition_links'], [])
        self.assertEqual(ex['links'][0]['unit_id'], 2)
        # Authored mapping expects governed unit 1. Wrong governance is semantics, not shape.
        self.assertNotEqual(ex['links'][0]['unit_id'], 1)

    def test_operator_and_exception_scope_inversions_are_semantic_negatives(self):
        for op, source, needles in [
            ('AND', 'Required object: A AND B.', ['A AND', 'B.']),
            ('EXC', 'Required object: base A EXCEPT carveout B.', ['base A', 'carveout B'])]:
            nodes = [dict(i='c1', o=op, a=['c2', 'c3'], x=[], g='', q=0, r=''),
                     leaf('c2', [phrase(source, needles[0])]), leaf('c3', [phrase(source, needles[1])])]
            value, table = envelope(source, nodes=nodes, links=[link(w='obj')])
            self.check(value, source, table)
            bad = copy.deepcopy(value)
            if op == 'AND':
                bad['g'][0]['o'] = 'OR'
                ex = self.check(bad, source, table)
                self.assertNotEqual(ex['nodes'][0]['op'], op)
            else:
                bad['g'][0]['a'].reverse()
                ex = self.check(bad, source, table)
                self.assertNotEqual(ex['nodes'][0]['args'], ['c2', 'c3'])

    def test_qual_requires_link_and_governing_unit_uncertainty(self):
        source = 'Applicants must provide records. Qualification role unclear: archive availability.'
        value, table = envelope(source, [unit(p=2, q=1, m=1)],
                                [leaf('c1', [phrase(source, 'archive availability')])], [link(w='qual', q=1)])
        ex = self.check(value, source, table)
        self.assertEqual(ex['units'][0]['modality'], 'mandatory')
        self.assertEqual(ex['units'][0]['applicability'], 'unknown')
        for change in ['link_q0', 'unit_p0', 'unit_p1', 'unit_q0', 'node_only']:
            bad = copy.deepcopy(value)
            if change == 'link_q0': bad['l'][0].update(q=0, r='')
            elif change == 'unit_p0': bad['u'][0]['p'] = 0
            elif change == 'unit_p1': bad['u'][0]['p'] = 1
            elif change == 'unit_q0': bad['u'][0].update(q=0, r='')
            else:
                bad['g'][0].update(q=1, r='Only node uncertainty present.')
                bad['l'][0].update(q=0, r='')
            with self.subTest(change=change): self.rejected(bad, source, table)
        clear = copy.deepcopy(value)
        clear['l'][0].update(w='obj', q=0, r='')
        clear['u'][0].update(p=0, q=0, r='')
        self.check(clear, source, table)

    def test_context_links_do_not_inherit_applicability_or_make_unconditional(self):
        value, table = long_value()
        value['u'].append(unit(i=2))
        value['u'][1]['d'] = [1]
        ex = self.check(value, LONG, table)
        self.assertEqual(ex['units'][1]['required_unit_ids'], [1])
        self.assertEqual(ex['units'][1]['condition_links'], [])
        self.assertEqual(ex['units'][1]['applicability'], 'none_reported')
        self.assertNotIn('unconditional', C.canonical(ex).decode())

    def test_conditional_tail_repeated_and_overlapping_anchors(self):
        source = 'TAIL prefix HEAD one TAIL two HEAD three TAIL end'
        table = C.span_table(source)
        ev = C.resolve_fragment(['s1', 'HEAD', 2, 's1', 'TAIL', 1], source, table)
        self.assertEqual(ev['text'], 'HEAD three TAIL')
        self.assertEqual(ev['start'], source.index('HEAD three'))
        source = 'repeat repeat repeat'
        table = C.span_table(source)
        short = C.resolve_fragment(['s1', 'repeat', 2, 's1', 'repeat', 1], source, table)
        wide = C.resolve_fragment(['s1', 'repeat', 2, 's1', 'repeat', 2], source, table)
        self.assertEqual((short['start'], short['end'], short['text']), (7, 13, 'repeat'))
        self.assertEqual((wide['start'], wide['end'], wide['text']), (7, 20, 'repeat repeat'))
        ev = C.resolve_fragment(['s1', 'aa', 2, 's1', 'aa', 2], 'aaaa', C.span_table('aaaa'))
        self.assertEqual((ev['start'], ev['end'], ev['text']), (1, 4, 'aaa'))

    def test_unicode_scalar_surrogate_pairs_and_normalization(self):
        source = '🫧' * 48
        value, table = envelope(source, nodes=[leaf('c1', [['s1', source, 1, 's1', source, 1]])], links=[link(w='obj')])
        raw = json.dumps(value, ensure_ascii=True)
        self.assertEqual(C.validate_response(raw, 'stop', source, table)['expanded']['nodes'][0]['evidence'][0]['text'], source)
        self.assertEqual(C.strict_load('"\\ud83e\\udee7"'), '🫧')
        for bad in ['"\\ud800"', '"\\udfff"']:
            with self.assertRaisesRegex(ValueError, 'unpaired_surrogate'): C.strict_load(bad)
        with self.assertRaisesRegex(ValueError, 'unpaired_surrogate'): C.source_hash(chr(0xD800))
        source = 'Cafe\u0301'
        with self.assertRaisesRegex(ValueError, 'head_not_found'):
            C.resolve_fragment(['s1', 'Café', 1, 's1', 'Café', 1], source, C.span_table(source))

    def test_cross_row_and_discontinuous_exact_evidence(self):
        source = 'Clause begins\r\nnotice in Café\u0085then Cafe\u0301\u2028and review\u2029Clause ends.'
        table = C.span_table(source)
        value, _ = envelope(source, [unit(p=2, q=1)],
                            [leaf('c1', [fragment(source, 0, len(source))])], [link(w='qual', q=1)])
        ev = self.check(value, source, table)['nodes'][0]['evidence'][0]
        self.assertEqual(ev['text'].encode(), source.encode())
        value['g'][0]['x'] = [phrase(source, 'Clause begins'), phrase(source, 'Clause ends.')]
        ex = self.check(value, source, table)
        self.assertEqual([e['text'] for e in ex['nodes'][0]['evidence']], ['Clause begins', 'Clause ends.'])
        bad = copy.deepcopy(value); bad['g'][0]['x'].reverse()
        self.rejected(bad, source, table, 'fragment_order_overlap')

    def test_full_source_receipt_binding_and_growth_without_fit_claim(self):
        value, table = long_value()
        mutated = LONG.replace('eligible-but-unplaced', 'eligible-and-placed')
        self.rejected(value, mutated, C.span_table(mutated), 'binding_version')
        self.rejected(value, mutated, table, 'exact_host_table')
        plan = C.build(LONG)
        user = json.loads(plan['body']['messages'][1]['content'])
        self.assertEqual(user['source_text'], LONG)
        self.assertEqual(''.join(row[3] for row in user['span_table']['rows']), LONG)
        self.assertEqual(user['source_text_sha256'], hashlib.sha256(LONG.encode()).hexdigest())
        longer = C.build(LONG + '\n' + LONG)
        self.assertGreater(longer['body_bytes'], plan['body_bytes'])
        self.assertEqual(plan['guarded_bytes'], plan['body_bytes'] + 1024)
        with self.assertRaisesRegex(ValueError, 'full_request_overflow'): C.build('x' * 40000)

    def test_count_sentinels_and_legal_high_ids(self):
        source = 'Synthetic condition.'
        value, table = envelope(source)
        value['u'] = [unit(i=i) for i in range(1, 160)]
        C.validate(value, source, table)
        value['u'][-1]['i'] = 160
        C.validate(value, source, table)
        value['u'].append(unit(i=159))
        self.rejected(value, source, table, 'capacity_review_u')
        value, table = envelope(source)
        x = [phrase(source, 'Synthetic condition.')]
        value['g'] = [leaf('c' + str(i), x) for i in range(1, 400)]
        value['l'] = [link(n='c' + str(i), w='acts') for i in range(1, 400)]
        C.validate(value, source, table)
        bad = copy.deepcopy(value); bad['g'].append(leaf('c400', x))
        self.rejected(bad, source, table, 'capacity_review_g')
        bad = copy.deepcopy(value); bad['u'].append(unit(i=2)); bad['l'].append(link(u=2, n='c1', w='acts'))
        self.rejected(bad, source, table, 'capacity_review_l')
        single, table = envelope(source, nodes=[leaf('c400', x)], links=[link(n='c400', w='acts')])
        self.check(single, source, table)

    def test_depth_cycles_dangling_orphans_and_final_node_failure(self):
        source = 'Condition.'
        x = [phrase(source, 'Condition.')]
        for depth in [12, 13]:
            nodes = [dict(i='c' + str(i), o='NOT', a=['c' + str(i + 1)], x=[], g='', q=0, r='') for i in range(1, depth)] + [leaf('c' + str(depth), x)]
            value, table = envelope(source, nodes=nodes, links=[link(w='obj')])
            if depth == 12: self.check(value, source, table)
            else: self.rejected(value, source, table, 'graph_depth')
        value, table = envelope(source, nodes=[leaf('c1', x)], links=[link(w='obj')])
        for change in ['cycle', 'dangling', 'orphan', 'final_bad']:
            bad = copy.deepcopy(value)
            if change == 'cycle':
                bad['g'] = [dict(i='c1', o='NOT', a=['c2'], x=[], g='', q=0, r=''), dict(i='c2', o='NOT', a=['c1'], x=[], g='', q=0, r='')]
            elif change == 'dangling': bad['l'][0]['n'] = 'c99'
            elif change == 'orphan': bad['g'].append(leaf('c2', x))
            else:
                bad['g'].append(leaf('c2', [['s1', 'missing', 1, 's1', 'missing', 1]]))
                bad['l'].append(link(n='c2', w='acts'))
            before = copy.deepcopy(bad)
            produced = None
            with self.subTest(change=change), self.assertRaises(ValueError): produced = C.expand(bad, source, table)
            self.assertIsNone(produced)
            self.assertEqual(bad, before)

    def test_fragment_anchor_raw_and_parser_boundaries(self):
        source = ' '.join('part' + str(i) for i in range(9))
        value, table = envelope(source, nodes=[leaf('c1', [phrase(source, 'part' + str(i)) for i in range(8)])], links=[link(w='obj')])
        self.check(value, source, table)
        value['g'][0]['x'].append(phrase(source, 'part8'))
        self.rejected(value, source, table, 'array_bound')
        source = '🫧' * 49
        table = C.span_table(source)
        C.resolve_fragment(['s1', source[:48], 1, 's1', source[:48], 1], source, table)
        with self.assertRaisesRegex(ValueError, 'text_bound'): C.resolve_fragment(['s1', source, 1, 's1', source, 1], source, table)
        self.assertEqual(C.strict_load(' ' * (C.RAW_LIMIT - 2) + '{}'), {})
        with self.assertRaisesRegex(ValueError, 'raw_size'): C.strict_load(' ' * (C.RAW_LIMIT - 1) + '{}')
        C.strict_load('[' * 64 + '0' + ']' * 64)
        with self.assertRaisesRegex(ValueError, 'parser_depth'): C.strict_load('[' * 65 + '0' + ']' * 65)

    def test_inverse_evidence_metadata_and_completeness_tamper(self):
        value, table = long_value()
        ex = self.check(value, LONG, table)
        for change in ['text', 'end', 'link', 'unit_copy', 'flag', 'wrong_list']:
            bad = copy.deepcopy(ex)
            if change == 'text': bad['nodes'][0]['evidence'][0]['text'] += 'changed'
            elif change == 'end': bad['nodes'][0]['evidence'][0]['end'] -= 1
            elif change == 'link': bad['links'][0]['role'] = 'if'
            elif change == 'unit_copy': bad['units'][0]['condition_links'] = []
            elif change == 'flag': bad['condition_coverage'] = 'complete'
            else: bad['nodes'] = None
            with self.subTest(change=change), self.assertRaises(ValueError): C.contract(bad, LONG, table)

    def test_unavailable_reference_and_explicit_modality_independent(self):
        source = 'Applicants must satisfy section 99. Section 99 is not supplied.'
        node = leaf('c1', [phrase(source, 'section 99')], q=2); node['o'] = 'R'
        value, table = envelope(source, [unit(p=1, m=1)], [node], [link()])
        ex = self.check(value, source, table)
        self.assertTrue(ex['nodes'][0]['unresolved_reference'])
        self.assertEqual(ex['units'][0]['modality'], 'mandatory')
        bad = copy.deepcopy(value); bad['g'][0]['o'] = 'L'
        ex = self.check(bad, source, table)
        self.assertFalse(ex['nodes'][0]['unresolved_reference'])
        # Wrong R->L classification is semantic, not automatically inferable from exact text.

    def test_deadline_dimensions_separate_absent_and_stated_basis(self):
        source = 'Mailed filings must be postmarked by April 2, 2032.\nElectronic filings must be received by April 2, 2032 at 17:00 Eastern Time.'
        absent = dict(s='absent', x=[], r='')
        u1 = unit(k=3, q=1, m=1); u1['s'] = 'Mailed filings deadline is April 2, 2032.'
        u1['y'] = dict(c=copy.deepcopy(absent), z=copy.deepcopy(absent), b=dict(s='stated', x=[phrase(source, 'postmarked')], r=''))
        u2 = unit(i=2, k=3, m=1, sid='s2'); u2['s'] = 'Electronic filings deadline is April 2, 2032.'
        u2['y'] = dict(c=dict(s='stated', x=[phrase(source, '17:00')], r=''), z=dict(s='stated', x=[phrase(source, 'Eastern Time')], r=''), b=dict(s='stated', x=[phrase(source, 'received')], r=''))
        value, table = envelope(source, [u1, u2])
        ex = self.check(value, source, table)
        self.assertEqual(ex['units'][0]['deadline']['z']['state'], 'absent')
        self.assertEqual(ex['units'][1]['deadline']['z']['evidence'][0]['text'], 'Eastern Time')
        self.assertEqual(ex['units'][0]['deadline']['b']['evidence'][0]['text'], 'postmarked')
        for change in ['false_absent_evidence', 'missing_uncertainty', 'na_clock']:
            bad = copy.deepcopy(value)
            if change == 'false_absent_evidence': bad['u'][0]['y']['z']['x'] = [phrase(source, 'Eastern Time')]
            elif change == 'missing_uncertainty': bad['u'][0].update(q=0, r='')
            else: bad['u'][1]['y']['c'].update(s='na', r='Wrong not-applicable clock.')
            with self.subTest(change=change): self.rejected(bad, source, table)

    def test_strict_types_raw_receipts_and_terminal_no_salvage(self):
        value, table = long_value()
        for change in ['bool_id', 'float_q', 'legacy_c', 'duplicate_id', 'unknown_evidence', 'terminal']:
            bad = copy.deepcopy(value)
            if change == 'bool_id': bad['u'][0]['i'] = True
            elif change == 'float_q': bad['u'][0]['q'] = 0.0
            elif change == 'legacy_c': bad['u'][0]['c'] = LONG
            elif change == 'duplicate_id': bad['u'].append(copy.deepcopy(bad['u'][0]))
            elif change == 'unknown_evidence': bad['u'][0]['e'] = ['s999']
            else: bad['z'] = 'STOP'
            with self.subTest(change=change): self.rejected(bad, LONG, table)
        raw = C.canonical(value).decode()
        for invalid in [raw[:-1], raw + ' trailing', '{"x":1,"x":2}', '[NaN]']:
            with self.assertRaises(ValueError): C.validate_response(invalid, 'stop', LONG, table)
        with self.assertRaisesRegex(ValueError, 'non_stop'): C.validate_response(raw, 'length', LONG, table)


if __name__ == '__main__':
    unittest.main(verbosity=2)
