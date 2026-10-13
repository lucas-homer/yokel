#!/usr/bin/env python3
"""Retain synthetic runtime controls only. No network/credentials/fresh sources."""
import contextlib
import io
import json
from pathlib import Path
import offline_checks as t
import run_pipeline as r
from operations import sha
BASE=Path(__file__).resolve().parent
FIXTURES={
    'positive_incidental_condition':t.POSITIVE,
    'paired_true_condition':t.POSITIVE.replace('October 31, 2026.','October 31, 2026 if a hearing is requested.',1),
    'clock_qualified_date':'Written comments must be received by 5:00 p.m. Pacific Time on October 31, 2026.',
    'relative_window_explicit_email':'Written comments are due within 30 days after publication.\n\nSubmit written comments to comments@example.gov.',
    'hearing_role_alternative':'Written comments may be presented at a hearing until November 2, 2026.\n\nWritten comments close October 31, 2026.',
    'conflicting_comment_windows':'Written comments close October 31, 2026. Written comments close November 2, 2026.'}


def main():
    rows=[]
    for name,text in FIXTURES.items():
        root=BASE/'development-controls'/name;root.mkdir(parents=True,exist_ok=False)
        def fake(payload):
            value=payload['state']['candidate']['value']
            role='mismatched' if value in ('access@example.gov','2026-11-02') else 'matched'
            return 200,t.response(payload,{'role':role})
        with contextlib.redirect_stdout(io.StringIO()):result,final,calls,_=t.execute(root,text,fake=fake)
        supported={o['field']:o['candidate_value'] for o in final['observations'] if o['shadow_status']=='text_supported'}
        if name=='positive_incidental_condition':assert supported=={'comment_deadline':'2026-10-31','submission_email':'comments@example.gov'}
        if name=='paired_true_condition':assert 'comment_deadline' not in supported
        if name=='clock_qualified_date':assert supported.get('comment_deadline')=='2026-10-31'
        if name=='relative_window_explicit_email':assert supported=={'submission_email':'comments@example.gov'}
        if name=='hearing_role_alternative':assert supported=={'comment_deadline':'2026-10-31'} and len(calls)==2
        if name=='conflicting_comment_windows':assert not calls and not supported
        rows.append({'fixture':name,'source_sha256':sha(text.encode()),'source_characters':len(text),'fake_operations':len(calls),
                     'supported_fields':supported,'terminal_reviews':sum(o['shadow_status']=='review' for o in final['observations']),
                     'full_notice_in_every_request':all(p['state']['source_text']==text for p in calls),
                     'action_ready':final['action_ready'],'totals':result['totals']})
    output={'status':'all_synthetic_control_assertions_passed','fixtures':rows,'pipeline_sha256':sha(t.PIPELINE.read_bytes()),
            'runtime_sha256':sha(Path(r.__file__).read_bytes()),'real_provider_calls':0,'fresh_sources_read':False,'labels_read':False,
            'interpretation':'Implementation reachability and gates only; favorable synthetic judgments are not measured model accuracy.'}
    (BASE/'development-controls.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))

if __name__=='__main__':main()
