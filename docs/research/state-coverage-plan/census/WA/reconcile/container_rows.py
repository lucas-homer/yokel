"""WA original container splitter and rights-safe A1 sizing (stdlib only).

PDF text is an explicitly supplied local PDFKit derivative, outside git. Source
bytes are checked by the caller; full text stays in memory, never in this output.
Filing listings use one ordered row per distinct WSR reference. Non-row lines
are counted explicitly; directories retain whole-original verification spans.
"""
import collections
import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import statistics

WSR=re.compile(r'(?<![\w-])\d\d-\d\d-\d{3}[a-z]?(?![\w-])',re.I)
TABLE_REF=re.compile(r'\b(?:AMD|A/R|DECOD|NEW|OBJECT|PREP|RE-AD|RECOD|REP|RESCIND|REVIEW|SUSP)(?:-[CEPSWX])?\s+(\d\d-\d\d-\d{3}[a-z]?)(?![\w-])',re.I)
INDEX_REF=re.compile(r'(?:PREP|PROP|MISC|PERM|EMER|EXPE)\s*(\d\d-\d\d-\d{3}[a-z]?)(?![\w-])',re.I)
PART=re.compile(r'\b(?:comment\w*|hearing\w*|petition\w*|objection\w*)\b',re.I)
SEARCH=re.compile(r'\b(?:comment\w*|hearing\w*|objection\w*)\b|\b(?:19|20)\d{2}\b|\b(?:Jan\w*|Feb\w*|Mar\w*|Apr\w*|May|Jun\w*|Jul\w*|Aug\w*|Sep\w*|Oct\w*|Nov\w*|Dec\w*)\s+\d{1,2}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b',re.I)
WAC=re.compile(r'^WAC\s+\d+[A-Z]?-\d+[A-Z]?-\d+',re.I)

def norm(s):return ' '.join(s.casefold().split())
def fingerprint(s):return hashlib.sha256(norm(s).encode()).hexdigest()
def words(s):return len(s.split())
def W(n):return max(2,math.ceil(n/250)+1)

class Node:
    def __init__(self,tag='',attrs=None):self.tag=tag;self.attrs=attrs or {};self.children=[]
    def text(self):return '' if self.tag in ('script','style','head') else ' '.join(c if isinstance(c,str) else c.text() for c in self.children)
    def descend(self):
        for c in self.children:
            if isinstance(c,Node):yield c;yield from c.descend()
