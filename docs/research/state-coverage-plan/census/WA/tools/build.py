"""Build census/WA/manifest.jsonl and run.json from capture results + stored originals.
Run from the census directory: python3 /tmp/wa-acq/tools/build.py
Reads only local hash-store bytes; makes no network requests."""
import sys, json, re, subprocess, collections, hashlib, html
from datetime import datetime, timezone
sys.path.insert(0, '/tmp/wa-acq/tools')
import store, filings, idx
from plan import *

UV = 'wa-v0.1+scope-signed-2026-10-15'
SURF = {s['surface_id']: s for s in json.load(open('../rights/surfaces.json'))}
DATES = {}  # issue -> publication date (closing-date calendar column 4)
R = store.results()
F = filings.table()
PROBES = json.load(open('/tmp/wa-acq/probes.json'))
SECS = json.load(open('/tmp/wa-acq/sections.json'))
IDXC = json.load(open('/tmp/wa-acq/indexcheck.json'))
import os
IMGS = json.load(open('/tmp/wa-acq/imgs.json')) if os.path.exists('/tmp/wa-acq/imgs.json') else {}

def review(tag):
    return f'PENDING-OWNER-REVIEW:wa-{tag}'

# --- issue dates from the calendars (column 4 = publication date)
def cal_dates():
    for k in ['wa-calendar-25-23', 'wa-calendar-26-19']:
        t = subprocess.run(['/tmp/wa-acq/tools/pdftext', store.path(R[k])], capture_output=True, text=True).stdout
        for m in re.finditer(r'^(\d\d-\d\d) (\S+) (\S+) (\S+) (\S+)', t, re.M):
            mo, d, y = m.group(5).split('/')
            DATES.setdefault(m.group(1), f'{y}-{int(mo):02d}-{int(d):02d}')
cal_dates()

def cycle(iss):
    return f'WSR {iss} (published {DATES[iss]})'

COHORT = {**{i: '[2026-06-03,2026-09-02) America/Los_Angeles (interval)' for i in INTERVAL},
          **{i: '[2025-12-03,2026-06-03) America/Los_Angeles (carry-in backward search, 180-day boundary)' for i in BACKWARD},
          **{i: '[2026-09-02,2026-11-05) America/Los_Angeles (post-close follow-up horizon; reported separately)' for i in FOLLOW + FUTURE}}

def rights(sid):
    s = SURF[sid]
    m = {'allowed': 'allowed', 'allowed_watched_only': 'allowed', 'on_hold': 'unresolved', 'blocked': 'denied'}
    return {'record_ref': 'rights/surfaces.json', 'version': s['version'],
            'collection_rule': m[s['collection_rule']],
            'retention_allowed': s['retention'] == 'internal_originals',
            'third_party_processing': 'allowed' if s['third_party_processing'] == 'public_notices_only' else 'denied',
            'public_evidence_rule': s['public_evidence_rule'], 'surface_id': sid}

def retrieval(eid):
    r = R.get(eid)
    if r is None:
        import os
        if os.environ.get('WA_TEST'):
            return {'result': 'not_attempted', 'requested_url': 'https://lawfilesext.leg.wa.gov/x', 'final_url': None, 'attempted_at': None, 'http_status': None, 'content_type': None, 'sha256': None, 'byte_length': None, 'storage_path': None, 'sidecar_path': None, 'reason': 'TEST placeholder'}
        raise SystemExit('no capture result for ' + eid)
    t = dict(r['retrieval'])
    if t['result'] != 'retrieved' and t['byte_length'] is not None:
        # capture.py reports the error-body length; the manifest schema requires null for failed units.
        t['reason'] = f"{t['reason']}; error body {t['byte_length']} bytes, not retained"
        t['byte_length'] = None
    return t

# --- text layer test (PDFKit native text per page)
PAGE_MIN = 40
_pp = {}
def pdf_pages(path):
    if path not in _pp:
        out = subprocess.run(['/tmp/wa-acq/tools/pdfpages', path], capture_output=True, text=True).stdout
        _pp[path] = json.loads(out) if out.strip() else {'error': 'no output'}
    return _pp[path]

def text_of(eid):
    r = R[eid]
    p = store.path(r)
    if r['retrieval']['content_type'] and 'pdf' in r['retrieval']['content_type']:
        return subprocess.run(['/tmp/wa-acq/tools/pdftext', p], capture_output=True, text=True).stdout
    return html.unescape(re.sub(r'<[^>]+>', ' ', store.text(r)))

