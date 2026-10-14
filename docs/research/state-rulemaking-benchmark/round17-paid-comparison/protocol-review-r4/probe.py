"""Offline r3 review. Fictional fixtures only. Writes nothing.
Run with python3 -I -S -B.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESIGN = HERE.parent / 'design-r3-1'
spec = importlib.util.spec_from_file_location('checker_r3', DESIGN / 'fixtures/check.py')
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
S, L = C.S, C.L
data = json.loads((DESIGN / 'fixtures/cases.json').read_bytes())

def case(prefix):
    return copy.deepcopy(next(c for c in data['cases'] if c['id'].startswith(prefix)))

def score(c):
    S.validate_reference(c['reference'], c['source'])
    return S.score(c['reference'], c['source'], c['output'], c['mappings'], c['arm'])

def show(name, value):
    print(json.dumps({'probe': name, 'observed': value}, sort_keys=True))

def rejected(fn):
    try:
        fn()
    except (S.SpecError, L.LedgerError) as exc:
        return str(exc)
    return False

pins = json.loads((DESIGN / 'READY.primary.json').read_bytes())['sha256']
assert all(hashlib.sha256((DESIGN / p).read_bytes()).hexdigest() == sha for p, sha in pins.items())
show('ready_primary_hashes', len(pins))

# All round-2 probe scenarios, migrated to r3's schema/API and acceptance assertions.
c = case('F09-')
c['reference']['relations'][0]['logic']['markers'] = []
e = rejected(lambda: score(c))
assert e and 'partition' in e
show('reference_missing_not', e)

c = case('F15b-')
c['output']['nodes'][1].update(op='NOT', args=['c4'], evidence=[])
c['output']['nodes'].append(dict(id='c4', op='L', args=[], q=0, evidence=[[22,36]]))
r = score(c)
assert r['relations']['R1']['verdict'] == 'inversion'
assert r['compounds']['R1:N1']['verdict'] == 'relation_failed'
show('invented_not_inside_and', {'relation': r['relations']['R1']['verdict'], 'compound': r['compounds']['R1:N1']['verdict']})
cells = {sid: dict(status='valid', completion_tokens=100,
                  relations=[dict(key=f'{sid}:{i}', verdict='correct', critical=True) for i in range(4)])
         for sid in ('S1','S2','S3')}
t = S.bar_T(cells, cells, [dict(verdict='relation_failed', critical=True) for _ in range(6)])
assert not t['pass']
show('false_not_can_pass_T', t)

c = case('F01b-')
c['output']['links'][0]['evidence'] = [[38,104]]
c['output']['nodes'][0]['evidence'] = [[0,37]]
assert score(c)['relations']['R1']['verdict'] == 'shortened'
show('whole_clause_link_unrelated_leaf', 'shortened')

c = case('F09-')
c['arm'] = 'FULL'
c['output']['nodes'][0].update(op='NOT', args=['c2'], evidence=[[34,37]])
c['output']['nodes'].append(dict(id='c2', op='L', args=[], q=0, evidence=[[22,33],[38,46]]))
assert score(c)['relations']['R1']['verdict'] == 'correct'
show('faithful_if_not', 'correct')

c = case('F10e-')
extra = copy.deepcopy(c['output']['links'][0]); extra['role'] = 'if'
c['output']['links'].append(extra)
assert score(c)['relations']['R1']['verdict'] == 'contradiction'
show('critical_extra_scope_change', 'contradiction')

a, b = case('F05a-'), case('F05b-')
assert a['gold'] and not b['gold']
assert all('assertion' in u and 'evidence' in u for c in data['cases'] if c['gold'] for u in c['output']['units'])
show('gold_mutation_split', {'F05a':a['gold'], 'F05b':b['gold'], 'missing_mapping_inputs':0})
n, failures = C.adjudicator_gate(data, {})
assert failures
show('zero_adjudicators', failures)
c = case('F15b-')
c['reference']['targets'].append(dict(tid='T2', gloss='', quote=c['reference']['relations'][0]['logic']['children'][0]['quotes'][0]))
e = rejected(lambda: score(c)); assert e and 'orphan' in e
show('orphan_target', e)
pinned = dict(limit=1_730_000_000, limit_reset=None)
rd = lambda u: dict(usage=u, **pinned)
assert L.reconcile(1,100_000_000,0,pinned,[(0,rd(0)),(60,rd(100_000_000))]) == ('RECONCILED',100_000_000)
assert L.reconcile(2,160_000_000,100_000_000,pinned,[(0,rd(160_000_000))]) == ('RECONCILED',160_000_000)
assert L.reconcile(1,100_000_000,0,pinned,[(t,rd(0)) for t in (0,60,300,900)])[0] == 'HALT'
show('lag_then_catchup', 'wait/reconcile; next cumulative total reconciles; persistent zero halts')
show('budget', dict(six_floors=6*L.FLOOR, key_limit=L.KEY_MAX, conditional=1_730_000_000+263_840_000))
old, new = HERE.parent/'sources', HERE.parent/'sources-r2'
screen_sha = json.loads((old/'READY.json').read_bytes())['files']['screen.py']['sha256']
assert all(hashlib.sha256((p/'screen.py').read_bytes()).hexdigest()==screen_sha for p in (old,new))
show('unchanged_screen_hash', screen_sha)

# New attacks: duplicate a good typed claim but change AND to OR on the duplicate.
def duplicate_wrong_tree(c):
    c = copy.deepcopy(c)
    out = c['output']
    uid = max(u['id'] for u in out['units'])+1
    unit = copy.deepcopy(out['units'][0]); unit['id']=uid; out['units'].append(unit)
    ren = {n['id']: 'bad_'+n['id'] for n in out['nodes']}
    extra_nodes = copy.deepcopy(out['nodes'])
    for n in extra_nodes:
        n['id']=ren[n['id']]; n['args']=[ren[a] for a in n['args']]
    extra_nodes[0]['op']='OR'
    out['nodes'] += extra_nodes
    link = copy.deepcopy(out['links'][0]); link.update(unit_id=uid,node_id=ren[link['node_id']])
    out['links'].append(link)
    c['mappings'][0]['units'].append(dict(unit=uid,form='direct'))
    return c

c = duplicate_wrong_tree(case('F15b-'))
r = score(c)
assert r['relations']['R1']['verdict']=='correct' and r['compounds']['R1:N1']['verdict']=='correct' and not r['invented']
show('duplicate_wrong_OR', r)

# A twelve-relation/nine-compound assembly, all three sources meet E8.
# Combine four distinct fictional fixtures per source, adjusting every span and id.
def combined(slot, arm, bad=False, irrespective=False, deny=False):
    prefixes = ['F15b-', 'F25a-', 'F10e-', 'F19-' if irrespective else 'F09b-']
    source=f'Fictional notice {slot}.\n'
    out=dict(units=[],nodes=[],links=[]); mappings=[]; refs=[]; targets=[]
    for ix,prefix in enumerate(prefixes,1):
        c=case(prefix)
        if bad and ix==1: c=duplicate_wrong_tree(c)
        if irrespective and ix==4:
            c['reference']['relations'][0].update(critical=True,critical_reason='Changes whether wagon owners owe a toll.')
            if deny:
                c['output']['units'][0]['assertion']='Tolls do not apply to any wagon.'
                c['mappings'][0]['units'][0]['form']='opposite'
        off=len(source); source+=c['source']+'\n'
        def shift(v):
            if isinstance(v,dict):
                return {k:(x+off if k in ('start','end') else shift(x)) for k,x in v.items()}
            if isinstance(v,list): return [shift(x) for x in v]
            return v
        ref=shift(c['reference'])
        tid=f'T{ix}'; rid=f'R{ix}'
        ref['targets'][0]['tid']=tid; targets+=ref['targets']
        ref['relations'][0].update(tid=tid,rid=rid); refs+=ref['relations']
        for u in c['output']['units']:
            u['id']+=ix*10; u['evidence']=[[a+off,b+off] for a,b in u['evidence']]
            out['units'].append(u)
        for n in c['output']['nodes']:
            n['id']=f'{ix}_'+n['id']; n['args']=[f'{ix}_'+a for a in n['args']]
            n['evidence']=[[a+off,b+off] for a,b in n['evidence']]; out['nodes'].append(n)
        for l in c['output']['links']:
            l['unit_id']+=ix*10; l['node_id']=f'{ix}_'+l['node_id']
            l['evidence']=[[a+off,b+off] for a,b in l['evidence']]; out['links'].append(l)
        m=c['mappings'][0]; m['tid']=tid
        for u in m['units']: u['unit']+=ix*10
        mappings.append(m)
    ref=dict(spec_version=S.REF_VERSION,source_id=slot,source_text_sha256=S.sha_bytes(source.encode()),
             targets=targets,relations=refs,out_of_scope_notes=[])
    # Occurrence indices must be recomputed after concatenation.
    def requote(v):
        if isinstance(v,dict):
            if set(v)=={'start','end','text','occurrence'}:
                v['occurrence']=S.match_starts(source,v['text']).index(v['start'])+1
            else:
                for x in v.values(): requote(x)
        elif isinstance(v,list):
            for x in v: requote(x)
    requote(ref)
    if arm=='OPQ':
        # Each relation is carried intact by a single leaf with its faithful role.
        out['nodes']=[]; out['links']=[]
        for ix,r in enumerate(refs,1):
            nid=f'leaf{ix}'
            out['nodes'].append(dict(id=nid,op='L',args=[],q=0,evidence=[[q['start'],q['end']] for q in r['clause']]))
            out['links'].append(dict(unit_id=ix*10+1,node_id=nid,role={'RESTRICT':'onlyif','IRRESPECTIVE':'regardless'}.get(r['class'],'if'),q=0,evidence=[]))
    return dict(source=source,reference=ref,output=out,mappings=mappings,arm=arm)

def assembly(bad=False, irrespective=False, deny=False):
    manifest=dict(spec_version=S.MANIFEST_VERSION, typed_testable=True,
                  adjudicators={r:dict(model=m,effort='high') for r,m in S.ADJUDICATORS.items()},sources={})
    calls={}; files={}
    for slot in S.SLOTS:
        c=combined(slot,'OPQ',irrespective=irrespective); src=c['source'].encode(); ref=S.canonical_bytes(c['reference'])
        files[f'{slot}.src']=src; files[f'{slot}.ref']=ref
        manifest['sources'][slot]=dict(source_id=slot,source_file=f'{slot}.src',source_sha256=S.sha_bytes(src),
            reference_file=f'{slot}.ref',reference_sha256=S.sha_bytes(ref),
            relations={r['rid']:r['critical'] for r in c['reference']['relations']},
            compounds={r['cid']:r['critical'] for r in S.compounds(c['reference'])})
        for arm in S.ARMS:
            c=combined(slot,arm,bad and slot=='S1' and arm=='FULL',irrespective,deny and slot=='S1' and arm=='OPQ')
            cid=f'{slot}-{arm}'; fn=f'{cid}.out'
            files[fn]=S.canonical_bytes(c['output']); h=S.sha_bytes(files[fn])
            calls[cid]=dict(call_id=cid,state=13,completion_tokens=1000,output_file=fn,output_sha256=h,halt=None)
            for role in S.ADJUDICATORS:
                files[f'{cid}.{role}.json']=S.canonical_bytes(C.adjudication(c,cid,role,slot,h,S.sha_bytes(ref),f'fresh-{role}-{cid}'))
    return manifest,calls,files

m,cs,fs=assembly(True)
r=S.decide(m,cs,fs)
assert r['outcome']=='O2'
show('duplicate_wrong_OR_decide', {'outcome':r['outcome'],'N':sum(len(s['relations']) for s in m['sources'].values()),
                                 'Nc':sum(len(s['compounds']) for s in m['sources'].values()),'T':r['phases']['FULL']['A1']['bar']})
out=json.loads(fs['S1-FULL.out'])
out['units']=[u for u in out['units'] if u['id']!=11]
out['links']=[l for l in out['links'] if l['unit_id']!=11]
out['nodes']=[n for n in out['nodes'] if not n['id'].startswith('1_c')]
fs['S1-FULL.out']=S.canonical_bytes(out)
cs['S1-FULL']['output_sha256']=S.sha_bytes(fs['S1-FULL.out'])
for role in S.ADJUDICATORS:
    fn=f'S1-FULL.{role}.json'; adj=json.loads(fs[fn])
    adj['output_sha256']=cs['S1-FULL']['output_sha256']
    adj['mappings'][0]['units']=[u for u in adj['mappings'][0]['units'] if u['unit']!=11]
    fs[fn]=S.canonical_bytes(adj)
assert S.decide(m,cs,fs)['outcome']=='O1'
show('wrong_OR_without_masking_copy','O1')

# Same-provider session reuse across outputs (model/effort/hash fields remain right).
m,cs,fs=assembly()
for fn in list(fs):
    if fn.endswith('.json'):
        a=json.loads(fs[fn]); a['adjudicator']['session']='reused-'+a['adjudicator']['role']; fs[fn]=S.canonical_bytes(a)
r=S.decide(m,cs,fs); assert r['outcome']=='O2'
show('reused_adjudicator_sessions', r['outcome'])

# Release policy values are not examined by admission reference semantics.
for policy in ('UNSET','P-HARD','P-ACCEPT'):
    es=[dict(type='INIT',required_calls=[f'{s}-{a}' for a in S.ARMS for s in S.SLOTS],key_limit=L.KEY_MAX,release_policy=policy),
        dict(type='BIND_RELEASE',release_sha256='0'*64)]
    show('admit_'+policy, L.admit(es,'S1-OPQ',0))

# Opposite with mere uncertain qualification can erase the unqualified-denial audit.
c=case('F05c-')
c['output']['links'].append(dict(unit_id=2,node_id='c1',role='qual',q=1,evidence=[[34,40]]))
show('opposite_with_qual',score(c)['relations']['R1'])

# Regression relative to a preceding lagging read, but still above prior-call baseline.
show('regression_between_reads',L.reconcile(2,160_000_000,100_000_000,pinned,
    [(0,rd(150_000_000)),(60,rd(140_000_000)),(300,rd(160_000_000))]))

# A record after HALT remains accepted by decide (all six structurally present).
m,cs,fs=assembly(); cs['S2-FULL']['halt']='KEY_USAGE_UNRECONCILED'
show('released_after_halt',S.decide(m,cs,fs)['outcome'])

# `regardless(any)` cannot ignore reversal of the target assertion itself.
c=case('F19-')
c['output']['units'][0]['assertion']='Tolls do not apply to any wagon.'
c['mappings'][0]['units'][0]['form']='opposite'
assert score(c)['relations']['R1']['verdict']=='correct'
show('opposite_irrespective',score(c)['relations']['R1'])
m,cs,fs=assembly(irrespective=True,deny=True)
r=S.decide(m,cs,fs); assert r['outcome']=='O2'
show('opposite_irrespective_decide',{'outcome':r['outcome'],'OPQ1_R4':r['scores']['S1-OPQ']['A1']['relations']['R4']['verdict']})

# Confirm the counterexamples survive the frozen candidate's actual wire validation.
# These imports/read calls are offline code, schemas and prompts, never R17 source files.
wp=HERE.parents[1]/'round16-wire-compat/protocol-w2-1/wire.py'
ws=importlib.util.spec_from_file_location('wire_review_r3',wp)
W=importlib.util.module_from_spec(ws); ws.loader.exec_module(W)

def wire_validate(c):
    source,out=c['source'],c['output']; profile='opaque' if c['arm']=='OPQ' else 'full'
    plan=W.build(source,profile); table=plan['table']; rows=table['rows']
    def fragment(span):
        a,b=span
        A=next(r for r in rows if r[1]<=a<r[2]); Z=next(r for r in rows if r[1]<b<=r[2])
        head=source[a:min(a+48,b,A[2])]; tail=source[max(Z[1],a,b-48):b]
        hs=S.match_starts(A[3],head); ho=hs.index(a-A[1])+1
        ts=[k for k in S.match_starts(Z[3],tail) if Z[1]+k>=a and Z[1]+k+len(tail)>=a+len(head)]
        to=ts.index(b-len(tail)-Z[1])+1
        return [A[0],head,ho,Z[0],tail,to]
    rename={n['id']:f'c{i}' for i,n in enumerate(out['nodes'],1)}
    units=[]
    for u in out['units']:
        app=any(l['unit_id']==u['id'] and l['role'] in ('if','onlyif','unless') for l in out['links'])
        ev=[r[0] for r in rows if any(a<r[2] and r[1]<b for a,b in u['evidence'])]
        units.append(dict(i=u['id'],k=6,s=u['assertion'],m=1,p=int(app),y=None,d=[],b=[],e=ev,q=0,r=''))
    compact=dict(v=W.r15.VERSION,h=W.r15.source_hash(source),t=W.r15.digest(table),z='END',u=units,
        g=[dict(i=rename[n['id']],o=n['op'],a=[rename[a] for a in n['args']],x=[fragment(x) for x in n['evidence']],g='',q=n['q'],r='') for n in out['nodes']],
        l=[dict(u=l['unit_id'],w=l['role'],n=rename[l['node_id']],x=[fragment(x) for x in l['evidence']],q=l['q'],r='') for l in out['links']])
    wire=W.from_compact(compact)
    expanded=W.validate_response(json.dumps(wire),'stop',source,table,profile,plan=plan)
    c=copy.deepcopy(c); c['output']=expanded
    return c

for name,c in [('duplicate_wrong_OR',combined('S1','FULL',True)),
               ('opposite_irrespective',combined('S1','OPQ',irrespective=True,deny=True))]:
    expanded=wire_validate(c); r=score(expanded)
    assert all(x['verdict']=='correct' for x in r['relations'].values())
    assert all(x['verdict']=='correct' for x in r['compounds'].values()) and not r['invented']
    show('wire_validated_'+name, {'relations':{k:v['verdict'] for k,v in r['relations'].items()},'compounds':{k:v['verdict'] for k,v in r['compounds'].items()}})

for attack in ('duplicate_wrong_OR','opposite_irrespective'):
    irr=attack=='opposite_irrespective'
    m,cs,fs=assembly(bad=not irr,irrespective=irr,deny=irr)
    for slot in S.SLOTS:
        for arm in S.ARMS:
            cid=f'{slot}-{arm}'
            c=combined(slot,arm,not irr and slot=='S1' and arm=='FULL',irr,irr and slot=='S1' and arm=='OPQ')
            expanded=wire_validate(c)
            fs[f'{cid}.out']=S.canonical_bytes(expanded['output'])
            h=S.sha_bytes(fs[f'{cid}.out']); cs[cid]['output_sha256']=h
            for role in S.ADJUDICATORS:
                fn=f'{cid}.{role}.json'; adj=json.loads(fs[fn]); adj['output_sha256']=h; fs[fn]=S.canonical_bytes(adj)
    result=S.decide(m,cs,fs)
    assert result['outcome']=='O2'
    show('all_six_wire_validated_'+attack,result['outcome'])
