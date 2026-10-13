"""Independent adversarial suite for the r16.w1 wire codec (DESIGN.md, frozen 2026-10-13).

Written BLIND: protocol/wire.py was not read. Every expected value is derived from the
frozen r15.1 ``compact.py`` (loaded by path), the unchanged R14 ``common.py`` checker,
the pinned ``design/schema.draft.json`` and the text of ``design/DESIGN.md``.
Run with ``python3 -I -S -B -m unittest`` from any directory, or ``python3 -I -S -B <this file>``.
If ``protocol/wire.py`` is absent every codec test skips; the reference self-tests still run.
"""
import copy
import hashlib
import importlib.util
import json
import traceback
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent
BENCH = ROUND.parent
R15 = BENCH / 'round15-condition-preservation' / 'protocol-revised'
R14_COMMON = BENCH / 'round14-semantic-contract' / 'runtime' / 'common.py'
DRAFT = ROUND / 'design' / 'schema.draft.json'
WIRE_PATH = ROUND / 'protocol' / 'wire.py'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R = load('r15_reference_compact', R15 / 'compact.py')          # frozen r15.1, the oracle
C14 = load('r14_reference_common', R14_COMMON)                 # unchanged checker
WIRE = None
WIRE_IMPORT_ERROR = None
if WIRE_PATH.is_file():
    try:
        WIRE = load('r16_wire_under_test', WIRE_PATH)
    except BaseException:  # an import failure of an existing wire.py is a defect, not a skip
        WIRE_IMPORT_ERROR = traceback.format_exc()

SKIP_REASON = ('protocol/wire.py not present yet' if not WIRE_PATH.is_file()
               else 'protocol/wire.py failed to import; see WireModuleTests')
needs_wire = unittest.skipIf(WIRE is None, SKIP_REASON)

# ---------------------------------------------------------------------------
# Authored fixtures (same content as the frozen r15.1 fictional controls; re-authored
# here so this file never imports the protocol directory's helper module).
# ---------------------------------------------------------------------------
LONG = ('Registered applicants whose independently verified annual report includes every required attachment, '
        'whose signature is witnessed by an authorized officer, whose renewal remains pending during the announced review period, '
        'and whose nominated representative retains written authority for this application, '
        'with each separately identified annex retained in its original language and supplied with the approved explanatory statement, '
        'subject to continuing compliance with the published accessibility arrangements and prior written confirmation of the review location, '
        'except applicants whose license was suspended after notice unless the review panel has issued a written stay preserving eligibility.')
SOURCE = ('The office approves permits only if residents AND either owners OR tenants, except banned applicants unless appeal granted.\n'
          'Qualification scope not identified: ' + LONG + '\r\n'
          'Applicants must comply with section Delta; governing content not supplied.\n'
          'Applications must be received by 16:00 UTC on February 8, 2037.\n'
          'Send remarks by March 9, 2037.\n'
          'Arrive in person by 09:00 UTC on May 1, 2037.\n'
          'Requests due April 3, 2037; clock 12:00 or 13:00 UTC, unresolved; dispatch controls timeliness.\n'
          'head tail head tail head tail\n'
          'Unlabeled Ω é 🫧 background.')
TABLE = R.span_table(SOURCE)
FRAG_KEYS = ['a', 'h', 'ho', 'z', 't', 'to']


def frag(sid, head, tail=None, ho=1, to=1, end=None):
    return [sid, head, ho, end or sid, tail if tail is not None else head, to]


def unit(i=1, k=6, s='The office approves permits.', m=0, p=0, y=None, d=None, e=None, q=0, r=''):
    return dict(i=i, k=k, s=s, m=m, p=p, y=y, d=d or [], b=[], e=e or ['s1'], q=q, r=r)


def node(i, op='L', children=None, x=None, q=0, r=''):
    return dict(i=i, o=op, a=children or [], x=x if x is not None else [frag('s1', 'residents')], g='', q=q, r=r)


def link(u, n, w='qual', x=None, q=0, r=''):
    return dict(u=u, w=w, n=n, x=x or [], q=q, r=r)


def dim(state='absent', x=None, reason=''):
    return dict(s=state, x=x or [], r=reason)


def envelope(source, units, nodes=None, links=None, table=None):
    table = table or R.span_table(source)
    return dict(v=R.VERSION, h=R.source_hash(source), t=R.digest(table), u=units, g=nodes or [], l=links or [], z='END')


def fixture():
    units = [unit(p=2, q=1, r='Full qualification scope is unresolved; explicit only-if condition retained.'),
             unit(2, s='Applicants must comply with section Delta.', m=1, p=2, e=['s3'], q=2, r='Governing reference content not supplied.')]
    y = dict(c=dim('stated', [frag('s4', '16:00')]), z=dim('stated', [frag('s4', 'UTC')]), b=dim('stated', [frag('s4', 'received')]))
    units.append(unit(3, k=3, s='Applications deadline date is February 8, 2037.', m=1, e=['s4'], y=y))
    units.append(unit(4, k=3, s='Remarks deadline date is March 9, 2037.', m=5, e=['s5'], q=1, r='Clock, zone, timeliness basis and directive force not stated.', y=dict(c=dim(), z=dim(), b=dim())))
    y = dict(c=dim('stated', [frag('s6', '09:00')]), z=dim('stated', [frag('s6', 'UTC')]), b=dim('na', [frag('s6', 'Arrive in person')], 'In-person arrival, not receipt or dispatch.'))
    units.append(unit(5, k=3, s='Arrival deadline date is May 1, 2037.', e=['s6'], y=y))
    y = dict(c=dim('ambiguous', [frag('s7', '12:00 or 13:00')], 'Notice leaves alternative clocks unresolved.'), z=dim('stated', [frag('s7', 'UTC')]), b=dim('stated', [frag('s7', 'dispatch')]))
    units.append(unit(6, k=3, s='Requests deadline date is April 3, 2037.', e=['s7'], q=1, r='Cutoff clock has unresolved alternatives.', y=y))
    units.append(unit(7, k=8, s='Unlabeled background function remains unknown.', e=['s9'], q=3, r='Function not stated.'))
    nodes = [node('c1', 'EXC', ['c2', 'c5'], [frag('s1', 'except')]), node('c2', 'AND', ['c3', 'c4'], [frag('s1', 'AND')]),
             node('c3', x=[frag('s1', 'residents')]), node('c4', 'OR', ['c6', 'c7'], [frag('s1', 'either'), frag('s1', 'OR')]),
             node('c5', 'EXC', ['c8', 'c9'], [frag('s1', 'unless')]), node('c6', x=[frag('s1', 'owners')]), node('c7', x=[frag('s1', 'tenants')]),
             node('c8', x=[frag('s1', 'banned applicants')]), node('c9', x=[frag('s1', 'appeal granted')]),
             node('c10', x=[frag('s2', LONG[:40], LONG[-40:])], q=1, r='The full qualification has no stated governed scope.'),
             node('c11', 'R', x=[frag('s3', 'section Delta')], q=2, r='Referenced governing content not supplied.')]
    links = [link(1, 'c1', 'onlyif', [frag('s1', 'only if')]), link(1, 'c10', 'qual', q=1, r='Scope is unresolved; no applicability logic inferred.'), link(2, 'c11', 'if')]
    return envelope(SOURCE, units, nodes, links)


def opaque_fixture():
    """A clause-only inventory: L/R leaves, no operator nodes, no children."""
    units = [unit(p=1), unit(2, s='Applicants must comply with section Delta.', m=1, p=2, e=['s3'], q=2, r='Governing reference content not supplied.')]
    nodes = [node('c1', x=[frag('s1', 'only if', 'appeal granted')]), node('c2', 'R', x=[frag('s3', 'section Delta')], q=2, r='Referenced governing content not supplied.')]
    links = [link(1, 'c1', 'onlyif'), link(2, 'c2', 'if')]
    return envelope(SOURCE, units, nodes, links)


