"""Ephemeral upload metadata over stdin; never log/store signed URLs or tokens."""
import argparse,hashlib,json,sys,time,urllib.request,urllib.error,uuid
from pathlib import Path
from transient_stdin import read_json_line
p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--sha256',required=True);args=p.parse_args()
raw=Path(args.input).read_bytes()
if hashlib.sha256(raw).hexdigest()!=args.sha256: raise SystemExit('Input hash mismatch before upload')
# Caller sends one JSON line over the live process pipe. Nothing is written to disk.
u=read_json_line()
url=u['uploadUrl'];method=u['method'].upper();headers=dict(u.get('headers') or {})
if not url.startswith('https://'):raise SystemExit('Upload requires HTTPS')
if u.get('maxSizeBytes') is not None and len(raw)>u['maxSizeBytes']:raise SystemExit('Declared upload size limit exceeded')
if method=='PUT':
 body=raw
elif method=='POST':
 # Generic presigned multipart instructions: retain exact field values in memory only.
 boundary='----docketclock-'+uuid.uuid4().hex
 chunks=[]
 for key,value in (u.get('fields') or {}).items():
  if '\r' in key or '\n' in key or '"' in key:raise SystemExit('Unsupported multipart field name')
  chunks.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n').encode())
 chunks.append((f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="input.pdf"\r\nContent-Type: application/pdf\r\n\r\n').encode())
 chunks.append(raw);chunks.append((f'\r\n--{boundary}--\r\n').encode());body=b''.join(chunks)
 headers['Content-Type']='multipart/form-data; boundary='+boundary
else:raise SystemExit('Unsupported upload method; stop without guessing')
start=time.monotonic()
try:
 req=urllib.request.Request(url,body,headers,method=method)
 with urllib.request.urlopen(req,timeout=90) as response:
  # No body/header output: object stores may return signed metadata.
  result={'success':200<=response.status<300,'http_status':response.status,'elapsed_seconds':time.monotonic()-start,'uploaded_pdf_bytes':len(raw),'input_sha256':args.sha256,'secrets_persisted':False}
except urllib.error.HTTPError as e:
 result={'success':False,'http_status':e.code,'elapsed_seconds':time.monotonic()-start,'error_type':'HTTPError','details_redacted':True,'secrets_persisted':False}
except Exception as e:
 # str(exception) can contain the signed URL; retain only exception class.
 result={'success':False,'elapsed_seconds':time.monotonic()-start,'error_type':type(e).__name__,'details_redacted':True,'secrets_persisted':False}
print(json.dumps(result),flush=True)
sys.exit(0 if result['success'] else 1)
