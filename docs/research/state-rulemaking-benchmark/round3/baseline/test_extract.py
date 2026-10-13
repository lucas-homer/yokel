import unittest
import json
from pathlib import Path
from extract import extract, normalize_date

class EvidenceTests(unittest.TestCase):
    def test_invalid_and_merged_days(self):
        for value in ('February 30, 2026', 'July 2223, 2026', '2026-13-02'):
            self.assertIn('invalid_calendar_date', normalize_date(value)[1])

    def test_no_guessing_year_order_or_timezone(self):
        for value in ('January 2', '01/02/2026', '01/02/26'):
            self.assertIsNone(normalize_date(value)[0])
        r = extract('Comments must be received by January 2, 2026 at 5 p.m.')
        self.assertIsNone(r['resolved_close_utc'])
        clock = next(c for c in r['candidates'] if c['kind'] == 'time')
        self.assertIn('timezone_missing', clock['unresolved'])

    def test_separate_clock_contexts(self):
        r = extract('Written comments close March 2, 2026.\n\nPublic hearing April 3, 2026.')
        dates = [c for c in r['candidates'] if c['kind'] == 'date']
        self.assertEqual(dates[0]['role_candidates'], ['comment_close_candidate'])
        self.assertEqual(dates[1]['role_candidates'], ['hearing_candidate'])

    def test_unclear_roles_are_not_decided(self):
        r = extract('Hearing and comment deadline March 2, 2026.')
        c = r['candidates'][0]
        self.assertIn('multiple_role_cues', c['unresolved'])
        self.assertIn('temporal_evidence_review', r['routes'])

    def test_relative_and_conditional_not_computed(self):
        r = extract('Comments close within 20 calendar days after publication; if requested, 25 working days.')
        self.assertEqual(len([c for c in r['candidates'] if c['kind'] == 'duration']), 2)
        self.assertIn('mixed_duration_bases_scope_unresolved', r['routes'])
        self.assertIsNone(r['resolved_close_utc'])
        self.assertTrue(all(c['normalization'] is None for c in r['candidates']))

    def test_span_integrity_unicode_and_pages(self):
        text = 'Résumé😀\n\fComments by July 22–23, 2026; email a+b@example.gov. https://example.gov/a?x=1.'
        r = extract(text)
        for c in r['candidates']:
            s = c['span']
            self.assertEqual(text[s['start']:s['end']], s['literal'])
            self.assertEqual(s['page'], 2)
        date = next(c for c in r['candidates'] if c['kind'] == 'date')
        self.assertEqual(date['normalization']['calendar_dates'], ['2026-07-22', '2026-07-23'])
        self.assertEqual(next(c['span']['literal'] for c in r['candidates'] if c['kind'] == 'email'), 'a+b@example.gov')
        self.assertEqual(next(c['span']['literal'] for c in r['candidates'] if c['kind'] == 'url'), 'https://example.gov/a?x=1')

    def test_neighboring_notices_do_not_force_single_close(self):
        r = extract('Comments by March 2, 2026.\n\nComments by April 3, 2026.')
        self.assertIn('multiple_comment_values_scope_unresolved', r['routes'])
        self.assertIsNone(r['resolved_close_utc'])

    def test_page_boundary_never_borrows_role(self):
        r = extract('Comments close\fMarch 2, 2026.')
        self.assertIn('role_missing', r['candidates'][0]['unresolved'])

    def test_proposed_or_historical_requires_review(self):
        for phrase in ('Proposed effective March 2, 2026.', 'Prior hearing March 2, 2026.'):
            self.assertIn('temporal_modifier_requires_review', extract(phrase)['candidates'][0]['unresolved'])

    def test_unpunctuated_year_is_retained(self):
        c = extract('Comments close October 31 2026')['candidates'][0]
        self.assertEqual(c['span']['literal'], 'October 31 2026')
        self.assertEqual(c['normalization']['calendar_dates'], ['2026-10-31'])

    def test_trailing_conditions_and_history(self):
        for text, modifier in (
            ('Comments close October 31, 2026 if a hearing is requested.', 'conditional'),
            ('March 2, 2026 was the prior hearing date.', 'historical'),
        ):
            c = extract(text)['candidates'][0]
            self.assertIn(modifier, c['modifiers'])
            self.assertIn('temporal_modifier_requires_review', c['unresolved'])
            for evidence in c['cue_evidence']:
                sp = evidence['span']
                self.assertEqual(text[sp['start']:sp['end']], sp['literal'])

    def test_clean_local_cue_still_has_unverified_scope(self):
        r = extract('Comments close October 31, 2026.')
        self.assertIn('notice_scope_and_role_binding_unverified', r['candidates'][0]['unresolved'])
        self.assertEqual(r['decision'], 'escalate')

    def test_clock_literal_keeps_periods(self):
        c = next(c for c in extract('Hearing 5 p.m.')['candidates'] if c['kind'] == 'time')
        self.assertEqual(c['span']['literal'], '5 p.m.')

    def test_retained_corpus_span_integrity(self):
        directory = Path(__file__).resolve().parent
        root = directory.parents[1]
        manifest = json.loads((directory / 'manifest.json').read_text())
        self.assertEqual(len(manifest['units']), 28)
        self.assertFalse(manifest['reference_answers_in_runtime'])
        for unit in manifest['units']:
            self.assertNotIn('reference', unit)
            self.assertNotIn('review/', unit['text_path'])
            text = (root / unit['text_path']).read_text()
            r = extract(text, unit['fixture_id'])
            self.assertIsNone(r['resolved_close_utc'])
            for c in r['candidates']:
                for sp in [c['span']] + [e['span'] for e in c['cue_evidence']]:
                    self.assertEqual(text[sp['start']:sp['end']], sp['literal'])
                    self.assertEqual(text.count('\f', 0, sp['start']) + 1, sp['page'])

    def test_empty_native_routes_fallback(self):
        r = extract('\n\f  ')
        self.assertEqual(r['routes'], ['parser_fallback_empty_native_text'])
        self.assertEqual(r['candidates'], [])

    def test_deterministic_and_research_only(self):
        text = 'Comments close March 2, 2026.'
        self.assertEqual(extract(text), extract(text))
        self.assertFalse(extract(text)['production_eligible'])
        self.assertEqual(extract(text)['source_fidelity'], 'not_established_from_native_text')

if __name__ == '__main__':
    unittest.main()