AGENCY_GROUPS = {'clean air': 'wa-local-clean-air', 'air pollution': 'wa-local-clean-air',
                 'columbia river gorge': 'wa-columbia-river-gorge-commission'}
def agency_group(names):
    gs = set()
    for n in names:
        low = n.lower()
        gs.add(next((g for k, g in AGENCY_GROUPS.items() if k in low), 'wa-state-agencies'))
    return 'wa-state-agencies' if 'wa-state-agencies' in gs else sorted(gs)[0]

PROCESS = {'PROP': 'cr102-proposal-family', 'EXPE': 'cr105-expedited', 'PREP': 'cr101-preproposal',
           'MISC': 'misc-filings', 'PERM': 'cr103p-permanent', 'EMER': 'cr103e-emergency'}
CONTAINER = ('wa-code-reviser', 'register-accounting')

entries = []
gaps = collections.OrderedDict()  # review ref -> description
def gap(tag, desc):
    ref = review(tag); gaps.setdefault(ref, desc); return ref

def entry(eid, kind, parent, source, lineage, expected, sid, ret, acc, agency, process, fmt, pubcycle, text_layer,
          completeness=None, review_ref=None):
    if completeness is None:
        completeness = 'accounted' if ret['result'] == 'retrieved' else 'gap'
    e = {'schema_version': '1.0.0', 'entry_id': eid, 'state': 'WA', 'universe_version': UV,
         'source_id': source, 'lineage_id': lineage, 'parent_entry_id': parent, 'kind': kind,
         'expected': expected, 'rights': rights(sid), 'retrieval': ret, 'accounting': acc,
         'prior_capture_entry_id': None, 'completeness': completeness, 'human_review_ref': review_ref,
         'agency_id': agency, 'process_id': process, 'format': fmt, 'publication_cycle': pubcycle,
         'text_layer': text_layer}
    if completeness != 'accounted' and not review_ref:
        raise SystemExit('gap without review ref: ' + eid)
    entries.append(e)
    return e

def acc(children=None, expected_children=0, page_range='single document', terminal=None, cross=None):
    children = children or []
    return {'expected_children': expected_children, 'observed_children': len(children),
            'child_entry_ids': children, 'pagination_or_page_range': page_range,
            'terminal_evidence_refs': terminal or [], 'cross_checks': cross or []}

def fail_ref(eid, ret):
    return gap('capture-failure-' + eid, f"{eid}: {ret['result']} ({ret['reason']})")

def capture_entry(eid, kind, parent, expected, agency, process, pubcycle, page_hint=None, terminal=None,
                  cross=None, children=None, expected_children=0, completeness=None, review_ref=None, src='wa-register'):
    ret = retrieval(eid)
    fmt, tl, pr = 'html', 'native', page_hint or 'single HTML document'
    if ret['result'] == 'retrieved' and ret['content_type'] and 'pdf' in ret['content_type'].lower():
        info = pdf_pages(store.path(R[eid]))
        if 'error' in info:
            fmt, tl, pr = 'text_pdf', 'none', 'PDF unreadable by PDFKit; page count unknown'
            expected['evidence_refs'].append(f'text-extract-fail:{eid}#document')
        else:
            n = info['pages']; low = [i + 1 for i, c in enumerate(info['chars']) if c < PAGE_MIN]
            img = [(i + 1, m) for i, m in enumerate(info['images']) if m]
            tl = 'native' if not low and not img else ('none' if len(low) == n else 'partial')
            fmt = 'scan_pdf' if tl == 'none' else 'text_pdf'
            pr = f'pages 1-{n} of {n} (PDFKit page count)'
            for p in low:
                expected['evidence_refs'].append(f'text-extract-fail:{eid}#page={p} (<{PAGE_MIN} native chars)')
            for p, m in img:
                expected['evidence_refs'].append(f'text-extract-fail:{eid}#page={p} region=embedded-image x{m} (image content absent from native text layer)')
    if ret['result'] != 'retrieved':
        completeness, review_ref = 'gap', review_ref or fail_ref(eid, ret)
        if '.pdf' in ret['requested_url']:
            fmt = 'text_pdf'
    return entry(eid, kind, parent, src, 'wa-cro', expected, 'wa-register', ret,
                 acc(children, expected_children, pr, terminal, cross), agency, process, fmt, pubcycle, tl,
                 completeness, review_ref)