def chain(depth, terminal_link='obj'):
    nodes = [dict(i=f'c{i}', o='NOT', a=[f'c{i + 1}'], x=[], g='', q=0, r='') for i in range(1, depth)] + [node(f'c{depth}')]
    return envelope(SOURCE, [unit()], nodes, [link(1, 'c1', terminal_link)])


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def frozen_fixtures():
    """(name, compact, source, table) for every valid frozen r15.1 fixture."""
    out = [('positive.json', load_json(R15 / 'fixtures' / 'positive.json'), SOURCE, TABLE)]
    for name, value in load_json(R15 / 'fixtures' / 'semantic-negatives.json').items():
        out.append(('semantic-negatives/' + name, value, SOURCE, TABLE))
    for name in ['long_disjoint1', 'long_disjoint8', 'long_disjoint16', 'long_shared8', 'long_shared64']:
        source = (R15 / 'fixtures' / f'{name}-source.txt').read_text(encoding='utf-8')
        out.append((name + '-graph.json', load_json(R15 / 'fixtures' / f'{name}-graph.json'), source, R.span_table(source)))
    out.append(('authored/fixture', fixture(), SOURCE, TABLE))
    out.append(('authored/opaque', opaque_fixture(), SOURCE, TABLE))
    out.append(('authored/chain12', chain(12), SOURCE, TABLE))
    return out


# ---------------------------------------------------------------------------
# Reference wire mapping, transcribed from DESIGN.md §3 (W1–W3) and §4 (from_wire/to_wire).
# This is the oracle for the codec's shape; it is NOT the implementation.
# ---------------------------------------------------------------------------
WIRE_VERSION = 'r16.w1'


def ref_frag_to_obj(f):
    return dict(zip(FRAG_KEYS, f))


def ref_to_wire(compact):
    w = copy.deepcopy(compact)
    w['v'] = WIRE_VERSION
    for u in w['u']:
        if u['y'] is not None:
            for d in u['y'].values():
                d['x'] = [ref_frag_to_obj(f) for f in d['x']]
        u['y'] = [] if u['y'] is None else [u['y']]
    for item in w['g'] + w['l']:
        item['x'] = [ref_frag_to_obj(f) for f in item['x']]
    return w


def ref_from_wire(wire):
    c = copy.deepcopy(wire)
    c['v'] = R.VERSION
    for u in c['u']:
        y = u['y'][0] if u['y'] else None
        if y is not None:
            for d in y.values():
                d['x'] = [[o[k] for k in FRAG_KEYS] for o in d['x']]
        u['y'] = y
    for item in c['g'] + c['l']:
        item['x'] = [[o[k] for k in FRAG_KEYS] for o in item['x']]
    return c


def span_width(table):
    return max(len(row[0]) for row in table['rows'])


def expected_schema(source, table, profile='full'):
    """design/schema.draft.json instantiated for (source, table): §3 W1–W4 and the opaque note."""
    s = load_json(DRAFT)
    s['properties']['h']['enum'] = [R.source_hash(source)]
    s['properties']['t']['enum'] = [R.digest(table)]
    w = span_width(table)
    unit_schema = s['properties']['u']['items']
    node_schema = s['properties']['g']['items']
    link_schema = s['properties']['l']['items']
    unit_schema['properties']['e']['items']['maxLength'] = w
    frag_schemas = [node_schema['properties']['x']['items'], link_schema['properties']['x']['items']]
    for d in unit_schema['properties']['y']['items']['properties'].values():
        frag_schemas.append(d['properties']['x']['items'])
    for fs in frag_schemas:
        fs['properties']['a']['maxLength'] = w
        fs['properties']['z']['maxLength'] = w
    if profile == 'opaque':
        node_schema['properties']['o']['enum'] = ['L', 'R']
        node_schema['properties']['a']['maxItems'] = 0
    return s


def raw_of(value):
    return R.canonical(value).decode('utf-8')


def schema_depth(n, d=0):
    m = d
    for c in n.get('properties', {}).values():
        m = max(m, schema_depth(c, d + 1))
    if 'items' in n:
        m = max(m, schema_depth(n['items'], d + 1))
    return m


def walk_schema(n, path='$'):
    yield path, n
    for k, c in n.get('properties', {}).items():
        yield from walk_schema(c, path + '.' + k)
    if 'items' in n:
        yield from walk_schema(n['items'], path + '[]')


def code_of(exc):
    code = getattr(exc, 'code', None)
    return {code, str(exc)}


# Host-only negatives: pass the wire schema, must be rejected by r15.1 validate with this code
# (DESIGN §4 T3, §5 rows 8, 11, 16, 21). Each entry mutates a compact fixture.
def _set_node3(v, nid):
    v['g'][2]['i'] = nid
    v['g'][1]['a'] = [nid, 'c4']


HOST_ONLY = [
    ('node_id_c0', lambda v: _set_node3(v, 'c0'), 'node_id'),
    ('node_id_leading_zero_c01', lambda v: _set_node3(v, 'c01'), 'node_id'),
    ('node_id_c007', lambda v: _set_node3(v, 'c007'), 'node_id'),
    ('node_id_c401', lambda v: _set_node3(v, 'c401'), 'node_id_range'),
    ('node_id_cyrillic_es', lambda v: _set_node3(v, 'с1'), 'node_id'),
    ('node_id_arabic_indic_digit', lambda v: _set_node3(v, 'c٣'), 'node_id'),
    ('node_id_upper_C1', lambda v: _set_node3(v, 'C1'), 'node_id'),
    ('node_id_c-1', lambda v: _set_node3(v, 'c-1'), 'node_id'),
    ('child_id_c0_only_in_a', lambda v: v['g'][1].update(a=['c0', 'c4']), 'node_id'),
    ('link_n_c0', lambda v: v['l'][2].update(n='c0'), 'node_id'),
    ('link_n_c401', lambda v: v['l'][2].update(n='c401'), 'node_id_range'),
    ('evidence_s0_absent', lambda v: v['u'][0].update(e=['s0']), 'evidence_id'),
    ('evidence_cyrillic_dze', lambda v: v['u'][0].update(e=['ѕ1']), 'evidence_id'),
    ('evidence_fullwidth_digit', lambda v: v['u'][0].update(e=['s１']), 'evidence_id'),
    ('evidence_upper_S1', lambda v: v['u'][0].update(e=['S1']), 'evidence_id'),
    ('fragment_a_s0_absent', lambda v: v['g'][2]['x'][0].__setitem__(0, 's0'), 'fragment_span'),
    ('fragment_z_cyrillic', lambda v: v['g'][2]['x'][0].__setitem__(3, 'ѕ1'), 'fragment_span'),
    ('fragment_a_z_swapped_rows', lambda v: v['g'][2].update(x=[frag('s2', 'Qualification', 'The office', end='s1')]), 'fragment_row_order'),
    ('anchor_whitespace_head', lambda v: v['g'][2]['x'][0].__setitem__(1, ' '), 'text_bound'),
    ('anchor_whitespace_tail', lambda v: v['g'][2]['x'][0].__setitem__(4, '\t'), 'text_bound'),
    ('assertion_blank', lambda v: v['u'][0].update(s='   '), 'text_bound'),
    ('head_occurrence_huge', lambda v: v['g'][2]['x'][0].__setitem__(2, 10 ** 30), 'head_not_found'),
    ('tail_occurrence_huge', lambda v: v['g'][2]['x'][0].__setitem__(5, 10 ** 30), 'tail_not_found'),
    ('head_nfc_variant_not_normalized', lambda v: v['u'][6].update(e=['s9']) or v['g'][2].update(x=[frag('s9', 'é')]), 'head_not_found'),
    ('deadline_on_nondeadline_kind', lambda v: v['u'][0].update(y=copy.deepcopy(v['u'][2]['y'])), 'deadline_kind'),
    ('duplicate_unit_id', lambda v: v['u'][6].update(i=1), 'duplicate_unit'),
    ('duplicate_node_id', lambda v: v['g'][2].update(i='c6'), 'duplicate_node'),
    ('uncertainty_reason_mismatch', lambda v: v['u'][0].update(q=1, r=''), 'uncertainty_reason'),
    ('qual_requires_p2', lambda v: v['u'][0].update(p=1), 'qual_requires_unknown_scope'),
    ('dimension_na_only_on_b', lambda v: v['u'][4]['y']['c'].update(s='na', r='Not applicable'), 'dimension_na_basis_only'),
    ('fragment_order_overlap', lambda v: v['g'][3].update(x=[frag('s1', 'OR'), frag('s1', 'either')]), 'fragment_order_overlap'),
]

# Checker-caught negatives applied to the WIRE object: the schema must report at least one error
# (DESIGN §4 T3, §5 rows 4–6, 13, 20).
def _frag0(v):
    return v['g'][2]['x'][0]


