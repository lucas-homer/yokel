"""Replay original attack constructors, with v2 envelope migration outside untouched copy."""
import ast
import copy
import json
from pathlib import Path
p=Path(__file__).resolve().with_name('probe.py')
tree=ast.parse(p.read_text())
# Original imports, initialization and function bodies; old vulnerability assertions
# intentionally remain in probe.py, and are replaced by independent observations here.
keep=[]
for n in tree.body:
    if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef)) or n.lineno<=16 or 277<=n.lineno<=280:
        keep.append(n)
ns={'__file__':str(p)}
exec(compile(ast.Module(body=keep,type_ignores=[]),str(p),'exec'),ns)
S,L,C=ns['S'],ns['L'],ns['C']
import importlib.util
sp=importlib.util.spec_from_file_location('oldscore',p.parent.parent/'design-r3/fixtures/r17score.py')
OLD=importlib.util.module_from_spec(sp);sp.loader.exec_module(OLD)
case,score,assembly,combined,dup=[ns[k] for k in ('case','score','assembly','combined','duplicate_wrong_tree')]
def emit(name,x): print(json.dumps({'probe':name,'result':x},sort_keys=True))
def run(m,cs,fs,**kw):
    m['excluded_sessions']=['reference-author','reference-reviewer']
    try: return S.decide(m,cs,fs,**kw)['outcome']
    except S.SpecError as e: return 'REJECT: '+str(e)
for name,opts in [('control',{}),('hidden_duplicate',{'bad':True}),('opposite_irrespective',{'irrespective':True,'deny':True})]:
    m,cs,fs=assembly(**opts)
    result=run(m,cs,fs); emit(name,result)
    assert result==({'control':'O2','hidden_duplicate':'O1'}.get(name,result))
    if name=='opposite_irrespective':
        assert result.startswith('REJECT: FULL released')
        for cid in cs:
            if cid!='S1-OPQ': cs[cid]={'call_id':cid,'state':'skipped'}
        assert run(m,cs,fs)=='O3'; emit(name+'_stopped','O3')
for kind in ['reused','excluded','post_halt']:
    m,cs,fs=assembly()
    if kind=='post_halt': cs['S2-FULL']['halt']='KEY_USAGE_UNRECONCILED'
    else:
        for fn in list(fs):
            if fn.endswith('.json'):
                a=json.loads(fs[fn]); a['adjudicator']['session']=('reused-'+a['adjudicator']['role']) if kind=='reused' else 'reference-author'; fs[fn]=S.canonical_bytes(a)
    r=run(m,cs,fs); assert r.startswith('REJECT:'); emit(kind,r)
for pol in ['UNSET',None,'P-SOFT','P-HARD','P-ACCEPT']:
    es=[dict(type='INIT',required_calls=C.CALLS6,key_limit=L.KEY_MAX,release_policy=pol),dict(type='BIND_RELEASE',release_policy=pol)]
    r=L.admit(es,'S1-OPQ',0); assert r[0]==(pol in ('P-HARD','P-ACCEPT')); emit('policy_'+str(pol),r)
pinned=dict(limit=L.KEY_MAX,limit_reset=None)
r=L.reconcile(2,160000000,100000000,pinned,[(t,dict(usage=u,**pinned)) for t,u in [(0,150000000),(60,140000000),(300,160000000)]])
assert r[0]=='HALT';emit('regression',r)
c=case('F05c-');c['output']['links'].append(dict(unit_id=2,node_id='c1',role='qual',q=1,evidence=[[34,40]]))
assert score(c)['relations']['R1']['verdict']=='contradiction';emit('qual_denial','contradiction')
# Correct typed duplicate, and hedges at either link or operator, both orders.
for kind in ['correct','hedged_link','hedged_node','alt']:
    for rev in [False,True]:
        c=dup(case('F15b-'))
        if kind=='correct':c['output']['nodes'][3]['op']='AND'
        elif kind=='hedged_link':c['output']['links'][1]['q']=1
        elif kind=='hedged_node':c['output']['nodes'][3]['q']=1
        else:c['output']['nodes'][3]['op']='ALT'
        if rev:c['output']['links'].reverse()
        r=score(c);emit(kind+('_reversed' if rev else ''),r)
        old=OLD.score(c['reference'],c['source'],c['output'],c['mappings'],c['arm'])
        assert r['compounds']['R1:N1']['verdict']==old['compounds']['R1:N1']['verdict'] and not r['invented']
        emit(kind+'_r3_comparison',old['compounds']['R1:N1']['verdict'])
