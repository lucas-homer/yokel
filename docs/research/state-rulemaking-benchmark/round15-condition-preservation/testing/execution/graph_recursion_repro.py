"""Supplemental original-r15.0 robustness repro; no edits, network or credentials."""
import importlib.util, json, sys
from pathlib import Path
p=Path(__file__).resolve().parents[2]/'protocol/compact.py'
spec=importlib.util.spec_from_file_location('r15_graph_repro',p)
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
source='Condition.';table=C.span_table(source)
u=dict(i=1,k=6,s='Authored stress fixture.',m=0,p=0,y=None,d=[],b=[],e=['s1'],q=0,r='')
nodes=[dict(i='c'+str(i),o='NOT',a=['c'+str(i+1)],x=[],g='',q=0,r='') for i in range(1,399)]
nodes.append(dict(i='c399',o='L',a=[],x=[['s1','Condition.',1,'s1','Condition.',1]],g='',q=0,r=''))
v=dict(v=C.VERSION,h=C.source_hash(source),t=C.digest(table),u=[u],g=nodes,l=[dict(u=1,w='obj',n='c1',x=[],q=0,r='')],z='END')
limit=int(sys.argv[1]);sys.setrecursionlimit(limit)
try:
    C.validate(v,source,table)
    result={'accepted':True}
except Exception as e:
    result={'accepted':False,'exception_type':type(e).__name__,'exception_text':str(e)}
print(json.dumps({'protocol':C.VERSION,'nodes':399,'authored_depth':399,'process_recursion_limit':limit,**result}))
