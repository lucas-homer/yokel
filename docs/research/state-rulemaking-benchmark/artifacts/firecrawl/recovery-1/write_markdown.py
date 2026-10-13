"""Capture public parser markdown byte-for-byte, without adding a trailing newline."""
import sys,json,hashlib
from pathlib import Path
from transient_stdin import read_json_line
path=Path(sys.argv[1]).resolve();root=Path(__file__).resolve().parent
assert root in path.parents
assert not path.exists(),'Existing exact markdown capture must not be overwritten'
value=read_json_line()['markdown'];assert isinstance(value,str)
raw=value.encode('utf-8');path.write_bytes(raw)
print(json.dumps({'sha256':hashlib.sha256(raw).hexdigest(),'byte_length':len(raw),'terminal_newline':value.endswith('\n'),'exact_utf8':True}))
