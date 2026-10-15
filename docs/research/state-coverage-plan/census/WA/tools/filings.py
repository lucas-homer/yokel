import sys,collections;sys.path.insert(0,'/tmp/wa-acq/tools');import store,parse_issue
from plan import *
def table():
    R=store.results(); F={}
    for iss in BACKWARD+INTERVAL+FOLLOW:
        rows,_=parse_issue.parse(store.text(R['wa-issue-'+iss]))
        for r in rows:
            w=r['wsr'].split()[0]
            f=F.setdefault(w,dict(wsr=w,num_issue='-'.join(w.split('-')[:2]),types=set(),agencies=[],listed_in=[],holdover_in=[],htm=r['htm'].replace('http://','https://'),pdf=r['pdf'].replace('http://','https://')))
            f['types'].add(r['type'])
            if r['agency'] not in f['agencies']: f['agencies'].append(r['agency'])
            if iss not in f['listed_in']: f['listed_in'].append(iss)
            if 'holdover' in r['wsr'] and iss not in f['holdover_in']: f['holdover_in'].append(iss)
    return F
def group(f):
    ni=f['num_issue']; L=set(f['listed_in'])
    if ni in INTERVAL or L & set(INTERVAL): return 'interval'
    if ni in BACKWARD and f['types'] & set(BACK_TYPES): return 'backward'
    if ni in FOLLOW and f['types'] & set(FOLLOW_TYPES): return 'followup'
    return None
