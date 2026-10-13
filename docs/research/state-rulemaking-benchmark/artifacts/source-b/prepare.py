from pathlib import Path
from pypdf import PdfReader,PdfWriter
from datetime import datetime,timezone
import shutil,json,hashlib,subprocess
P=Path(__file__).resolve().parent;D=P/'discovery'
ma='https://archives.lib.state.ma.us/bitstreams/c514279d-c8b6-4e29-a97e-755be559cbeb/download'
nc='https://www.ncsbe.gov/about-elections/legal-resources/rulemaking'
co='https://www.sos.state.co.us/CCR/RegisterHome.do'
units=[
('B01','MA','scanned/filled forms','ma-register.pdf',[61,62],ma,'https://archives.lib.state.ma.us/','Hospital Assessment emergency filing','First bounded filled filing form in emergency section; historical filled form, not image-only scan.'),
('B02','MA','scanned/filled forms','ma-register.pdf',[69,70,71],ma,'https://archives.lib.state.ma.us/','Social Workers licensure emergency filing','Next agency filing form; includes contiguous emergency rationale; second and last from issue 1542.'),
('B03','NC','clean standalone PDFs','nc-exempt.pdf',[1,2],'https://s3.amazonaws.com/dl.ncsbe.gov/Legal/Rules/2026%20Proposed%20Rules/Exempt%20Sales%20Plan%20Rule/CF%20Exempt%20Sales%20Rule%20Notice%20of%20Text.pdf',nc,'Exempt sales plan notice','First currently open Notice of Text on agency listing; unchanged short original.'),
('B04','NC','clean standalone PDFs','nc-waiver.pdf',[1,2],'https://s3.amazonaws.com/dl.ncsbe.gov/Legal/Rules/2026%20Proposed%20Rules/Waiver%20Rule%20Amendment/Notice%20of%20Text%20Waiver%20Rule%20Amendment.pdf',nc,'Waiver rule amendment notice','After campaigns notice exceeded 4-page full package, selected complete 2-page Form 300 notice from waiver package; proposed rule attachment excluded.'),
('B05','TX','dense register layouts','tx0522.pdf',[30,31,32],'https://www.sos.texas.gov/texreg/pdf/backview/0522/0522is.pdf','https://www.sos.texas.gov/texreg/pdf/backview/0522/index.shtml','Educator certification passing standards proposal','First bounded education proposal in inspected proposed section; preserve heading and full notice across columns/pages.'),
('B06','TX','dense register layouts','tx0522.pdf',[32,33],'https://www.sos.texas.gov/texreg/pdf/backview/0522/0522is.pdf','https://www.sos.texas.gov/texreg/pdf/backview/0522/index.shtml','Broker Responsibility Advisory Committee proposal','Next bounded notice after education proposal; relative deadline; second and last from issue.'),
('B07','TX','dense register layouts','tx0605.pdf',[19,20],'https://www.sos.state.tx.us/texreg/pdf/backview/0605/0605is.pdf','https://www.sos.texas.gov/texreg/index.shtml','Optometry License Designation proposal','First complete bounded amendment in inspected optometry sequence, across two pages; distinct second issue.'),
('B08','CO','lifecycle changes','co0910-response',[1207],'https://www.sos.state.co.us/CCR/RegisterPdfContents.do?publicationDay=09/10/2026',co,'Education terminated rulemaking 2026-00317','Newest PDF-available issue termination; administrative-error refiling with unchanged hearing date.'),
('B09','CO','lifecycle changes','co0825-response',[1018],'https://www.sos.state.co.us/CCR/RegisterPdfContents.do?publicationDay=08/25/2026',co,'Treasury terminated rulemaking 2026-00275','Next earlier issue termination; hearing to be rescheduled with no replacement date.'),
('B10','CO','lifecycle changes','co0910-response',[233],'https://www.sos.state.co.us/CCR/RegisterPdfContents.do?publicationDay=09/10/2026',co,'Retail marijuana tax permanent adoption notice','First permanent-adoption notice header in Sept 10 issue; bounded one-page lifecycle notice, adopted rule text excluded; second and last from issue.')]
for uid,state,bucket,name,pages,url,listing,title,reason in units:
 d=P/uid;d.mkdir(exist_ok=True);shutil.copyfile(D/name,d/'original.pdf');r=PdfReader(d/'original.pdf')
 if pages==list(range(1,len(r.pages)+1)):shutil.copyfile(d/'original.pdf',d/'input.pdf')
 else:
  w=PdfWriter()
  for i in pages:w.add_page(r.pages[i-1])
  with (d/'input.pdf').open('wb') as f:w.write(f)
 rr=PdfReader(d/'input.pdf');text='\n\f\n'.join(x.extract_text() or '' for x in rr.pages);(d/'native.txt').write_text(text)
 subprocess.run(['pdftoppm','-scale-to','1400','-png',str(d/'input.pdf'),str(d/'page')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 meta=dict(fixture_id=uid,state=state,bucket=bucket,layout_features=['filled form' if state=='MA' else 'two-column dense' if state=='TX' else 'single-column notice'],event_type='emergency_adoption' if state=='MA' else 'proposal' if state in ['NC','TX'] else 'termination' if uid!='B10' else 'permanent_adoption',source_url=url,discovery_url=listing,retrieved_at=datetime.fromtimestamp((D/name).stat().st_mtime,timezone.utc).isoformat(),source_title=title,selection_reason=reason,original_sha256=hashlib.sha256((d/'original.pdf').read_bytes()).hexdigest(),input_sha256=hashlib.sha256((d/'input.pdf').read_bytes()).hexdigest(),original_bytes=(d/'original.pdf').stat().st_size,input_bytes=(d/'input.pdf').stat().st_size,original_page_count=len(r.pages),input_page_count=len(rr.pages),original_physical_pages=pages,package_limitations='Unchanged publisher PDF.' if uid=='B03' else 'Derived contiguous complete notice/form excerpt. Full original retained; attachments/rule text outside selected notice are excluded; whole physical pages may contain neighboring notice material.',reference_fields=[],annotation_author='Codex source collector agent; not human gold')
 (d/'fixture.json').write_text(json.dumps(meta,indent=2)+'\n')
 print(uid,len(rr.pages),pages)
