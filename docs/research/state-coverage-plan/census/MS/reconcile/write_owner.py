#!/usr/bin/env python3
"""Render the unsigned MS owner sheet and draft adjudications from the queue.

Inputs: review-queue.jsonl (reconcile.py), visual-readings.json (primary's
render readings) and the case notes below, written after reading originals.
Nothing here adjudicates: drafts carry review_status=proposed and null human fields.
"""
import collections
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
STATE = OUT.parent
ROOT = OUT.parents[5]
START = date(2026, 5, 18)
RATE = {('high', False): 1, ('high', True): 3, ('medium', True): 4, ('low', True): 6, ('medium', False): 2}


def read(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def canonical(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


CLASS_NOTES = {
    'relative-close-status': ('At any time within the twenty-five (25) day public comment period, written submissions … may be submitted to the filing agency.',
                              'standard form boilerplate, e.g. ms-form-28574 p1'),
    'explicit-opening': ('within twenty (20) days after the filing of this notice', 'ms-form-28574 p1, request paragraph'),
    'opening-cutoff': ('Filing/effective/adoption/signature dates are not automatically participation deadlines.', 'brief.txt, TEMPORAL FIELDS'),
    'carry-in-relative': ('An opportunity filed before 2026-05-18 counts when its relative clock (25 d comment / 20 d request, from filing) reaches 2026-05-18 or later.',
                          'MS/UNIVERSE.md, carry-in rule (signed)'),
    'stamp-index-mismatch': ('Index dates/type flags cannot replace stamp reading/body classification.', 'brief.txt, FROZEN UNIVERSE'),
    'completion-attribution': ('Counts may overlap across views.', 'brief.txt, INSPECTION AND COMPLETION'),
}

# Case notes written after reading the originals named in `checked`.
# Key: (bundle, trigger). Values: confidence, LOOK, checked originals, proposal.
CASES = {
    ('MS 28436+28594+28656', 'disagreement'): ('medium', True, ['ms-form-28436 p1', 'ms-form-28656 p1'],
        'A keeps 28436 as a historical-support root; B rejects the 28436 form as outside_interval. Both can stand: keep the outside_interval rejection of 28436’s own windows, and keep a support-only root only if the identity case in this row roots the withdrawal at 28436.'),
    ('MS 28436+28594+28656', 'lifecycle_ambiguity'): ('medium', True, ['ms-form-28656 p1'],
        'One full_withdrawal, older_proceeding_update (both passes). Form: “X Withdrawn”, “Date Proposed Rule Filed: 12/31/25”, no system number. The bulletin title says it withdraws final 28594 (navigation only). Keep target_opportunity_ids empty with that reason; no participation change and no invented prior opportunity.'),
    ('MS 28436+28594+28656', 'identity'): ('medium', True, ['ms-form-28656 p1', 'ms-form-28436 p1'],
        'Root the round at proposal 28436 (A): the form’s 12/31/25 proposal date and identical rule title match 28436, FILED DEC 31 2025. Keep B’s provisional 28656 root as a crosswalk alias. Applied here only as a comparison mapping.'),
    ('MS 28564+28623+28628', 'identity'): ('high', True, ['ms-form-28628 p1'],
        '28628 is a new-system-number re-proposal after 28623 withdrew 28564: a separate round with the prior link kept as an annotation. No reopening update. Both passes agree.'),
    ('MS 28578', 'lifecycle_ambiguity'): ('high', True, ['ms-form-28578 p1'],
        'Final 28644 (FILED MAY 13 2026, prior proposal 4/17/26, same SOS Rule 3.4(A)) adopts the rule before the start. Reject 28578’s comment and request windows as carry-ins (outside_interval, historical support). C04’s offsets give the same result (−6/−11 days).'),
    ('MS 28614', 'date_ambiguity'): ('high', False, ['ms-form-28614 p3'],
        'receipt_or_postmark null (A). The EIS Public Notice says “Written comments will be received by the Division of Medicaid …”, which names the recipient, not a receipt-vs-postmark condition. Keep the channel.'),
    ('MS 28615+28670', 'lifecycle_ambiguity'): ('high', False, ['ms-form-28670 p1'],
        '28670 explicitly withdraws “proposed rule filing ID #28615” (FILED MAY 26 2026, final box). One full_withdrawal targeting both 28615 windows, older_proceeding_update; keep the literal “30 days after filing” wording.'),
    ('MS 28625+28744+28753', 'disagreement'): ('high', False, ['ms-form-28744 p1'],
        'Cohort older_proceeding_update only, as A, on the 28744 notice and update. B’s extra carry_in belongs to 28625’s windows, not to the withdrawal. Same as CT C1 (pending owner signature).'),
    ('MS 28625+28744+28753', 'lifecycle_ambiguity'): ('high', True, ['ms-form-28744 p1', 'ms-form-28625 p1'],
        'Full withdrawal of System #28625 (both windows), FILED JUN 18 2026. Its “Date Proposed Rule Filed: 05/04/26” matches the index, not 28625’s MAY 05 stamp (C05). Keep A’s “To repeal … not finalized in 2018” wording note as reference.'),
    ('MS 28625+28744+28753', 'identity'): ('high', True, ['ms-form-28753 p1'],
        '28753 (FILED JUN 23 2026, Part 275 standards) is a separate round after the 28744 withdrawal. Keep the prior link as an annotation; no reopening update. Both passes agree.'),
    ('MS 28687', 'scope'): ('high', True, ['ms-form-28687 p1'],
        'Include. This is an Administrative Code rule filed with SOS inside the HCBS waiver Part, not a State Plan or waiver notice. Both passes include it. The EIS page it ticks is absent from the entry (EIS is excluded anyway).'),
    ('MS 28708+28796+28847', 'disagreement'): ('high', False, ['ms-form-28796 p1'],
        'Cohort interval_update only, as A. 28708 itself is new_notice in the interval; B’s extra new_notice on the withdrawal notice and update double-counts.'),
    ('MS 28708+28796+28847', 'lifecycle_ambiguity'): ('high', False, ['ms-form-28796 p1'],
        'Explicit “System ID #28708”. One full_withdrawal of both 28708 windows, FILED JUL 02 2026, “Date Proposed Rule Filed: 6/2/2026”, effective “Immediately”.'),
    ('MS 28708+28796+28847', 'identity'): ('high', True, ['ms-form-28847 p1'],
        '28847 (FILED JUL 24 2026, Title 7 Part 7 Kindergarten Guidelines) is a separate round after the 28796 withdrawal. Keep the prior link as an annotation; no merge by title.'),
    ('MS 28713', 'scope'): ('high', True, ['ms-form-28713 p1'],
        'Include. An Administrative Code amendment conforming to approved 1915(c) waivers is an SOS rule filing, not a waiver notice. Both passes include it.'),
    ('MS 28720', 'date_ambiguity'): ('medium', True, ['ms-form-28720 p1', 'ms-xchk-mdeq-notice-28720 p1'],
        'Close 2026-08-04, date precision. Keep the literal receipt wording (“delivered … by the end of business”) on the close and null on the open. Signed Q3 makes agency-stated closes conflicting; here the SOS form states no comment period, so nothing competes. Propose supported; owner confirms Q3.'),
    ('MS 28720', 'identity'): ('high', True, ['ms-xchk-mdeq-notice-28720 p1', 'ms-form-28720 p1'],
        'The MDEQ notice matches SOS 28720 by rule citation and the identical Aug 4, 2026 2:00 p.m. hearing. One comment window plus the scheduled hearing; no agency-only notice. Append-only fix: link the window from A’s 28720 notice (A’s self-reported gap).'),
    ('MS 28736', 'lifecycle_ambiguity'): ('high', False, ['ms-form-28736 p1'],
        '“Withdrawing and replacing the complete chapter” describes the proposal’s content; no SOS filing is withdrawn. No update; the proposal’s own windows stand.'),
    ('MS 28804', 'scope'): ('high', True, ['ms-form-28804 p1'],
        'Include. An MDA (state agency) rule for a program serving local governments is not a local-government filing.'),
    ('MS 28807', 'scope'): ('low', True, ['ms-form-28807 p1'],
        'Provisionally include. Pearl River Valley Water Supply District files Title 33 rules with SOS under the APA. Owner decides whether this state-created district falls under the signed local-government exclusion; if so, reject 2 windows.'),
    ('MS 28842+28855', 'identity'): ('medium', True, ['ms-form-28842 p1', 'ms-form-28855 p1'],
        'Keep two proposals (different system numbers and rule lists, FILED JUL 23 and JUL 30). B’s possible-overlap note is no basis for a merge.'),
    ('MS 28865', 'scope'): ('high', True, ['ms-form-28865 p1'],
        'Include. An MDA rule for a grant program serving small municipalities is a state-agency filing.'),
    ('MS-pass-A-dropped-notes', 'scope'): ('high', False, [],
        'Append A’s 26 omitted notes (attestation) to its labels as an append-only reference correction. None changes an included record. The scored ones (28568, 28569, 28905) and the 28933/28938 marks have their own visual cases.'),
    ('MS-source-gaps', 'missing_source'): ('high', False, [],
        'Keep the signed named gap: 28935 a.pdf/b.pdf returned 404 (owner-signoff id-gap-28935). Completeness is not established; nothing is inferred.'),
}

# Visual items needing more than a render confirmation, keyed by bundle.
VISUAL = {
    'MS 28568': ('high', 'Scheduled box ticked with typed “11/3/2025 9:30 a.m.”, five months before the APR 01 2026 stamp; the same board’s finals (index) adopted 7/30/2026. Keep the outside_interval rejection and preserve the literal date as conflicting. No carry-in.'),
    'MS 28569': ('high', 'Same as 28568: scheduled 11/3/2025 9:30 a.m. against an APR 01 2026 stamp. Keep the outside_interval rejection and preserve the literal date as conflicting.'),
    'MS 28615+28670': ('high', 'Neither oral option selected: scheduled box empty, not-scheduled sentence printed with no box or mark. Keep the conditional hearing_request with hearing_status unknown (both passes). 28670 stamp MAY 26 2026.'),
    'MS 28645': ('high', 'Stamp MAY 18 2026, the interval’s first day (start included): new_notice turns on this reading. Clear stamp, not-scheduled X.'),
    'MS 28651': ('high', 'MSDH variant with both oral boxes empty. Keep the hearing_request with status unknown and its condition (both passes).'),
    'MS 28652': ('high', 'Scheduled 6/17/26 10:00 AM by Zoom (box X). A blue pen line on “New rule(s)” changes only the action subtype, not any participation field.'),
    'MS 28658': ('high', 'Neither option selected (not-scheduled sentence unboxed and unmarked). Status unknown, as both passes have it.'),
    'MS 28721': ('high', 'MSDH variant with both oral boxes empty. Status unknown (both passes).'),
    'MS 28735': ('high', 'MSDH variant with both oral boxes empty. Status unknown (both passes). DocuSign time is not filing evidence.'),
    'MS 28736': ('high', 'MSDH variant with both oral boxes empty. Status unknown (both passes).'),
    'MS 28759': ('high', 'Chiropractic variant prints only the scheduled box (empty) and no not-scheduled line, while the request paragraph is printed. Status unknown (both passes).'),
    'MS 28811': ('high', 'A is right: scheduled box empty and the not-scheduled sentence has no box or mark. Set hearing_status unknown; B read not_scheduled.'),
    'MS 28841': ('high', 'Same layout as 28811 and the same call: A’s unknown, not B’s not_scheduled.'),
    'MS 28839': ('high', '“120” sits in the temporary column’s “To be in effect in __ days” with no Original/Renewal mark. The proposed column is marked and the stamp is in the middle box, so this is a proposal, as both passes have it.'),
    'MS 28860': ('high', 'The FILED stamp is in the right (final) box, but only the proposed column is marked and the final column is blank. Read as a proposal (both passes); the stamp position is a clerk anomaly.'),
    'MS 28905': ('high', 'SEP 14 2026 stamp (year faint); the index has 8/14/2026, which is inside the interval. Same-agency neighbours 28903/28904 are indexed 9/14, so the index date is a slip. The stamp governs: keep the outside_interval rejection.'),
    'MS 28933': ('high', 'The stamp (left, temporary box) is illegible even at 4× render. Both passes quote SEP 29 2026, which the original cannot confirm (A took it from the index). Record the stamp date as unknown; the temporary-rule exclusion does not depend on it.'),
}


def visual_case(item, readings, passes_box):
    """Summarise an item's renders; return (confidence, look, text, forms)."""
    reading = readings['items'][item['item_id']]
    forms = reading['forms']
    special = VISUAL.get(item['proceeding'])
    if special:
        return special[0], True, special[1], forms
    disagree = []
    for f in forms:
        for side, val in passes_box.get(f['form'], {}).items():
            pass
    bits = []
    for f in forms:
        stamp = f['stamp']
        box = {'not_scheduled': 'not-scheduled', 'scheduled': 'scheduled', None: 'withdrawal/final', 'n/a': 'n/a'}.get(f['box'], f['box'])
        bits.append(f'{f["form"]} FILED {stamp}, {box}, hand {f["hand"].split(" ")[0]}')
    text = 'Render confirms ' + '; '.join(bits) + ' — matches both passes.'
    if any(x['class'] == 'handwritten_id_disagreement' for x in item['sub_issues']):
        f = forms[0]
        text = (f'Pre-interval form; handwritten accession reads “{f["hand"]}”. The system number comes from the selector/index; '
                'no scored effect. Keep the reading as a separate alias.')
    return 'high', False, text, forms


def part1(items):
    md = ['# MS owner sheet — proposed, unsigned', '',
          'The owner decides every item. Agent agreement is not a verdict. Full immutable target IDs, item IDs and class membership are in `review-queue.jsonl` and `proposed-adjudications.jsonl`. '
          'The drafts use `author.role=primary`, `review_status=proposed`, `draft:true` and null human fields; never ingest them as signed verdicts. No sealed input or adjudication log is changed.', '',
          '## Part 1 — Class questions', '',
          'Counts are A/B label-record versions / comparison instances, with overlap across classes; they are not unique opportunities. Every policy awaits owner signature. Classes settle policy only; stamps, boxes, targets and scope calls stay in Part 2.', '']
    for i in [i for i in items if i['item_kind'] == 'class']:
        quote, cite = CLASS_NOTES[i['policy_key']]
        assert len(quote) <= 200
        extra = ''
        if i['policy_key'] == 'carry-in-relative':
            c = collections.Counter((x['detail']['opportunity_type'], x['detail']['proposed_outcome'].split(' ')[0]) for x in i['sub_issues'])
            near = sorted(x['detail']['form'] + ('c' if x['detail']['opportunity_type'] == 'written_comment' else 'r')
                          for x in i['sub_issues'] if -1 <= x['detail']['offset_from_start_days'] <= 1)
            extra = (f' Under the proposal: comment {c[("written_comment","carry_in")]} carry_in / {c[("written_comment","outside_interval")]} out; '
                     f'request {c[("hearing_request","carry_in")]} carry_in / {c[("hearing_request","outside_interval")]} out (21 windows leave the scored count). '
                     f'{len(near)} windows sit within ±1 day of the start and flip under a different counting rule: {", ".join(near)} (c=comment, r=request). '
                     'Scheduled carry-in hearings (28576 May 20, 28608 May 28, 28618 June 17) use their literal dates. 28596/28599 are index 4/23 versus stamp 4/24: the comment window stays carry_in either way.')
        if i['policy_key'] == 'stamp-index-mismatch':
            d = collections.Counter(x['detail']['stamp_minus_nearest_index_days'] for x in i['sub_issues'])
            extra = (f' Offsets (stamp − nearest index date, days): {", ".join(f"{k:+d}×{v}" for k, v in sorted(d.items()))}. '
                     '+0 means the stamp equals another index field (withdrawn date: 28423, 28459). One changes scope: 28905 (case below). '
                     '28938 (not among the 76; A’s dropped note) carries an index proposed date of 4/1 on an OCT 1 withdrawal. Same-band mismatches on included forms: 28596, 28599, 28625, 28635, 28705–28707, 28794, 28803, 28811, 28855.')
        if i['policy_key'] == 'completion-attribution':
            extra = (' A: every bulletin slice logged 0 (self-reported); 28436 and 28720 differ from direct links. '
                     'B: the six slices it self-reported (prop ×3, final/eff/wd 2026-05-18), plus 28720 and two MDEQ cross-check rows.')
        md += [f'**{i["owner_ref"]}. {i["question"]}** {i["proposed_answer"]} {i["rationale"]}{extra} '
               f'**{sum(map(len, i["record_ids"].values()))} records / {i["affected_instance_count"]} instances.** Quote: “{quote}” ({cite}).', '']
    return md


def part2(items, readings):
    cases = [i for i in items if i['item_kind'] == 'case']
    rows, routine, checks = [], [], {}
    for i in cases:
        if i['trigger'] == 'visual_mark':
            conf, look, text, forms = visual_case(i, readings, {})
            checks[i['item_id']] = {'confidence': conf, 'look': look, 'proposal': text,
                                    'checked': [f'ms-form-{f["form"]} render' for f in forms], 'forms': len(forms)}
        else:
            conf, look, checked, text = CASES[(i['proceeding'], i['trigger'])]
            checks[i['item_id']] = {'confidence': conf, 'look': look, 'proposal': text, 'checked': checked, 'forms': 0}
    by_bundle = collections.defaultdict(list)
    for i in cases:
        by_bundle[i['proceeding']].append(i)
    md = ['## Part 2 — Cases, bundled by SOS system-number chain', '',
          '**LOOK** means the owner personally inspects the original or render: scope, identity, lifecycle, source gaps and every non-routine visual mark. '
          'Confidence rates the proposal, not source completeness. Every K-reference is a distinct queue item with its own draft. '
          'Renders are at `.census-passes/MS/review-renders/<item_id>.png` (outside git; the item ID is in the queue). '
          'The primary viewed all 155 renders one per tool call; primary inspection is not the owner signature.', '',
          'Case / stake | Passes | Checked original | Proposed resolution', '---|---|---|---']
    for bundle, ii in by_bundle.items():
        cc = [checks[i['item_id']] for i in ii]
        if all(i['trigger'] == 'visual_mark' for i in ii) and not any(c['look'] for c in cc):
            routine.append((ii[0]['owner_ref'], cc[0]['proposal']))
            continue
        refs = ', '.join(i['owner_ref'] for i in ii)
        conf = min((c['confidence'] for c in cc), key=['low', 'medium', 'high'].index)
        trig = {i['trigger'] for i in ii}
        classes = {x['class'] for i in ii for x in i['sub_issues']}
        passes = ('A/B differ' if 'disagreement' in trig or 'oral_box_disagreement' in classes or 'native_root_crosswalk' in classes
                  else 'A/B differ on a decisive temporal field' if 'decisive_temporal' in classes else 'A/B agree; review remains')
        checked = '; '.join(sorted({x for c in cc for x in c['checked']})) or 'no original (named gap / attestation)'
        prop = ' '.join(dict.fromkeys(c['proposal'] for c in cc if not c['proposal'].startswith('Render confirms')))
        render = [c['proposal'] for c in cc if c['proposal'].startswith('Render confirms')]
        if render:
            prop += ' ' + render[0].replace(' — matches both passes.', '.')
        md.append(f'**{bundle}** — {refs}; **{conf}**' + (' **LOOK**' if any(c['look'] for c in cc) else '') +
                  f' | {passes} | {checked} | {prop.strip()}')
    md += ['', f'**Routine render confirmations ({len(routine)} items, 1 minute each).** For each: open the render, confirm the FILED date, '
           'the oral-proceeding selection and the handwritten number. The primary’s reading matched both passes on every one. Format: ref system-number stamp/box.', '']
    line = []
    for ref, text in routine:
        if text.startswith('Pre-interval'):
            line.append(f'{ref} hand-ID (out of interval)')
            continue
        for part in text.removeprefix('Render confirms ').removesuffix(' — matches both passes.').split('; '):
            n, rest = part.split(' FILED ')
            stamp, box = rest.split(', ')[:2]
            short = {'not-scheduled': 'ns', 'scheduled': 'sched', 'withdrawal/final': 'wd'}.get(box, box)
            line.append(f'{ref} {n} {stamp[5:]}/{short}')
    md += ['; '.join(line) + '.', '']
    return md, checks, routine


def write_drafts(items, checks):
    meta_path = OUT / '.draft-meta.json'
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    if 'draft_created_at' not in meta:
        meta['draft_created_at'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        meta_path.write_text(json.dumps(meta, indent=1) + '\n')
    refs = [STATE / 'pass-A.jsonl', STATE / 'pass-B.jsonl', STATE / 'completion.jsonl', STATE / 'manifest.jsonl',
            STATE / 'brief.txt', STATE / 'UNIVERSE.md', STATE / 'attestations/pass-A.json', STATE / 'attestations/pass-B.json',
            STATE.parent / 'PROTOCOL.md', STATE.parent / 'SCOPE-DECISIONS.md', STATE.parent.parent / 'rights/DECISIONS.md',
            ROOT / '.census-passes/MS/inputs/manifest.pass.jsonl', OUT / 'review-queue.jsonl', OUT / 'visual-readings.json']
    versions = [str(p.relative_to(ROOT)) + '@sha256:' + hashlib.sha256(p.read_bytes()).hexdigest() for p in refs]
    universe = read(STATE / 'pass-A.jsonl')[0]['universe_version']
    drafts = []
    for i in items:
        if i['item_kind'] == 'class':
            proposal, rationale = i['proposed_answer'], i['rationale']
        else:
            c = checks[i['item_id']]
            proposal = c['proposal']
            rationale = ('Checked: ' + ('; '.join(c['checked']) or 'no original (named gap / attestation)') +
                         f'. Proposal confidence {c["confidence"]}; LOOK={c["look"]}. No owner decision applied.')
        targets = sorted({rid for s in 'AB' for rid in i['record_ids'][s]} |
                         {x['detail']['manifest_entry_id'] for x in i['sub_issues'] if x['detail'].get('manifest_entry_id')})
        drafts.append({'schema_version': '1.0.0', 'draft': True, 'record_id': 'draft-owner:' + i['item_id'] + ':v1',
                       'entity_id': i['item_id'], 'state': 'MS', 'universe_version': universe, 'label_version': 1,
                       'supersedes_record_id': None, 'record_type': 'adjudication', 'phase': 'adjudicated',
                       'author': {'role': 'primary', 'task_id': None, 'provider': 'claudeAgent', 'model': 'claude-opus-5-5'},
                       'created_at': meta['draft_created_at'], 'cohorts': [], 'aliases': [], 'evidence': [],
                       'review_status': 'proposed', 'unresolved': ['Draft proposal only; owner decision required.'],
                       'payload': {'trigger': i['trigger'], 'target_record_ids': targets, 'input_versions': versions,
                                   'finding': f'{i["owner_ref"]}: {i["question"]} Proposed answer: {proposal}',
                                   'decision': 'not_established' if i['trigger'] == 'missing_source' else 'revise',
                                   'rationale': rationale, 'reviewer_id': None, 'started_at': None, 'ended_at': None,
                                   'minutes': None, 'result_versions': [], 'rescore_required': True, 'rescore_refs': [], 'audit': None}})
    (OUT / 'proposed-adjudications.jsonl').write_text(''.join(canonical(d) + '\n' for d in drafts))


def part3(items, checks, summary):
    classes = [i for i in items if i['item_kind'] == 'class']
    routine = sum(c['forms'] for c in checks.values() if not c['look'] and c['forms'])
    routine_items = sum(1 for c in checks.values() if not c['look'] and c['forms'])
    groups = collections.Counter((c['confidence'], c['look']) for c in checks.values() if c['look'] or not c['forms'])
    rows = [('Class signatures', len(classes), 2)]
    rows.append((f'Render confirmations, per form ({routine_items} visual items: the listed routine ones plus those inside bundled rows)', routine, 1))
    for (conf, look), n in sorted(groups.items(), key=lambda x: (-x[0][1], ['high', 'medium', 'low'].index(x[0][0]))):
        rows.append((f'{conf}-confidence cases{" with LOOK" if look else " without LOOK"}', n, RATE[(conf, look)]))
    total = sum(n * m for _, n, m in rows)
    md = ['## Part 3 — Mandatory owner minutes', '',
          f'**Mandatory {total} minutes against the 360-minute MS budget (decision 14); {360 - total} remain for the audit.** These are planning costs, not measured throughput. No overlap credit is assumed.', '',
          'Work | Count | Min each | Minutes', '---|---:|---:|---:']
    md += [f'{label} | {n} | {m} | {n * m}' for label, n, m in rows]
    md += [f'**Mandatory subtotal** | | | **{total}**', '',
           f'The union has {summary["union_opportunities"]} opportunities, above PROTOCOL §5’s 150, so the every-date check does not apply. '
           'Every decisive visual mark on an included filing is still mandatory (decision 14), so each has its own case. '
           'Recount after the class decisions: C04 alone would remove 21 windows from the scored carry-in count.', '',
           '**Audit: not estimated here.** It will be estimated under proposed Amendment A1 (a fixed sample of 30 units per state, with a container crosswalk). '
           'A1 is not yet signed. No frame, seed, sample or audit minutes are drawn or claimed. Nothing here establishes completeness: MS remains single-lineage, with the 28935 gap.', '']
    return md, total


def main():
    items = read(OUT / 'review-queue.jsonl')
    readings = json.loads((OUT / 'visual-readings.json').read_text())
    summary = json.loads((OUT / 'comparison-summary.json').read_text())
    assert {i['item_id'] for i in items if i['trigger'] == 'visual_mark' and i['item_kind'] == 'case'} == set(readings['items'])
    md = part1(items)
    p2, checks, routine = part2(items, readings)
    md += p2
    conf = collections.Counter(c['confidence'] for c in checks.values())
    def ref(bundle, trigger):
        return next(i['owner_ref'] for i in items if i['proceeding'] == bundle and i['trigger'] == trigger)
    md += [f'Case confidence: {conf["high"]} high / {conf["medium"]} medium / {conf["low"]} low; '
           f'**{sum(c["look"] for c in checks.values())} LOOK items** among {len(checks)} cases.', '',
           '**Both passes look wrong or unconfirmed:** 28933’s stamp date (both quote SEP 29 2026; the original is illegible). '
           f'Both mark 28720’s agency-stated close supported, against the letter of signed Q3 ({ref("MS 28720", "date_ambiguity")}). '
           'Both keep all 75 relative carry-in windows provisional, although 21 fall before the start under the signed UNIVERSE carry-in rule (C04). '
           'Single-pass errors: B on 28811/28841 (oral box) and on the 28744/28796 cohorts; '
           'A on the 28720 notice link and its 26 dropped notes.', '']
    p3, total = part3(items, checks, summary)
    md += p3
    (OUT / 'OWNER-SHEET.md').write_text('\n'.join(md) + '\n')
    write_drafts(items, checks)
    (OUT / 'case-source-checks.json').write_text(json.dumps(
        {'note': 'Primary proposals after reading originals; not owner decisions.', 'mandatory_minutes': total,
         'cases': [{'item_id': k, 'owner_ref': next(i['owner_ref'] for i in items if i['item_id'] == k), **v} for k, v in checks.items()]},
        indent=1, sort_keys=True) + '\n')
    print('owner sheet bytes', (OUT / 'OWNER-SHEET.md').stat().st_size, 'mandatory', total, 'cases', len(checks),
          'look', sum(c['look'] for c in checks.values()), dict(conf))


if __name__ == '__main__':
    main()
