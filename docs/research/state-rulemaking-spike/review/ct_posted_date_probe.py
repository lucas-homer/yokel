#!/usr/bin/env python3
"""Replay an inspected CT normalizer only in isolated reviewer-owned copies."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent
SOURCE=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parent/'ct'
results=[]
for mutation in (False,True):
    with tempfile.TemporaryDirectory(prefix='ct-probe-',dir=ROOT) as tmp:
        target=Path(tmp)
        (target/'captures').mkdir()
        shutil.copyfile(SOURCE/'normalize.py',target/'normalize.py')
        for name in ('open.json','history059.json','fc059retry.md','fc014.md'):
            shutil.copyfile(SOURCE/'captures'/name,target/'captures'/name)
        if mutation:
            p=target/'captures'/'fc059retry.md'
            text=p.read_text()
            old='| 11 | 10/02/2026 | Comment Period Closed |'
            assert text.count(old)==1
            p.write_text(text.replace(old,'| 11 | 10/04/2026 | Comment Period Closed |'))
        run=subprocess.run([sys.executable,str(target/'normalize.py')],capture_output=True,text=True)
        observations=json.loads((target/'observations.json').read_text()) if run.returncode==0 else []
        selected=[o for o in observations if o['source_record_id']=='PR2024-059' and o['predicate']=='comment_close']
        results.append({'mutated_posted_date_only':mutation,'returncode':run.returncode,'stdout':run.stdout,'stderr':run.stderr,'comment_close_observations':selected})
report={'normalizer_sha256':hashlib.sha256((SOURCE/'normalize.py').read_bytes()).hexdigest(),
        'purpose':'Synthetic mutation of Posted Date only; native deadline fields untouched.',
        'results':results}
(ROOT/'ct-posted-date-results.json').write_text(json.dumps(report,indent=2)+'\n')
for result in results:
    print(json.dumps({'mutated_posted_date_only':result['mutated_posted_date_only'],'returncode':result['returncode'],'close_values':[o['value'] for o in result['comment_close_observations']]}))