def ev(basis, refs, iss, selector):
    return {'basis': basis, 'evidence_refs': list(refs), 'publication_interval': COHORT.get(iss, 'n/a (authority/roster evidence, not a publication unit)'),
            'selector': selector}

# ---------- discovery / authority entries
A, P = CONTAINER
capture_entry('wa-landing', 'attachment', None, ev('Register landing page: official-publication statement and current-issue banner', ['UNIVERSE.md#authority'], None, 'leg.wa.gov Register landing'), A, P, 'n/a')
capture_entry('wa-description', 'attachment', None, ev('Register description: issue cadence (1st/3rd Wednesday) and certified PDF as official publication', ['UNIVERSE.md#authority'], None, 'description.htm'), A, P, 'n/a')
capture_entry('wa-wsrbyissue', 'index', None, ev('Issue archive 05-19..current; links to every issue page', ['WsrByIssue.htm'], None, 'WsrByIssue.htm'), A, P, 'n/a',
              terminal=['wa-wsrbyissue: 2026 row links issues 01-19; 20-24 present as unlinked cells (not yet published)'])
for y in ['2025', '2026']:
    capture_entry(f'wa-docsbytype-{y}', 'index', None, ev(f'{y} filings-by-type matrix linking every type index', [f'WSRDocsByType{y[2:]}.htm'], None, f'WSRDocsByType{y[2:]}.htm'), A, P, 'n/a',
                  terminal=[f'wa-docsbytype-{y}: one link per type x issue; terminal = last linked issue column'])
capture_entry('wa-agencywac', 'agency_roster', None, ev('Agency-to-WAC roster of Register filers (roster authority)', ['UNIVERSE.md#roster'], None, 'AgencyWac.htm'), A, P, 'n/a')
for k in ['wa-calendar-25-23', 'wa-calendar-26-11', 'wa-calendar-26-19']:
    capture_entry(k, 'attachment', None, ev('Closing-date calendar: issue publication dates (column 4), first hearing dates, expedited adoption dates', ['UNIVERSE.md#interval'], None, k), A, P, 'n/a')

