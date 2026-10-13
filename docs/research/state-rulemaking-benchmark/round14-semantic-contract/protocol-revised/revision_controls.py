"""Data-only overflow and illustration leakage controls; never prompt additions."""
import copy
from compact import VERSION, source_hash, span_table, digest
from fictional_controls import fixture

LONG_QUALIFICATION = ('Applies only to applicants who submitted both the original application and its signed annex before review, '
                      'except applicants granted a written extension, and subject to separate confirmation of the review date by the office.')
LONG_SOURCE = 'Applications must arrive by March 6, 2034. '+LONG_QUALIFICATION+'\n'
LEAKAGE_SOURCE = 'The archive opened in 1978.\n'

def envelope(source,unit):
    table=span_table(source)
    return dict(v=VERSION,h=source_hash(source),t=digest(table),u=[unit],z='END')

def overflow_controls():
    result={}
    for key,text in [('c',LONG_QUALIFICATION),('s','The application deadline applies with these qualifications: '+LONG_QUALIFICATION+' Additional written confirmation is required.'),('r','The actor’s precise eligibility remains uncertain because '+LONG_QUALIFICATION)]:
        u=copy.deepcopy(fixture()['u'][0]);u['i']=1;u['e']=['s1'];u['d']=[]
        u.update(s='Application deadline date is March 6, 2034.',c='',r='Clock, timezone and receipt-versus-dispatch are not stated.',q=1)
        u[key]=text
        result[key]=envelope(LONG_SOURCE,u)
    return result

def leakage_control():
    u=copy.deepcopy(fixture()['u'][0]);u['i']=1;u['e']=['s1'];u['d']=[]
    return envelope(LEAKAGE_SOURCE,u)
