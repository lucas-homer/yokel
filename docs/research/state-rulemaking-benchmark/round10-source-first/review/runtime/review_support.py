"""Independent offline oracles. Never import production/runtime code here."""
import hashlib,json,math
from decimal import Decimal,ROUND_CEILING
from pathlib import Path
COLS=('id','kind','assertion','modality','applicability','uncertainty','uncertainty_reason','required_unit_ids','evidence')
PRIOR=858310718;RESERVE=161920000;CEILING=2000000000

def encode(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def strict(raw):
 def pairs(rows):
  d={}
  for k,v in rows:
   if k in d:raise ValueError('duplicate JSON key')
   d[k]=v
  return d
 def number(s):
  n=float(s)
  if not math.isfinite(n):raise ValueError('nonfinite number')
  return n
 def constant(s):raise ValueError('nonstandard number')
 return json.loads(raw,object_pairs_hook=pairs,parse_float=number,parse_constant=constant)

def charge(usage):
 costs=[RESERVE]
 if isinstance(usage,dict):
  v=usage.get('cost')
  if type(v) in (int,float) and math.isfinite(v) and v>=0:costs.append(int((Decimal(str(v))*10**9).to_integral_value(rounding=ROUND_CEILING)))
  if all(type(usage.get(k)) is int and usage[k]>=0 for k in ('prompt_tokens','completion_tokens')):costs.append(usage['prompt_tokens']*2000+usage['completion_tokens']*10000)
 return max(costs)

def projection(x):
 if isinstance(x,dict):return {k:projection(v) for k,v in x.items() if k not in ('evidence','coverage')}
 if isinstance(x,list):return [projection(v) for v in x]
 return x

def fields(record):
 out={}
 def walk(obj,p):
  for k,v in obj.items():
   if k in ('id','evidence'):continue
   if k in ('timing','components'):
    for i,row in enumerate(v):walk(row,p+'/'+k+'/'+str(i))
   else:out[p+'/'+k]=v
 for name in ('events','routes','requirements','identities','uncertainties','alternative_groups'):
  for i,obj in enumerate(record[name]):walk(obj,'/'+name+'/'+str(i))
 return out

def identities(x,path=''):
 out={}
 if isinstance(x,dict):
  if 'id' in x:out[x['id']]=path
  children=((k.replace('~','~0').replace('/','~1'),v) for k,v in x.items())
 elif isinstance(x,list):children=((str(i),v) for i,v in enumerate(x))
 else:return out
 for k,v in children:
  other=identities(v,path+'/'+k)
  if out.keys()&other.keys():raise ValueError('duplicate item ID')
  out.update(other)
 return out

def occurrences(source,quote):
 if type(quote) is not str or not quote.strip():raise ValueError('blank quote')
 out=[];pos=0
 while True:
  pos=source.find(quote,pos)
  if pos<0:return out
  out.append(pos);pos+=1

def span_encode(inventory,source):
 if inventory['source_text_sha256']!=sha(source.encode()):raise ValueError('source binding')
 rows=[]
 for u in inventory['units']:
  if set(u)!=set(COLS):raise ValueError('unit fields')
  row=[]
  for k in COLS:
   if k!='evidence':row.append(u[k]);continue
   selectors=[]
   for e in u[k]:
    if set(e)!={'quote','occurrence'} or type(e['occurrence']) is not int:raise ValueError('selector')
    pp=occurrences(source,e['quote']);n=e['occurrence']
    if not 1<=n<=len(pp):raise ValueError('occurrence')
    start=pp[n-1];selectors.append([start,start+len(e['quote']),n])
   row.append(selectors)
  rows.append(row)
 return {'schema_version':'round10.inventory-span-tuples.v1','source_text_sha256':inventory['source_text_sha256'],'columns':list(COLS),'evidence_columns':['start','end','occurrence'],'units':rows}

def span_restore(wire,source,inventory):
 if set(wire)!={'schema_version','source_text_sha256','columns','evidence_columns','units'}:raise ValueError('envelope')
 if wire['schema_version']!='round10.inventory-span-tuples.v1' or wire['columns']!=list(COLS) or wire['evidence_columns']!=['start','end','occurrence'] or wire['source_text_sha256']!=sha(source.encode()):raise ValueError('wire binding')
 units=[]
 for row in wire['units']:
  if type(row) is not list or len(row)!=9:raise ValueError('row width')
  u=dict(zip(COLS,row));evidence=[]
  for span in u['evidence']:
   if type(span) is not list or len(span)!=3 or any(type(v) is not int for v in span):raise ValueError('span type')
   start,end,occurrence=span
   if not 0<=start<end<=len(source):raise ValueError('span range')
   quote=source[start:end];pp=occurrences(source,quote)
   if not 1<=occurrence<=len(pp) or pp[occurrence-1]!=start:raise ValueError('span occurrence')
   evidence.append({'quote':quote,'occurrence':occurrence})
  u['evidence']=evidence;units.append(u)
 out={'schema_version':'round10.source-inventory.v1','source_text_sha256':sha(source.encode()),'units':units}
 if encode(out)!=encode(inventory) or sha(encode(out))!=sha(encode(inventory)):raise ValueError('canonical roundtrip')
 return out

def native(content,usage=None):
 return {'model':'openai/gpt-6.1-sol','provider':'OpenAI','choices':[{'finish_reason':'stop','native_finish_reason':'completed','message':{'role':'assistant','content':content if isinstance(content,str) else encode(content).decode()}}],'usage':usage if usage is not None else {'prompt_tokens':100,'completion_tokens':100,'cost':.01}}

def install_guard(root):
 """Call before importing a stopped runtime. Caller must already set no-bytecode."""
 import sys
 root=Path(root).resolve()
 def guard(event,args):
  if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise AssertionError('network/process forbidden')
  if event=='open' and isinstance(args[0],(str,bytes)):
   path=Path(args[0]).resolve();mode,flags=args[1:3]
   if any(x in path.parts for x in ('.ssh','.aws','Keychains','.gnupg')) or path.name=='.env':raise AssertionError('credential file forbidden')
   write=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and (flags&3) in (1,2))
   if write and not path.is_relative_to(root):raise AssertionError('write outside runtime review')
 sys.addaudithook(guard)