CHECKER_CAUGHT = [
    ('fragment_tuple_shape', lambda w: v_set(w, ['g', 2, 'x', 0], ['s1', 'residents', 1, 's1', 'residents', 1])),
    ('fragment_missing_to', lambda w: _frag0(w).pop('to')),
    ('fragment_extra_key', lambda w: _frag0(w).update(extra=1)),
    ('fragment_ho_zero', lambda w: _frag0(w).update(ho=0)),
    ('fragment_ho_negative', lambda w: _frag0(w).update(ho=-1)),
    ('fragment_ho_bool', lambda w: _frag0(w).update(ho=True)),
    ('fragment_ho_float', lambda w: _frag0(w).update(ho=1.0)),
    ('fragment_ho_string', lambda w: _frag0(w).update(ho='1')),
    ('fragment_to_bool', lambda w: _frag0(w).update(to=True)),
    ('fragment_head_empty', lambda w: _frag0(w).update(h='')),
    ('fragment_head_49_codepoints', lambda w: _frag0(w).update(h='x' * 49)),
    ('fragment_a_too_long', lambda w: _frag0(w).update(a='s100')),
    ('fragment_a_too_short', lambda w: _frag0(w).update(a='s')),
    ('fragment_a_integer', lambda w: _frag0(w).update(a=1)),
    ('y_null', lambda w: w['u'][2].update(y=None)),
    ('y_object_not_list', lambda w: w['u'][2].update(y=w['u'][2]['y'][0])),
    ('y_two_items', lambda w: w['u'][2].update(y=w['u'][2]['y'] * 2)),
    ('y_list_of_null', lambda w: w['u'][2].update(y=[None])),
    ('y_list_of_empty_object', lambda w: w['u'][2].update(y=[{}])),
    ('y_deadline_extra_key', lambda w: w['u'][2]['y'][0].update(d=w['u'][2]['y'][0]['c'])),
    ('y_deadline_missing_b', lambda w: w['u'][2]['y'][0].pop('b')),
    ('dimension_state_not_enum', lambda w: w['u'][2]['y'][0]['c'].update(s='unknown')),
    ('dimension_five_fragments', lambda w: w['u'][2]['y'][0]['c'].update(x=w['u'][2]['y'][0]['c']['x'] * 5)),
    ('version_r15_1', lambda w: w.update(v='r15.1')),
    ('version_missing', lambda w: w.pop('v')),
    ('envelope_extra_key', lambda w: w.update(extra=0)),
    ('terminal_marker_wrong', lambda w: w.update(z='end')),
    ('source_hash_wrong', lambda w: w.update(h='0' * 64)),
    ('table_digest_wrong', lambda w: w.update(t='0' * 64)),
    ('unit_i_bool', lambda w: w['u'][0].update(i=True)),
    ('unit_k_float', lambda w: w['u'][0].update(k=1.0)),
    ('unit_k_out_of_range', lambda w: w['u'][0].update(k=9)),
    ('unit_extra_key', lambda w: w['u'][0].update(c='legacy')),
    ('unit_missing_y', lambda w: w['u'][0].pop('y')),
    ('unit_s_empty', lambda w: w['u'][0].update(s='')),
    ('unit_e_empty', lambda w: w['u'][0].update(e=[])),
    ('unit_e_seven', lambda w: w['u'][0].update(e=['s1', 's2', 's3', 's4', 's5', 's6', 's7'])),
    ('unit_e_id_too_long', lambda w: w['u'][0].update(e=['s100'])),
    ('unit_d_bool_member', lambda w: w['u'][0].update(d=[True])),
    ('node_id_too_long_c1000', lambda w: _set_node3(w, 'c1000')),
    ('node_id_too_short', lambda w: _set_node3(w, 'c')),
    ('node_operator_not_enum', lambda w: w['g'][0].update(o='XOR')),
    ('node_nine_children', lambda w: w['g'][0].update(a=[f'c{i}' for i in range(2, 11)])),
    ('node_nine_fragments', lambda w: w['g'][2].update(x=w['g'][2]['x'] * 9)),
    ('link_role_not_enum', lambda w: w['l'][0].update(w='normative')),
    ('link_three_fragments', lambda w: w['l'][0].update(x=w['l'][0]['x'] * 3)),
    ('link_u_zero', lambda w: w['l'][0].update(u=0)),
    ('units_empty', lambda w: w.update(u=[])),
    ('units_161', lambda w: w.update(u=[dict(unit(i), y=[]) for i in range(1, 162)])),
    ('reason_181', lambda w: w['u'][0].update(r='x' * 181)),
    ('gloss_121', lambda w: w['g'][0].update(g='x' * 121)),
]


def v_set(obj, path, value):
    for key in path[:-1]:
        obj = obj[key]
    obj[path[-1]] = value


# ---------------------------------------------------------------------------
# Reference self-tests: these run even without wire.py and prove the oracle is coherent.
# ---------------------------------------------------------------------------
class ReferenceSelfTests(unittest.TestCase):
    """Oracle coherence (DESIGN §1, §4, §5). Failures here mean the suite, not the codec, is wrong."""

    def test_authored_fixture_matches_frozen_positive_and_expanded(self):
        """§4: expected values come from the pinned r15.1 fixtures (positive.json, expanded.json)."""
        positive = load_json(R15 / 'fixtures' / 'positive.json')
        self.assertEqual(R.canonical(fixture()), R.canonical(positive))
        self.assertEqual(R.canonical(R.expand(copy.deepcopy(positive), SOURCE, TABLE)), R.canonical(load_json(R15 / 'fixtures' / 'expanded.json')))

    def test_all_reference_fixtures_validate_and_wire_roundtrip(self):
        """§4 losslessness argument: ref_from_wire(ref_to_wire(C)) == C and the wire is schema-clean."""
        for name, compact, source, table in frozen_fixtures():
            with self.subTest(fixture=name):
                R.validate(copy.deepcopy(compact), source, table)
                wire = ref_to_wire(compact)
                self.assertEqual(R.canonical(ref_from_wire(wire)), R.canonical(compact))
                self.assertEqual(wire['v'], WIRE_VERSION)
                schema = expected_schema(source, table)
                C14.check_schema(schema)
                self.assertEqual(C14.schema_errors(wire, schema), [])

    def test_draft_schema_figures_from_design(self):
        """§6/§7: draft is checker-accepted, depth 8, 13 object schemas, 73 properties, 5,085 bytes."""
        draft = load_json(DRAFT)
        C14.check_schema(draft)
        self.assertEqual(schema_depth(draft), 8)
        objects = [n for _, n in walk_schema(draft) if n.get('type') == 'object']
        self.assertEqual(len(objects), 13)
        self.assertEqual(sum(len(n['properties']) for n in objects), 73)
        self.assertEqual(len(C14.encode(draft)), 5085)
        self.assertEqual(len(R.canonical(draft)), 5085)
        self.assertEqual(hashlib.sha256(DRAFT.read_bytes()).hexdigest(), load_json(ROUND / 'design' / 'READY.json')['sha256']['schema.draft.json'])

    def test_host_only_negatives_pass_schema_but_fail_r15_1_with_claimed_code(self):
        """§5 rows 8/11/16/21: these must slip past the checker and be caught by r15.1 validate."""
        schema = expected_schema(SOURCE, TABLE)
        for name, mutate, code in HOST_ONLY:
            with self.subTest(case=name):
                v = fixture()
                mutate(v)
                self.assertEqual(C14.schema_errors(ref_to_wire(v), schema), [], 'expected the wire schema to accept this case')
                with self.assertRaises(ValueError) as cm:
                    R.validate(v, SOURCE, TABLE)
                self.assertEqual(str(cm.exception), code)

    def test_checker_caught_negatives_are_rejected_by_expected_schema(self):
        """§4 T3: every listed wire negative yields a schema error from the unchanged checker."""
        schema = expected_schema(SOURCE, TABLE)
        for name, mutate in CHECKER_CAUGHT:
            with self.subTest(case=name):
                w = ref_to_wire(fixture())
                mutate(w)
                self.assertNotEqual(C14.schema_errors(w, schema), [])

    def test_occurrence_oracle_values(self):
        """SPEC fragment rule: head occurrence then conditional tail; literal offsets on row s8."""
        s8 = TABLE['rows'][7][1]
        self.assertEqual(SOURCE[s8:s8 + 29], 'head tail head tail head tail')
        cases = {(2, 1): (s8 + 10, 'head tail'), (1, 3): (s8, 'head tail head tail head tail'), (3, 1): (s8 + 20, 'head tail')}
        for (ho, to), (start, text) in cases.items():
            ev = R.resolve_fragment(['s8', 'head', ho, 's8', 'tail', to], SOURCE, TABLE)
            self.assertEqual((ev['start'], ev['text']), (start, text))


