"""Offline research parser for the saved WSR div template; abstain on changes."""
from pathlib import Path
from html.parser import HTMLParser
from datetime import datetime
import json, re

ROOT = Path(__file__).resolve().parent

class DivText(HTMLParser):
    def __init__(self):
        super().__init__(); self.depth=0; self.parts=[]; self.lines=[]
    def handle_starttag(self, tag, attrs):
        if tag=='div':
            if self.depth==0: self.parts=[]
            self.depth+=1
    def handle_data(self, data):
        if self.depth: self.parts.append(data)
    def handle_endtag(self, tag):
        if tag=='div' and self.depth:
            self.depth-=1
            if self.depth==0:
                self.lines.append(re.sub(r'\s+', ' ', ''.join(self.parts)).strip())

def date(s): return datetime.strptime(s, '%B %d, %Y').date().isoformat()
def time(s, meridian):
    return datetime.strptime(s+' '+meridian.replace('.', '').upper(), '%I:%M %p').strftime('%H:%M')
def local(d,t):
    return dict(kind='local_datetime',date=d,time=t,timezone_text=None,iana_zone=None,utc_instant=None)

def parse(path):
    html=path.read_text(encoding='utf-8-sig')
    for field in ('WSRNumber','WSRRegType','WSRAgencyName'):
        if '<!-- field: '+field+' -->' not in html: raise ValueError('Unsupported missing field marker: '+field)
    p=DivText(); p.feed(html); lines=p.lines
    if len(lines)<4 or not re.fullmatch(r'WSR \d{2}-\d{2}-\d{3}',lines[0]): raise ValueError('Unsupported notice header')
    rid=lines[0][4:]; event=lines[1]
    if event not in ('PROPOSED RULES','WITHDRAWAL OF PROPOSED RULES'): raise ValueError('Unsupported event template '+event)
    text='\n'.join(lines)+'\n'; textpath=path.with_suffix('.txt'); textpath.write_text(text)
    artifact='wa-'+path.stem+'-text'; obs=[]
    def add(pred,val,quote,kind='notice',suffix='',warnings=None):
        assert quote in text
        obs.append(dict(schema_version='state-spike-v1',observation_id=f'wa-{rid}-{pred}{suffix}',jurisdiction='US-WA',source_record_id=rid,subject=dict(kind=kind,id=f'wa:wsr:{rid}'+suffix),predicate=pred,value=val,evidence=[dict(artifact_id=artifact,locator='line '+str(text[:text.index(quote)].count('\n')+1),quote=quote,support='text_exact')],method=dict(kind='deterministic',name='wsr-guarded-div-fields',version='1'),review_state='candidate',warnings=warnings or []))
    filing_indices=[i for i,x in enumerate(lines[:8]) if x.startswith('[Filed ')]
    if len(filing_indices)!=1 or not 3<=filing_indices[0]<=5: raise ValueError('Unsupported agency/filing header')
    fi=filing_indices[0]; agency_quote='\n'.join(lines[2:fi])
    canonical_event={'PROPOSED RULES':'proposal','WITHDRAWAL OF PROPOSED RULES':'withdrawal'}[event]
    add('event_type',canonical_event,event); add('agency',' '.join(lines[2:fi]),agency_quote)
    m=re.fullmatch(r'\[Filed ([A-Za-z]+ \d{1,2}, \d{4}), (\d{1,2}:\d{2}) ([ap]\.m\.)\]',lines[fi])
    if not m: raise ValueError('Unsupported filing datetime')
    add('filing_date',local(date(m[1]),time(m[2],m[3])),lines[fi],warnings=['Timezone not stated; no UTC conversion.'])
    if event=='WITHDRAWAL OF PROPOSED RULES':
        target=re.search(r'\bwithdraw WSR (\d{2}-\d{2}-\d{3}) from its filing\.',text)
        scope=re.search(r'The withdrawal is only for the (.+?)\.',text)
        if not target or not scope: raise ValueError('Withdrawal target/scope requires review')
        add('withdraws',dict(target_source_record_id=target[1],scope=scope[1]),target[0])
        obs[-1]['evidence'].append(dict(artifact_id=artifact,locator='scope sentence',quote=scope[0],support='text_exact'))
    else:
        def field(label):
            matches=[x for x in lines if x.startswith(label)]
            if len(matches)!=1: raise ValueError('Expected one '+label)
            return matches[0]
        title=field('Title of Rule and Other Identifying Information: ')
        add('title',title.split(': ',1)[1],title)
        close=field('Submit Written Comments to: ')
        m=re.search(r', by ([A-Za-z]+ \d{1,2}, \d{4})\.$',close)
        if not m: raise ValueError('Unsupported comment close; do not use other by dates')
        add('comment_close',dict(kind='date',date=date(m[1])),close,kind='participation_window',suffix=':written-comments',warnings=['No clock time or receipt/postmark condition stated.'])
        hearing=field('Hearing Location(s): ')
        m=re.search(r': On ([A-Za-z]+ \d{1,2}, \d{4}), at (\d{1,2}:\d{2}) ([ap]\.m\.),',hearing)
        if not m: raise ValueError('Unsupported hearing template')
        add('hearing_time',local(date(m[1]),time(m[2],m[3])),hearing,kind='hearing',suffix=':hearing-1',warnings=['Timezone not stated; no UTC conversion.'])
    return obs

def main():
    # Explicit saved input files, never expectations/model output.
    obs=[]
    for name in ('withdrawal.html','proposal.html'): obs.extend(parse(ROOT/name))
    (ROOT/'observations.json').write_text(json.dumps(obs,indent=2)+'\n')
    print(json.dumps({'observation_count':len(obs)}))
if __name__=='__main__': main()