# ---------- per issue
def issue_entries(iss):
    group = 'interval' if iss in INTERVAL else 'backward' if iss in BACKWARD else 'followup'
    types = TYPES if group == 'interval' else BACK_TYPES if group == 'backward' else FOLLOW_TYPES
    ieid = f'wa-issue-{iss}'
    children = []
    # type indexes
    for t in types:
        k = f'wa-idx-{iss}-{t}'; c = IDXC[k]
        ok = not c['missing'] and not c['extra']
        detail = (f"type index rows={c['rows']} unique={c['unique']}; matches issue-page {t} rows" if ok else
                  f"type index vs issue page {t}: missing from index {c['missing']}, extra in index {c['extra']}")
        ref = None if ok else gap(f'index-discrepancy-{iss}-{t}', f'{k}: {detail} (same lineage; owner to confirm listing)')
        capture_entry(k, 'index', ieid, ev(f'{t} type index for issue {iss} (linked from issue page and WSRDocsByType)', [ieid, f'wa-docsbytype-20{iss[:2]}'], iss, f'WSR{iss}{t}.htm'),
                      A, P, cycle(iss), terminal=[f'{k}: complete static table, {c["rows"]} filing rows, closing </table>'],
                      cross=[{'against_entry_id': ieid, 'result': 'matches' if ok else 'gap', 'detail': detail, 'lineage_id': 'wa-cro'}],
                      completeness=None if ok else 'gap', review_ref=ref)
        children.append(k)
    extra_secs = [] if group == 'interval' else [t for t in PDF_SECTIONS if f'wa-sec-{iss}-{t}' in R]
    if group == 'interval' or extra_secs:
        for t in (PDF_SECTIONS if group == 'interval' else extra_secs):
            k = f'wa-sec-{iss}-{t}'
            info = SECS.get(k)
            if info:
                listed = sorted(w for w, f in F.items() if iss in f['listed_in'] and t in f['types'])
                missing = [w for w in listed if w not in info['wsr_pages']]
                extra = [w for w in info['wsr_pages'] if w not in listed]
                ok = not missing and not extra
                detail = (f'section PDF page headers name {len(info["wsr_pages"])} filings; equals issue-page {t} rows' if ok else
                          f'section PDF vs issue page: not in PDF {missing}, not listed {extra}')
                cross = [{'against_entry_id': ieid, 'result': 'matches' if ok else 'gap', 'detail': detail, 'lineage_id': 'wa-cro'}]
            else:
                ok, cross = True, []
            capture_entry(k, 'attachment', ieid, ev(f'Certified {t} section PDF of issue {iss} (issue page header link)' + ('' if group == 'interval' else '; captured to resolve holdover publication issue (filings printed in both numbering and holdover issues)'), [ieid], iss, f'{iss}{t}.pdf'),
                          A, P, cycle(iss), cross=cross, completeness=None if ok else 'gap',
                          review_ref=None if ok else gap(f'section-discrepancy-{iss}-{t}', f'{k}: {detail}'))
            children.append(k)
    # filings numbered in this issue (captured groups)
    own = sorted((f for f in F.values() if f['num_issue'] == iss and filings.group(f)), key=lambda f: f['wsr'])
    for f in own:
        t = min(f['types']); proc = PROCESS[t]; ag = agency_group(f['agencies'])
        hold = [i for i in f['holdover_in']]
        refs = [f'{ieid}#row:{f["wsr"]}', f'wa-idx-{iss}-{t}']
        secpages = SECS.get(f'wa-sec-{iss}-{t}', {}).get('wsr_pages', {}).get(f['wsr'])
        if secpages: refs.append(f'wa-sec-{iss}-{t}#pages={secpages[0]}-{secpages[1]}')
        for h in hold:
            refs.append(f'wa-issue-{h}#holdover-row:{f["wsr"]}')
            hp = SECS.get(f'wa-sec-{h}-{t}', {}).get('wsr_pages', {}).get(f['wsr'])
            if hp: refs.append(f'wa-sec-{h}-{t}#pages={hp[0]}-{hp[1]} (holdover continuation)')
        basis = (f'{t} filing listed on issue page {iss} under {"; ".join(f["agencies"])}' +
                 (f'; also listed as holdover in {", ".join(hold)}' if hold else '') +
                 '; WSR sequence-number closure for the issue')
        ids = {}
        for kind in ['htm', 'pdf']:
            eid = f'wa-f-{f["wsr"]}-{kind}'
            ids[kind] = eid
        cross = {}
        both = all(R.get(ids[k], {}).get('retrieval', {}).get('result') == 'retrieved' for k in ids)
        if both:
            th, tp = text_of(ids['htm']), text_of(ids['pdf'])
            norm = lambda s: re.sub(r'\s+', ' ', s)
            fh = re.search(r'\[Filed ([^\]]+)\]', norm(th)); fp = re.search(r'\[Filed ([^\]]+)\]', norm(tp))
            same_wsr = f['wsr'] in th and f['wsr'] in tp
            same_filed = (fh and fp and fh.group(1).strip() == fp.group(1).strip()) or (not fh and not fp)
            res = 'matches' if same_wsr and same_filed else 'gap'
            d = (f'content identity: WSR number present in both; filed stamp {fh.group(1).strip() if fh else "absent"} = '
                 f'{fp.group(1).strip() if fp else "absent"}') if res == 'matches' else \
                (f'content identity mismatch: wsr_in_htm={f["wsr"] in th} wsr_in_pdf={f["wsr"] in tp} '
                 f'filed_htm={fh.group(1) if fh else None} filed_pdf={fp.group(1) if fp else None}')
            cross['htm'] = [{'against_entry_id': ids['pdf'], 'result': res, 'detail': d, 'lineage_id': 'wa-cro'}]
            cross['pdf'] = [{'against_entry_id': ids['htm'], 'result': res, 'detail': d, 'lineage_id': 'wa-cro'}]
            if secpages:
                cross['pdf'].append({'against_entry_id': f'wa-sec-{iss}-{t}', 'result': 'matches',
                                     'detail': f'filing appears in certified section PDF pages {secpages[0]}-{secpages[1]}', 'lineage_id': 'wa-cro'})
        for kind in ['htm', 'pdf']:
            eid = ids[kind]
            cc = cross.get(kind, [])
            bad = [c for c in cc if c['result'] != 'matches']
            imgs = IMGS.get(eid, []) if kind == 'htm' else []
            img_ids = [f'wa-img-{f["wsr"]}-{i + 1:02d}' for i in range(len(imgs))]
            for i, (iid, src) in enumerate(zip(img_ids, imgs)):
                iret = retrieval(iid)
                capture_entry(iid, 'attachment', eid,
                              ev(f'Embedded image {i + 1}/{len(imgs)} of {eid} (<img src> in the filing HTML)', [f'{eid}#img[{i}]'], iss, src.split('/')[-1]),
                              ag, proc, cycle(iss), page_hint='single PNG image')
                entries[-1]['format'] = 'mixed'; entries[-1]['text_layer'] = 'none'
                entries[-1]['expected']['evidence_refs'].append(f'text-extract-fail:{iid}#image (no text layer; content duplicated as embedded image in the certified PDF)')
            e = capture_entry(eid, 'attachment', ieid,
                              ev(basis, refs, iss, f'WSR {f["wsr"]} ({"HTML navigation copy" if kind == "htm" else "certified PDF filing"})'),
                              ag, proc, cycle(iss), cross=cc, children=img_ids, expected_children=len(img_ids),
                              completeness='gap' if bad or any(next(x for x in entries if x['entry_id'] == c)['completeness'] != 'accounted' for c in img_ids) else None,
                              review_ref=gap(f'identity-{f["wsr"]}', f'{eid}: {bad[0]["detail"] if bad else "image attachment not retrieved"}') if bad or any(next(x for x in entries if x['entry_id'] == c)['completeness'] != 'accounted' for c in img_ids) else None)
            if imgs:
                e['text_layer'] = 'partial'
                for i, src in enumerate(imgs):
                    e['expected']['evidence_refs'].append(f'text-extract-fail:{eid}#img[{i}] region=embedded-image {src.split("/")[-1]} (see {img_ids[i]})')
            children.append(eid)
    # sequence holes: explicit entries
    for w, why in PROBES.items():
        if why != 'hole' or not w.startswith(iss + '-'):
            continue
        for kind in ['htm', 'pdf']:
            eid = f'wa-probe-{w}-{kind}'
            ret = retrieval(eid)
            if ret['result'] == 'retrieved':
                raise SystemExit(f'UNLISTED FILING FOUND {eid} -- handle manually')
            ref = gap(f'sequence-hole-{w}', f'WSR number {w} absent from every captured issue page (25-23..26-19) and type index; direct URL probe -> {ret["result"]} HTTP {ret["http_status"]}. Unused/void number or unlisted filing: owner to confirm with Code Reviser or accept as void.')
            entry(eid, 'attachment', ieid, 'wa-register', 'wa-cro',
                  ev(f'Sequence closure: number {w} lies between listed numbers of issue {iss} but is listed nowhere', [ieid, f'capture-results/06-sequence-probes.jsonl#{eid}'], iss, f'WSR {w} ({kind})'),
                  'wa-register', ret, acc(page_range='probe of expected filing URL'), A, P,
                  'html' if kind == 'htm' else 'text_pdf', cycle(iss), 'native', 'gap', ref)
            children.append(eid)
    # terminal evidence
    term = [f'{ieid}: issue page lists {len([w for w, f in F.items() if iss in f["listed_in"]])} distinct WSR numbers (holdovers included)']
    for w, why in PROBES.items():
        if why == 'terminal' and w.startswith(iss + '-'):
            for kind in ['htm', 'pdf']:
                r = R.get(f'wa-probe-{w}-{kind}')
                term.append(f'capture-results/06-sequence-probes.jsonl#wa-probe-{w}-{kind}: next number after max -> '
                            f'{r["retrieval"]["result"] if r else "not run"} HTTP {r["retrieval"]["http_status"] if r else None}')
    # holdovers listed here from earlier issues (bodies are children of their numbering issue)
    held_in = sorted(w for w, f in F.items() if iss in f['holdover_in'])
    holdnote = f'; holdover rows from earlier numbering issues: {held_in} (body entries are children of their numbering issue)' if held_in else ''
    ret = retrieval(ieid)
    bad_child = [c for c in children if next(e for e in entries if e['entry_id'] == c)['completeness'] != 'accounted']
    scope_note = {'interval': 'all six Register types + 8 certified section PDFs + every filing (HTML + certified PDF)',
                  'backward': 'PREP/PROP/EXPE indexes and filings only (signed universe: candidate carry-ins = every CR-101/CR-102-family/CR-105 filing in the 180-day boundary; PERM/EMER/MISC not collected)',
                  'followup': 'PROP/EXPE/MISC indexes and filings only (follow-up lifecycle events: continuances, withdrawals, supplementals, MISC window changes)'}[group]
    e = entry(ieid, 'issue', None, 'wa-register', 'wa-cro',
              ev(f'Issue {iss} published {DATES[iss]} per closing-date calendar column 4; expected units: {scope_note}{holdnote}',
                 ['wa-calendar-26-19' if iss >= '26-13' else 'wa-calendar-25-23', 'wa-wsrbyissue'], iss, f'{iss}.htm'),
              'wa-register', ret, acc(children, len(children), 'single HTML issue page', term), A, P, 'html', cycle(iss), 'native',
              'gap' if bad_child else 'accounted',
              gap(f'issue-incomplete-{iss}', f'{ieid}: {len(bad_child)} child unit(s) not accounted: {bad_child[:6]}') if bad_child else None)
    entries.remove(e); entries.insert(0, e)  # issues first for readability