# ---------------------------------------------------------------------------
# Codec tests (skip cleanly when wire.py is absent)
# ---------------------------------------------------------------------------
class WireModuleTests(unittest.TestCase):
    def test_wire_module_imports_or_is_absent(self):
        """Interface: protocol/wire.py must import under -I -S -B by path with no side effects."""
        if not WIRE_PATH.is_file():
            self.skipTest(SKIP_REASON)
        self.assertIsNone(WIRE_IMPORT_ERROR, WIRE_IMPORT_ERROR)
        for name in ['WireError', 'to_compact', 'from_compact', 'schema', 'validate_response', 'build']:
            self.assertTrue(hasattr(WIRE, name), name)
        self.assertTrue(issubclass(WIRE.WireError, Exception))


def expanded_of(result):
    """validate_response may return the expanded record or {wire, compact, expanded} (see EXPECTATIONS.md)."""
    if isinstance(result, dict) and 'expanded' in result and 'schema_version' not in result:
        return result['expanded']
    return result


def compact_of(result):
    if isinstance(result, dict) and 'compact' in result and 'schema_version' not in result:
        return result['compact']
    return None


class WireBase(unittest.TestCase):
    def setUp(self):
        self.c = fixture()
        self.w = ref_to_wire(self.c)
        self.schema = expected_schema(SOURCE, TABLE)

    def assertWireError(self, fn, *args, **kwargs):
        with self.assertRaises(WIRE.WireError) as cm:
            fn(*args, **kwargs)
        self.assertIsInstance(cm.exception.code, str)
        self.assertTrue(cm.exception.code)
        return cm.exception

    def assertR15Code(self, code, fn, *args, **kwargs):
        with self.assertRaises(Exception) as cm:
            fn(*args, **kwargs)
        self.assertIn(code, code_of(cm.exception), f'expected r15.1 code {code!r}, got {cm.exception!r}')
        return cm.exception

    def respond(self, wire_or_raw, finish='stop', source=SOURCE, table=TABLE, profile='full'):
        raw = wire_or_raw if isinstance(wire_or_raw, str) else raw_of(wire_or_raw)
        return WIRE.validate_response(raw, finish, source, table, profile)

    def expanded(self, *args, **kwargs):
        return expanded_of(self.respond(*args, **kwargs))


