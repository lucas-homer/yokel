#!/usr/bin/env python3
"""Unsampled source-item sizing for the alternative container costing.

Read frozen VA originals only. PDF native text is a local PDFKit derivative
created by pdf-inventory.swift; no parser/label output supplies item lengths.
No source text, names of commenters, random selections or seeds are written.
"""
import collections
import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import statistics

OUT=Path(__file__).resolve().parent
INPUTS=OUT.parents[5]/'.census-passes/VA/inputs'
PDF_CACHE=Path('/private/tmp/va-reconcile-tools/issue-text')
CLOSE=re.compile(r'VA\.R\.\s*Doc\.?\s*No\.?\s*([A-Z]*\d+-\d+)\s*;\s*Filed[^\n]*',re.I)
SECTION_IDS={'04':'divPetitions','05':'divNOIRA','06':'divRegs','07':'divMisc',
             '08':'divGenNotices','10':'divPRSBIR','11':'divErrata'}
SECTION_LABELS={'04':'petition','05':'noira','06':'regulation_action','07':'governor_action',
                '08':'general_notice','10':'periodic_review','11':'erratum'}

def words(text):return len(re.findall(r'\S+',text))
def norm(text):return ' '.join(re.sub(r'[^a-z0-9]+',' ',text.casefold()).split())
class Node:
 def __init__(self,tag='',attrs=None):self.tag=tag;self.attrs=attrs or {};self.children=[]
 def text(self):
  if self.tag in ('script','style','head'):return ''
  return ' '.join(x if isinstance(x,str) else x.text() for x in self.children)
 def descend(self):
  for c in self.children:
   if isinstance(c,Node):yield c;yield from c.descend()
