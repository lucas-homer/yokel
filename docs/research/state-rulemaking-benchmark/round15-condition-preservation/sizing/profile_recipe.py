"""Authored dimensional sizing recipes, never model output, source gold or semantic tests.
Instantiate only after an exact protocol READY import via candidate measurement.
"""
import copy

def clause(index,length):
    head=f'Clause{index:03d} starts: ';tail=f' :Clause{index:03d} ends.'
    filler='the fictional permit remains in effect and the complete record is retained; '
    return head+(filler*((length//len(filler))+1))[:length-len(head)-len(tail)]+tail

def profiles(k):
    specs=[
        ('shared160-u24',24,160,True,12,1,False),
        ('disjoint160-u24',24,160,False,12,1,False),
        ('shared600-u1',1,600,True,12,1,False),
        ('shared600-u24-shortanchors',24,600,True,12,1,False),
        ('shared600-u24-longanchors',24,600,True,48,1,False),
        ('shared600-u110',110,600,True,12,1,False),
        ('shared600-u159',159,600,True,12,1,False),
        ('disjoint600-u8',8,600,False,12,1,False),
        ('disjoint600-u24',24,600,False,12,1,False),
        ('leaf-fragments8',1,600,True,12,8,False),
        ('leaf-fragments9',1,600,True,12,9,False),
        ('deadline-shared600-u8',8,600,True,12,1,True),
    ]
    result=[]
    for name,count,length,shared,width,fragment_count,deadline in specs:
        clauses=[clause(i,length) for i in range(1,(fragment_count if shared else count)+1)]
        rows=list(clauses)
        if deadline:rows.append('The deadline is receipt by 17:00 UTC on 8 September 2037.')
        source='\n'.join(rows);table=k.span_table(source)
        def fragment(row,text,width_):return [f's{row}',text[:width_],1,f's{row}',text[-width_:],1]
        nodes=[]
        for i in range(1,(1 if shared else count)+1):
            xs=[fragment(j,clauses[j-1],width) for j in range(1,fragment_count+1)] if shared else [fragment(i,clauses[i-1],width)]
            nodes.append(dict(i=f'c{i}',o='L',a=[],x=xs,g='',q=0,r=''))
        units=[];links=[];repeated=[]
        for i in range(1,count+1):
            sid='s1' if shared else f's{i}';unit=dict(i=i,k=3 if deadline else 6,s=f'Authored dimensional assertion {i}.',m=0,p=1,y=None,d=[],b=[],e=[sid],q=0,r='')
            if deadline:
                def dim(text):return dict(s='stated',x=[[f's{len(rows)}',text,1,f's{len(rows)}',text,1]],r='')
                unit['y']={'c':dim('17:00'),'z':dim('UTC'),'b':dim('receipt')};unit['e'].append(f's{len(rows)}')
            units.append(unit);links.append(dict(u=i,w='if',n='c1' if shared else f'c{i}',x=[],q=0,r=''))
            old={key:copy.deepcopy(unit[key]) for key in ('i','k','s','m','d','b','e','q','r')};old['c']='\n'.join(clauses) if shared else clauses[i-1];repeated.append(old)
        wire={'v':k.VERSION,'h':k.source_hash(source),'t':k.digest(table),'u':units,'g':nodes,'l':links,'z':'END'}
        # No purported migration: this is authored text repeated per unit solely for byte accounting.
        prose={'v':'authored-unbounded-repeat.v0','h':wire['h'],'t':wire['t'],'u':repeated,'z':'END'}
        result.append({'id':name,'source':source,'wire':wire,'repeated_text_fixture':prose,'condition_length_per_fragment':length,'anchor_width':width,'purpose':'Authored same-clause attachment sizing; not model extraction, asserted legal equivalence or R14 migration.','expected_graph_admission':fragment_count<=8,'R14_c180_admissible_by_length_only':max(len(u['c']) for u in repeated)<=180})
    base=next(x for x in result if x['id']=='shared600-u1')
    for depth in (12,13):
        p=copy.deepcopy(base);p['id']=f'depth{depth}';p['purpose']='Authored unary DAG depth stress; no claimed source logical entailment.';p['expected_graph_admission']=depth<=12
        leaf=p['wire']['g'][0];leaf['i']=f'c{depth}';p['wire']['g']=[dict(i=f'c{i}',o='NOT',a=[f'c{i+1}'],x=[],g='',q=0,r='') for i in range(1,depth)]+[leaf]
        result.append(p)
    for name,nodes,links in [('nodes399-links399',399,399),('nodes400-links399',400,399),('nodes399-links400',399,400)]:
        p=copy.deepcopy(base);p['id']=name;p['purpose']='Authored count/sentinel stress; duplicated leaves are not semantic coverage or canonical graph design.';p['expected_graph_admission']=nodes<400 and links<400
        unit=p['wire']['u'][0];unit.update(p=2,q=1,r='Authored stress fixture leaves applicability structure unresolved.')
        leaf=p['wire']['g'][0];p['wire']['g']=[dict(copy.deepcopy(leaf),i=f'c{i}') for i in range(1,nodes+1)]
        p['wire']['l']=[dict(u=1,w='qual',n=f'c{i}',x=[],q=1,r='Opaque stress qualification; logical role unresolved.') for i in range(1,min(nodes,links)+1)]
        if nodes>links:p['wire']['g'][-2].update(o='NOT',a=[f'c{nodes}'],x=[])
        if links>nodes:p['wire']['l'].append(dict(u=1,w='acts',n='c1',x=[],q=0,r=''))
        result.append(p)
    # Paired exact complete clause, opaque deferred interpretation versus authored typed grouping.
    a,b,c=(clause(i,190) for i in (901,902,903))
    condition='ONLY IF '+a+' AND '+b+' EXCEPT '+c
    source='The fictional office accepts requests '+condition+'.';table=k.span_table(source)
    def frag(text):return ['s1',text[:12],1,'s1',text[-12:],1]
    def short(text):return ['s1',text,1,'s1',text,1]
    base_unit=dict(i=1,k=6,s='The fictional office accepts requests.',m=0,p=1,y=None,d=[],b=[],e=['s1'],q=0,r='')
    prose_unit={key:copy.deepcopy(base_unit[key]) for key in ('i','k','s','m','d','b','e','q','r')};prose_unit['c']=condition
    common={'source':source,'condition_length_per_fragment':len(condition),'anchor_width':12,'expected_graph_admission':True,'R14_c180_admissible_by_length_only':False,'paired_authored_control':'opaque-versus-typed-same-complete-fictional-clause','purpose':'Same authored fictional source/clause/scope; typed grouping is authored interpretation and opaque version defers interpretation. Byte overhead only, no host semantic equivalence or model improvement claim.','repeated_text_fixture':{'v':'authored-unbounded-repeat.v0','h':k.source_hash(source),'t':k.digest(table),'u':[prose_unit],'z':'END'}}
    opaque_unit=copy.deepcopy(base_unit);opaque_unit.update(p=2,q=1,r='Applicability grouping is deliberately deferred in this authored opaque control.')
    opaque={'v':k.VERSION,'h':k.source_hash(source),'t':k.digest(table),'u':[opaque_unit],'g':[dict(i='c1',o='L',a=[],x=[frag(condition)],g='',q=1,r='Complete clause preserved without a logical parse.')],'l':[dict(u=1,w='qual',n='c1',x=[],q=1,r='Opaque exact clause; connective role deliberately unresolved.')],'z':'END'}
    typed={'v':k.VERSION,'h':k.source_hash(source),'t':k.digest(table),'u':[base_unit],'g':[dict(i='c1',o='EXC',a=['c2','c5'],x=[short('EXCEPT')],g='',q=0,r=''),dict(i='c2',o='AND',a=['c3','c4'],x=[short('AND')],g='',q=0,r=''),dict(i='c3',o='L',a=[],x=[frag(a)],g='',q=0,r=''),dict(i='c4',o='L',a=[],x=[frag(b)],g='',q=0,r=''),dict(i='c5',o='L',a=[],x=[frag(c)],g='',q=0,r='')],'l':[dict(u=1,w='onlyif',n='c1',x=[short('ONLY IF')],q=0,r='')],'z':'END'}
    result.extend([dict(copy.deepcopy(common),id='paired-opaque-complete-clause',wire=opaque),dict(copy.deepcopy(common),id='paired-typed-complete-clause',wire=typed)])
    return result