@needs_wire
class CodecShapeTests(WireBase):
    """Family A: exact wire shape and bijection (DESIGN §3 W1–W3, §4 T1)."""

    def test_from_compact_matches_design_wire_shape(self):
        """§3: four syntactic changes only; every other key, value, order and ID string identical."""
        for name, compact, source, table in frozen_fixtures():
            with self.subTest(fixture=name):
                self.assertEqual(R.canonical(WIRE.from_compact(compact)), R.canonical(ref_to_wire(compact)))

    def test_to_compact_inverts_from_compact_bijectively(self):
        """§4 T1: canonical(from_wire(to_wire(C))) == canonical(C) and to_wire(from_wire(W)) == W."""
        for name, compact, source, table in frozen_fixtures():
            with self.subTest(fixture=name):
                wire = WIRE.from_compact(compact)
                back = WIRE.to_compact(wire)
                self.assertEqual(R.canonical(back), R.canonical(compact))
                self.assertEqual(back['v'], 'r15.1')
                self.assertEqual(R.canonical(WIRE.from_compact(back)), R.canonical(wire))

    def test_fragment_object_fields_are_positional_by_key_name(self):
        """§3 W2 example: ["s3","Comments must",1,"s4","p.m.",1] <-> {a,h,ho,z,t,to}; key order is irrelevant."""
        tuple_form = ['s8', 'head', 2, 's8', 'tail', 3]
        c = envelope(SOURCE, [unit(p=0)], [node('c1', x=[tuple_form])], [link(1, 'c1', 'obj')])
        w = WIRE.from_compact(c)
        self.assertEqual(w['g'][0]['x'][0], dict(a='s8', h='head', ho=2, z='s8', t='tail', to=3))
        reordered = copy.deepcopy(w)
        reordered['g'][0]['x'][0] = {k: w['g'][0]['x'][0][k] for k in ['to', 't', 'z', 'ho', 'h', 'a']}
        self.assertEqual(WIRE.to_compact(reordered)['g'][0]['x'][0], tuple_form)

    def test_y_empty_list_is_null_and_singleton_is_the_deadline(self):
        """§3 W3 + design note: y:[] <-> null; [Y] <-> Y; an all-absent deadline is NOT collapsed to []."""
        w = WIRE.from_compact(self.c)
        self.assertEqual([u['y'] for u in w['u'] if u['k'] != 3], [[], [], []])
        self.assertEqual(len(w['u'][3]['y']), 1)
        self.assertEqual(w['u'][3]['y'][0], dict(c=dim(), z=dim(), b=dim()))
        c = WIRE.to_compact(w)
        self.assertIsNone(c['u'][0]['y'])
        self.assertEqual(c['u'][3]['y'], dict(c=dim(), z=dim(), b=dim()))
        self.assertEqual(c['u'][2]['y']['c']['x'], [frag('s4', '16:00')])

    def test_to_compact_rejects_structural_wire_violations(self):
        """§4 from_wire requires: closed envelope, v==r16.w1, lists, y list <=1, {c,z,b}, {a,h,ho,z,t,to}."""
        cases = {
            'version_r15_1': lambda w: w.update(v='r15.1'),
            'version_missing': lambda w: w.pop('v'),
            'envelope_extra_key': lambda w: w.update(extra=1),
            'envelope_missing_l': lambda w: w.pop('l'),
            'envelope_not_dict': lambda w: w.clear() or None,
            'u_not_list': lambda w: w.update(u={}),
            'y_null': lambda w: w['u'][2].update(y=None),
            'y_object': lambda w: w['u'][2].update(y=w['u'][2]['y'][0]),
            'y_two_items': lambda w: w['u'][2].update(y=w['u'][2]['y'] * 2),
            'y_list_of_null': lambda w: w['u'][2].update(y=[None]),
            'y_item_missing_b': lambda w: w['u'][2]['y'][0].pop('b'),
            'y_item_extra_key': lambda w: w['u'][2]['y'][0].update(d=1),
            'fragment_tuple': lambda w: v_set(w, ['g', 2, 'x', 0], ['s1', 'residents', 1, 's1', 'residents', 1]),
            'fragment_missing_ho': lambda w: _frag0(w).pop('ho'),
            'fragment_extra_key': lambda w: _frag0(w).update(n=1),
            'fragment_string': lambda w: v_set(w, ['g', 2, 'x', 0], 'residents'),
            'deadline_fragment_tuple': lambda w: v_set(w, ['u', 2, 'y', 0, 'c', 'x', 0], frag('s4', '16:00')),
            'link_fragment_extra_key': lambda w: w['l'][0]['x'][0].update(q=0),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                w = ref_to_wire(fixture())
                mutate(w)
                self.assertWireError(WIRE.to_compact, w)

    def test_to_compact_never_coerces_scalar_types(self):
        """§4: decode never repairs or coerces. A bool/float/str in an integer slot is rejected or passed through untouched."""
        for name, value in [('bool', True), ('float', 1.0), ('string', '1'), ('neg', -1), ('big', 10 ** 30)]:
            with self.subTest(case=name):
                w = ref_to_wire(fixture())
                _frag0(w)['ho'] = value
                try:
                    c = WIRE.to_compact(w)
                except WIRE.WireError:
                    continue
                got = c['g'][2]['x'][0][2]
                self.assertIs(type(got), type(value))
                self.assertEqual(got, value)

    def test_from_compact_is_pure_structure_even_for_semantically_invalid_compacts(self):
        """§4 T2: an invalid r15.1 fixture still maps to a wire and keeps its r15.1 error code after to_compact."""
        for name, compact, code in [('depth13', chain(13), 'graph_depth'),
                                    ('units160', envelope(SOURCE, [unit(i) for i in range(1, 161)]), 'capacity_review_u'),
                                    ('nodes400', envelope(SOURCE, [unit()], [node(f'c{i}') for i in range(1, 401)], [link(1, f'c{i}', 'regardless') for i in range(1, 401)]), 'capacity_review_g')]:
            with self.subTest(case=name):
                self.assertR15Code(code, R.validate, copy.deepcopy(compact), SOURCE, TABLE)
                wire = WIRE.from_compact(compact)
                self.assertEqual(R.canonical(wire), R.canonical(ref_to_wire(compact)))
                self.assertR15Code(code, R.validate, WIRE.to_compact(wire), SOURCE, TABLE)

    def test_wire_error_carries_a_code(self):
        """Interface: WireError(Exception) with .code."""
        exc = self.assertWireError(WIRE.to_compact, dict(self.w, v='r15.1'))
        self.assertIsInstance(exc, Exception)
        self.assertIsInstance(exc.code, str)


@needs_wire
class AliasingTests(WireBase):
    """Family B: fresh objects, no aliasing (DESIGN §4 T5)."""

    def test_from_compact_returns_fresh_objects(self):
        """§4 T5 / 'fresh objects, no aliasing'."""
        original = copy.deepcopy(self.c)
        w = WIRE.from_compact(self.c)
        w['u'][2]['y'][0]['c']['x'][0]['h'] = 'tampered'
        w['g'][0]['a'].append('c9')
        w['u'][0]['d'].append(2)
        w['l'][0]['x'][0]['a'] = 's9'
        self.assertEqual(self.c, original)
        snapshot = copy.deepcopy(w)
        self.c['g'][0]['x'][0][1] = 'changed'
        self.c['u'][2]['y']['c']['x'][0][1] = 'changed'
        self.c['u'][0]['e'].append('s2')
        self.assertEqual(w, snapshot)

    def test_to_compact_returns_fresh_objects(self):
        """§4: 'all leaf values copied by value (deep copy)'."""
        original = copy.deepcopy(self.w)
        c = WIRE.to_compact(self.w)
        c['g'][0]['x'][0][1] = 'changed'
        c['u'][2]['y']['c']['x'][0][1] = 'changed'
        c['u'][0]['d'].append(2)
        c['g'][0]['a'].reverse()
        self.assertEqual(self.w, original)
        snapshot = copy.deepcopy(c)
        self.w['g'][0]['x'][0]['h'] = 'changed'
        self.w['u'][2]['y'][0]['c']['x'][0]['h'] = 'changed'
        self.w['u'][0]['e'].append('s2')
        self.assertEqual(c, snapshot)

    def test_validate_response_result_parts_do_not_alias(self):
        """§4 T5 on decode_response: mutating compact or expanded must not mutate the other, nor the table."""
        table = copy.deepcopy(TABLE)
        result = self.respond(self.w, table=table)
        expanded = expanded_of(result)
        reference = R.canonical(R.expand(fixture(), SOURCE, TABLE))
        compact = compact_of(result)
        if compact is not None:
            compact['g'][0]['x'][0][1] = 'changed'
            compact['u'][2]['y']['c']['x'][0][1] = 'changed'
            compact['u'][0]['d'].append(9)
        self.assertEqual(R.canonical(expanded), reference)
        expanded['nodes'][0]['evidence'][0]['fragment'][1] = 'changed'
        expanded['units'][2]['deadline']['c']['evidence'][0]['fragment'][1] = 'changed'
        if compact is not None:
            self.assertEqual(compact['g'][0]['x'][0][1], 'changed')
        self.assertEqual(table, TABLE)
        self.assertEqual(R.canonical(expanded_of(self.respond(self.w))), reference)


@needs_wire
class SchemaTests(WireBase):
    """Family C: the wire schema (DESIGN §3 table, §4 T4 lint, §6 provider rules, inventory §3)."""

    def test_full_schema_equals_pinned_draft_instantiated_for_source(self):
        """§3 + schema.draft.json: only h/t enums and the span-ID maxLength W depend on the source."""
        self.assertEqual(WIRE.schema(SOURCE, TABLE), expected_schema(SOURCE, TABLE))
        self.assertEqual(WIRE.schema(SOURCE, TABLE, 'full'), expected_schema(SOURCE, TABLE, 'full'))
        self.assertEqual(len(C14.encode(WIRE.schema(SOURCE, TABLE))), 5085)

    def test_opaque_profile_differs_only_in_operator_enum_and_child_cap(self):
        """§3 'opaque profile': same wire with o enum ["L","R"] and node a maxItems:0."""
        opaque = WIRE.schema(SOURCE, TABLE, 'opaque')
        self.assertEqual(opaque, expected_schema(SOURCE, TABLE, 'opaque'))
        node_schema = opaque['properties']['g']['items']['properties']
        self.assertEqual(node_schema['o']['enum'], ['L', 'R'])
        self.assertEqual(node_schema['a']['maxItems'], 0)
        patched = copy.deepcopy(opaque)
        patched['properties']['g']['items']['properties']['o']['enum'] = R.OPS
        patched['properties']['g']['items']['properties']['a']['maxItems'] = 8
        self.assertEqual(patched, WIRE.schema(SOURCE, TABLE, 'full'))

    def test_unknown_profile_raises_value_error(self):
        """Interface: other profiles raise ValueError."""
        for profile in ['typed', '', None, 'FULL', 'Opaque']:
            with self.subTest(profile=profile):
                with self.assertRaises(ValueError):
                    WIRE.schema(SOURCE, TABLE, profile)

    def test_span_id_width_tracks_the_table_and_node_width_is_fixed(self):
        """§3 W4 (W = longest span ID) and node ID 2..4 regardless of table size."""
        for source, w in [('one row only', 2), ('\n'.join(f'row {i}' for i in range(10)), 3), ('\n'.join(f'row {i}' for i in range(100)), 4), ('\n'.join(f'row {i}' for i in range(1000)), 5)]:
            with self.subTest(width=w):
                table = R.span_table(source)
                s = WIRE.schema(source, table)
                self.assertEqual(s, expected_schema(source, table))
                unit_schema = s['properties']['u']['items']['properties']
                self.assertEqual(unit_schema['e']['items']['maxLength'], w)
                self.assertEqual(unit_schema['e']['items']['minLength'], 2)
                fragment = s['properties']['g']['items']['properties']['x']['items']['properties']
                self.assertEqual((fragment['a']['maxLength'], fragment['z']['maxLength']), (w, w))
                node_schema = s['properties']['g']['items']['properties']
                self.assertEqual((node_schema['i']['minLength'], node_schema['i']['maxLength']), (2, 4))
                self.assertEqual((node_schema['a']['items']['minLength'], node_schema['a']['items']['maxLength']), (2, 4))
                self.assertEqual((s['properties']['l']['items']['properties']['n']['minLength'], s['properties']['l']['items']['properties']['n']['maxLength']), (2, 4))

    def test_schema_binds_source_hash_and_table_digest(self):
        """§5 row 3: h = source SHA-256, t = canonical table digest, single-value enums."""
        s = WIRE.schema(SOURCE, TABLE)
        self.assertEqual(s['properties']['h'], dict(type='string', enum=[R.source_hash(SOURCE)]))
        self.assertEqual(s['properties']['t'], dict(type='string', enum=[R.digest(TABLE)]))
        self.assertEqual(s['properties']['v'], dict(type='string', enum=['r16.w1']))
        self.assertEqual(s['properties']['z'], dict(type='string', enum=['END']))

    def test_schema_lint_closes_the_checker_meta_gap(self):
        """§4 T4 / §8 R4: every node declares a scalar type; objects closed and fully required; no type lists;
        keyword set within the R14 allowlist; checker depth <= 16; no schema-valued additionalProperties."""
        allowed = {'type', 'properties', 'required', 'additionalProperties', 'enum', 'minimum', 'maximum', 'minLength', 'maxLength', 'items', 'minItems', 'maxItems'}
        for profile in ['full', 'opaque']:
            s = WIRE.schema(SOURCE, TABLE, profile)
            C14.check_schema(s)
            self.assertLessEqual(schema_depth(s), 16)
            self.assertNotIn('$schema', s)
            for path, n in walk_schema(s):
                with self.subTest(profile=profile, path=path):
                    self.assertIsInstance(n, dict)
                    self.assertLessEqual(set(n), allowed)
                    self.assertIsInstance(n.get('type'), str, 'every node declares exactly one scalar type')
                    self.assertIn(n['type'], {'object', 'array', 'string', 'integer'})
                    if n['type'] == 'object':
                        self.assertIs(n.get('additionalProperties'), False)
                        self.assertIsInstance(n.get('properties'), dict)
                        self.assertTrue(n['properties'])
                        self.assertEqual(sorted(n.get('required', [])), sorted(n['properties']))
                        self.assertEqual(len(n['required']), len(set(n['required'])))
                    else:
                        self.assertNotIn('properties', n)
                        self.assertNotIn('required', n)
                        self.assertNotIn('additionalProperties', n)
                    if n['type'] == 'array':
                        self.assertIsInstance(n.get('items'), dict, 'items must be a schema object (default {} accepts anything)')
                        self.assertIsInstance(n.get('minItems'), int)
                        self.assertIsInstance(n.get('maxItems'), int)
                        self.assertLessEqual(n['minItems'], n['maxItems'])
                    else:
                        self.assertNotIn('items', n)
                    if n['type'] == 'string':
                        self.assertTrue('enum' in n or ('minLength' in n and 'maxLength' in n))
                        if 'enum' in n:
                            self.assertTrue(all(isinstance(e, str) for e in n['enum']))
                            self.assertEqual(len(n['enum']), len(set(n['enum'])))
                        if 'minLength' in n:
                            self.assertIs(type(n['minLength']), int)
                            self.assertIs(type(n['maxLength']), int)
                            self.assertLessEqual(n['minLength'], n['maxLength'])
                    if n['type'] == 'integer':
                        self.assertIs(type(n.get('minimum')), int)
                        self.assertNotIn('enum', n)
                        if 'maximum' in n:
                            self.assertIs(type(n['maximum']), int)
                            self.assertLessEqual(n['minimum'], n['maximum'])

    def test_provider_rules_depth_and_counts(self):
        """§6 + inventory §3: closed objects, all required, nesting <= 10 (OpenAI), 13 objects / 73 properties / depth 8."""
        s = WIRE.schema(SOURCE, TABLE)
        self.assertEqual(schema_depth(s), 8)
        self.assertLessEqual(schema_depth(s), 10)
        objects = [n for _, n in walk_schema(s) if n.get('type') == 'object']
        self.assertEqual(len(objects), 13)
        self.assertEqual(sum(len(n['properties']) for n in objects), 73)
        self.assertEqual(s['type'], 'object')
        enum_values = sum(len(n['enum']) for _, n in walk_schema(s) if 'enum' in n)
        self.assertLessEqual(enum_values, 1000)

    def test_schema_accepts_every_valid_wire_and_the_draft_is_not_forgotten(self):
        """§4 T1: no false schema rejection on any valid fixture, under the schema the codec itself emits."""
        for name, compact, source, table in frozen_fixtures():
            with self.subTest(fixture=name):
                self.assertEqual(C14.schema_errors(WIRE.from_compact(compact), WIRE.schema(source, table)), [])

    def test_schema_result_is_fresh_per_call(self):
        """§4 T5 analogue: mutating one returned schema must not change the next call's result."""
        first = WIRE.schema(SOURCE, TABLE)
        first['properties']['u']['items']['additionalProperties'] = {}
        first['properties']['v']['enum'].append('r15.1')
        self.assertEqual(WIRE.schema(SOURCE, TABLE), expected_schema(SOURCE, TABLE))


@needs_wire
class PipelineAcceptTests(WireBase):
    """Family D: validate_response on valid wires; byte identity with r15.1 (DESIGN §4 D0–D6, losslessness)."""

    def test_expanded_record_is_byte_identical_to_r15_1(self):
        """§4: E is produced by the unchanged R.expand, so expanded is byte-identical to r15.1 for the same content."""
        for name, compact, source, table in frozen_fixtures():
            with self.subTest(fixture=name):
                expected = R.canonical(R.expand(copy.deepcopy(compact), source, table))
                result = self.respond(ref_to_wire(compact), source=source, table=table)
                self.assertEqual(R.canonical(expanded_of(result)), expected)
                if compact_of(result) is not None:
                    self.assertEqual(R.canonical(compact_of(result)), R.canonical(compact))

    def test_expanded_record_has_no_wire_version_and_keeps_r15_1_flags(self):
        """§5 row 23 and §8 R7/Q5: the expanded record stays round15.expanded-inventory.v2 and never names r16.w1."""
        e = self.expanded(self.w)
        self.assertEqual(e['schema_version'], 'round15.expanded-inventory.v2')
        self.assertNotIn('r16.w1', R.canonical(e).decode('utf-8'))
        self.assertEqual((e['completeness'], e['condition_coverage'], e['semantic_validity'], e['evaluation']), ('unverified', 'unverified', 'unverified', 'not_performed'))
        self.assertIs(e['production_eligible'], False)
        self.assertIs(e['action_ready'], False)
        self.assertEqual(e['evidence_match'], 'exact')
        self.assertEqual(R.canonical(R.contract(copy.deepcopy(e), SOURCE, TABLE)), R.canonical(self.c))

    def test_expanded_fragments_are_tuples_not_objects(self):
        """§4: expansion records the original fragment TUPLE (r15.1 shape), not the wire object."""
        e = self.expanded(self.w)
        self.assertEqual(e['nodes'][0]['evidence'][0]['fragment'], ['s1', 'except', 1, 's1', 'except', 1])
        self.assertEqual(e['units'][2]['deadline']['c']['evidence'][0]['fragment'], ['s4', '16:00', 1, 's4', '16:00', 1])
        self.assertEqual(e['links'][0]['evidence'][0]['fragment'], ['s1', 'only if', 1, 's1', 'only if', 1])
        self.assertEqual(e['nodes'][9]['evidence'][0]['text'], LONG)

    def test_occurrence_indexes_are_one_based_and_not_swapped(self):
        """SPEC fragment rule via §3 W2: ho picks the head, to is conditional on it; off-by-one or ho/to swap changes the text."""
        s8 = TABLE['rows'][7][1]
        for (ho, to), (start, text) in {(2, 1): (s8 + 10, 'head tail'), (1, 3): (s8, 'head tail head tail head tail'), (3, 1): (s8 + 20, 'head tail'), (1, 1): (s8, 'head tail')}.items():
            with self.subTest(ho=ho, to=to):
                c = envelope(SOURCE, [unit(p=0)], [node('c1', x=[['s8', 'head', ho, 's8', 'tail', to]])], [link(1, 'c1', 'obj')])
                w = ref_to_wire(c)
                self.assertEqual(w['g'][0]['x'][0], dict(a='s8', h='head', ho=ho, z='s8', t='tail', to=to))
                ev = self.expanded(w)['nodes'][0]['evidence'][0]
                self.assertEqual((ev['start'], ev['end'], ev['text']), (start, start + len(text), text))
                self.assertEqual(ev['fragment'], ['s8', 'head', ho, 's8', 'tail', to])

    def test_start_and_end_spans_are_not_swapped(self):
        """§3 W2: a is the start span, z the end span; a cross-row fragment resolves only in that direction."""
        c = envelope(SOURCE, [unit(p=0)], [node('c1', x=[['s1', 'The office', 1, 's2', 'Qualification', 1]])], [link(1, 'c1', 'obj')])
        ev = self.expanded(ref_to_wire(c))['nodes'][0]['evidence'][0]
        self.assertEqual((ev['a'], ev['z'], ev['start'], ev['end']), ('s1', 's2', 0, 137))
        self.assertEqual(ev['text'], SOURCE[:137])
        c['g'][0]['x'][0] = ['s2', 'Qualification', 1, 's1', 'The office', 1]
        self.assertR15Code('fragment_row_order', self.respond, ref_to_wire(c))

    def test_y_empty_list_means_not_a_deadline_never_unknown(self):
        """§3 design note: y:[] is a positive non-deadline claim == r15.1 null; the 'unknown' deadline form is an explicit all-absent object."""
        e = self.expanded(self.w)
        self.assertIsNone(e['units'][0]['deadline'])
        self.assertIsNone(e['units'][6]['deadline'])
        unknown = e['units'][3]['deadline']
        self.assertEqual({k: d['state'] for k, d in unknown.items()}, dict(c='absent', z='absent', b='absent'))
        self.assertEqual(e['units'][3]['uncertainty'], 'source_ambiguous')
        c = fixture()
        c['u'][2].update(y=None, m=1)
        w = ref_to_wire(c)
        self.assertEqual(w['u'][2]['y'], [])
        self.assertIsNone(self.expanded(w)['units'][2]['deadline'])
        self.assertEqual(R.canonical(self.expanded(w)), R.canonical(R.expand(c, SOURCE, TABLE)))

    def test_all_absent_deadline_requires_unit_uncertainty_exactly_as_r15_1(self):
        """§5 row 15: absent dimensions need unit q!=0 ('deadline_uncertainty'); the codec must not drop the explicit form."""
        c = fixture()
        c['u'][3].update(m=0, q=0, r='')
        self.assertR15Code('deadline_uncertainty', self.respond, ref_to_wire(c))

    def test_key_order_in_raw_json_does_not_change_meaning(self):
        """§1 checker ignores key order; §4 maps by key name. Reversed fragment keys and b/z/c dimension order decode identically."""
        text = json.dumps(self.w, ensure_ascii=False)
        reference = R.canonical(R.expand(fixture(), SOURCE, TABLE))
        self.assertEqual(R.canonical(self.expanded(text)), reference)
        w = copy.deepcopy(self.w)
        for item in w['g'] + w['l']:
            item['x'] = [{k: o[k] for k in reversed(FRAG_KEYS)} for o in item['x']]
        for u in w['u']:
            if u['y']:
                y = u['y'][0]
                u['y'] = [{k: {kk: y[k][kk] for kk in ['r', 'x', 's']} for k in ['b', 'z', 'c']}]
        text = json.dumps(w, ensure_ascii=False)
        self.assertNotEqual(text, raw_of(self.w))
        self.assertEqual(R.canonical(self.expanded(text)), reference)

    def test_boundary_values_accepted(self):
        """§5 rows 4, 16: c400 valid, unit ID 160 valid below the count sentinel, 159 units, 399 nodes+links, depth 12, 48-codepoint anchor."""
        c = fixture()
        c['g'][-1]['i'] = 'c400'
        c['l'][2]['n'] = 'c400'
        cases = {'node_c400': c,
                 'unit_id_160': envelope(SOURCE, [unit(160)]),
                 'units_159': envelope(SOURCE, [unit(i) for i in range(1, 160)]),
                 'nodes_399_links_399': envelope(SOURCE, [unit()], [node(f'c{i}') for i in range(1, 400)], [link(1, f'c{i}', 'regardless') for i in range(1, 400)]),
                 'depth_12': chain(12),
                 'anchor_48_codepoints': envelope(SOURCE, [unit(p=0)], [node('c1', x=[frag('s2', LONG[:48])])], [link(1, 'c1', 'obj')]),
                 'anchor_with_combining_and_emoji': envelope(SOURCE, [unit(p=0, e=['s9'])], [node('c1', x=[frag('s9', 'Ω é 🫧')])], [link(1, 'c1', 'obj')])}
        for name, compact in cases.items():
            with self.subTest(case=name):
                expected = R.canonical(R.expand(copy.deepcopy(compact), SOURCE, TABLE))
                self.assertEqual(R.canonical(self.expanded(ref_to_wire(compact))), expected)

    def test_opaque_profile_accepts_clause_only_wires_identically(self):
        """§3 opaque profile: the result decodes to the same r15.1 object under both profiles."""
        c = opaque_fixture()
        expected = R.canonical(R.expand(copy.deepcopy(c), SOURCE, TABLE))
        self.assertEqual(R.canonical(self.expanded(ref_to_wire(c), profile='opaque')), expected)
        self.assertEqual(R.canonical(self.expanded(ref_to_wire(c), profile='full')), expected)
        self.assertEqual(R.canonical(self.expanded(ref_to_wire(c))), expected)


@needs_wire
class PipelineRejectTests(WireBase):
    """Family E: validate_response rejections, in pipeline order D0 → D1 → D2 → D3 → D4 (DESIGN §4)."""

    def test_non_stop_finish_reason_rejects_before_parsing(self):
        """§4 D0 / §5 row 25: finish_reason != stop rejects first, even for unparsable raw."""
        for finish in ['length', 'content_filter', '', None, 'STOP']:
            with self.subTest(finish=finish):
                self.assertR15Code('non_stop', self.respond, 'not json', finish=finish)
                self.assertR15Code('non_stop', self.respond, self.w, finish=finish)

    def test_raw_guards_apply_to_the_wire_text(self):
        """§4 D1/T6 and §5 row 22: r15.1 strict_load limits on the raw WIRE with r15.1 codes."""
        base = raw_of(self.w)
        cases = {
            'duplicate_top_level_key': ('{"v":"r16.w1",' + base[1:], 'duplicate_key'),
            'duplicate_fragment_key': (base.replace('{"a":"s1","h":"except"', '{"a":"s1","a":"s1","h":"except"', 1), 'duplicate_key'),
            'duplicate_deadline_dim_key': (base.replace('"c":{"r":"","s":"stated"', '"c":{"r":"","r":"","s":"stated"', 1), 'duplicate_key'),
            'nan_constant': (base.replace('"ho":1', '"ho":NaN', 1), 'nonfinite_constant'),
            'infinity_constant': (base.replace('"ho":1', '"ho":-Infinity', 1), 'nonfinite_constant'),
            'unpaired_surrogate_escape': (base.replace('"g":""', '"g":"\\ud800"', 1), 'unpaired_surrogate'),
            'parser_depth_65': (base[:-1] + ',"extra":' + '[' * 65 + ']' * 65 + '}', 'parser_depth'),
            'raw_size_600001': (' ' * (600001 - len(base.encode('utf-8'))) + base, 'raw_size'),
        }
        for name, (raw, code) in cases.items():
            with self.subTest(case=name):
                self.assertNotEqual(raw, base)
                self.assertR15Code(code, self.respond, raw)
        for name, raw in {'trailing_data': base + ' {}', 'truncated': base[:-1], 'not_json': 'END', 'top_level_array': '[' + base + ']'}.items():
            with self.subTest(case=name):
                with self.assertRaises(Exception):
                    self.respond(raw)

    def test_raw_size_boundary_is_inclusive(self):
        """§5 row 22: raw <= 600,000 B is accepted."""
        base = raw_of(self.w)
        padded = ' ' * (600000 - len(base.encode('utf-8'))) + base
        self.assertEqual(R.canonical(self.expanded(padded)), R.canonical(R.expand(fixture(), SOURCE, TABLE)))

    def test_checker_rejections_are_wire_errors(self):
        """§4 D2: schema_errors on the WIRE object → WireError (no normalization, no partial expansion)."""
        for name, mutate in CHECKER_CAUGHT:
            with self.subTest(case=name):
                w = ref_to_wire(fixture())
                mutate(w)
                self.assertWireError(self.respond, w)

    def test_r15_1_compact_shape_is_not_accepted_on_the_wire(self):
        """§3 W1/§4: the checker runs on the wire; an r15.1 compact (tuples, y null, v r15.1) is rejected, never auto-upgraded."""
        self.assertWireError(self.respond, self.c)
        w = ref_to_wire(fixture())
        w['v'] = 'r15.1'
        self.assertWireError(self.respond, w)

    def test_host_only_invariants_keep_their_r15_1_codes(self):
        """§5 rows 8/11/16/21 + §4 T2: span membership, node-ID syntax/range, nonblankness and resolution are host checks with r15.1 codes."""
        for name, mutate, code in HOST_ONLY:
            with self.subTest(case=name):
                v = fixture()
                mutate(v)
                self.assertR15Code(code, self.respond, ref_to_wire(v))

    def test_short_but_absent_span_ids_with_wider_tables(self):
        """§4 T3 'short but absent': a 3-char ID like s99 passes maxLength 3 on a 10-row table and must fail on the host."""
        source = '\n'.join(f'row {i} text' for i in range(10))
        table = R.span_table(source)
        self.assertEqual(span_width(table), 3)
        c = envelope(source, [unit(p=0, e=['s10'])], [node('c1', x=[frag('s10', 'row')])], [link(1, 'c1', 'obj')])
        self.assertEqual(R.canonical(self.expanded(ref_to_wire(c), source=source, table=table)), R.canonical(R.expand(copy.deepcopy(c), source, table)))
        for name, mutate, code in [('e_s99', lambda v: v['u'][0].update(e=['s99']), 'evidence_id'), ('e_s00', lambda v: v['u'][0].update(e=['s00']), 'evidence_id'),
                                   ('e_s01', lambda v: v['u'][0].update(e=['s01']), 'evidence_id'), ('frag_s99', lambda v: v['g'][0]['x'][0].__setitem__(3, 's99'), 'fragment_span')]:
            with self.subTest(case=name):
                v = copy.deepcopy(c)
                mutate(v)
                self.assertR15Code(code, self.respond, ref_to_wire(v), source=source, table=table)

    def test_capacity_sentinels_and_depth_keep_r15_1_codes(self):
        """§5 row 4 and §4 T2: 160 units / 400 nodes pass the schema bounds and are rejected by r15.1 sentinels; depth 13 → graph_depth."""
        cases = {'units_160': (envelope(SOURCE, [unit(i) for i in range(1, 161)]), 'capacity_review_u'),
                 'nodes_400': (envelope(SOURCE, [unit()], [node(f'c{i}') for i in range(1, 401)], [link(1, f'c{i}', 'regardless') for i in range(1, 401)]), 'capacity_review_g'),
                 'links_400': (envelope(SOURCE, [unit()], [node(f'c{i}') for i in range(1, 400)], [link(1, f'c{i}', 'regardless') for i in range(1, 400)] + [link(1, 'c1', 'acts')]), 'capacity_review_l'),
                 'depth_13': (chain(13), 'graph_depth'),
                 'node_cycle': (envelope(SOURCE, [unit()], [dict(node('c1', 'NOT', ['c2']), x=[]), dict(node('c2', 'NOT', ['c1']), x=[])], [link(1, 'c1', 'obj')]), 'node_cycle'),
                 'orphan_node': (envelope(SOURCE, [unit()], [node('c1'), node('c2')], [link(1, 'c1', 'obj')]), 'orphan_node'),
                 'dangling_link': (envelope(SOURCE, [unit()], [node('c1')], [link(1, 'c2', 'obj')]), 'dangling_link')}
        for name, (compact, code) in cases.items():
            with self.subTest(case=name):
                self.assertEqual(C14.schema_errors(ref_to_wire(compact), self.schema), [])
                self.assertR15Code(code, self.respond, ref_to_wire(compact))

    def test_opaque_profile_rejects_typed_nodes_and_children(self):
        """§3 opaque profile: AND/OR/NOT/EXC/ALT or any child list must be a checker rejection under profile='opaque'."""
        self.assertWireError(self.respond, self.w, profile='opaque')
        c = opaque_fixture()
        for name, mutate in {'and_node': lambda v: v['g'].append(dict(node('c3', 'AND', ['c1', 'c2']), x=[])) or v['l'].append(link(1, 'c3', 'regardless')),
                             'not_node': lambda v: v['g'].append(dict(node('c3', 'NOT', ['c1']), x=[])) or v['l'].append(link(1, 'c3', 'regardless')),
                             'leaf_with_child': lambda v: v['g'][0].update(a=['c2'])}.items():
            with self.subTest(case=name):
                v = copy.deepcopy(c)
                mutate(v)
                self.assertWireError(self.respond, ref_to_wire(v), profile='opaque')

    def test_unknown_profile_rejected_on_validate_response(self):
        """Interface: profiles other than full/opaque are a caller error, not a silent fallback to full."""
        for profile in ['typed', 'FULL', '']:
            with self.subTest(profile=profile):
                with self.assertRaises(Exception):
                    self.respond(self.w, profile=profile)

    def test_stale_table_and_wrong_source_reject(self):
        """§5 row 3 + r15.1 exact_host_table: a tampered table or a different source must not validate."""
        table = copy.deepcopy(TABLE)
        table['rows'][0][3] = 'changed'
        with self.assertRaises(Exception):
            self.respond(self.w, table=table)
        with self.assertRaises(Exception):
            self.respond(self.w, source=SOURCE + ' ')

    def test_no_partial_expansion_on_final_node_error(self):
        """§4: 'Any failure rejects the whole response ... no partial expansion' (r15.1 final-node precedent)."""
        c = fixture()
        c['g'][-1]['x'][0][1] = 'absent literal'
        self.assertR15Code('head_not_found', self.respond, ref_to_wire(c))


@needs_wire
class BuildTests(WireBase):
    """Family F: request plan and guarded byte counts (DESIGN §1 guard, §7 sizing, §9 prompt)."""

    def test_plan_counts_and_schema_binding(self):
        """§1: guard is len(encode(body)) + 1024 <= 40000; the body carries strict json_schema == schema(source, table, profile)."""
        for profile in ['full', 'opaque']:
            with self.subTest(profile=profile):
                plan = WIRE.build(SOURCE, profile)
                body = plan['body']
                raw = R.canonical(body)
                self.assertEqual(plan['body_bytes'], len(raw))
                self.assertEqual(plan['guarded_bytes'], len(raw) + 1024)
                self.assertLessEqual(plan['guarded_bytes'], 40000)
                self.assertEqual(plan['request_sha256'], hashlib.sha256(raw).hexdigest())
                rf = body['response_format']
                self.assertEqual(rf['type'], 'json_schema')
                self.assertIs(rf['json_schema']['strict'], True)
                self.assertEqual(rf['json_schema']['schema'], WIRE.schema(SOURCE, TABLE, profile))
                self.assertEqual(rf['json_schema']['schema'], expected_schema(SOURCE, TABLE, profile))
                C14.check_schema(rf['json_schema']['schema'])
                if 'table' in plan:
                    self.assertEqual(R.canonical(plan['table']), R.canonical(TABLE))

    def test_user_envelope_is_pinned_and_source_exact(self):
        """§1 contract.py:14: user envelope keys {source_text, source_text_sha256, span_table, span_table_sha256}, source untouched."""
        plan = WIRE.build(SOURCE)
        messages = plan['body']['messages']
        self.assertEqual([m['role'] for m in messages], ['system', 'user'])
        user = R.strict_load(messages[1]['content'])
        self.assertEqual(set(user), {'source_text', 'source_text_sha256', 'span_table', 'span_table_sha256'})
        self.assertEqual(user['source_text'], SOURCE)
        self.assertEqual(user['source_text_sha256'], R.source_hash(SOURCE))
        self.assertEqual(R.canonical(user['span_table']), R.canonical(TABLE))
        self.assertEqual(user['span_table_sha256'], R.digest(TABLE))
        self.assertEqual(user['span_table']['v'], 'r15.spans.2')

    def test_system_prompt_names_the_wire_version(self):
        """§3 W1 + §9 edit 1: the prompt asks for an r16.w1 envelope, not r15.1."""
        system = WIRE.build(SOURCE)['body']['messages'][0]['content']
        self.assertIn('r16.w1', system)
        self.assertNotIn('r15.1 envelope', system)

    def test_build_default_profile_is_full_and_bad_profile_raises(self):
        """Interface: build(source, profile='full'); other profiles raise."""
        self.assertEqual(WIRE.build(SOURCE)['request_sha256'], WIRE.build(SOURCE, 'full')['request_sha256'])
        self.assertNotEqual(WIRE.build(SOURCE)['request_sha256'], WIRE.build(SOURCE, 'opaque')['request_sha256'])
        with self.assertRaises(Exception):
            WIRE.build(SOURCE, 'typed')

    def test_build_guard_reports_or_rejects_oversize_and_rejects_bad_source(self):
        """§1 guard (len(encode(body)) + 1024 <= 40000) and §7 (over-guard profiles are measured and marked ✗):
        an oversize source either raises r15.1's full_request_overflow or returns an honest plan (guarded = body + 1024
        > 40000) whose boolean guard verdict is False. It must never present an over-guard plan as dispatchable."""
        try:
            plan = WIRE.build('a' * 40000)
        except Exception as exc:
            self.assertIn('full_request_overflow', code_of(exc))
        else:
            raw = R.canonical(plan['body'])
            self.assertEqual(plan['body_bytes'], len(raw))
            self.assertEqual(plan['guarded_bytes'], len(raw) + 1024)
            self.assertGreater(plan['guarded_bytes'], 40000)
            verdicts = {k: v for k, v in plan.items() if isinstance(v, bool)}
            self.assertTrue(verdicts, 'a returned over-guard plan must carry an explicit boolean guard verdict')
            self.assertTrue(all(v is False for v in verdicts.values()), verdicts)
        ok = WIRE.build(SOURCE)
        self.assertLessEqual(ok['guarded_bytes'], 40000)
        self.assertTrue(all(v is True for v in ok.values() if isinstance(v, bool)))
        for bad in ['bad\ud800', '   ', '']:
            with self.subTest(source=repr(bad)):
                with self.assertRaises(Exception):
                    WIRE.build(bad)

    def test_build_schema_is_the_fixed_5085_byte_form(self):
        """§7: A1 schema bytes are 5,085 and independent of span count below 1,000 spans."""
        for source in [SOURCE, '\n'.join(f'row {i}' for i in range(120))]:
            with self.subTest(rows=len(R.span_table(source)['rows'])):
                schema = WIRE.build(source)['body']['response_format']['json_schema']['schema']
                self.assertEqual(len(R.canonical(schema)), 5085)


if __name__ == '__main__':
    unittest.main(verbosity=2)