for iss in BACKWARD + INTERVAL + FOLLOW:
    issue_entries(iss)

# not-yet-published follow-up issues
for iss in FUTURE:
    ret = {'result': 'not_attempted', 'requested_url': f'{B}/wsr/{ydir(iss)}/{iss}.htm', 'final_url': None,
           'attempted_at': None, 'http_status': None, 'content_type': None, 'sha256': None, 'byte_length': None,
           'storage_path': None, 'sidecar_path': None,
           'reason': f'Not yet published: publication date {DATES[iss]} per closing-date calendar (wa-calendar-26-19); WsrByIssue shows {iss[3:]} unlinked on 2026-10-15'}
    entry(f'wa-issue-{iss}', 'issue', None, 'wa-register', 'wa-cro',
          ev(f'Follow-up horizon issue {iss} (publication {DATES[iss]}); needed for post-close follow-up of 26-15/26-16 opportunities', ['wa-calendar-26-19', 'wa-wsrbyissue'], iss, f'{iss}.htm'),
          'wa-register', ret, acc(expected_children=None, page_range='not yet published'), A, P, 'html', cycle(iss), 'native', 'gap',
          gap(f'followup-not-published-{iss}', f'Issue {iss} (publication {DATES[iss]}) not yet published at acquisition; capture after publication, then re-run step 3 for follow-up'))

