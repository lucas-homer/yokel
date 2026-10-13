"""Full fictional request plus dimensional output sizing; never dispatches."""
import copy
import math
from compact import *
from fictional_controls import SOURCE, fixture, semantic_negative_controls

def run():
    request=build(SOURCE)
    artifacts={'span-table.json':request['table'],'schema.json':schema(SOURCE,request['table']),
               'offline-request.json':request['body'],'fictional-positive.json':fixture(),
               'fictional-negatives.json':semantic_negative_controls()}
    results={'scope':'fictional offline only; not model output or semantic accuracy',
             'request_bytes':request['body_bytes'],'guarded_request_bytes':request['guarded_bytes'],
             'input_guard':40000,'output_cap':8192,'tokenizer':'unavailable; byte sensitivity is not a proven bound',
             'profiles':{}}
    for count,stress in [(32,False),(64,False),(96,True),(128,True)]:
        value=fixture();value['u']=[]
        for i in range(1,count+1):
            template=fixture()['u']; offset=((i-1)//len(template))*len(template)
            u=copy.deepcopy(template[(i-1)%len(template)]);u['i']=i
            u['d']=[dep+offset for dep in u['d']]
            u['s']=f"Dimensional copy {i}: "+u['s']
            if stress:
                u['s']+= ' Qualifications include a source-specific exception and independently linked historical context; Ω e\u0301 🫧 retain exact Unicode.'
                u['c']='Cutoff clock unknown; timezone unknown; receipt-versus-dispatch unknown. Context applies only to this stated deadline; other purposes remain separate and independently linked.'
            value['u'].append(u)
        validate(value,SOURCE,request['table'])
        raw=canonical(value);name=('stressed' if stress else 'representative')+str(count)+'.json'
        artifacts[name]=value
        estimates={str(ratio):math.ceil(len(raw)/ratio)+256 for ratio in [2,3,4]}
        results['profiles'][name]={'bytes':len(raw),'units':count,'estimated_tokens':estimates,
            'two_byte_residual':8192-estimates['2'],
            'prudent_headroom_pass':estimates['2']<=8192*(.85 if stress else .70),
            'threshold_fraction':.85 if stress else .70}
    for name,value in artifacts.items():(ROOT/name).write_bytes(canonical(value)+b'\n')
    (ROOT/'offline-results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))
if __name__=='__main__':run()
