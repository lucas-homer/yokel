from pathlib import Path
import subprocess,json,hashlib
from datetime import datetime,timezone
from pypdf import PdfReader
R=Path(__file__).parent
sources=[
('H01','WI','https://dnr.wisconsin.gov/sites/default/files/topic/Rules/FWP2224HearingNotice2.pdf','https://dnr.wisconsin.gov/sites/default/files/topic/Rules/FWP2224HearingNotice2.pdf'),
('H02','ME','https://www.maine.gov/dmr/sites/maine.gov.dmr/files/regulations-2026-08/MAPA3_Ch34_Whiting%20Gear%20Specs_08062026%20FINAL_Aurora%20Burgess.pdf','https://www11.maine.gov/dmr/rules-enforcement/regulations-rules/proposed-rulemaking'),
('H03','TN','https://publications.tnsosfiles.com/rules_filings/09-17-26.pdf','https://www.tn.gov/workforce/events/2026/11/10/dfwp-public-rulemaking-hearing.html'),
('H04','KS','https://sos.ks.gov/publications/Register/Volume-45/PDF/Vol-45-No-20-May-14-2026.pdf','https://sos.ks.gov/publications/Register/Volume-45/PDF/Vol-45-No-20-May-14-2026.pdf'),
('H05','OR','https://www.oregon.gov/oblpct/Documents/PermOAR_Notice_4-9-26.pdf','https://www.oregon.gov/oblpct/pages/rulemaking.aspx'),
('H06','MN','https://mn.gov/admin/assets/SR50_44_tcm36-745071.pdf','https://mn.gov/admin/assets/SR50_44_tcm36-745071.pdf'),
('H07','UT','https://rules.utah.gov/wp-content/uploads/d20260801.pdf','https://rules.utah.gov/wp-content/uploads/d20260801.pdf'),
('H08','AK','https://www.adfg.alaska.gov/static/regulations/regprocess/gameboard/pdfs/2026-2027/notice-6.12.2026.pdf','https://www.newsreleasearchive.adfg.alaska.gov/index.cfm?adfg=gameboard.main')]
records=[]
for k,state,url,discovery in sources:
 d=R/k;d.mkdir(exist_ok=True);target=d/'original.pdf'
 c=subprocess.run(['curl','-L','--fail','--max-time','45','-sS',url,'-o',str(target)],capture_output=True,text=True)
 rec=dict(fixture_id=k,state=state,source_url=url,discovery_url=discovery,retrieved_at=datetime.now(timezone.utc).isoformat(),retrieval_exit=c.returncode,retrieval_error=c.stderr)
 if c.returncode==0:
  try:
   pdf=PdfReader(target);rec.update(original_page_count=len(pdf.pages),original_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),original_bytes=target.stat().st_size)
   (d/'original-native.txt').write_text('\n'.join(f'\n=== ORIGINAL PHYSICAL PAGE {i+1} ===\n'+page.extract_text() for i,page in enumerate(pdf.pages)))
  except Exception as e:rec['validation_error']=str(e)
 records.append(rec);print(json.dumps(rec))
(R/'retrieval-inventory.json').write_text(json.dumps(records,indent=2)+'\n')