# Duplicate every completely faithful FULL gold case (including nested structures).
count=0
for base in ns['data']['cases']:
    if base['arm']!='FULL':continue
    before=score(base)
    if not all(r['verdict']=='correct' for r in before['relations'].values()) or not all(x['verdict']=='correct' for x in before['compounds'].values()) or before['invented']:continue
    c=copy.deepcopy(base);o=c['output']; ids={u['id']:u['id']+1000 for u in o['units']};ren={n['id']:'twin_'+n['id'] for n in o['nodes']}
    o['units'] += [dict(u,id=ids[u['id']]) for u in list(o['units'])]
    o['nodes'] += [dict(n,id=ren[n['id']],args=[ren[a] for a in n['args']]) for n in list(o['nodes'])]
    o['links'] += [dict(l,unit_id=ids[l['unit_id']],node_id=ren[l['node_id']]) for l in list(o['links'])]
    for m in c['mappings']:m['units'] += [dict(u,unit=ids[u['unit']]) for u in list(m['units'])]
    after=score(c)
    assert all(x['verdict']=='correct' for x in after['compounds'].values()) and not after['invented'],(base['id'],after)
    count+=1
emit('faithful_full_gold_twins',count)
for form in ['direct','inverse','opposite']:
    for depth in range(4):
        c=case('F19-');c['arm']='FULL';c['mappings'][0]['units'][0]['form']=form
        for i in range(depth):
            root=c['output']['links'][0]['node_id'];nid='not'+str(i)
            c['output']['nodes'].append(dict(id=nid,op='NOT',args=[root],q=0,evidence=[]));c['output']['links'][0]['node_id']=nid
        r=score(c)['relations']['R1']['verdict'];assert r==('correct' if form=='direct' else 'inversion');emit('regardless_'+form+'_'+str(depth),r)
print('ALL FOCUSED ASSERTIONS PASSED')
# Reuse the original wire_validate function without changing its attack construction.
wp=p.parent.parent.parent/'round16-wire-compat/protocol-w2-1/wire.py'
sp=importlib.util.spec_from_file_location('wire_r4',wp)
W=importlib.util.module_from_spec(sp);sp.loader.exec_module(W);ns['W']=W
for attack in ['duplicate_wrong_OR','opposite_irrespective']:
    irr=attack=='opposite_irrespective';m,cs,fs=assembly(bad=not irr,irrespective=irr,deny=irr)
    for slot in S.SLOTS:
        for arm in S.ARMS:
            cid=f'{slot}-{arm}'
            c=combined(slot,arm,not irr and slot=='S1' and arm=='FULL',irr,irr and slot=='S1' and arm=='OPQ')
            expanded=ns['wire_validate'](c)
            fs[f'{cid}.out']=S.canonical_bytes(expanded['output']);h=S.sha_bytes(fs[f'{cid}.out']);cs[cid]['output_sha256']=h
            for role in S.ADJUDICATORS:
                fn=f'{cid}.{role}.json';adj=json.loads(fs[fn]);adj['output_sha256']=h;fs[fn]=S.canonical_bytes(adj)
    r=run(m,cs,fs);emit('wire_six_'+attack,r)
    assert r=='O1' if not irr else r.startswith('REJECT: FULL released')
print('WIRE ASSERTIONS PASSED')
