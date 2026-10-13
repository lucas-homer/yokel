"""Authored offline controls; never provider responses or semantic oracle results."""
import copy
from compact import VERSION, source_hash, span_table, digest
SOURCE = ('Send remarks by April 9, 2031.\r\n'
          'Applications must be received by 5 p.m. Eastern on May 12, 2031.\n'
          'Dispatch requests by June 3, 2031; dispatch controls timeliness.\n'
          'Amend Rule Q-8 (previous filing F-17, filed January 6, 2029, effective February 2, 2029).\n'
          'The office is in Alder City, North Province.\n'
          'Readers should consult the archive for background.\n'
          'Unlabeled item: Ω e\u0301 🫧.\n'
          'The commission was founded in 1964.\n'
          'Arrive in person by 09:00 UTC on July 4, 2031.\n'
          'Requests are due August 2, 2031; cutoff is 12:00 or 13:00 UTC, unresolved by this notice.')

def fixture():
    units=[]
    def add(k,s,e,m=0,c='',d=None,q=0,r=''):
        units.append(dict(i=len(units)+1,k=k,s=s,m=m,c=c,d=d or [],b=[],e=[e],q=q,r=r))
    add(3,'Remarks deadline date is April 9, 2031.','s1',5,
        'Cutoff clock unknown; timezone unknown; receipt-versus-dispatch unknown.',q=1,
        r='Source gives only a date; cutoff clock, timezone, timeliness basis and directive force remain unknown.')
    add(6,'An unspecified actor is directed to send remarks by the deadline.','s1',5,d=[1],q=1,r='Actor is not stated; bare directive does not settle mandatory versus advisory force.')
    add(3,'Applications deadline date is May 12, 2031.','s2',1,
        'Cutoff clock 5 p.m.; timezone Eastern; timeliness basis receipt.')
    add(3,'Applications cutoff clock is 5 p.m.','s2',1,d=[3])
    add(3,'Applications cutoff timezone is Eastern.','s2',1,d=[3])
    add(6,'Applications must be received by the deadline.','s2',1,d=[3])
    add(3,'Requests deadline date is June 3, 2031.','s3',5,
        'Cutoff clock unknown; timezone unknown; timeliness basis dispatch.',q=1,
        r='Clock, timezone and directive force are unspecified; dispatch basis is explicit.')
    add(6,'Dispatch controls request timeliness.','s3',d=[7])
    add(0,'Affected rule identity is Rule Q-8.','s4')
    add(0,'Historical filing identity is F-17.','s4')
    add(1,'The amendment affects Rule Q-8; F-17 is the previous filing context.','s4',d=[9,10])
    add(3,'Historical filing F-17 was filed January 6, 2029.','s4',d=[10])
    add(3,'Historical filing F-17 became effective February 2, 2029.','s4',d=[10])
    add(0,'The office city is Alder City.','s5')
    add(0,'The office province is North Province.','s5')
    add(6,'Readers should consult the archive for background.','s6',2)
    add(8,'The function of the unlabeled item is unresolved.','s7',5,q=3,r='Source does not identify this item’s function.')
    add(8,'The commission was founded in 1964.','s8')
    add(3,'In-person arrival deadline date is July 4, 2031.','s9',5,
        'Cutoff clock 09:00; timezone UTC; receipt-versus-dispatch not applicable: in-person arrival.',q=1,
        r='Bare arrival directive force is ambiguous; clock and timezone are stated, timeliness function is arrival.')
    add(3,'Requests deadline date is August 2, 2031.','s10',5,
        'Cutoff clock stated but ambiguous: 12:00 or 13:00; timezone UTC; receipt-versus-dispatch not stated (unknown).',q=1,
        r='Source leaves two cutoff clocks unresolved; timeliness basis is absent, directive force unknown.')
    add(3,'In-person arrival cutoff clock is 09:00.','s9',d=[19])
    add(3,'In-person arrival cutoff timezone is UTC.','s9',d=[19])
    add(3,'Requests cutoff clock is stated as 12:00 or 13:00, unresolved.','s10',d=[20],q=1,r='Source leaves the two stated cutoff clocks unresolved.')
    add(3,'Requests cutoff timezone is UTC.','s10',d=[20])
    table=span_table(SOURCE)
    return dict(v=VERSION,h=source_hash(SOURCE),t=digest(table),u=units,z='END')

def semantic_negative_controls():
    # All are structurally admissible. Independent review, not validate(), rejects them.
    base=fixture(); out={}
    v=copy.deepcopy(base);v['u'][0].update(c='',q=0,r='',m=2)
    out['silently_missing_deadline_dimensions']=v
    v=copy.deepcopy(base);v['u'][10]['s']='The amendment affects filing F-17.'
    out['historical_filing_replaces_affected_rule']=v
    v=copy.deepcopy(base);v['u'][13]['s']='The office is in Alder City, North Province.';del v['u'][14]
    out['independently_lossy_facts_bundled']=v
    v=copy.deepcopy(base);v['u'][1].update(m=1,q=0,r='')
    out['unsupported_force_certainty']=v
    v=copy.deepcopy(base);v['u']=[u for u in v['u'] if u['i']!=18]
    out['background_dropped_but_all_spans_still_cited']=v
    # Keep s8 covered while omitting its assertion: broad evidence coverage is insufficient.
    out['background_dropped_but_all_spans_still_cited']['u'][-1]['e'].append('s8')
    return out
