'''Offline tests for the r14 compact inventory contract. Synthetic fixture only.

No network, no writes, no build(), no provider output. Reviewer helpers in this file are
AI assessment heuristics over fixture wording; they are not a semantic oracle, and nothing
here claims that validate() must reject semantic defects.
'''
import copy
import re
import unittest

import compact as C
import fictional_controls as F

SOURCE = F.SOURCE
TABLE = C.span_table(SOURCE)
CRLF = chr(13) + chr(10)
CLOCK = re.compile('[0-9]{1,2}:[0-9]{2}|[ap][.]m[.]')
MODAL = re.compile('(?i)(^|[^a-z])(must|shall|should|required|prohibited)([^a-z]|$)')
FORCE_MODALITIES = {'mandatory', 'advisory', 'optional', 'prohibited'}


def fixture():
    return F.fixture()


def expanded(value=None):
    return C.expand(fixture() if value is None else value, SOURCE, TABLE)


def by_id(exp):
    return {u['id']: u for u in exp['units']}


def quotes(unit):
    return ' '.join(e['quote'] for e in unit['evidence'])


def cites(unit, span_id):
    return any(e['span_id'] == span_id for e in unit['evidence'])


def cited_spans(exp):
    return {e['span_id'] for u in exp['units'] for e in u['evidence']}


def recoverable(exp, span_id, needle):
    '''A fact is recoverable when some unit citing span_id states it in assertion or
    applicability. Deliberately independent of unit count: bundling and broad spans pass.'''
    return any(cites(u, span_id) and (needle in u['assertion'] or needle in u['applicability'])
               for u in exp['units'])


def force_is_justified(unit):
    '''Heuristic: a forceful modality asserted with uncertainty none needs an explicit modal in
    the cited text; otherwise a non-none uncertainty with a reason is required. Contested force
    with a stated reason is accepted, not treated as error.'''
    if unit['modality'] not in FORCE_MODALITIES:
        return True
    if unit['uncertainty'] != 'none':
        return bool(unit['uncertainty_reason'].strip())
    return MODAL.search(quotes(unit)) is not None


def date_only_dims_explicit(unit):
    '''Heuristic: a deadline timing unit whose cited text has no clock token must either say
    something about the missing dimensions or carry uncertainty; silence is the defect.'''
    if unit['kind'] != 'timing' or 'deadline' not in unit['assertion']:
        return True
    if CLOCK.search(quotes(unit)):
        return True
    return bool(unit['applicability'].strip()) or unit['uncertainty'] != 'none'


def raises(fn, fragment):
    try:
        fn()
    except ValueError as err:
        return fragment in str(err)
    return False


def check(v, fragment):
    return raises(lambda: C.validate(v, SOURCE, TABLE), fragment)


class SpanTableAndBinding(unittest.TestCase):

    def test_partition_is_exact_and_byte_preserving(self):
        rows = TABLE['rows']
        self.assertEqual(len(rows), 10)
        self.assertEqual(C.reconstruct(SOURCE, TABLE), SOURCE)
        self.assertTrue(rows[0][3].endswith(CRLF))
        self.assertEqual((rows[0][2], rows[1][1]), (32, 32))
        self.assertIn(chr(0x65) + chr(0x301), rows[6][3])
        self.assertNotIn(chr(0xE9), rows[6][3])
        self.assertEqual(fixture()['t'], C.digest(TABLE))
        self.assertEqual(fixture()['h'], C.source_hash(SOURCE))

    def test_one_byte_source_mutation_breaks_binding(self):
        mutated = SOURCE.replace('1964', '1965')
        self.assertNotEqual(mutated, SOURCE)
        self.assertTrue(raises(lambda: C.validate(fixture(), mutated, TABLE), 'exact host span table'))
        self.assertTrue(raises(lambda: C.validate(fixture(), mutated, C.span_table(mutated)), 'binding/version'))
        v = fixture()
        v['h'] = C.source_hash(mutated)
        self.assertTrue(check(v, 'binding/version'))
        v = fixture()
        v['t'] = C.digest(C.span_table(mutated))
        self.assertTrue(check(v, 'binding/version'))


