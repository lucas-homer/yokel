"""Independent read-only frozen-input checks; writes only this review directory."""
import copy, hashlib, json, sys
from decimal import Decimal
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROUND=HERE.parent
BASE=ROUND.parent
checks=[]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def enc(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def read(path): return json.loads(path.read_bytes())
def check(name, ok, detail=None):
    checks.append(dict(name=name,passed=bool(ok),detail=detail))
    if not ok: raise AssertionError(name)
def guard(event,args):
    if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'): raise AssertionError('offline process/network guard')
    if event=='open':
        p=args[0]
        if isinstance(p,(str,bytes)):
            p=Path(p).resolve();mode=args[1];flags=args[2]
            if any(x in p.parts for x in ('.ssh','.aws','Keychains')) or p.name=='.env': raise AssertionError('credential file guard')
            writing=(isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags & 3 in (1,2))
            if writing and not p.is_relative_to(HERE): raise AssertionError('review-only writes')
sys.addaudithook(guard)
baseline=ROUND/'prior-baseline.json'
check('Primary baseline exact bytes',sha(baseline)=='9df0a6b5f9bda5d031ef87426f4a03e929f268f2e3f3dceb8d7fea20ef1223ac')
rows=read(baseline)['files'];bad=[]
for row in rows:
    p=(BASE/row['path']).resolve()
    if not p.is_relative_to(BASE) or not p.is_file() or sha(p)!=row['sha256'] or p.stat().st_size!=row['bytes']: bad.append(row['path'])
check('Historical files immutable',not bad,{'checked':len(rows),'mismatches':bad})
r9=BASE/'round9-exact-id-completeness';proto=r9/'protocol'
check('Protocol READY exact bytes',sha(proto/'READY.json')=='613b372963791f54f7afa3160a48cf15d1750e454f126a9b75c5b1ec4d4db2f1')
check('Offline runtime READY exact bytes',sha(r9/'runtime/READY.json')=='ac2d64c61c054d4a4cdd47c34f780103d66bece4df3abdc133f8af7efa3c8451')
for path,want in read(proto/'READY.json')['artifacts'].items(): check('Protocol pin '+path,sha(proto/path)==want)
for path,want in read(r9/'runtime/READY.json')['files'].items(): check('Offline runtime pin '+path,sha(r9/'runtime'/path)==want['sha256'])
request=read(proto/'wi70-offline-request.fixture.json');old=read(BASE/'round8-stronger-cap-probe/execution/run/documents/doc-92211b8c7ba0/stronger-request.json')
sizes=read(proto/'wire-size-check.json')
expected=copy.deepcopy(old);expected['messages'][0]['content']+='\n'+sizes['added_neutral_instruction'];expected['response_format']['json_schema']['schema']=read(proto/'wi70-response.schema.json')
check('Exact neutral-only request delta',request==expected)
check('Exact request canonical pin',hashlib.sha256(enc(request)).hexdigest()=='093b205a1c01bc0f2f2d6640944d3e0854e88ba34ffc0ad4c2b5f9f4e4b812f5')
check('Request byte size and unchanged guard',len(enc(request))==38432 and len(enc(request))+1024==39456 and 39456<=40000)
check('Model and completion retained',request['model']==old['model'] and request['max_tokens']==8192 and request['provider']==old['provider'] and request['reasoning']==old['reasoning'])
assembled=read(BASE/'round8-stronger-cap-probe/execution/run/documents/doc-92211b8c7ba0/assembled.json');record=assembled['record'];ids=[]
for kind in ('events','routes','requirements','identities','uncertainties','alternative_groups'):
    for item in record[kind]:
        ids.append(item['id'])
        for sub in item.get('timing',[]) if kind=='events' else item.get('components',[]) if kind=='routes' else []: ids.append(sub['id'])
schema=request['response_format']['json_schema']['schema'];assessment=schema['properties']['assessments']
check('Independent 70-ID schema membership',len(ids)==len(set(ids))==70 and set(ids)==set(assessment['properties'])==set(assessment['required']) and assessment['additionalProperties'] is False and 'coverage' not in ids)
charges=[]
for name in ('round8','round8-cap-probe','round8-contract-probe','round8-evidence-table','round8-stronger-cap-probe'):
    for folder in sorted((BASE/name/'execution/run/operations').iterdir()):
        if not (folder/'intent.json').exists():continue
        intent=read(folder/'intent.json');raw=(folder/'response.body').read_bytes();native=json.loads(raw,parse_float=Decimal);status=read(folder/'status.json')
        check('Prior request/response binding '+folder.name,intent['request_sha256']==sha(folder/'request.json') and status['response_sha256']==sha(folder/'response.body'))
        reserve=Decimal(str(intent['reserved_nominal_usd']));reported=native.get('usage',{}).get('cost') or Decimal(0)
        parsed=read(folder/'result.json').get('observed_cost_usd') if (folder/'result.json').exists() else None
        charge=max(reserve,Decimal(str(reported)),Decimal(str(parsed or 0)))
        charges.append({'round':name,'kind':intent['kind'],'reserved':str(reserve),'reported':str(reported),'parsed':parsed,'conservative_charge':str(charge)})
total=sum((Decimal(row['conservative_charge']) for row in charges),Decimal(0))
check('Six retained conservative debits',len(charges)==6 and abs(total-Decimal('.696390718'))<Decimal('0.000000000001'),{'total_with_legacy_float_residue':str(total),'rows':charges})
check('Completed ledger agrees',Decimal(str(read(BASE/'round8-stronger-cap-probe/execution/run/completed.json')['totals']['budget_charge_usd']))==Decimal('.696390718'))
check('Exact request reservation',Decimal(39456)*Decimal('.000002')+Decimal(8192)*Decimal('.00001')==Decimal('.160832'))
check('Worst case reservation and cumulative admission',Decimal(40000)*Decimal('.000002')+Decimal(8192)*Decimal('.00001')==Decimal('.161920') and Decimal('.696390718')+Decimal('.161920')==Decimal('.858310718')<Decimal(2))
report={'state':'passed','provider_calls':0,'credentials_read':False,'checks':checks,'limitations':['Schema compatibility remains a live unknown.','Prior provider costs are reporting, not invoice verification.','No runtime candidate was approved by preparation checks.']}
(HERE/'preparation-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'state':'passed','checks':len(checks),'historical_files':len(rows),'prior_debit':'0.696390718'}))