class DOM(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.root=Node();self.stack=[self.root]
    def handle_starttag(self,tag,attrs):
        n=Node(tag,dict(attrs));self.stack[-1].children.append(n)
        if tag not in ('br','hr','img','meta','link','input','wbr','area','base','embed','param','source','track','col'):self.stack.append(n)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:del self.stack[i:];break
    def handle_data(self,s):self.stack[-1].children.append(s)

def participation(text):
    # Whole preamble, whole participation-bearing WAC sections, residual hits
    # (including substantive dates conservatively) plus VA's 2-minute allowance.
    blocks=[x.strip() for x in text.splitlines() if x.strip()]
    starts=[i for i,x in enumerate(blocks) if WAC.match(x)]
    if not starts:return {'words':words(text),'participation_words':words(text),'remaining_search_hits':0,'minutes':W(words(text))+2,'method':'whole item; no reliable WAC-body boundary'}
    selected=set(range(starts[0]))
    for start,end in zip(starts,starts[1:]+[len(blocks)]):
        if PART.search(' '.join(blocks[start:min(start+3,end)])):selected.update(range(start,end))
    selected.update(i for i,x in enumerate(blocks) if PART.search(x))
    wc=sum(words(x) for i,x in enumerate(blocks) if i in selected)
    hits=sum(len(SEARCH.findall(x)) for i,x in enumerate(blocks) if i not in selected)
    return {'words':words(text),'participation_words':wc,'remaining_search_hits':hits,'minutes':W(wc)+hits+2,'method':'whole heading/preamble; participation WAC sections and keyword paragraphs; residual hits in context'}

def reference_frame(pages, table=False, index=False):
    """First source occurrence orders distinct references; retain EVERY citing line.

    TABLE references follow an action token, never a pure WAC citation. HTML
    pages here contain visible DOM text; line numbers refer to that deterministic
    text view. No source line text is written, only location/fingerprint/counts.
    """
    references=collections.OrderedDict(); non_row=0;total=0;by_page=[]
    for pn,page in enumerate(pages,1):
        page_total=page_citing=0
        for ln,line in enumerate(page.splitlines(),1):
            if not line.strip():continue
            total+=1;page_total+=1
            docs=[x.lower() for x in (TABLE_REF.findall(line) if table else INDEX_REF.findall(line) if index else WSR.findall(line))]
            if not docs:non_row+=1;continue
            page_citing+=1
            for doc in dict.fromkeys(docs):
                references.setdefault(doc,[]).append({'page':pn,'line':ln,
                    'native_line_fingerprint':fingerprint(line),'occurrences':docs.count(doc)})
        by_page.append({'page':pn,'nonblank_lines':page_total,'citing_lines':page_citing,
                        'non_row_lines':page_total-page_citing})
    metadata={'row_method':'distinct_normalized_WSR_first_source_occurrence',
        'reference_pattern':'WSR after TABLE action token' if table else 'WSR after INDEX filing type' if index else 'WSR filing number in visible/native text',
        'nonblank_line_count':total,'citing_line_count':total-non_row,'non_row_line_count':non_row,
        'distinct_WSR_count':len(references),'page_line_counts':by_page}
    return references,metadata


def label_index(compare, labels):
    """Accepted notice/update for the filing; rejected evidence citing the filing.

    Rejection quotations can cite another filing explicitly. Read those references
    for accounting without asserting that the other filing body was supplied.
    Never use a title match or a blanket container rejection for a WSR row.
    """
    bydoc=collections.defaultdict(dict);byview=collections.defaultdict(dict)
    for r in labels:
        docs=set(compare.numbers(r, r['record_type']=='update'))
        if r['record_type']=='rejected_candidate':
            for e in compare.evidence(r):
                text=e.get('quote_or_mark_description','')+' '+e['locator']
                docs.update(n.lower() for n in re.findall(r'\bWSR\s+(\d\d-\d\d-\d{3}[a-z]?)(?![\w-])',text,re.I))
                if e['manifest_entry_id'].startswith(('wa-issue-','wa-idx-','wa-sec-','wa-agencywac')):
                    docs.update(n.lower() for n in WSR.findall(text))
        for n in docs:bydoc[n.lower()][r['record_id']]=r
        for e in r['evidence']:byview[e['manifest_entry_id']][r['record_id']]=r
    return bydoc,byview


def container_issue(container_id):
    match=re.fullmatch(r'wa-(?:issue|idx|sec)-(\d\d-\d\d)(?:-[A-Za-z]+)?',container_id)
    return match[1] if match else None


def manifest_filings(manifest):
    result=collections.defaultdict(list)
    for row in manifest:
        match=re.fullmatch(r'wa-(?:f|probe)-(\d\d-\d\d-\d{3}[a-z]?)-(?:pdf|htm)',row['entry_id'],re.I)
        if match:result[match[1].lower()].append(row['entry_id'])
    return {n:sorted(ids) for n,ids in result.items()}


def pointer_labels(compare,labels):
    """All latest union label types can resolve an other-issue pointer."""
    result=collections.defaultdict(set)
    for row in labels:
        refs=set(compare.numbers(row))
        for alias in row.get('aliases',[]):
            native=re.sub(r'^WSR\s*','',alias['native_id'].strip(),flags=re.I)
            if WSR.fullmatch(native):refs.add(native.lower())
        for e in compare.evidence(row):
            text=e.get('quote_or_mark_description','')+' '+e['locator']
            refs.update(n.lower() for n in re.findall(r'\bWSR\s+(\d\d-\d\d-\d{3}[a-z]?)(?![\w-])',text,re.I))
        for n in refs:result[n].add(row['record_id'])
    return {n:sorted(ids) for n,ids in result.items()}


def classify_ownership(rows,manifest,union_refs):
    """Primary ruling: keep other-issue citations, exclude them from owner work."""
    mf=manifest_filings(manifest)
    for row in rows:
        issue=container_issue(row['container_id']);docs=row['doc_numbers']
        row['owner_accounting_eligible']=True
        row['pointer_status']=None;row['pointer_resolution']=None
        if not (issue and docs):continue
        assert len(docs)==1,(row['container_id'],'filing boundary is not singular')
        doc=docs[0]
        if doc[:5]==issue:continue
        targets={'manifest_entry_ids':mf.get(doc,[]),'union_record_ids':union_refs.get(doc,[])}
        resolved=bool(targets['manifest_entry_ids'] or targets['union_record_ids'])
        row['referenced_item_kind']=row['item_kind'];row['item_kind']='pointer'
        row['accounting_role']='pointer';row['accounting_status']='pointer' if resolved else 'pointer_unresolved'
        row['pointer_status']=row['accounting_status'];row['pointer_resolution']=targets
        row['owner_accounting_eligible']=False;row['complete_item']=False
        row['participation_read']=None;row['source_entry_id']=row['container_id']
        row['source_locator']='Other-issue pointer: inspect retained citing spans only; original filing belongs to issue '+doc[:5]+'. No owner accounting or item read in this container.'
        row['unaccounted_reason']=None
    return rows


def build(directory,inputs,manifest,pdf_text_dir):
    from importlib.util import spec_from_file_location,module_from_spec
    spec=spec_from_file_location('wa_sealed_comparison',directory/'reconcile/reconcile.py');compare=module_from_spec(spec);spec.loader.exec_module(compare)
    all_labels=[r for side in 'AB' for r in compare.latest(compare.read(directory/f'pass-{side}.jsonl'))]
    labels=[r for r in all_labels if r['record_type'] in ('notice','update','rejected_candidate')]
    bydoc,byview=label_index(compare,labels)
    full_manifest=compare.read(directory/'manifest.jsonl')
    filing_entries=manifest_filings(full_manifest)
    union_refs=pointer_labels(compare,all_labels)
    for doc,targets in bydoc.items():
        union_refs[doc]=sorted(set(union_refs.get(doc,[])) | set(targets))
    cache={};reading_cache={}
    def source_text(mid):
        if mid not in cache:
            m=manifest[mid]
            if m['format'] in ('text_pdf','scan_pdf'):
                p=pdf_text_dir/(mid+'.json')
                if not p.exists():raise ValueError(f'{mid}: missing native PDF derivative: {p}')
                cache[mid]='\n'.join(json.loads(p.read_text()))
            elif m['format']=='html':
                p=DOM();p.feed((inputs/m['original_path']).read_text(errors='replace'));cache[mid]=p.root.text()
            else:cache[mid]=''
        return cache[mid]
    def filing(n):
        return next((mid for mid in sorted(filing_entries.get(n,[]),key=lambda x:(not x.endswith('-pdf'),x)) if mid in manifest),None)
    rows=[]
    def emit(mid,ordinal,text,docs,kind,source=None,locator=None,pages=None,complete=False,spans=None,metadata=None):
        docs=sorted(set(n.lower() for n in docs))
        matches={r['record_id']:r for n in docs for r in bydoc[n].values()}
        # A non-filing whole-original verification may point to a direct label
        # for that document. It cannot account for any named WSR filing row.
        if not docs and kind=='whole_original_verification_span':matches.update(byview[mid])
        matches=sorted(matches.values(),key=lambda r:(r['record_type']=='rejected_candidate',r['record_type'],r['record_id']))
        source=source or mid
        if complete and source not in reading_cache:reading_cache[source]=participation(source_text(source))
        rows.append({'container_id':mid,'item_ordinal':ordinal,'item_kind':kind,'heading_fingerprint':fingerprint(text),
            'native_text_fingerprint':fingerprint(text),'doc_numbers':docs,'native_pdf_pages':pages,
            'item_frame_status':'resolved','complete_item':complete,'source_entry_id':source,
            'source_locator':locator or f'Original listing row {ordinal}; linked complete filing not supplied',
            'source_spans':spans or [],'container_frame_metadata':metadata if ordinal==1 else None,
            'accounting_role':'filing_reference' if docs else 'document_verification',
            'owner_accounting_eligible':True,'pointer_status':None,'pointer_resolution':None,
            'accounting_status':'accounted' if matches else 'unaccounted',
            'union_record_id':matches[0]['record_id'] if matches else None,
            'union_label_matches':[{'record_id':r['record_id'],'record_type':r['record_type'],
                'disposition':'rejected' if r['record_type']=='rejected_candidate' else 'accepted',
                'method':'exact filing notice/update or rejection evidence cites WSR' if docs else 'direct label evidence for whole-document verification'} for r in matches],
            'accept_reject_conflict':bool(any(r['record_type']=='rejected_candidate' for r in matches) and any(r['record_type']!='rejected_candidate' for r in matches)),
            'unaccounted_reason':None if matches else 'No accepted notice/update or rejection evidence for this WSR in either latest pass.' if docs else 'No direct label for this document-verification span; no missing WSR is asserted.',
            'word_count':words(text),'participation_read':reading_cache.get(source) if complete else None})
    def emit_references(mid,pages,table=False,index=False):
        refs,metadata=reference_frame(pages,table,index)
        for ordinal,(doc,spans) in enumerate(refs.items(),1):
            src=filing(doc)
            # Span fingerprints and all page/line locations preserve every
            # occurrence, including repeated agency rows and WAC-table uses.
            emit(mid,ordinal,json.dumps(spans,sort_keys=True,separators=(',',':')),[doc],
                'WSR_filing_reference',src,
                f'Every original citing line is in source_spans; complete retained filing {doc} for the item read' if src else
                f'Every original citing line is in source_spans; complete filing {doc} is not retained',
                sorted({s['page'] for s in spans}) if manifest[mid]['format'] in ('text_pdf','scan_pdf') else None,
                bool(src),spans,metadata)
        if not refs:
            text='\n'.join(pages)
            emit(mid,1,text,[],'whole_original_verification_span',mid,
                'Read WHOLE original: directory/empty listing has no WSR filing rows; verify non-row lines and unsupplied outgoing pointers. Not a filing item.',
                complete=True,metadata=metadata)
            rows[-1]['participation_read']={'words':words(text),'participation_words':words(text),
                'remaining_search_hits':0,'minutes':W(words(text)),'method':'whole-original document verification; not a filing row'}
    for mid,m in sorted(manifest.items()):
        if not (m['kind'] in ('issue','index','portal_slice','history_slice','agency_roster') or mid.startswith('wa-sec-')):continue
        if mid.startswith('wa-sec-'):
            pages=json.loads((pdf_text_dir/(mid+'.json')).read_text())
            if mid.endswith(('-TABLE','-INDEX')):emit_references(mid,pages,mid.endswith('-TABLE'),mid.endswith('-INDEX'))
            else:
                groups=[]
                for pn,page in enumerate(pages,1):
                    header=re.search(r'Washington State Register,?\s*Issue\s+\d\d-\d\d\s+WSR\s+(\d\d-\d\d-\d{3}[a-z]?)',page,re.I)
                    heads=sorted(set(x.lower() for x in re.findall(r'^WSR\s+(\d\d-\d\d-\d{3}[a-z]?)\s*$',page,re.I|re.M)))
                    n=header[1].lower() if header else heads[0] if len(heads)==1 else None
                    if not groups or groups[-1]['doc']!=n:groups.append({'doc':n,'first':pn,'last':pn,'text':page})
                    else:groups[-1]['last']=pn;groups[-1]['text']+='\n'+page
                for ordinal,g in enumerate(groups,1):
                    emit(mid,ordinal,g['text'],[g['doc']] if g['doc'] else [],'section_pdf_filing' if g['doc'] else 'section_pdf_preface',mid,
                        f'PDF pages {g["first"]}–{g["last"]}; complete original span, including boundary context',[g['first'],g['last']],True)
                    rows[-1]['participation_read']=participation(g['text'])
        else:
            parser=DOM();parser.feed((inputs/m['original_path']).read_text(errors='replace'))
            nodes=list(parser.root.descend());main=next((n for n in nodes if n.tag=='main'),None)
            text=main.text() if main is not None and mid.startswith('wa-xc-hca-') else parser.root.text()
            emit_references(mid,[text])
    classify_ownership(rows,full_manifest,union_refs)
    # A listing may cite only unretained filings. Keep its WSR rows intact and
    # add a separately identified whole-source verification pool member.
    grouped=collections.defaultdict(list)
    for r in rows:grouped[r['container_id']].append(r)
    for mid,rr in sorted(grouped.items()):
        if any(r['complete_item'] for r in rr):continue
        text=source_text(mid)
        emit(mid,len(rr)+1,text,[],'whole_original_verification_span',mid,
            'Read WHOLE original and all listing rows; referenced filing bodies are unsupplied; no abbreviated item read.',complete=True,
            metadata=rr[0]['container_frame_metadata'])
        rows[-1]['participation_read']={'words':words(text),'participation_words':words(text),'remaining_search_hits':0,
            'minutes':W(words(text)),'method':'whole-original verification fallback; no abbreviated participation read'}
    for mid,rr in grouped.items():
        first=rr[0]
        summary={'container_issue':container_issue(mid),'own_filing_rows':sum(r['accounting_role']=='filing_reference' for r in rr),
            'pointer_rows':sum(r['accounting_role']=='pointer' for r in rr),
            'pointer_unresolved':sum(r['pointer_status']=='pointer_unresolved' for r in rr)}
        first['issue_ownership_summary']=summary
    return sorted(rows,key=lambda r:(r['container_id'],r['item_ordinal']))
