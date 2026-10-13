"""Materialize complete fictional outputs/sizing. No provider dispatch/tokenizer."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent)) # explicit local modules under -I -S
import copy
import json
import math
from compact import *
from fictional_controls import *


def write(path,value):
    path.write_bytes(canonical(value)+b'\n')


def run():
    fixtures=ROOT/'fixtures';fixtures.mkdir(exist_ok=True)
    request=build(SOURCE);value=fixture()
    validate_response(canonical(value).decode(),'stop',SOURCE,request['table'])
    (fixtures/'source.txt').write_bytes(SOURCE.encode('utf-8'))
    write(fixtures/'positive.json',value)
    write(fixtures/'expanded.json',expand(value,SOURCE,request['table']))
    write(fixtures/'semantic-negatives.json',semantic_negatives())
    write(fixtures/'expected.json',{'role':'authored preservation controls, not semantic oracle/model output','long_text':LONG,'long_node':'c10','no_inheritance_unit':7,
                                  'negative_cases':list(semantic_negatives()),'limits':'independent semantic review required; no aggregate accuracy'})
    write(ROOT/'span-table.json',request['table'])
    write(ROOT/'schema.json',schema(SOURCE,request['table']))
    write(ROOT/'offline-request.json',request['body'])
    profiles={}
    for name,count,shared in [('long_disjoint1',1,False),('long_disjoint8',8,False),('long_disjoint16',16,False),('long_shared8',8,True),('long_shared64',64,True)]:
        rows=['Qualification '+str(i)+': '+LONG for i in range(1,(1 if shared else count)+1)]
        source='\n'.join(rows)
        units=[unit(i=i,s='Authored sizing assertion '+str(i)+'.',p=2,q=1,r='Qualification scope unresolved.',e=['s1' if shared else f's{i}']) for i in range(1,count+1)]
        nodes=[node(f'c{i}',x=[frag(f's{i}',row[:40],row[-40:])],q=1,r='Whole qualification; unresolved scope.') for i,row in enumerate(rows,1)]
        links=[link(i,'c1' if shared else f'c{i}','qual',q=1,r='Scope not evaluated.') for i in range(1,count+1)]
        graph=envelope(source,units,nodes,links)
        validate(graph,source,span_table(source))
        # Paired complete-clause baseline is a measurement representation, NOT legacy conversion.
        baseline={'v':'standalone-full-clause-sizing-only','h':source_hash(source),
                  'u':[dict(i=i,s=units[i-1]['s'],condition_text=rows[0 if shared else i-1],state='unknown') for i in range(1,count+1)],
                  'semantic_status':'not_assessed'}
        raw=canonical(graph);base_raw=canonical(baseline)
        req_info={}
        try:
            req=build(source);req_info={'request_bytes':req['body_bytes'],'guarded_request_bytes':req['guarded_bytes'],'request_guard_pass':True}
        except ValueError as exc:
            req_info={'request_guard_pass':False,'request_error':str(exc)}
        write(fixtures/(name+'-graph.json'),graph)
        write(fixtures/(name+'-full-clause.json'),baseline)
        (fixtures/(name+'-source.txt')).write_bytes(source.encode())
        profiles[name]=dict(units=count,nodes=len(nodes),links=len(links),source_bytes=len(source.encode()),graph_bytes=len(raw),baseline_bytes=len(base_raw),
                            graph_over_baseline=len(raw)/len(base_raw),estimates={str(r):math.ceil(len(raw)/r)+256 for r in [2,3,4]},**req_info)
    result={'status':'OFFLINE_ONLY','fictional_request_bytes':request['body_bytes'],'fictional_guarded_bytes':request['guarded_bytes'],'long_condition_codepoints':len(LONG),
            'settings_output_cap':8192,'input_guard_bytes':40000,'tokenizer':'not used;2/3/4bytes-per-token+256 allowance is sensitivity, not bound',
            'paired_baseline':'complete clauses repeated per unit; authored sizing only, not semantically scored or legacy conversion','compression_claim':False,'profiles':profiles}
    write(ROOT/'offline-results.json',result)
    print(json.dumps(result,indent=2))

if __name__=='__main__':run()