class StructuralInvariants(unittest.TestCase):

    def test_fixture_validates_roundtrips_and_never_claims_completeness(self):
        v = fixture()
        self.assertIs(C.validate(v, SOURCE, TABLE), v)
        self.assertEqual(C.strict_load(C.canonical(v).decode('utf-8')), v)
        exp = expanded(v)
        self.assertEqual(C.contract(exp, SOURCE, TABLE), v)
        self.assertTrue(all(e['occurrence'] == 1 for u in exp['units'] for e in u['evidence']))
        # Fixture preservation only: these flags record that nothing here proves model discovery.
        self.assertEqual(exp['source_inventory_completeness'], 'unverified')
        self.assertFalse(exp['production_eligible'])
        self.assertFalse(exp['action_ready'])
        self.assertIn('never provider responses', F.__doc__)
        promoted = copy.deepcopy(exp)
        promoted['production_eligible'] = True
        self.assertTrue(raises(lambda: C.contract(promoted, SOURCE, TABLE), 'expanded evidence/field equality'))
        tampered = copy.deepcopy(exp)
        tampered['units'][0]['evidence'][0]['quote'] = 'Send remarks by April 10, 2031.' + CRLF
        self.assertTrue(raises(lambda: C.contract(tampered, SOURCE, TABLE), 'expanded evidence/field equality'))

    def test_id_evidence_cycle_terminal_capacity_and_truncation_rejections(self):
        cases = []
        v = fixture(); v['u'][1]['i'] = 1; cases.append((v, 'duplicate unit ID'))
        v = fixture(); v['u'][0]['e'] = ['s11']; cases.append((v, 'unknown evidence ID'))
        v = fixture(); v['u'][0]['e'] = ['s1', 's1']; cases.append((v, 'duplicate references'))
        v = fixture(); v['u'][2]['d'] = [4]; cases.append((v, 'dependency cycle'))
        v = fixture(); v['u'][0]['d'] = [99]; cases.append((v, 'unknown dependency'))
        v = fixture(); v['z'] = 'STOP'; cases.append((v, 'terminal marker'))
        v = fixture(); v['u'][0]['extra'] = 1; cases.append((v, 'closed keys'))
        v = fixture(); v['u'][0].update(q=0, r=''); cases.append((v, 'unknown modality without uncertainty'))
        v = fixture(); v['u'][0].update(r=''); cases.append((v, 'uncertainty/reason contradiction'))
        v = fixture(); v['u'][2].update(q=1); cases.append((v, 'uncertainty/reason contradiction'))
        filler = [dict(i=n, k=8, s='filler', m=0, c='', d=[], b=[], e=['s8'], q=0, r='') for n in range(1, 161)]
        v = fixture(); v['u'] = filler; cases.append((v, 'inventory bound/capacity reached'))
        for v, fragment in cases:
            self.assertTrue(check(v, fragment), fragment)
        v = fixture(); v['u'] = filler[:159]
        C.validate(v, SOURCE, TABLE)
        self.assertTrue(raises(lambda: C.validate(fixture(), SOURCE, TABLE, finish_reason='length'), 'non-stop/truncated response'))
        dup = '{' + chr(34) + 'a' + chr(34) + ':1,' + chr(34) + 'a' + chr(34) + ':2}'
        self.assertTrue(raises(lambda: C.strict_load(dup), 'duplicate key'))
        self.assertTrue(raises(lambda: C.strict_load('[NaN]'), 'nonfinite constant'))

    def test_dependency_edges_carry_no_force_and_endpoint_rule_is_structural(self):
        v = fixture()
        # Allocate test-only IDs above whatever the fixture currently uses, never hard-coded.
        top = max(u['i'] for u in v['u'])
        ep, role, rel = top + 1, top + 2, top + 3
        self.assertLessEqual(rel, 160)
        # Precondition: the fixture units this method leans on keep their kinds.
        kinds = {u['i']: u['k'] for u in v['u']}
        self.assertEqual((kinds[14], kinds[15], kinds[19]), (0, 0, 3))
        v['u'].append(dict(i=ep, k=4, s='The office in Alder City is the in-person arrival endpoint.', m=0, c='', d=[14, 15], b=[], e=['s5', 's9'], q=0, r=''))
        v['u'].append(dict(i=role, k=5, s='The office serves as the arrival location for the July 4, 2031 deadline.', m=0, c='', d=[ep, 19], b=[], e=['s9', 's5'], q=0, r=''))
        units = by_id(C.expand(v, SOURCE, TABLE))
        self.assertEqual(units[role]['required_unit_ids'], [ep, 19])
        self.assertEqual(units[ep]['modality'], 'informational')
        self.assertEqual(units[14]['modality'], 'informational')
        # A mandatory dependent does not make its prerequisites mandatory: edges have no force.
        w = copy.deepcopy(v); w['u'][-1].update(m=1)
        self.assertEqual(by_id(C.expand(w, SOURCE, TABLE))[ep]['modality'], 'informational')
        # The role-to-endpoint ordering rule is purely structural and is enforced as such.
        w = copy.deepcopy(v); w['u'][-1]['d'] = [19, ep]
        self.assertTrue(check(w, 'role endpoint dependency'))
        w = copy.deepcopy(v)
        w['u'].append(dict(i=rel, k=7, s='Rule Q-8 and filing F-17 relate as amended rule and prior filing.', m=0, c='', d=[], b=[9, 10], e=['s4'], q=0, r=''))
        C.validate(w, SOURCE, TABLE)
        w['u'][-1]['b'] = [9]
        self.assertTrue(check(w, 'relationship members'))
        w = copy.deepcopy(v); w['u'][0]['b'] = [2]
        self.assertTrue(check(w, 'members on nonrelationship'))


