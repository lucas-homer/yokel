"""Authored dimensional controls, not provider output or a semantic oracle."""
import copy
from compact import *

LONG = ('Registered applicants whose independently verified annual report includes every required attachment, '
        'whose signature is witnessed by an authorized officer, whose renewal remains pending during the announced review period, '
        'and whose nominated representative retains written authority for this application, '
        'with each separately identified annex retained in its original language and supplied with the approved explanatory statement, '
        'subject to continuing compliance with the published accessibility arrangements and prior written confirmation of the review location, '
        'except applicants whose license was suspended after notice unless the review panel has issued a written stay preserving eligibility.')
SOURCE = ('The office approves permits only if residents AND either owners OR tenants, except banned applicants unless appeal granted.\n'
          'Qualification scope not identified: ' + LONG + '\r\n'
          'Applicants must comply with section Delta; governing content not supplied.\n'
          'Applications must be received by 16:00 UTC on February 8, 2037.\n'
          'Send remarks by March 9, 2037.\n'
          'Arrive in person by 09:00 UTC on May 1, 2037.\n'
          'Requests due April 3, 2037; clock 12:00 or 13:00 UTC, unresolved; dispatch controls timeliness.\n'
          'head tail head tail head tail\n'
          'Unlabeled Ω e\u0301 🫧 background.')

def frag(sid, head, tail=None, ho=1, to=1, end=None):
    return [sid, head, ho, end or sid, tail if tail is not None else head, to]

def unit(i=1, k=6, s='The office approves permits.', m=0, p=0, y=None, d=None, e=None, q=0, r=''):
    return dict(i=i, k=k, s=s, m=m, p=p, y=y, d=d or [], b=[], e=e or ['s1'], q=q, r=r)

def node(i, op='L', children=None, x=None, q=0, r=''):
    return dict(i=i, o=op, a=children or [], x=x if x is not None else [frag('s1', 'residents')], g='', q=q, r=r)

def link(u, n, w='qual', x=None, q=0, r=''):
    return dict(u=u, w=w, n=n, x=x or [], q=q, r=r)

def dim(state='absent', x=None, reason=''):
    return dict(s=state, x=x or [], r=reason)

def envelope(source, units, nodes=None, links=None):
    table=span_table(source)
    return dict(v=VERSION, h=source_hash(source), t=digest(table), u=units, g=nodes or [], l=links or [], z='END')

def fixture():
    units=[unit(p=2,q=1,r='Full qualification scope is unresolved; explicit only-if condition retained.'), unit(2, s='Applicants must comply with section Delta.', m=1, p=2, e=['s3'], q=2, r='Governing reference content not supplied.')]
    y=dict(c=dim('stated',[frag('s4','16:00')]),z=dim('stated',[frag('s4','UTC')]),b=dim('stated',[frag('s4','received')]))
    units.append(unit(3,k=3,s='Applications deadline date is February 8, 2037.',m=1,e=['s4'],y=y))
    units.append(unit(4,k=3,s='Remarks deadline date is March 9, 2037.',m=5,e=['s5'],q=1,r='Clock, zone, timeliness basis and directive force not stated.',y=dict(c=dim(),z=dim(),b=dim())))
    y=dict(c=dim('stated',[frag('s6','09:00')]),z=dim('stated',[frag('s6','UTC')]),b=dim('na',[frag('s6','Arrive in person')],'In-person arrival, not receipt or dispatch.'))
    units.append(unit(5,k=3,s='Arrival deadline date is May 1, 2037.',e=['s6'],y=y))
    y=dict(c=dim('ambiguous',[frag('s7','12:00 or 13:00')],'Notice leaves alternative clocks unresolved.'),z=dim('stated',[frag('s7','UTC')]),b=dim('stated',[frag('s7','dispatch')]))
    units.append(unit(6,k=3,s='Requests deadline date is April 3, 2037.',e=['s7'],q=1,r='Cutoff clock has unresolved alternatives.',y=y))
    units.append(unit(7,k=8,s='Unlabeled background function remains unknown.',e=['s9'],q=3,r='Function not stated.'))
    nodes=[node('c1','EXC',['c2','c5'],[frag('s1','except')]),node('c2','AND',['c3','c4'],[frag('s1','AND')]),
           node('c3',x=[frag('s1','residents')]),node('c4','OR',['c6','c7'],[frag('s1','either'),frag('s1','OR')]),
           node('c5','EXC',['c8','c9'],[frag('s1','unless')]),node('c6',x=[frag('s1','owners')]),node('c7',x=[frag('s1','tenants')]),
           node('c8',x=[frag('s1','banned applicants')]),node('c9',x=[frag('s1','appeal granted')]),
           node('c10',x=[frag('s2',LONG[:40],LONG[-40:])],q=1,r='The full qualification has no stated governed scope.'),
           node('c11','R',x=[frag('s3','section Delta')],q=2,r='Referenced governing content not supplied.')]
    links=[link(1,'c1','onlyif',[frag('s1','only if')]),link(1,'c10','qual',q=1,r='Scope is unresolved; no applicability logic inferred.'),link(2,'c11','if')]
    return envelope(SOURCE,units,nodes,links)

def semantic_negatives():
    out={}
    v=fixture();v['g'][3]['o']='AND';out['OR_changed_to_AND']=v
    v=fixture();v['g'][0]['a'].reverse();out['exception_scope_swapped']=v
    v=fixture();v['g'][9]['x'][0][4]='published accessibility arrangements';out['long_tail_omits_essential_exception']=v
    v=fixture();v['l'][0]['w']='obj';v['u'][0].update(p=0,q=0,r='');v['l'][1]['u']=2;out['applicability_lost_into_object_role']=v
    v=fixture();v['l'][1]['u']=2;out['correct_condition_wrong_unit']=v
    v=fixture();v['l'][0]['w']='if';out['if_substituted_for_onlyif']=v
    v=fixture();v['g'][-1]['o']='L';out['unresolved_reference_claimed_source_content']=v
    v=fixture();v['u'][6]['d']=[1];out['context_not_applicability']=v
    v=fixture();v['l'].append(link(2,'c10','qual',q=1,r='Shared scope unresolved.'));out['shared_fragment_does_not_establish_scope']=v
    return out