# agency cross-check entries (independent lineage, wa-agency-rulemaking 2026-10-15.4: internal retention)
def slug(name):
    return 'wa-agency/' + re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
SKIPPED = {
    'doh': ('https://doh.wa.gov/', 'skipped on terms: DOH privacy/copyright statement (doh.wa.gov/privacyandcopyright, read 2026-10-15) says some content is third-party and reuse requires webmaster permission'),
    'dol': ('https://dol.wa.gov/', 'skipped on terms: dol.wa.gov/about/conditions-use bars exploiting site information "for commercial purposes"'),
    'wdfw': ('https://wdfw.wa.gov/', 'skipped on terms: wdfw.wa.gov/privacy limits copying/distribution to informational, non-commercial use with a reproduction disclaimer'),
    'dcyf': ('https://www.dcyf.wa.gov/', 'skipped on terms: dcyf.wa.gov/privacy-notice says some photos/text belong to others and reuse requests go to communications@dcyf.wa.gov'),
}
for a, (url, note) in SKIPPED.items():
    ret = {'result': 'not_attempted', 'requested_url': url, 'final_url': None, 'attempted_at': None, 'http_status': None,
           'content_type': None, 'sha256': None, 'byte_length': None, 'storage_path': None, 'sidecar_path': None,
           'reason': note + '; DECISIONS item 5 requires skipping agencies whose terms restrict reuse'}
    entry(f'wa-xc-{a}', 'portal_slice', None, f'wa-agency-{a}', f'wa-agency-{a}',
          ev(f'Planned independent-lineage cross-check: {a.upper()} rule-making pages vs its WSR filings in 26-11..26-16', ['rights/DECISIONS.md#5', 'SCOPE-DECISIONS.md#cross-state'], '26-11', f'{a} agency rule-making listing'),
          'wa-agency-rulemaking', ret, acc(expected_children=None, page_range='not attempted'), 'wa-state-agencies', 'cr102-proposal-family', 'html',
          'interval 26-11..26-16', 'native', 'gap', gap(f'agency-terms-skip-{a}', f'{a.upper()} cross-check skipped: {note}. Owner may override if internal retention is acceptable under these terms.'))
ret = {'result': 'not_attempted', 'requested_url': 'https://ecology.wa.gov/', 'final_url': None, 'attempted_at': None, 'http_status': None,
       'content_type': None, 'sha256': None, 'byte_length': None, 'storage_path': None, 'sidecar_path': None,
       'reason': 'wa-ecology-pointers is on_hold / pointer-only (Ecology terms bar political or lobbying use); not collected'}