class SemanticVersusStructural(unittest.TestCase):

    def test_all_semantic_negatives_pass_the_structural_validator(self):
        '''validate() is semantics-blind by design. Every authored negative must pass it and
        round-trip. Rejecting them is independent review work; this asserts no structural catch.'''
        negatives = F.semantic_negative_controls()
        self.assertEqual(len(negatives), 5)
        for name, v in negatives.items():
            with self.subTest(name=name):
                exp = C.expand(v, SOURCE, TABLE)
                self.assertEqual(C.contract(exp, SOURCE, TABLE), v)
                self.assertEqual(exp['source_inventory_completeness'], 'unverified')


class DeadlineDimensions(unittest.TestCase):

    def test_missing_present_ambiguous_dimensions_and_silent_drop(self):
        units = by_id(expanded())
        missing = units[1]
        self.assertEqual((missing['modality'], missing['uncertainty']), ('unknown', 'source_ambiguous'))
        for token in ('clock unknown', 'timezone unknown', 'receipt-versus-dispatch unknown'):
            self.assertIn(token, missing['applicability'])
        self.assertIsNone(CLOCK.search(quotes(missing)))
        present = units[3]
        self.assertEqual((present['modality'], present['uncertainty']), ('mandatory', 'none'))
        for token in ('5 p.m.', 'Eastern'):
            self.assertIn(token, present['applicability'])
            self.assertIn(token, quotes(present))
        self.assertIn('receipt', present['applicability'])
        self.assertIn('received', quotes(present))
        ambiguous = units[20]
        self.assertEqual(ambiguous['uncertainty'], 'source_ambiguous')
        self.assertTrue(ambiguous['uncertainty_reason'].strip())
        self.assertIn('12:00 or 13:00', ambiguous['applicability'])
        self.assertIn('12:00 or 13:00', quotes(ambiguous))
        self.assertIn('unknown', ambiguous['applicability'])
        self.assertIn('dispatch', units[7]['applicability'])
        self.assertIn('dispatch', quotes(units[7]))
        self.assertIn('not applicable', units[19]['applicability'])
        self.assertTrue(all(date_only_dims_explicit(u) for u in units.values()))
        neg = by_id(C.expand(F.semantic_negative_controls()['silently_missing_deadline_dimensions'], SOURCE, TABLE))[1]
        self.assertEqual((neg['applicability'], neg['uncertainty'], neg['modality']), ('', 'none', 'advisory'))
        self.assertFalse(date_only_dims_explicit(neg))
        self.assertFalse(force_is_justified(neg))


