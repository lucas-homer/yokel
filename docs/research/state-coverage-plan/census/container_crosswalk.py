#!/usr/bin/env python3
"""Build provisional source-row/union-label crosswalks, without any seed or review.

Usage: container_crosswalk.py VA [--inputs DIR] [--pdf-text-dir DIR] [--output FILE]
VA reuses the retained source splitter and conservative matching from VA/reconcile.
Its native PDF page JSON is an existing PDFKit derivative (stdlib cannot extract
arbitrary PDF text); --pdf-text-dir makes that dependency explicit and relocatable.
Other states use conservative HTML/XML/JSON listing rows. Unsupported PDF/container
formats fail closed rather than emitting a misleading empty crosswalk. No other
state's passes are read. Source text stays in memory; output uses fingerprints.
"""
import argparse
import bisect
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urldefrag, urlsplit

HOME = Path(__file__).resolve().parent
ROOT = HOME.parents[3]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def read(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def issue(mid):
    match = re.fullmatch(r'va-(\d+)-(\d+)-(?:pdf|toc|s\d+)', mid)
    return f'va-{int(match[1])}-{int(match[2]):02d}-' if match else None


def original_manifest(directory, inputs):
    """Canonical manifest supplies membership/hash; pass manifest supplies paths only."""
    paths = {r['entry_id']: r for r in read(inputs/'manifest.pass.jsonl')} if (inputs/'manifest.pass.jsonl').exists() else {}
    result = {}
    for row in read(directory/'manifest.jsonl'):
        if row['retrieval']['result'] != 'retrieved':
            continue
        eid = row['entry_id']
        relative = paths.get(eid, {}).get('original_path', 'originals/'+row['retrieval']['sha256'])
        path = (inputs/relative).resolve()
        if not path.is_relative_to(inputs.resolve()):
            raise ValueError(f'{eid}: original path escapes inputs')
        if sha(path) != row['retrieval']['sha256']:
            raise ValueError(f'{eid}: original hash mismatch')
        result[eid] = {**row, 'original_path': relative}
    return result


def va_rows(directory, inputs, pdf_text_dir):
 OUT = directory/'reconcile'
 ci = module('source_inventory', HOME/'VA/reconcile/container-inventory.py')
 compare = module('sealed_comparison', HOME/'VA/reconcile/reconcile.py')
 ci.INPUTS = inputs
 ci.PDF_CACHE = pdf_text_dir
 inv=json.loads((OUT/'container-inventory.json').read_text())['containers']
 labels=[r for s in 'AB' for r in compare.latest(read(OUT.parent/f'pass-{s}.jsonl'))
         if r['record_type'] in ('notice','rejected_candidate')]
 by_issue=collections.defaultdict(list)
 for r in labels:
  for key in {issue(e['manifest_entry_id']) for e in compare.evidence(r)}-{None}:by_issue[key].append(r)
 # Reuse the exact source-item splitter; retain raw text only in this process.
 original_item=ci.item
 def raw_item(text,*args,**kw):return {**original_item(text,*args,**kw),'_source_text':text}
 ci.item=raw_item
 manifest=original_manifest(directory, inputs)
 sources={};html=collections.defaultdict(list);native={};groups={}
 for mid,c in inv.items():
  if c['container_kind']!='html_issue_section':continue
  b=(ci.INPUTS/manifest[mid]['original_path']).read_bytes();assert hashlib.sha256(b).hexdigest()==c['original_sha256']
  parser=ci.DOM();parser.feed(b.decode(errors='replace'))
  its=ci.section_items(parser.root,mid[-2:]);assert len(its)==c['item_count']
  for it,old in zip(its,c['items']):
   assert (it['word_count'],it['heading_fingerprint'])==(old['word_count'],old['heading_fingerprint'])
  for ordinal, it in enumerate(its, 1):
   it['_source_entry_id']=mid
   it['_source_locator']=f'Complete original HTML item {ordinal}, through its closing identifier or next item heading'
  sources[mid]=its;html[issue(mid)].extend(its)
 for mid,c in inv.items():
  if c['container_kind']!='issue_pdf':continue
  assert sha(ci.INPUTS/manifest[mid]['original_path'])==c['original_sha256']
  pages=json.loads((ci.PDF_CACHE/(mid+'.json')).read_text());text='\n'.join(pages)
  pn=[ci.norm(p) for p in pages];offsets=[];offset=0
  for page in pn:offsets.append(offset);offset+=len(page)+1
  native[mid]=(pn,offsets,ci.norm(text))
  closings=list(ci.CLOSE.finditer(text));raw=[]
  for i,old in enumerate(c['items'][:len(closings)]):
   doc=closings[i][1].upper();assert doc in old['doc_numbers']
   matches=[x for x in html[issue(mid)] if doc in x['doc_numbers']]
   if matches:
    it=min(matches,key=lambda x:(abs(x['word_count']-old['word_count']),x['heading_fingerprint'],x['word_count']))
    raw.append({**old,'_source_text':it['_source_text'], '_source_entry_id':it['_source_entry_id'], '_source_locator':it['_source_locator']})
   else:
    start=closings[i-1].end() if i else max(text.find('PETITIONS FOR RULEMAKING',100),text.find('NOTICES OF INTENDED REGULATORY ACTION',100),0)
    if start>closings[i].start():start=0
    page_starts=[];offset=0
    for page in pages:page_starts.append(offset);offset+=len(page)+1
    first=bisect.bisect_right(page_starts,start);last=bisect.bisect_right(page_starts,closings[i].end()-1)
    raw.append({**old,'_source_text':text[start:closings[i].end()], '_source_entry_id':mid,
                '_source_locator':f'PDF pages {first}–{last}; Doc. No. {doc}. Read the complete page span (including boundary context), not the approximate extracted segment'})
  guidance=ci.guidance_items(pages)
  end=len(c['items'])-len(guidance)
  for old in c['items'][len(closings):end]:
   matches=[x for x in html[issue(mid)] if x['heading_fingerprint']==old['heading_fingerprint'] and x['word_count']==old['word_count']]
   assert matches,(mid,old['item_ordinal'],'no retained HTML source')
   it=matches[0]
   raw.append({**old,'_source_text':it['_source_text'], '_source_entry_id':it['_source_entry_id'],
               '_source_locator':it['_source_locator']+('; expanded issue inventory: PDF counterpart not located; compare the retained HTML original and PDF, do not infer PDF presence' if 'not located' in old['method'] else '')})
  cursor=0
  for it,old in zip(guidance,c['items'][end:]):
   assert (it['word_count'],it['heading_fingerprint'])==(old['word_count'],old['heading_fingerprint'])
   fragment=ci.norm(it['_source_text']);start=native[mid][2].find(fragment,cursor)
   assert start>=0,(mid,old['item_ordinal'],'guidance native span absent')
   cursor=start+len(fragment)
   raw.append({**old,'_source_text':it['_source_text'],'_native_span':(start,cursor)})
  assert len(raw)==c['item_count'];sources[mid]=raw
  if mid[:-3]+'toc' in inv:sources[mid[:-3]+'toc']=raw
  gg=[]
  for r in by_issue[issue(mid)]:
   if r['record_type']!='rejected_candidate' or 'entireagencylisting' not in r['payload']['rationale'].replace(' ','').casefold():continue
   for e in r['evidence']:
    if issue(e['manifest_entry_id'])!=issue(mid):continue
    m=re.fullmatch(r'PDF page (\d+), annual guidance inventory: .+; all continuation through PDF page (\d+)',e['locator'])
    if not m:continue
    first,last=map(int,m.groups());title=ci.norm(e['quote_or_mark_description'])
    pos=pn[first-1].find(title)
    if pos<0:continue  # No inferred agency boundary from label wording alone.
    gg.append({'start':offsets[first-1]+pos,'end':offsets[last] if last<len(pn) else len(native[mid][2]),
               'record_id':r['record_id'],'first_page':first,'last_page':last})
  for g in gg:g['end']=min([g['end']]+[h['start'] for h in gg if h['start']>g['start']])
  groups[mid]=gg
 rows=[]
 for mid,c in sorted(inv.items()):
  raw=sources[mid];pdf=issue(mid)+'pdf';local=by_issue[issue(mid)]
  normtext=[ci.norm(it['_source_text']) for it in raw]
  bodykey=[hashlib.sha256(t.encode()).hexdigest() for t in normtext]
  candidates=collections.defaultdict(dict)
  for r in local:
   docs=set(compare.doc_aliases(r))
   for e in compare.evidence(r):docs.update(x.upper() for x in ci.CLOSE.findall(e.get('quote_or_mark_description','')))
   if docs:
    for k,it in enumerate(raw):
     if docs.intersection(it['doc_numbers']):candidates[k][r['record_id']]='exact Doc. No. in same issue'
    continue  # A numbered action must not cover a different unnumbered item
              # just because a generic title/contact quote also appears there.
   # Direct, unique source aliases/quotes for notices without native Doc. No.
   needles=[ci.norm(a['native_id']) for a in r['aliases'] if len(ci.norm(a['native_id']))>=6 and not compare.DOC.search(a['native_id'])]
   needles += [ci.norm(e['quote_or_mark_description']) for e in compare.evidence(r)
     if e['manifest_entry_id'] in (mid,pdf,issue(mid)+'toc') and
        len(re.findall(r'[A-Za-z]{2,}',e['quote_or_mark_description']))>=5 and len(e['quote_or_mark_description'])>=30]
   for needle in set(needles):
    hits=[k for k,it in enumerate(raw) if not it['doc_numbers'] and not it['kind'].startswith('guidance_catalogue_') and ' '+needle+' ' in ' '+normtext[k]+' ']
    if len({bodykey[k] for k in hits})==1:
     for k in hits:candidates[k].setdefault(r['record_id'],'unique exact native alias/evidence text in container')
  for k,it in enumerate(raw):
   span=it.get('_native_span');catalogue=it['kind']=='guidance_catalogue_row'
   if catalogue and span:
    gg=[g for g in groups[pdf] if g['start']<=span[0] and span[1]<=g['end']]
    if len({(g['start'],g['end']) for g in gg})==1:
     for g in gg:candidates[k][g['record_id']]='explicit whole-agency catalogue rejection; native row wholly inside declared agency span'
   matched=candidates[k]
   labelmap={r['record_id']:r for r in local}
   refs=sorted(matched,key=lambda rid:(labelmap[rid]['record_type']!='notice',rid))
   status='accounted' if refs else 'unaccounted'
   rows.append({'container_id':mid,'item_ordinal':k+1,'item_kind':it['kind'],
    'heading_fingerprint':it['heading_fingerprint'],'doc_numbers':it['doc_numbers'],
    'native_text_fingerprint':bodykey[k],
    'item_frame_status':'resolved', 'complete_item':not catalogue,
    'source_entry_id':it.get('_source_entry_id', pdf),
    'source_locator':it.get('_source_locator') or (f'PDF pages {bisect.bisect_right(native[pdf][1],span[0])}–{bisect.bisect_right(native[pdf][1],span[1]-1)}; '+('catalogue pointer row, linked body unsupplied' if catalogue else 'complete guidance publication notice') if span else None),
    'native_pdf_pages':([bisect.bisect_right(native[pdf][1],span[0]),bisect.bisect_right(native[pdf][1],span[1]-1)] if span else None),
    'accounting_status':status,'union_record_id':refs[0] if refs else None,
    'union_label_matches':[{'record_id':rid,'disposition':'rejected' if labelmap[rid]['record_type']=='rejected_candidate' else 'accepted',
      'method':matched[rid]} for rid in refs],
    'accept_reject_conflict':len({labelmap[rid]['record_type'] for rid in refs})>1,
    'unaccounted_reason':None if refs else 'No conservative native-identity, unique-text or explicit whole-agency-span mapping; unresolved source boundary/identity is not treated as an omission verdict.'})
 return rows

def generic_rows(directory, inputs, manifest, skip=()):
    # Reuse the VA DOM, normalization, evidence and latest-head semantics.
    ci = module('generic_inventory', HOME/'VA/reconcile/container-inventory.py')
    compare = module('generic_union', HOME/'VA/reconcile/reconcile.py')
    labels = [r for side in 'AB' for r in compare.latest(read(directory/f'pass-{side}.jsonl'))
              if r['record_type'] in ('notice', 'rejected_candidate')]
    def url_key(url):
        value = urlsplit(urldefrag(url)[0])
        return (value.netloc.casefold(), value.path, value.query)
    urls = {}
    for eid, e in manifest.items():
        for field in ('requested_url', 'final_url'):
            if e['retrieval'].get(field):
                urls.setdefault(url_key(e['retrieval'][field]), eid)
    rows = []
    for mid, entry in sorted(manifest.items()):
        if mid in skip or entry['kind'] not in ('issue', 'index', 'portal_slice', 'history_slice'):
            continue
        data = (inputs/entry['original_path']).read_bytes()
        content_type = entry['retrieval'].get('content_type', '') or ''
        if entry['format'] in ('text_pdf', 'scan_pdf'):
            raise ValueError(f'{mid}: PDF listing needs a verified source-item adapter/native derivative')
        links = []
        if entry['format'] == 'json':
            payload = json.loads(data)
            if isinstance(payload, dict):
                arrays = [v for v in payload.values() if isinstance(v, list)]
                if len(arrays) != 1:
                    raise ValueError(f'{mid}: ambiguous JSON row array')
                payload = arrays[0]
            if not isinstance(payload, list):
                raise ValueError(f'{mid}: no JSON row array')
            items = [json.dumps(v, sort_keys=True, ensure_ascii=False) for v in payload]
        elif 'xml' in content_type or data.lstrip().startswith(b'<?xml'):
            root = ET.fromstring(data)
            nodes = [n for n in root.iter() if n.tag.split('}')[-1] in ('item', 'entry')]
            if not nodes:
                raise ValueError(f'{mid}: XML listing has no identifiable rows')
            items = [' '.join(n.itertext()) for n in nodes]
            links = [[(x.text or x.attrib.get('href', '')) for x in n.iter() if x.tag.split('}')[-1] == 'link'] for n in nodes]
        else:
            parser = ci.DOM()
            parser.feed(data.decode(errors='replace'))
            nodes = list(parser.root.descend())
            # Prefer table/list rows. Outermost rows prevent double-counting nested lists.
            candidates = [n for n in nodes if n.tag in ('tr', 'li') and ci.norm(n.text())]
            nested = {id(n) for parent in candidates for n in parent.descend()}
            candidates = [n for n in candidates if id(n) not in nested]
            if not candidates:
                candidates = [n for n in nodes if n.tag == 'a' and ci.norm(n.text())]
            items = [n.text() for n in candidates]
            links = [[x.attrs['href'] for x in [n, *n.descend()] if x.tag == 'a' and x.attrs.get('href')] for n in candidates]
            if not items:
                raise ValueError(f'{mid}: listing has no identifiable rows; source adapter required')
        local = [r for r in labels if any(e['manifest_entry_id'] == mid for e in compare.evidence(r))]
        normalized = [ci.norm(t) for t in items]
        for ordinal, text in enumerate(normalized, 1):
            matches = []
            for label in local:
                # Generalize the unique exact alias/evidence rule, never blanket section rejection.
                needles = [ci.norm(a['native_id']) for a in label.get('aliases', [])]
                needles += [ci.norm(e.get('quote_or_mark_description', '')) for e in compare.evidence(label)
                            if e['manifest_entry_id'] == mid]
                if any(len(needle) >= 30 and len(needle.split()) >= 5
                       and ' '+needle+' ' in ' '+text+' '
                       and len({t for t in normalized if ' '+needle+' ' in ' '+t+' '}) == 1
                       for needle in needles):
                    matches.append(label)
            matches.sort(key=lambda r: (r['record_type'] != 'notice', r['record_id']))
            fingerprint = hashlib.sha256(text.encode()).hexdigest()
            base = entry['retrieval'].get('final_url', '')
            retained = sorted({urls[url] for link in (links[ordinal-1] if links else [])
                               if (url := url_key(urljoin(base, link.strip()))) in urls and urls[url] != mid})
            source = retained[0] if retained else mid
            parent = manifest[source].get('parent_entry_id')
            if retained and manifest[source]['kind'] == 'index' and parent in manifest and manifest[parent]['kind'] == 'issue':
                source = parent  # retained issue PDF supplies the complete body behind its TOC

            rows.append({'container_id': mid, 'item_ordinal': ordinal,
                         'item_kind': 'generic_listing_row', 'heading_fingerprint': fingerprint,
                         'item_frame_status': 'resolved', 'complete_item': bool(retained),
                         'source_entry_id': source,
                         'source_locator': ('Read complete retained linked document (all participation-bearing sections; full read if boundaries uncertain)' if retained else f'Original listing row {ordinal}; pointer only, no complete retained linked body'),
                         'native_text_fingerprint': fingerprint, 'doc_numbers': [], 'native_pdf_pages': None,
                         'accounting_status': 'accounted' if matches else 'unaccounted',
                         'union_record_id': matches[0]['record_id'] if matches else None,
                         'union_label_matches': [{'record_id': r['record_id'],
                            'disposition': 'accepted' if r['record_type'] == 'notice' else 'rejected',
                            'method': 'unique exact evidence/alias text in original container'} for r in matches],
                         'accept_reject_conflict': len({r['record_type'] for r in matches}) > 1,
                         'unaccounted_reason': None if matches else 'No conservative unique source/union-label match; source boundaries need review.'})
    return rows


def ms_bulletin_rows(payload):
    """SOS BulletinSearch $.d wire rows: 12 tilde fields, caret rows, |count|page.

    Field 8 is the system number, fields 9–11 are attachment filenames. Never
    search free text for numbers (titles can mention other filings). Only the
    retained, unpaginated page-0 shape is supported; counts/caps fail closed.
    """
    if not isinstance(payload, dict) or set(payload) != {'d'} or not isinstance(payload['d'], str):
        raise ValueError('unsupported MS BulletinSearch JSON envelope')
    parts = payload['d'].rsplit('|', 2)
    if len(parts) != 3 or not re.fullmatch(r'0|[1-9][0-9]*', parts[1]) or parts[2] != '0':
        raise ValueError('invalid MS BulletinSearch count/page trailer')
    body, count, _ = parts
    raw = body.split('^') if body else []
    if len(raw) != int(count) or int(count) >= 1000:
        raise ValueError('MS BulletinSearch count mismatch or pagination cap reached')
    rows, seen = [], set()
    for text in raw:
        fields = text.split('~')
        if len(fields) != 12 or fields[1] not in ('True', 'False') or not fields[0].strip():
            raise ValueError('unsupported MS BulletinSearch row fields')
        if not re.fullmatch(r'[1-9][0-9]*', fields[8]):
            raise ValueError('invalid MS BulletinSearch system number')
        number = fields[8]
        if number in seen:
            raise ValueError('duplicate MS BulletinSearch system number')
        seen.add(number)
        for filename in fields[9:]:
            if filename == 'Not Found':
                continue
            match = re.fullmatch(r'([0-9]{8})[a-z]\.pdf', filename)
            if not match or int(match[1]) != int(number):
                raise ValueError('MS BulletinSearch attachment/system number mismatch')
        rows.append((number, text))
    return rows


def ms_rows(directory, inputs, manifest):
    """MS identity crosswalk; scan forms remain independent full-read units.

    For agency pages whose row/body boundaries have no verified adapter, use
    ONE conservative whole-original span, unaccounted, requiring a full read.
    This is not an assertion that the page has only one listing. Empty responses
    similarly retain a document-verification span, not a fictitious filing row:
    build_frames requires a nonempty complete-source pool for every index/slice.
    Neither fallback licenses an abbreviated participation-only read.
    """
    compare = module('ms_union', HOME/'VA/reconcile/reconcile.py')
    labels = [r for side in 'AB' for r in compare.latest(read(directory/f'pass-{side}.jsonl'))
              if r['record_type'] in ('notice', 'rejected_candidate')]
    by_number = collections.defaultdict(dict)
    for label in labels:
        numbers = {str(int(a['native_id'])) for a in label.get('aliases', [])
                   if a['source_id'] in ('ms-sos-acproposed', 'ms-sos-bulletin-service')
                   and re.fullmatch(r'[0-9]+', a['native_id'])}
        anchors = {match[1] for e in label['evidence']
                   if (match := re.fullmatch(r'ms-form-([1-9][0-9]*)', e['manifest_entry_id']))}
        # Form anchors identify the retained source even when a handwritten
        # accession alias is disputed. Never let such an alias cover another row.
        # Multiple-source evidence needs one corroborated alias; otherwise leave
        # the identity unresolved instead of fanning a label out across filings.
        numbers = (anchors if len(anchors) == 1 else numbers & anchors) if anchors else numbers
        if len(numbers) != 1:
            continue
        for number in numbers:
            by_number[number][label['record_id']] = label
    agency_pages = {'ms-xchk-mdeq-regulations-page', 'ms-xchk-mid-proposed-regulations-page',
                    'ms-xchk-mdeq-wp-sitemap'}
    rows = []
    for mid, entry in sorted(manifest.items()):
        if entry['kind'] not in ('issue', 'index', 'portal_slice', 'history_slice'):
            continue
        data = (inputs/entry['original_path']).read_bytes()
        if entry['kind'] == 'portal_slice' and entry['format'] == 'json' and entry['source_id'] == 'ms-sos-bulletin-service':
            try:
                items = ms_bulletin_rows(json.loads(data))
            except ValueError as exc:
                raise ValueError(f'{mid}: {exc}') from exc
        elif mid in agency_pages and entry['kind'] == 'index' and entry['format'] == 'html':
            items = None
            if mid.endswith('wp-sitemap'):
                root = ET.fromstring(data)
                if root.tag.split('}')[-1] != 'urlset' or list(root):
                    raise ValueError(f'{mid}: unsupported nonempty MS sitemap')
        else:
            raise ValueError(f'{mid}: unsupported MS container; source adapter required')
        fallback = not items
        if fallback:
            # Keep the whole original, including hidden HTML, in the source span.
            items = [(None, data.decode('utf-8'))]
        for ordinal, (number, text) in enumerate(items, 1):
            empty = fallback and (mid not in agency_pages or mid.endswith('wp-sitemap'))
            matches = list(by_number[number].values()) if number else []
            if empty:
                matches = [r for r in labels if r['record_type'] == 'rejected_candidate'
                           and any(e['manifest_entry_id'] == mid for e in compare.evidence(r))]
            matches.sort(key=lambda r: (r['record_type'] != 'notice', r['record_id']))
            source = 'ms-form-'+number if number and 'ms-form-'+number in manifest else mid
            complete = fallback or source != mid
            fingerprint = hashlib.sha256(text.encode()).hexdigest()
            rows.append({'container_id': mid, 'item_ordinal': ordinal,
                'item_kind': 'empty_listing_verification' if empty else 'full_original_fallback' if fallback else 'ms_bulletin_filing_row',
                'heading_fingerprint': fingerprint, 'native_text_fingerprint': fingerprint,
                'item_frame_status': 'resolved', 'complete_item': complete,
                'source_entry_id': source,
                'source_locator': ('Read full original; verified empty listing, no filing items; document verification only'
                    if empty else 'Read full original agency page, including every listed item, hidden section and participation passage; no verified row/body splitter'
                    if fallback else f'Read full original linked filing form (all pages), SOS system number {number}'
                    if complete else f'Original $.d row {ordinal}, SOS system number {number}; linked form not retained, explicit source gap'),
                'doc_numbers': [number] if number else [], 'native_pdf_pages': None,
                'accounting_status': 'accounted' if matches else 'unaccounted',
                'union_record_id': matches[0]['record_id'] if matches else None,
                'union_label_matches': [{'record_id': r['record_id'],
                    'disposition': 'accepted' if r['record_type'] == 'notice' else 'rejected',
                    'method': 'exact SOS system number alias or original form evidence anchor' if number else 'verified empty original and direct document rejection'} for r in matches],
                'accept_reject_conflict': len({r['record_type'] for r in matches}) > 1,
                'unaccounted_reason': None if matches else 'Whole original agency page requires full read; no inferred row boundaries or blanket page rejection'
                    if fallback else 'No exact SOS system number in latest union notice/rejection aliases or form evidence.'})
    return rows


def wa_rows(directory, inputs, manifest, pdf_text_dir):
    """WA has its own splitter; VA/MS code and serialized output stay unchanged."""
    adapter = module('wa_container_rows', HOME/'WA/reconcile/container_rows.py')
    return adapter.build(directory, inputs, manifest, pdf_text_dir or Path('/private/tmp/wa-reconcile-tools/native-text'))


def build_rows(directory, inputs=None, pdf_text_dir=None):
    run = json.loads((directory/'run.json').read_text())
    inputs = inputs or ROOT/'.census-passes'/run['state']/'inputs'
    manifest = original_manifest(directory, inputs)
    if run['state'] == 'VA':
        pdf_dir = pdf_text_dir or inputs/'native-text'
        if not pdf_dir.is_dir() and pdf_text_dir is None:
            pdf_dir = Path('/private/tmp/va-reconcile-tools/issue-text')
        rows = va_rows(directory, inputs, pdf_dir)
        rows.extend(generic_rows(directory, inputs, manifest, skip={r['container_id'] for r in rows}))
        return rows
    if run['state'] == 'MS':
        return ms_rows(directory, inputs, manifest)
    if run['state'] == 'WA':
        return wa_rows(directory, inputs, manifest, pdf_text_dir)
    return generic_rows(directory, inputs, manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('state_dir', type=Path, help='State code or directory containing manifest/pass files')
    parser.add_argument('--inputs', type=Path)
    parser.add_argument('--pdf-text-dir', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    directory = args.state_dir if args.state_dir.is_dir() else HOME/args.state_dir
    run = json.loads((directory/'run.json').read_text())
    rows = build_rows(directory, args.inputs, args.pdf_text_dir)
    target = args.output or directory/'reconcile/container-crosswalk.jsonl'
    target.parent.mkdir(parents=True, exist_ok=True)
    # Complete all extraction and matching before replacing the output.
    encoded = ''.join(json.dumps(r, sort_keys=True, separators=(',', ':'))+'\n' for r in rows)
    target.write_text(encoded)
    print(json.dumps({'state': run['state'], 'containers': len({r['container_id'] for r in rows}),
                      'rows': len(rows), 'unaccounted': sum(r['accounting_status'] == 'unaccounted' for r in rows),
                      'sha256': sha(target), 'seed': None}))


if __name__ == '__main__':
    main()