class DOM(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.root=Node();self.stack=[self.root]
 def handle_starttag(self,tag,attrs):
  node=Node(tag,dict(attrs));self.stack[-1].children.append(node)
  if tag not in ('br','hr','img','meta','link','input','wbr','area','base','embed','param','source','track','col'):self.stack.append(node)
 def handle_endtag(self,tag):
  for i in range(len(self.stack)-1,0,-1):
   if self.stack[i].tag==tag:del self.stack[i:];break
 def handle_data(self,text):self.stack[-1].children.append(text)

# Conservative passage sizing, not a substantive classification: technical
# hearings/petitions also qualify. Year-only matches deliberately overcount
# legislative citations rather than silently overlooking a possible date.
PARTICIPATION=re.compile(r'\b(?:comment\w*|hearing\w*|petition\w*|effective|dates?|objection\w*)\b',re.I)
MONTH=r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
DAY=r'(?:0?[1-9]|[12]\d|3[01])'
MON=r'(?:0?[1-9]|1[0-2])'
SEARCH=re.compile(r'\b(?:comment\w*|hearing\w*|objection\w*)\b|(?<![\w./-])(?:19|20)\d{2}-'+MON+'-'+DAY+r'\b|(?<![\w./-])'+MON+'/'+DAY+r'/\d{2,4}\b|(?<![\w./-])'+MON+'-'+DAY+r'-\d{2,4}\b|\b'+MONTH+r'\.?\s+'+DAY+r'(?:,?\s+\d{4})?\b|\b(?:19|20)\d{2}\b',re.I)
BODY=re.compile(r'^\d+\s*VAC\s*\d+[-–]\d+[-–]\d+\s*\.',re.I)

def participation_read(text,kind,blocks=None):
 """Size full preamble, selected full sections/paragraphs, residual hits.

 HTML paragraph boundaries/classes are preferred. PDF-only native blocks
 split at blank lines, or one native line when PDFKit supplies no paragraphs;
 adjacent blocks give context for residual search hits. Non-regulation notices
 are conservatively read in full, with no residual search body.
 """
 blocks=blocks or [{'text':s,'class':''} for s in re.split(r'\n\s*\n|\n',text) if s.strip()]
 blocks=[{'text':' '.join(b['text'].split()),'class':b.get('class','').casefold()} for b in blocks if b['text'].strip()]
 body=next((i for i,b in enumerate(blocks) if b['class']=='vacno' or BODY.match(b['text'])),None)
 # No reliable regulatory-body boundary: cost the whole item, not an
 # arbitrary truncated preamble. Short notices are intentionally full reads.
 if body is None or kind not in ('regulation_action','pdf_only_native_action'):
  wc=words(text)
  return {'preamble_participation_words':wc,'remaining_body_words':0,'search_hits':0,
   'search_hit_counts':{'date':0,'comment':0,'hearing':0,'objection':0},'hit_context_words':0,
   'word_rate_minutes':max(2,math.ceil(wc/250)+1),'minutes':max(2,math.ceil(wc/250)+1)+2,
   'method':'Conservative whole item: non-regulation notice or no reliable native body boundary'}
 selected=set(range(body));section=False
 # A participation-titled Part/Article governs its child sections too. A
 # title may be a separate centered paragraph after the Part/Article number.
 major=[(i,1 if b['class']=='part' else 2) for i,b in enumerate(blocks) if i>=body and b['class'] in ('part','article')]
 for i,rank in major:
  end=next((j for j,r in major if j>i and r<=rank),len(blocks))
  title=' '.join(b['text'] for b in blocks[i:min(i+3,end)] if b['class'] in ('part','article','center','center0'))
  if PARTICIPATION.search(title):selected.update(range(i,end))
 for i in range(body,len(blocks)):
  b=blocks[i]
  heading=b['class']=='vacno' or BODY.match(b['text'])
  if heading:section=bool(PARTICIPATION.search(b['text']))
  if section or PARTICIPATION.search(b['text']) or b['class'] in ('textbl','textbi','summary'):selected.add(i)
 # Text outside paragraph nodes (e.g. headings and closing identifiers) is
 # conservatively assigned to the full heading/preamble read.
 outside=max(0,words(text)-sum(words(b['text']) for b in blocks))
 wc=outside+sum(words(b['text']) for i,b in enumerate(blocks) if i in selected)
 counts=collections.Counter({'date':0,'comment':0,'hearing':0,'objection':0});context=set()
 for i,b in enumerate(blocks):
  if i in selected:continue
  for hit in SEARCH.finditer(b['text']):
   key=next((k for k in ('comment','hearing','objection') if hit[0].casefold().startswith(k)),'date')
   counts[key]+=1;context.update(j for j in range(max(0,i-1),min(len(blocks),i+2)) if j not in selected)
 hits=sum(counts.values());rate=max(2,math.ceil(wc/250)+1)
 return {'preamble_participation_words':wc,'remaining_body_words':sum(words(b['text']) for i,b in enumerate(blocks) if i not in selected),
  'search_hits':hits,'search_hit_counts':dict(counts),'hit_context_words':sum(words(blocks[i]['text']) for i in context),
  'word_rate_minutes':rate,'minutes':rate+hits+2,
  'method':'Full heading/preamble; full participation-titled Parts/Articles/VAC sections and every keyword paragraph; residual native hits with adjacent-paragraph context'}

def paragraph_blocks(nodes):
 return [{'text':n.text(),'class':n.attrs.get('class','')} for n in nodes]

def item(text,kind,heading='',method='',blocks=None):
 reading=None if kind.startswith('guidance_catalogue_') else participation_read(text,kind,blocks)
 text=' '.join(text.split());docs=[x.upper() for x in CLOSE.findall(text)]
 return {'kind':kind,'word_count':words(text),'doc_numbers':docs,
         'heading_fingerprint':hashlib.sha256(norm(heading or text[:160]).encode()).hexdigest(),
         'method':method,'_heading':heading or text[:160],**({'participation_read':reading} if reading else {})}

def section_items(root,code):
 target=next((n for n in root.descend() if n.attrs.get('id','').endswith('_'+SECTION_IDS[code])),None)
 assert target is not None,code
 if not words(target.text()):
  populated=[n for n in root.descend() if n.tag=='div' and
             n.attrs.get('id') in {'ContentPlaceHolder1_'+x for x in SECTION_IDS.values()} and words(n.text())]
  assert len(populated)==1,('Expected section body is empty; no unique original body',code)
  target=populated[0]  # Retained template misfiles some bodies under divErrata.
 wrapped=[n for n in target.children if isinstance(n,Node) and n.tag=='div' and n.attrs.get('class')=='inthisissue' and not n.attrs.get('id')]
 if wrapped:
  result=[]
  for n in wrapped:
   text=n.text().strip()
   position=target.children.index(n)
   for sibling in target.children[position+1:]:
    if not isinstance(sibling,Node):continue
    if sibling.attrs.get('class')=='inthisissueActNo':text+=' '+sibling.text()
    break  # The closing Doc. No. is a sibling, not part of the body div.
   if words(text):result.append(item(text,SECTION_LABELS[code],method='one original action-body wrapper',blocks=paragraph_blocks([p for p in n.descend() if p.tag=='p'])))
  return result
 paragraphs=[n for n in target.descend() if n.tag=='p' and n.text().strip()]
 if not paragraphs:
  text=target.text().strip()
  return [item(text,SECTION_LABELS[code],method='single original section body')] if words(text) else []
 starts=[]
 for i,p in enumerate(paragraphs):
  t=' '.join(p.text().split());cls=p.attrs.get('class','').casefold()
  if code=='04' and t.casefold() in ('initial agency notice','agency decision'):starts.append(i)
  elif code=='10' and t.casefold() in ('agency notice','initial agency notice'):starts.append(i)
  elif code=='07' and re.match(r'^(?:EXECUTIVE (?:ORDER|DIRECTIVE)|GOVERNOR.S (?:RECOMMENDATION|COMMENT)|Governor.s)',t):starts.append(i)
  elif code=='08' and 'center' in cls and t and not t.isupper() and re.search(r'[A-Za-z]{3}',t):starts.append(i)
 if code=='11' or not starts:
  # Errata/native-number notices end at a closing identifier; do not count
  # references inside a regulatory body as independent actions.
  result=[];begin=0
  for i,p in enumerate(paragraphs):
   t=' '.join(p.text().split())
   if re.match(r'^VA\.R\.\s*Doc\.?\s*No\.?',t,re.I) and CLOSE.search(t):
    result.append(item(' '.join(n.text() for n in paragraphs[begin:i+1]),SECTION_LABELS[code],method='original closing-identifier paragraph',blocks=paragraph_blocks(paragraphs[begin:i+1])));begin=i+1
  tail=' '.join(n.text() for n in paragraphs[begin:]).strip()
  if not result and tail:return [item(tail,SECTION_LABELS[code],method='single original section notice',blocks=paragraph_blocks(paragraphs[begin:]))]
  # Footer-free tail normally contains no separate body. Keep substantive
  # residuals explicit instead of claiming the item frame is complete.
  if words(tail)>30:result.append(item(tail,SECTION_LABELS[code],method='substantive unclosed section residual',blocks=paragraph_blocks(paragraphs[begin:])))
  return result
 result=[]
 for k,start in enumerate(starts):
  end=starts[k+1] if k+1<len(starts) else len(paragraphs)
  text=' '.join(n.text() for n in paragraphs[start:end])
  result.append(item(text,SECTION_LABELS[code],heading=paragraphs[start].text(),method='original notice/order heading to next notice/order',blocks=paragraph_blocks(paragraphs[start:end])))
 return result

def guidance_items(pages):
 start=next((i for i,p in enumerate(pages) if i>3 and p.strip().startswith('GUIDANCE DOCUMENTS')),None)
 if start is None:return []
 end=next((i for i,p in enumerate(pages[start+1:],start+1) if p.strip().startswith(('GENERAL NOTICES','ERRATA'))),len(pages))
 text='\n'.join(pages[start:end])
 # Certified-document publication notices: retain each full Titles/Title block.
 anchors=list(re.finditer(r'\bTitles? of Documents?\s*:',text,re.I))
 annual=re.search(r'(?:List|Listing) of Guidance Documents',text,re.I)
 result=[]
 for k,m in enumerate(anchors):
  stop=anchors[k+1].start() if k+1<len(anchors) else (annual.start() if annual and annual.start()>m.start() else len(text))
  if annual and m.start()>annual.start():continue
  result.append(item(text[m.start():stop],'guidance_notice',method='PDF guidance publication title block'))
 if annual:
  tail=text[annual.end():]
  # The annual catalogue actually lists individual retained rows. A row ends
  # at its printed revision/effective date; continuation lines belong to it.
  # Count these for accounting, not as one enormous umbrella rejection.
  boundaries=list(re.finditer(r'\b(?:\d{1,2}/\d{1,2}/\d{4}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\s*(?=\n|$)',tail))
  begin=0
  for m in boundaries:
   row=tail[begin:m.end()];begin=m.end()
   if words(row):result.append(item(row,'guidance_catalogue_row',method='PDF retained annual-catalogue row ending in printed date; linked external guidance is not supplied'))
  if words(tail[begin:])>25:result.append(item(tail[begin:],'guidance_catalogue_residual',method='PDF annual-catalogue undated residual; requires future inventory review'))
 return result

def main():
 manifest={r['entry_id']:r for r in map(json.loads,(INPUTS/'manifest.pass.jsonl').read_text().splitlines()) if r['retrieval']['result']=='retrieved'}
 inventory={};all_html={};roots={}
 for mid,m in sorted(manifest.items()):
  match=re.fullmatch(r'va-(\d+)-(\d+)-s(\d+)',mid)
  if not match:continue
  b=(INPUTS/m['original_path']).read_bytes();assert hashlib.sha256(b).hexdigest()==m['retrieval']['sha256']
  parser=DOM();parser.feed(b.decode(errors='replace'));root=parser.root
  its=section_items(root,match[3]);assert its,(mid,'empty parsed section inventory')
  all_html[mid]=its
  inventory[mid]={'container_kind':'html_issue_section','original_sha256':m['retrieval']['sha256'],
                  'items':its,'method':'Original HTML action wrappers or notice/order headings; no label-entity count used.'}
 for mid,m in sorted(manifest.items()):
  if m['kind']!='issue':continue
  pages=json.loads((PDF_CACHE/(mid+'.json')).read_text());text='\n'.join(pages)
  prefix=mid[:-3]
  section_rows=[it for sid,its in all_html.items() if sid.startswith(prefix) for it in its]
  native_html=collections.defaultdict(list)
  for it in section_rows:
   for doc in set(it['doc_numbers']):native_html[doc].append(it)
  native=list(CLOSE.finditer(text));seen=collections.Counter();pdf_items=[]
  for k,match in enumerate(native):
   doc=match[1].upper();seen[doc]+=1
   counterparts=native_html.get(doc,[])
   if counterparts:
    # Repeated chapter wrappers are display repeats; actual PDF closings give
    # the action count. Median same-document HTML body sizes the full action.
    wc=statistics.median(it['word_count'] for it in counterparts)
    kind='regulation_action' if any(it['kind']=='regulation_action' for it in counterparts) else counterparts[0]['kind']
    rec={'kind':kind,'word_count':wc,'doc_numbers':[doc],
         'heading_fingerprint':hashlib.sha256((doc+':'+str(seen[doc])).encode()).hexdigest(),
         'method':'PDF closing-identifier action count; same-issue original HTML full-action median length'}
    representative=sorted(counterparts,key=lambda it:(abs(it['word_count']-wc),it['heading_fingerprint'],it['word_count']))[0]
    rec['participation_read']={**representative['participation_read'],
     'source_method':'Same-issue original HTML body closest to the median full-action length; deterministic fingerprint tie-break',
     'source_full_item_words':representative['word_count']}
   else:
    start=native[k-1].end() if k else max(text.find('PETITIONS FOR RULEMAKING',100),text.find('NOTICES OF INTENDED REGULATORY ACTION',100),0)
    # Never size first body from a later section or from front-matter TOC.
    if start>match.start():start=0
    fragment=text[start:match.end()]
    rec=item(fragment,'pdf_only_native_action',method='PDF-only closing-identifier segment; column/front-matter boundaries are approximate')
    rec['doc_numbers']=[doc];rec.pop('_heading',None)
   pdf_items.append(rec)
  pdf_normal=norm(text)
  for it in section_rows:
   if it['doc_numbers']:continue
   heading=norm(it['_heading'])
   corroborated=bool(heading and ' '.join(heading.split()[:8]) in pdf_normal)
   rec={k:v for k,v in it.items() if k!='_heading'}
   rec['method']='No-number retained HTML notice/order sized in full; PDF counterpart heading '+('corroborated' if corroborated else 'not located in native text (planning inventory candidate)')
   pdf_items.append(rec)
  pdf_items+=guidance_items(pages)
  assert pdf_items,mid
  inventory[mid]={'container_kind':'issue_pdf','original_sha256':m['retrieval']['sha256'],'items':pdf_items,
                  'method':'One per original PDF native closing identifier, plus no-number section notices/orders and PDF-only guidance publications/catalogue rows.'}
  toc=prefix+'toc'
  if toc in manifest:
   inventory[toc]={'container_kind':'issue_toc','original_sha256':manifest[toc]['retrieval']['sha256'],'items':pdf_items,
                   'method':'TOC container cost uses the same issue-wide expanded action/listing inventory as its PDF; merged PDF/TOC charged once.'}
 for mid,v in inventory.items():
  for k,it in enumerate(v['items'],1):
   it.pop('_heading',None);it['item_ordinal']=k
  lengths=[it['word_count'] for it in v['items']]
  readable=[it for it in v['items'] if not it['kind'].startswith('guidance_catalogue_')]
  assert readable,(mid,'No complete notice/action available for the one-item read')
  v['item_count']=len(lengths);v['median_listed_row_words']=statistics.median(lengths);v['max_item_words']=max(lengths)
  v['read_item_count']=len(readable);v['median_item_words']=statistics.median(it['word_count'] for it in readable)
  costs=[it['participation_read']['minutes'] for it in readable]
  v['participation_read']={'median_b_minutes':statistics.median(costs),'max_b_minutes':max(costs),
   'median_preamble_participation_words':statistics.median(it['participation_read']['preamble_participation_words'] for it in readable),
   'max_preamble_participation_words':max(it['participation_read']['preamble_participation_words'] for it in readable),
   'median_search_hits':statistics.median(it['participation_read']['search_hits'] for it in readable),
   'max_search_hits':max(it['participation_read']['search_hits'] for it in readable)}
  v['read_pool_definition']='Complete retained notices/actions. Annual catalogue pointer rows receive accounting but are not themselves complete notices/actions or supplied linked guidance texts.'
  v['item_kind_counts']=dict(collections.Counter(it['kind'] for it in v['items']))
  regs=[it['word_count'] for it in v['items'] if it['kind']=='regulation_action']
  v['median_regulation_action_words']=statistics.median(regs) if regs else None
  v['max_regulation_action_words']=max(regs) if regs else 0
 kinds={}
 for kind in ('html_issue_section','issue_pdf','issue_toc'):
  vv=[v for v in inventory.values() if v['container_kind']==kind]
  kinds[kind]={'containers':len(vv),'median_item_count':statistics.median(v['item_count'] for v in vv),
               'max_item_count':max(v['item_count'] for v in vv),
               'median_read_item_count':statistics.median(v['read_item_count'] for v in vv),
               'max_read_item_count':max(v['read_item_count'] for v in vv),
               'max_item_count_ids':[mid for mid,v in inventory.items() if v['container_kind']==kind and v['item_count']==max(x['item_count'] for x in vv)]}
 output={'status':'retrospective sizing inventory only; not a frozen item frame or proof of accounting coverage',
  'word_rate':250,'container_count':len(inventory),'item_count_summary':kinds,'containers':inventory,
  'participation_read_method':{'word_cost':'max(2, ceil(preamble/participation words / 250) + 1); retain original one-minute check and two-minute minimum',
   'b_cost':'word cost + residual search hits + 2 minutes overhead; median of individual eligible-item costs per container, not separately combined medians',
   'passages':'All pre-body heading/preamble/summary paragraphs and later textbl/textbi/summary preamble-style paragraphs; text outside paragraph nodes is charged as heading/preamble. Whole Parts/Articles/VAC sections whose headings match participation keywords; each other paragraph matching comment*, hearing*, petition*, effective, date(s), objection*. Other notices/no reliable body boundary conservatively read whole.',
   'search':'Remaining native text only: nonoverlapping comment*, hearing*, objection*, ISO dates, numeric month/day/year or month-day-year, month-name/day dates and standalone 19xx/20xx years. Year-like legislative/code citations deliberately count as possible dates. Bare slash fractions (1/3, 1/6) are excluded. Each occurrence costs one minute, even repeated; context is its paragraph and adjacent paragraphs, deduplicated only for context word reporting.',
   'pdf':'HTML counterpart closest to median full-body size supplies structured passage counts where available; PDF-only native blocks use lines/blank lines and VAC boundaries. Counts are sizing estimates, not completed human reads.',
   'owner_approval_required':True},
  'limitations':['Counts are displayed source items, not accepted entity counts or sums of completion fields.',
   'PDF/TOC share expanded issue-wide items, not just top-level TOC headings. Display-repeated HTML actions remain separate accounting rows; PDF counts native action closings once.',
   'PDF-only native-action lengths use native closing-marker segments; no-number HTML counterparts may not match native PDF heading order. These are flagged sizing candidates, not adjudicated identities.',
   'Annual guidance catalogue rows contribute separate accounting items. They are excluded from the one-complete-notice/action read pool: a pointer row is not the full linked guidance text. Complete guidance publication notices remain eligible. This nested population definition must be reviewed before any future seed.',
   'No item was drawn and no seed generated. A future item frame must resolve flagged residuals and full-item/linked-document boundaries before sampling.']}
 (OUT/'container-inventory.json').write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n')
 print(json.dumps({'container_count':len(inventory),'summary':kinds},indent=2))
if __name__=='__main__':main()