class AffectedRuleVersusHistoricalFiling(unittest.TestCase):

    def test_affected_rule_and_historical_filing_stay_distinct_on_one_broad_span(self):
        units = by_id(expanded())
        transitions = [u for u in units.values() if u['kind'] == 'rule_transition']
        self.assertEqual(len(transitions), 1)
        t = transitions[0]
        deps = [units[i] for i in t['required_unit_ids']]
        self.assertTrue(all(d['kind'] == 'identity' for d in deps))
        affected = [d for d in deps if 'Q-8' in d['assertion']]
        historical = [d for d in deps if 'F-17' in d['assertion']]
        self.assertEqual((len(affected), len(historical)), (1, 1))
        self.assertIn('Affected', affected[0]['assertion'])
        self.assertIn('Historical', historical[0]['assertion'])
        self.assertIn('Q-8', t['assertion'])
        self.assertIn('F-17', t['assertion'])
        dated = [u for u in units.values() if u['kind'] == 'timing' and '2029' in u['assertion']]
        self.assertEqual(len(dated), 2)
        for u in dated:
            self.assertEqual(u['required_unit_ids'], [historical[0]['id']])
            self.assertIn('F-17', u['assertion'])
            self.assertNotIn('Q-8', u['assertion'])
        self.assertEqual({e['span_id'] for u in [t] + deps + dated for e in u['evidence']}, {'s4'})

    def test_misattributed_transition_is_structurally_valid_and_separately_reviewable(self):
        exp = C.expand(F.semantic_negative_controls()['historical_filing_replaces_affected_rule'], SOURCE, TABLE)
        t = [u for u in exp['units'] if u['kind'] == 'rule_transition'][0]
        self.assertNotIn('Q-8', t['assertion'])
        self.assertIn('F-17', t['assertion'])
        # Q-8 is still recoverable from its identity unit: the defect is the transition claim, not loss.
        self.assertTrue(recoverable(exp, 's4', 'Q-8'))
        self.assertIn(9, t['required_unit_ids'])


class RecoverabilityAndDecomposition(unittest.TestCase):

    def test_bundled_facts_remain_recoverable_with_fewer_units(self):
        base = expanded()
        neg = C.expand(F.semantic_negative_controls()['independently_lossy_facts_bundled'], SOURCE, TABLE)
        for needle in ('Alder City', 'North Province'):
            self.assertTrue(recoverable(base, 's5', needle))
            self.assertTrue(recoverable(neg, 's5', needle))
        s5_units = lambda exp: sum(cites(u, 's5') for u in exp['units'])
        # Completeness comparison retains both facts; only atomicity, a prompt-level requirement, differs.
        self.assertEqual((s5_units(base), s5_units(neg)), (2, 1))
        self.assertEqual(len(neg['units']), len(base['units']) - 1)

    def test_span_coverage_does_not_prove_fact_coverage(self):
        base = expanded()
        neg = C.expand(F.semantic_negative_controls()['background_dropped_but_all_spans_still_cited'], SOURCE, TABLE)
        all_spans = {row[0] for row in TABLE['rows']}
        self.assertEqual(cited_spans(base), all_spans)
        self.assertEqual(cited_spans(neg), all_spans)
        self.assertTrue(recoverable(base, 's8', '1964'))
        self.assertFalse(recoverable(neg, 's8', '1964'))
        self.assertNotIn(18, by_id(neg))


class AmbiguousForce(unittest.TestCase):

    def test_contested_force_with_reason_accepted_unsupported_certainty_flagged(self):
        units = by_id(expanded())
        self.assertTrue(all(force_is_justified(u) for u in units.values()))
        self.assertEqual(units[2]['modality'], 'unknown')
        self.assertEqual(units[16]['modality'], 'advisory')
        self.assertIsNotNone(MODAL.search(quotes(units[16])))
        # Contested alternative reading with explicit uncertainty and reason is admissible.
        v = fixture()
        v['u'][1].update(m=1, q=1, r='Imperative read as mandatory; source states no consequence or exception.')
        contested = by_id(C.expand(v, SOURCE, TABLE))[2]
        self.assertEqual((contested['modality'], contested['uncertainty']), ('mandatory', 'source_ambiguous'))
        self.assertTrue(force_is_justified(contested))
        # The negative is flagged for certainty without support, not for choosing mandatory.
        neg = by_id(C.expand(F.semantic_negative_controls()['unsupported_force_certainty'], SOURCE, TABLE))[2]
        self.assertEqual((neg['modality'], neg['uncertainty']), ('mandatory', 'none'))
        self.assertIsNone(MODAL.search(quotes(neg)))
        self.assertFalse(force_is_justified(neg))


if __name__ == '__main__':
    unittest.main()
