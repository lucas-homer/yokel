from pathlib import Path
from datetime import datetime,timezone
import subprocess,json
p=Path(__file__).resolve().parent/'discovery'
items=[('ms-bulletin','https://www.sos.ms.gov/adminsearch/'),('wa-cro','https://leg.wa.gov/state-laws-and-rules/washington-state-register/rule-making-activity/cro-activity/'),('ca-wildlife','https://wildlife.ca.gov/Notices/Regulations'),('ca-mussels','https://wildlife.ca.gov/Notices/Regulations/Invasive-Mussels'),('ca-dmv','https://www.dmv.ca.gov/portal/about-the-california-department-of-motor-vehicles/california-dmv-rulemaking-actions/'),('ny-register','https://dos.ny.gov/state-register')]
log=[]
for key,url in items:
 start=datetime.now(timezone.utc).isoformat()
 r=subprocess.run(['curl','-L','-sS','--max-time','40','-D',str(p/(key+'.headers')),'-o',str(p/(key+'.html')),'-w','%{http_code} %{time_total} %{url_effective}',url],capture_output=True,text=True)
 log.append({'artifact':key+'.html','url':url,'started_at':start,'retrieved_at':datetime.now(timezone.utc).isoformat(),'exit_code':r.returncode,'receipt':r.stdout,'error':r.stderr});print(key,r.stdout,r.stderr)
(p/'retrievals.json').write_text(json.dumps(log,indent=2)+'\n')
