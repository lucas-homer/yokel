#!/usr/bin/env python3
"""Unsampled, provisional listed-item accounting; never a human verdict.

Original source text stays in memory. Output contains fingerprints and sealed
record pointers, not source/commenter text. Unknown/ambiguous mappings remain
unaccounted. No sampling, seed, pass edits or accounting coverage claim.
"""
import collections
import bisect
import hashlib
import importlib.util
import json
from pathlib import Path
import re

OUT=Path(__file__).resolve().parent
def module(name,file):
 spec=importlib.util.spec_from_file_location(name,OUT/file)
 result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
ci=module('source_inventory','container-inventory.py')
compare=module('sealed_comparison','reconcile.py')
def read(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def issue(mid):
 m=re.fullmatch(r'va-(\d+)-(\d+)-(?:pdf|toc|s\d+)',mid)
 return f'va-{int(m[1])}-{int(m[2]):02d}-' if m else None
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
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
 manifest={r['entry_id']:r for r in read(ci.INPUTS/'manifest.pass.jsonl') if r['retrieval']['result']=='retrieved'}
 sources={};html=collections.defaultdict(list);native={};groups={}
 for mid,c in inv.items():
  if c['container_kind']!='html_issue_section':continue
  b=(ci.INPUTS/manifest[mid]['original_path']).read_bytes();assert hashlib.sha256(b).hexdigest()==c['original_sha256']
  parser=ci.DOM();parser.feed(b.decode(errors='replace'))
  its=ci.section_items(parser.root,mid[-2:]);assert len(its)==c['item_count']
  for it,old in zip(its,c['items']):
   assert (it['word_count'],it['heading_fingerprint'])==(old['word_count'],old['heading_fingerprint'])
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
    raw.append({**old,'_source_text':it['_source_text']})
   else:
    start=closings[i-1].end() if i else max(text.find('PETITIONS FOR RULEMAKING',100),text.find('NOTICES OF INTENDED REGULATORY ACTION',100),0)
    if start>closings[i].start():start=0
    raw.append({**old,'_source_text':text[start:closings[i].end()]})
  guidance=ci.guidance_items(pages)
  end=len(c['items'])-len(guidance)
  for old in c['items'][len(closings):end]:
   matches=[x for x in html[issue(mid)] if x['heading_fingerprint']==old['heading_fingerprint'] and x['word_count']==old['word_count']]
   assert matches,(mid,old['item_ordinal'],'no retained HTML source')
   raw.append({**old,'_source_text':matches[0]['_source_text']})
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
 rows=[];summary={}
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
    'native_pdf_pages':([bisect.bisect_right(native[pdf][1],span[0]),bisect.bisect_right(native[pdf][1],span[1]-1)] if span else None),
    'accounting_status':status,'union_record_id':refs[0] if refs else None,
    'union_label_matches':[{'record_id':rid,'disposition':'rejected' if labelmap[rid]['record_type']=='rejected_candidate' else 'accepted',
      'method':matched[rid]} for rid in refs],
    'accept_reject_conflict':len({labelmap[rid]['record_type'] for rid in refs})>1,
    'unaccounted_reason':None if refs else 'No conservative native-identity, unique-text or explicit whole-agency-span mapping; unresolved source boundary/identity is not treated as an omission verdict.'})
  rr=rows[-len(raw):];un=sum(r['accounting_status']=='unaccounted' for r in rr);accounted=len(rr)-un
  summary[mid]={'listed_rows':len(rr),'accounted_rows':accounted,'unaccounted_rows':un,
   'verification_rows':min(accounted,5),'owner_accounting_minutes':3+un+min(accounted,5)}
 with (OUT/'container-crosswalk.jsonl').open('w') as f:
  for r in rows:f.write(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n')
 output={'status':'Script-produced provisional crosswalk, not an owner-verified completeness finding; no seed or sample',
  'input_versions':{str(p.relative_to(OUT.parents[5])):sha(p) for p in [OUT.parent/'pass-A.jsonl',OUT.parent/'pass-B.jsonl',OUT/'container-inventory.json',Path(__file__).resolve()]},
  'crosswalk_sha256':sha(OUT/'container-crosswalk.jsonl'),'container_count':len(summary),'listed_row_instances':len(rows),
  'accounted_row_instances':sum(x['accounted_rows'] for x in summary.values()),
  'unaccounted_row_instances':sum(x['unaccounted_rows'] for x in summary.values()),
  'accept_reject_conflict_row_instances':sum(r['accept_reject_conflict'] for r in rows),
  'containers':summary,'seed':None,'selected_verification_rows':[],
  'method':['Latest notice/rejected-candidate heads from both passes; accepted means a pass inclusion, not a human verdict.',
   'Exact Doc. No. plus issue (padding normalized), or unique exact native alias/evidence wording in the container. Repeated identical display bodies may share a label. No generic section rejection blanket-maps its children.',
   'Catalogue rows map many-to-one only where a label explicitly rejects the entire agency listing and its native heading/page span wholly contains the row. Boundary-crossing rows remain unaccounted. Residual/unsupplied identities remain unresolved.',
   'Unaccounted is a conservative crosswalk failure, not proof the passes omitted an item. Agency grouping, source splitting and matches need verification.',
   'Verification sample size is min(accounted rows,5); all unaccounted rows are additional. Primary scripting is excluded from owner minutes. PDF/TOC inventories repeat in baseline and are paired once from step 1.']}
 (OUT/'container-crosswalk-summary.json').write_text(json.dumps(output,indent=2)+'\n')
 print(json.dumps({k:v for k,v in output.items() if k not in ('containers','input_versions','method')},indent=2))
if __name__=='__main__':main()
