"""Read-only guard: verify parent freeze checksum and identical input bytes; no provider calls."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parent
freeze=Path(sys.argv[1]);expected=sys.argv[2]
assert hashlib.sha256(freeze.read_bytes()).hexdigest()==expected,'Freeze checksum mismatch'
manifest=json.loads(freeze.read_text());corpus=manifest.get('corpus',manifest)
if 'units' in manifest:
 for name,record in manifest['files'].items():
  target=(freeze.parent/name).resolve();assert freeze.parent.resolve() in target.parents
  assert hashlib.sha256(target.read_bytes()).hexdigest()==record['sha256'],'Frozen source/reference file changed: '+name
 check=json.loads((freeze.parent/'corpus-check.json').read_text());assert check['passed'] is True
 assert manifest['arm_settings']['firecrawl_local_parse']=={'formats':['markdown'],'parsers':['pdf'],'onlyMainContent':False,'pdfOptions':{'maxPages':'each input_page_count'}}
 fixtures=manifest['units']
else:
 assert corpus.get('passed') is True,'Parent corpus verification must pass'
 fixtures=corpus['fixtures']
order=[f'{lane}{i:02}' for lane in 'AB' for i in range(1,11)]
assert [f['fixture_id'] for f in fixtures]==order,'Exact frozen fixture order required'
allowed=(ROOT.parent/'source-a',ROOT.parent/'source-b');total=0;hashes=[]
for f in fixtures:
 path=Path(f['input_path']).resolve();assert any(root.resolve() in path.parents for root in allowed),'Input outside assigned immutable corpus'
 raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==f['input_sha256'],'Input hash changed'
 assert len(raw)==f['input_bytes'],'Input byte count changed'
 assert isinstance(f['input_page_count'],int) and 1<=f['input_page_count']<=4
 for key,name in [('original_sha256','original.pdf'),('fixture_metadata_sha256','fixture.json'),('native_sha256','native.txt')]:
  if key in f:assert hashlib.sha256((path.parent/name).read_bytes()).hexdigest()==f[key],name+' changed since freeze'
 # Do not overwrite results or silently resume a potentially billed job.
 assert not (ROOT/f['fixture_id']).exists(),'Existing result directory; inspect prior operation before any provider call'
 total+=f['input_page_count'];hashes.append(f['input_sha256'])
assert total<=80 and len(set(hashes))==20
print(json.dumps({'freeze_sha256':expected,'fixtures':fixtures,'total_pages':total}))