entry('wa-xc-ecology', 'portal_slice', None, 'wa-agency-ecology', 'wa-agency-ecology',
      ev('Ecology rule-making page: pointer-only, excluded as a cross-check', ['rights/DECISIONS.md#defaults'], '26-11', 'ecology rule-making listing'),
      'wa-ecology-pointers', ret, acc(expected_children=None, page_range='not attempted'), 'wa-state-agencies', 'cr102-proposal-family', 'html',
      'interval 26-11..26-16', 'native', 'gap', gap('ecology-pointer-only', 'Ecology agency page is pointer-only under rights; no cross-check possible'))

XC_AGENCY = {'hca': r'health care authority|employees benefits board', 'lni': r'labor and industries'}
XC_TERMS = {'hca': 'HCA: no reuse restriction located (website privacy policy page, 2026-10-15); proceed per DECISIONS item 5',
            'lni': 'L&I privacy and security statement: site content "is considered public information ... may be copied, downloaded, or distributed"'}
XC_TYPES = {'PROP': 'cr102-proposal-family', 'EXPE': 'cr105-expedited', 'PREP': 'cr101-preproposal'}
coverage_checks = collections.defaultdict(list)   # process -> checks
best = {}  # wsr -> (process, check, matched)
for k in sorted(x for x in R if x.startswith('wa-xc-')):
    a = k.split('-')[2]
    page = store.text(R[k]); cited = set(re.findall(r'\b(\d\d-\d\d-\d{3}[A-Z]?)\b', page))
    mine = sorted((f for f in F.values() if f['num_issue'] in INTERVAL and f['types'] & set(XC_TYPES)
                   and any(re.search(XC_AGENCY[a], n, re.I) for n in f['agencies'])), key=lambda f: f['wsr'])
    others = sorted(w for w in cited if w[:5] in INTERVAL and w not in {f['wsr'] for f in mine})
    resolved_others = {w: (sorted(F[w]['types']), F[w]['agencies']) for w in others if w in F}
    cross = []
    for f in mine:
        target = f'wa-f-{f["wsr"]}-pdf'
        hit = f['wsr'] in cited
        cross.append({'against_entry_id': target, 'lineage_id': 'wa-cro', 'result': 'matches' if hit else 'unresolved',
                      'detail': (f'agency page cites WSR {f["wsr"]}; existence and agency match (dates not compared at step 3)' if hit else
                                 f'WSR {f["wsr"]} not cited on this rolling agency page; absence is not evidence of omission')})
        proc = XC_TYPES[min(f['types'] & set(XC_TYPES))]
        prev = best.get(f['wsr'])
        if prev is None or (hit and not prev[2]):
            best[f['wsr']] = (proc, {'entry_id': k, 'against_entry_id': target, 'scope': 'partial',
                'scope_basis': f'{k}: rolling {a.upper()} rule-making page captured 2026-10-15; expected to list only current/recent {a.upper()} proceedings, not every interval filing',
                'expected_unit_ids': [f['wsr']], 'matched_unit_ids': [f['wsr']] if hit else [], 'mismatched_unit_ids': [],
                'unresolved_unit_ids': [] if hit else [f['wsr']]}, hit)
    unlisted = [w for w in others if w not in F]
    capture_entry(k, 'portal_slice', None,
                  ev(f'Independent-lineage {a.upper()} rule-making page ({XC_TERMS[a]}). Cites {len(cited)} WSR-like numbers; '
                     f'{len([f for f in mine if f["wsr"] in cited])}/{len(mine)} of {a.upper()} interval PREP/PROP/EXPE filings cited. '
                     f'Other interval numbers cited resolve to Register filings: {resolved_others}; unresolved: {unlisted}',
                     ['rights/DECISIONS.md#5', 'rights/surfaces.json#wa-agency-rulemaking@2026-10-15.4'], '26-11', k),
                  'wa-state-agencies', 'cr102-proposal-family', 'interval 26-11..26-16 (rolling page captured 2026-10-15)',
                  terminal=[f'{k}: single rolling HTML page, no pagination; captured 2026-10-15'], cross=cross,
                  completeness=None if not unlisted else 'gap',
                  review_ref=gap(f'agency-unlisted-{k}', f'{k} cites interval WSR numbers absent from the Register listings: {unlisted}') if unlisted else None,
                  src=f'wa-agency-{a}')
    entries[-1]['lineage_id'] = f'wa-agency-{a}'
    entries[-1]['rights'] = rights('wa-agency-rulemaking')
