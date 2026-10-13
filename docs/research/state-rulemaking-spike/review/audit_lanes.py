#!/usr/bin/env python3
"""Read-only lane audit: replay and mutate only reviewer-owned copies."""
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
SOURCE=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parent
VALIDATOR=Path(sys.argv[2]) if len(sys.argv)>2 else Path('/Users/home/.codex/worktrees/e8f4/yokel/docs/research/state-rulemaking-spike/validate.py')
spec=importlib.util.spec_from_file_location('validator',VALIDATOR)
validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator)
report={'source_root':str(SOURCE.resolve()),'validator_sha256':hashlib.sha256(VALIDATOR.read_bytes()).hexdigest(),'lanes':{},'checks':[],'mutations':[]}
def check(name,ok,details=None):
    report['checks'].append({'name':name,'passed':bool(ok),'details':details})
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def obs(lane):return json.loads((SOURCE/lane/'observations.json').read_text())
def source_copy(lane,destination):
    shutil.copytree(SOURCE/lane,destination,ignore=shutil.ignore_patterns('__pycache__'))
def run(lane):
    p=subprocess.run([sys.executable,'-B',str(lane/'normalize.py')],capture_output=True,text=True,cwd=ROOT)
    return {'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
for name in ['ct','wa','pdf']:
    source=SOURCE/name
    validation=validator.validate_lane(source)
    with tempfile.TemporaryDirectory(prefix=name+'-replay-',dir=ROOT) as tmp:
        lane=Path(tmp)/name;source_copy(name,lane)
        before={p.relative_to(lane).as_posix():digest(p) for p in lane.rglob('*') if p.is_file()}
        first=run(lane)
        middle={p.relative_to(lane).as_posix():digest(p) for p in lane.rglob('*') if p.is_file()}
        second=run(lane)
        after={p.relative_to(lane).as_posix():digest(p) for p in lane.rglob('*') if p.is_file()}
        report['lanes'][name]={'normalizer_sha256':digest(source/'normalize.py'),'manifest_sha256':digest(source/'manifest.json'),
            'validation':validation,'first':first,'second':second,'first_changed_files':[k for k in before.keys()|middle.keys() if before.get(k)!=middle.get(k)],
            'second_changed_files':[k for k in middle.keys()|after.keys() if middle.get(k)!=after.get(k)]}
        check(name+'_replays_identically',first['returncode']==second['returncode']==0 and before==middle==after)

allobs=[o for name in ['ct','wa','pdf'] for o in obs(name)]
check('cross_lane_observation_ids_unique',len({o['observation_id'] for o in allobs})==len(allobs))
allarts=[a for name in ['ct','wa','pdf'] for a in json.loads((SOURCE/name/'manifest.json').read_text())]
check('cross_lane_artifact_ids_unique',len({a['artifact_id'] for a in allarts})==len(allarts))

# JSON pointer validation and independent timestamp conversion for every native CT assertion.
native_count=0
for o in obs('ct'):
    ev=o['evidence'][0]
    if ev['artifact_id'] not in ('ct-open.json','ct-history059.json'):continue
    filename=ev['artifact_id'][3:]
    document=json.loads((SOURCE/'ct/captures'/filename).read_text())
    node=document
    for part in ev['locator'].split('/')[1:]:node=node[int(part)] if isinstance(node,list) else node[part]
    value=o['value']
    if isinstance(value,dict) and value['kind']=='instant':
        epoch=int(re.fullmatch(r'/Date\((-?\d+)\)/',node)[1])
        expected=dt.datetime(1970,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(milliseconds=epoch)
        actual=dt.datetime.fromisoformat(value['utc_instant'].replace('Z','+00:00'))
        check(o['observation_id']+'_epoch_and_locator',expected==actual)
    else:check(o['observation_id']+'_value_and_locator',node==value)
    native_count+=1
check('ct_all_native_observations_pointer_checked',native_count==16,native_count)
history=[o for o in obs('ct') if o['source_record_id']=='PR2024-059' and o['predicate']=='comment_close' and o['value']['kind']=='instant']
check('ct_historical_cycles_distinct',len(history)==2 and len({o['subject']['id'] for o in history})==2)
openids={r['TrackingNumber'] for r in json.loads((SOURCE/'ct/captures/open.json').read_text())}
check('ct_missing_record_not_withdrawn','PR2024-059' not in openids and not any(o['predicate']=='withdraws' for o in obs('ct')))
check('ct_no_generic_hearing_assertions',not any(o['predicate'] in ['hearing_time','hearing_status'] for o in obs('ct')))
ctlocal=[o for o in obs('ct') if o['predicate']=='comment_close' and o['value']['kind']=='local_datetime']
check('ct_display_zone_unresolved',len(ctlocal)==1 and ctlocal[0]['value']=={'kind':'local_datetime','date':'2026-10-11','time':'23:45','timezone_text':None,'iana_zone':None,'utc_instant':None})

wa=obs('wa')
w=[o for o in wa if o['predicate']=='withdraws']
check('wa_partial_withdrawal',len(w)==1 and w[0]['value']=={'target_source_record_id':'26-15-113','scope':'CR-102 portion of the rule making'})
check('wa_withdrawal_no_future_dates',not any(o['predicate'] in ['comment_close','hearing_time','effective_date'] and o['source_record_id']=='26-18-058' for o in wa))
check('wa_proposal_comment_date_only',[o['value'] for o in wa if o['predicate']=='comment_close']==[{'kind':'date','date':'2026-10-09'}])
check('wa_proposal_hearing_separate',[o['value'] for o in wa if o['predicate']=='hearing_time']==[{'kind':'local_datetime','date':'2026-10-15','time':'09:00','timezone_text':None,'iana_zone':None,'utc_instant':None}])
check('wa_no_current_effective_date',not any(o['predicate']=='effective_date' for o in wa))

pdf=obs('pdf');pd={o['predicate']:o for o in pdf}
check('pdf_twenty_vs_twentyfive',pd['hearing_request_duration']['value']['duration']==20 and pd['comment_duration']['value']['duration']==25 and pd['hearing_request_duration']['subject']['id']!=pd['comment_duration']['subject']['id'])
check('pdf_no_computed_deadline',not any(o['predicate'] in ['comment_close','effective_date'] for o in pdf) and all(pd[p]['value']['computed_close'] is None for p in ['hearing_request_duration','comment_duration']))
check('pdf_visual_methods_explicit',all(pd[p]['method']['kind']=='manual_visual' for p in ['event_type','hearing_status','filing_date']))
check('pdf_eligibility_in_evidence',any('submitted by a political subdivision, an agency or ten (10) or more persons.' in e['quote'] for e in pd['hearing_request_duration']['evidence']))
check('pdf_eligibility_scope_warning',any('not yet a separately typed field' in w for w in pd['hearing_request_duration']['warnings']))
review=json.loads((SOURCE/'pdf/derived/visual-review.json').read_text())
check('pdf_review_hash_links',review['image_sha256']==digest(SOURCE/'pdf/derived/page-1.png') and review['source_pdf_sha256']==digest(SOURCE/'pdf/raw/inherited.pdf'))
check('pdf_fresh_original_equals_inherited',(SOURCE/'pdf/raw/inherited.pdf').read_bytes()==(SOURCE/'pdf/raw/fresh.pdf').read_bytes())
for name in ['ct','wa','pdf']:
    pairs={'ct':[('captures/fc059.json','captures/fc059.md'),('captures/fc059retry.json','captures/fc059retry.md'),('captures/fc014.json','captures/fc014.md')],
           'wa':[('firecrawl-withdrawal.json','firecrawl-withdrawal.md'),('firecrawl-proposal.json','firecrawl-proposal.md')],
           'pdf':[('raw/firecrawl-parse.json','derived/firecrawl.md')]}[name]
    for response,derived in pairs:
        data=json.loads((SOURCE/name/response).read_text())
        payload=data.get('structuredContent',data.get('response'))
        if payload is None:
            payload=json.loads(next(c['text'] for c in data['content'] if c['type']=='text'))
        retained=(SOURCE/name/derived).read_text()
        check(name+'_'+derived+'_response_lineage',retained in (payload['markdown'],payload['markdown']+'\n'),
              {'transformation':'trailing newline appended' if retained==payload['markdown']+'\n' else 'exact'})

def mutate(name,label,change):
    with tempfile.TemporaryDirectory(prefix=name+'-negative-',dir=ROOT) as tmp:
        lane=Path(tmp)/name;source_copy(name,lane)
        change(lane)
        outcome=run(lane)
        output=json.loads((lane/'observations.json').read_text()) if (lane/'observations.json').exists() else []
        report['mutations'].append({'lane':name,'label':label,'run':outcome,'observation_count':len(output),'predicates':[o['predicate'] for o in output],
                                   'shared_validation_passed':validator.validate_lane(lane)['passed'] if outcome['returncode']==0 else None})
def change_text(lane,path,old,new,rehash=False):
    p=lane/path;body=p.read_text();assert old in body;p.write_text(body.replace(old,new))
    if rehash:
        m=json.loads((lane/'manifest.json').read_text())
        for a in m:
            if a['path']==path:a['sha256']=digest(p)
        (lane/'manifest.json').write_text(json.dumps(m))
mutate('wa','missing_comment_label',lambda p:change_text(p,'proposal.html','Submit Written Comments to:','Unexpected New Label:'))
mutate('pdf','missing_public_comment_clause_with_valid_hash',lambda p:change_text(p,'derived/firecrawl.md','At any time within the twenty-five (25) day public comment period,','Changed template for the public comment period,',True))
mutate('pdf','missing_hearing_clause_with_valid_hash',lambda p:change_text(p,'derived/firecrawl.md','within twenty (20) days after the filing of this notice of proposed rule adoption','within an unspecified period',True))
mutate('pdf','missing_eligibility_with_valid_hash',lambda p:change_text(p,'derived/firecrawl.md','submitted by a political subdivision, an agency or ten (10) or more persons.','submitted by an unspecified eligible requester.',True))

(ROOT/'lane-audit-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'checks':len(report['checks']),'failed_checks':[c for c in report['checks'] if not c['passed']],
 'lane_counts':{n:r['validation']['observation_count'] for n,r in report['lanes'].items()},
 'mutations':[{'label':m['label'],'returncode':m['run']['returncode'],'count':m['observation_count'],'validator_pass':m['shared_validation_passed']} for m in report['mutations']]},indent=2))
