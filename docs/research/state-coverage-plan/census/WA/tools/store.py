import json, os, glob
def results(pattern='WA/capture-results/*.jsonl'):
    out={}
    for f in sorted(glob.glob(pattern)):
        for l in open(f):
            r=json.loads(l); out[r['manifest_entry_id']]=r
    return out
def path(r):
    p=r['retrieval']['storage_path']
    return os.path.expanduser(p) if p else None
def text(r):
    return open(path(r),'rb').read().decode('utf-8','replace')
