"""Primary-only freeze helpers; no provider calls or source selection."""
import datetime,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def freeze(paths,destination,description):
 if destination.exists():raise ValueError('Refusing to replace prior freeze')
 files=[{'path':str(p.relative_to(ROOT)),'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(set(paths))]
 result={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'description':description,'files':files}
 destination.write_text(json.dumps(result,indent=2)+'\n');return result
def verify(path):
 data=json.loads(path.read_text());changed=[x['path'] for x in data['files'] if digest(ROOT/x['path'])!=x['sha256']]
 return {'files':len(data['files']),'unchanged':not changed,'changed':changed}