for w, (proc, chk, hit) in sorted(best.items()):
    coverage_checks[proc].append(chk)

gap('holdover-double-publication', 'Holdover filings are printed in full (incl. Original Notice cover) in both the numbering issue and a later issue (e.g. 26-09-129: 26-09 PROP pp.287-291 and 26-11 PROP pp.1-2; 26-10-027: 26-10 and 26-12). Earliest evidenced publication = numbering issue, so 26-09-129 and 26-10-027 are carry-in candidates, not new notices; 26-16-038/057/075 publish first in 26-16 (in interval). Step-5 mandatory review of publication-date attribution.')
# ---------- write
with open('WA/manifest.jsonl', 'w') as out:
    for e in entries:
        out.write(json.dumps(e, ensure_ascii=False, sort_keys=False) + '\n')

procs = sorted({(e['agency_id'], e['process_id']) for e in entries})
SL = gap('single-lineage', 'No independent-lineage source covers this process (agency cross-checks only reach HCA and L&I PREP/PROP/EXPE filings; DOH/DOL/WDFW/DCYF skipped on terms; Ecology pointer-only). single_lineage=true caps completeness at not_established.')
def process_row(a, p):
    if a == 'wa-state-agencies' and p in coverage_checks:
        t = {v: k for k, v in XC_TYPES.items()}[p]
        units = sorted((f for f in F.values() if f['num_issue'] in INTERVAL and t in f['types'] and agency_group(f['agencies']) == a), key=lambda f: f['wsr'])
        return {'agency_id': a, 'process_id': p, 'single_lineage': False, 'human_review_ref': None,
                'coverage': {'mode': 'independent_partial', 'unit_kind': 'proceeding',
                    'universe_basis': f'Every {t} filing numbered in interval issues 26-11..26-16 whose filer is a state agency (local clean-air agencies and the Columbia River Gorge Commission excluded per SCOPE Q2), from the issue pages wa-issue-26-11..16 captured 2026-10-15. Unit = one WSR filing number (acquisition-time proxy for a proceeding/notice; step-4 enumeration may split or merge). Carry-ins are not in this denominator.',
                    'universe': [{'unit_id': f['wsr'], 'agency_id': slug(f['agencies'][0])} for f in units],
                    'checks': coverage_checks[p], 'claim_agency_ids': [], 'completeness': 'not_established'}}
    return {'agency_id': a, 'process_id': p, 'single_lineage': True, 'human_review_ref': SL}
now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
run = {
    'schema_version': '1.0.0', 'synthetic': False, 'state': 'WA', 'universe_version': UV,
    'scope_resolved': True, 'history_bounded': True, 'attended': False,
    'rights_file': '../../rights/surfaces.json',
    'processes': [process_row(a, p) for a, p in procs],
    'brief_file': 'brief.txt',
    'brief_sha256': None,
    'brief_frozen_at': None,
    'passes': [], 'crosswalk': [],
    'completeness_review_ref': review('completeness-verdict'),
    'mandatory_review_refs': list(gaps),
    'temporal_log': [],
    'audit': {'seed': None, 'frame_hash': None, 'coarsening_level': 0, 'frozen_before_seed': False,
              'mandatory_minutes_estimate': 0, 'overlap_minutes': 0, 'estimate_minutes': 0, 'actual_minutes': 0,
              'strata': [], 'unit_coverage': {}, 'coarsening_history': []},
    'credits': [{'state': s, 'actual': 0, 'outstanding': 0, 'reserve_released': 0, 'primary_release_ref': None, 'reviewer_minutes': 0}
                for s in ['WA', 'CT', 'VA', 'TN']],
}
json.dump(run, open('WA/run.json', 'w'), indent=2); open('WA/run.json', 'a').write('\n')
json.dump({'gaps': gaps, 'dates': DATES}, open('/tmp/wa-acq/gaps.json', 'w'), indent=1)
c = collections.Counter((e['kind'], e['retrieval']['result']) for e in entries)
print(len(entries), dict(c))
print('text_layer', collections.Counter((e['format'], e['text_layer']) for e in entries))
print('completeness', collections.Counter(e['completeness'] for e in entries))
print('gaps', len(gaps)); [print(' ', k, '|', v[:160]) for k, v in gaps.items()]
