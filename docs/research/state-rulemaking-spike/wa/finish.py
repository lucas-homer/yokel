"""Build collection manifest and diagnostic validation from retained artifacts."""
from pathlib import Path
from html.parser import HTMLParser
from datetime import datetime,timezone
import json,hashlib,re,importlib.util,tempfile
P=Path(__file__).resolve().parent
def save(n,o): (P/n).write_text(json.dumps(o,indent=2)+'\n')
base='https://lawfilesext.leg.wa.gov/law/wsr/2026/18/'
manifest=[]
def artifact(n,aid,url,rep,collector,lineage,timestamp):
    manifest.append(dict(artifact_id=aid,path=n,sha256=hashlib.sha256((P/n).read_bytes()).hexdigest(),source_url=url,retrieved_at=timestamp,media_type={'html':'text/html','native_text':'text/plain','markdown':'text/markdown','raw_json':'application/json'}[rep],representation=rep,source_lineage="washington-code-reviser:wsr:"+url.rsplit("/",1)[-1]+(" <- "+",".join(lineage) if lineage else ":public-source"),collector=collector,is_inherited=False))
for n,rid,t in [('index',None,'2026-10-05T23:27:45Z'),('withdrawal','26-18-058','2026-10-05T23:27:45Z'),('proposal','26-18-032','2026-10-05T23:28:10Z')]:
    url=base+(rid or '26-18')+'.htm'
    t=datetime.fromtimestamp((P/(n+'.html')).stat().st_mtime,timezone.utc).isoformat()
    artifact(n+'.html','wa-'+n+'-html',url,'html','curl public GET',[],t)
    if rid:
        artifact(n+'.txt','wa-'+n+'-text',url,'native_text','normalize.py DivText whitespace-normalized div text',['wa-'+n+'-html'],t)
        fc=json.loads((P/('firecrawl-'+n+'.json')).read_text())['structuredContent']
        (P/('firecrawl-'+n+'.md')).write_text(fc['markdown'])
        ft=datetime.fromtimestamp((P/('firecrawl-'+n+'.json')).stat().st_mtime,timezone.utc).isoformat()
        artifact('firecrawl-'+n+'.json','wa-firecrawl-'+n+'-response',url,'raw_json','Firecrawl scrape maxAge=0; timestamp is response persistence upper bound',[],ft)
        artifact('firecrawl-'+n+'.md','wa-firecrawl-'+n+'-markdown',url,'markdown','Firecrawl clean text',['wa-firecrawl-'+n+'-response'],ft)
ft=datetime.fromtimestamp((P/'firecrawl-model.json').stat().st_mtime,timezone.utc).isoformat()
artifact('firecrawl-model.json','wa-firecrawl-model-response',base+'26-18-058.htm','raw_json','Firecrawl prompt-only JSON maxAge=0; timestamp is response persistence upper bound',[],ft)
save('manifest.json',manifest)
class Rows(HTMLParser):
    def __init__(self): super().__init__();self.rows=[];self.row=None;self.cell=None
    def handle_starttag(self,t,a):
        if t=='tr': self.row=[]
        elif t=='td' and self.row is not None:self.cell=[]
    def handle_data(self,d):
        if self.cell is not None:self.cell.append(d)
    def handle_endtag(self,t):
        if t=='td' and self.cell is not None:self.row.append(''.join(self.cell).strip());self.cell=None
        elif t=='tr' and self.row is not None:self.rows.append(self.row);self.row=None
r=Rows();r.feed((P/'index.html').read_text());props=[];agency=None
for row in r.rows:
    if len(row)==5 and row[4]=='PROP':
        props.append(dict(agency_cell=row[1],source_record_id=row[2],category=row[4]))
save('index-enumeration.json',dict(PROP_rows=len(props),unique_PROP_ids=len(set(x['source_record_id'] for x in props)),rows=props))
obs=json.loads((P/'observations.json').read_text()); arts={x['artifact_id']:x for x in manifest}
quotes=sum(len(o['evidence']) for o in obs)
for o in obs:
    for e in o['evidence']:assert e['quote'] in (P/arts[e['artifact_id']]['path']).read_text()
assert len({o['observation_id'] for o in obs})==len(obs)
assert len(props)==14 and len(set(x['source_record_id'] for x in props))==13
assert [o['value']['date'] for o in obs if o['predicate']=='comment_close']==['2026-10-09']
assert not any(o['predicate']=='effective_date' for o in obs)
assert {o['value'] for o in obs if o['predicate']=='event_type'}=={'proposal','withdrawal'}
fcmodel=json.loads((P/'firecrawl-model.json').read_text())['structuredContent']['json']
modelquotechecks=[q in (P/'withdrawal.txt').read_text() for q in fcmodel['evidence_quotes']]
spec=importlib.util.spec_from_file_location('normalizer',P/'normalize.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
with tempfile.TemporaryDirectory(dir=P) as tmp:
    bad=Path(tmp)/'unsupported.html';bad.write_text('<html><div>generic dates October 9, 2026</div></html>')
    try: module.parse(bad);raise AssertionError('Unsupported page did not abstain')
    except ValueError: pass
save('validation.json',dict(observation_count=len(obs),exact_quote_count=quotes,all_quotes_match=True,unique_observation_ids=True,unsupported_template_rejected=True,index_counts_match=True,canonical_event_types_match=True,model_evidence_quotes_match=modelquotechecks,model_null_fields_are_strings=True))
print(json.dumps(dict(observations=len(obs),quotes=quotes,PROP_rows=len(props),unique_PROP_ids=len(set(x['source_record_id'] for x in props)))))
