from pathlib import Path
from datetime import datetime,timezone
import subprocess,json
ROOT=Path(__file__).resolve().parent
SOURCES=[
('A01','https://www.sos.ms.gov/adminsearch/ACProposed/00028528a.pdf'),
('A02','https://www.sos.ms.gov/adminsearch/ACProposed/00028576a.pdf'),
('A03','https://www.sos.ms.gov/adminsearch/ACProposed/00028572a.pdf'),
('A04','https://leg.wa.gov/media/0khlud2v/wsr-25-08-088.pdf'),
('A05','https://lawfilesext.leg.wa.gov/law/wsr/2026/16/26-16PROP.pdf'),
('ny-issue','https://dos.ny.gov/september-30-2026vol-xlviii-issue-39'),
('A06','https://nrm.dfg.ca.gov/FileHandler.ashx?DocumentID=247277&inline='),
('A07','https://www.dmv.ca.gov/portal/file/electronic-lien-and-title-program-notice-of-second-modified-regulatory-text-pdf/'),
('A08','https://nrm.dfg.ca.gov/FileHandler.ashx?DocumentID=241124')]
log=json.loads((ROOT/'acquisition.json').read_text()) if (ROOT/'acquisition.json').exists() else []
for fid,url in SOURCES:
 if (ROOT/fid/'original.pdf').exists(): continue
 folder=ROOT/fid;folder.mkdir(exist_ok=True)
 start=datetime.now(timezone.utc).isoformat()
 r=subprocess.run(['curl','-L','-sS','--max-time','60','-D',str(folder/'retrieval.headers'),'-o',str(folder/'original.pdf'),'-w','%{http_code} %{time_total} %{url_effective}',url],capture_output=True,text=True)
 end=datetime.now(timezone.utc).isoformat()
 log.append({'fixture_id':fid,'url':url,'started_at':start,'retrieved_at':end,'exit_code':r.returncode,'receipt':r.stdout,'error':r.stderr})
 print(fid,r.stdout,r.stderr)
(ROOT/'acquisition.json').write_text(json.dumps(log,indent=2)+'\n')
