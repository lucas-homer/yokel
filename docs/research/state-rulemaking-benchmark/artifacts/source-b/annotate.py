"""Agent source annotations written before vendor parsing; no parser outputs read."""
from pathlib import Path
import json,re
P=Path(__file__).resolve().parent
def fields(uid,rows):
 d=P/uid;m=json.loads((d/'fixture.json').read_text());texts=(d/'native.txt').read_text().split('\n\f\n');out=[]
 for fid,q,v,a,critical,page,region,quote,basis in rows:
  if quote is not None and basis=='source_text':
   if quote not in texts[page-1]:
    pattern=r'\s+'.join(re.escape(x) for x in quote.split())
    match=re.search(pattern,texts[page-1])
    assert match,(uid,fid,repr(quote))
    quote=match[0]
   assert quote in texts[page-1]
  out.append(dict(field_id=fid,question=q,expected_value=v,answerability=a,critical=critical,original_page=m['original_physical_pages'][page-1],input_page=page,region=region,source_quote=quote,basis=basis))
 m['reference_fields']=out;m['visual_inspection']='All input pages inspected as rendered images by collector agent; source-only references, pending independent review.'
 (d/'fixture.json').write_text(json.dumps(m,indent=2)+'\n')
def f(fid,q,v,page,quote,critical=True,region='Target notice labeled field',a='present',basis='source_text'):return(fid,q,v,a,critical,page,region,quote,basis)
def absent(fid,q,page,scope):return f(fid,q,None,page,None,True,scope,'not_stated','full_scope_absence')

fields('B01',[
 f('agency','Which agency filed the Hospital Assessment form?','Executive Office of Health and Human Services',1,'AGENCY: Executive Office of Health and Human Services',False),
 f('citation','What chapter is this filing for?','101 CMR 514.00',1,'CHAPTER NUMBER: 101 CMR 514.00'),
 f('event','Is this an emergency adoption?','emergency adoption',2,'This is an emergency \nregulation.  There are no \nreplacement pages.'),
 f('effective','What effective date is supplied, independently of publication?','2025-02-07',2,'EFFECTIVE DATE: 2/7/25'),
 f('publication','What register publication date is supplied?','2025-02-28',2,'MASSACHUSETTS REGISTER NUMBER: 1542 DATE: 2/28/25'),
 f('signature_date','What date accompanies the agency attestation?','2025-02-07',2,'SIGNATURE: SIGNATURE ON FILE DATE: Feb 07 2025',False),
 absent('comment_close','Does the filled form supply a comment closing date?',1,'Complete Hospital Assessment form input pages 1-2; public-review date line blank.'),
 absent('hearing','Does the filled form supply a scheduled hearing date?',1,'Complete Hospital Assessment form input pages 1-2; public-review date line blank.')])
fields('B02',[
 f('agency','Which agency filed the licensure form?','Board of Registration of Social Workers',1,'AGENCY: Board of Registration of Social Workers',False),
 f('citation','What chapter is this filing for?','258 CMR 9.00',1,'CHAPTER NUMBER: 258 CMR 9.00'),
 f('event','What lifecycle action does the promulgation field state?','emergency amendment',2,'Emergency promulgation will amend 258 CMR 9.00.'),
 f('effective','What effective date is stated?','2025-02-05',2,'EFFECTIVE DATE: 2/5/25'),
 f('publication','What register publication date is supplied?','2025-02-28',2,'MASSACHUSETTS REGISTER NUMBER: 1542 DATE: 2/28/25'),
 f('public_review_ambiguous','What date occupies the combined hearing-or-comment-period field, and can its role be separated?',{'date':'2025-03-14','role':'hearing or comment period; not disambiguated'},1,'Date of public hearing or comment period:          March 14, 2025'),
 absent('comment_close','Does this form explicitly identify a comment-close date separately?',1,'Complete form and emergency rationale input pages 1-3; March 14 combined field does not identify a close.'),
 absent('review_clock','Is a clock time or timezone given for the March 14 public-review date?',1,'Complete form and emergency rationale input pages 1-3.')])
fields('B03',[
 f('agency','Which agency proposes the exempt sales rule?','State Board of Elections',1,'TITLE 08 – STATE BOARD OF ELECTIONS',False),
 f('citation','Which rule is proposed?','08 NCAC 21 .0605',1,'21 .0605.'),
 f('event','What action is proposed?','adoption',1,'intends to adopt the rule'),
 f('proposed_effective','What proposed effective date is given?','2027-01-01',1,'Proposed Effective Date: January 1, 2027'),
 f('comment_close','What date closes this public comment period?','2026-11-16',1,'Comment period ends: November 16, 2026'),
 f('hearing','What hearing date/time is stated?',{'date':'2026-10-05','time':'10:00','timezone':None},1,'Date: October 5, 2026\nTime: 10:00 a.m.'),
 f('objection_condition','What later objection deadline is described, separate from comment close?',{'time':'17:00','relative_anchor':'day following Commission approval','computed_date':None},1,'until 5:00 p.m. on the day following the day the Commission approves the',True,'Legislative-review paragraph'),
 absent('close_clock','Does the notice state a clock time for November 16 comment close?',1,'Complete notice/rule input pages 1-2; 5 p.m. belongs to later legislative objections.'),
 absent('timezone','Does the notice explicitly state a hearing timezone?',1,'Complete notice/rule input pages 1-2.')])
fields('B04',[
 f('agency','Which agency proposes the waiver amendment?','State Board of Elections',1,'1. Rule-Making Agency: State Board of Elections',False),
 f('citation','Which rule citation is selected for amendment?','08 NCAC 21 .0206',1,'AMENDMENT: 08 NCAC 21 .0206'),
 f('event_selected','Which action is marked, rather than merely listed?','amendment',1,'X AMENDMENT: 08 NCAC 21 .0206',True,'Block 3: X aligned with AMENDMENT row','present','visual_mark'),
 f('proposed_effective','What proposed effective date is given?','2026-11-01',1,'4. Proposed effective date: 11/01/2026'),
 f('hearing','What hearing date/time is given?',{'date':'2026-08-03','time':'10:00','timezone':None},1,'08/03/2026 10:00 am'),
 f('comment_close','What date closes public comments?','2026-08-31',2,'10. Comment Period Ends: 08/31/2026'),
 f('filing','What filing date does the stamp show?','2026-06-08',1,'Filed Jun 8, 2026',False,'OAH filing stamp'),
 absent('close_clock','Does the notice state a clock time for August 31 comment close?',2,'Complete two-page Form 300; 5 p.m. belongs to legislative-review objections.'),
 absent('timezone','Is the public-hearing timezone explicitly stated?',1,'Complete two-page Form 300 input pages 1-2.')])

fields('B05',[
 f('agency','Which agency proposes the Passing Standards notice?','Texas Education Agency',2,'The T exas Education Agency (TEA) proposes',False),
 f('citation','Which rule is this target notice amending?','19 TAC §151.1001',2,'§151.1001, concerning passing standards'),
 f('source_id','What is the native TRD identifier of this target notice?','TRD-202601979',3,'TRD-202601979'),
 f('comment_window','What explicit comment opening and closing dates apply to this target notice?',{'open':'2026-05-22','close':'2026-06-22','time':None},2,'comment period on the proposal begins May 22, 2026, and \nends June 22, 2026.'),
 f('hearing_request','What relative hearing-request duration and anchor are given?',{'days':14,'day_basis':'calendar','anchor':'notice published May 22, 2026','computed_date':None},2,'must be received by the commissioner of education not more \nthan 14 calendar days after notice of the proposal has been \npublished in the Texas Register on May 22, 2026.'),
 f('filing','What filing date belongs to TRD-202601979?','2026-05-11',3,'Filed with the Office of the Secretary of State on May 11, 2026.'),
 f('earliest_adoption','What date is described as earliest possible adoption, rather than effectivity?','2026-06-21',3,'Earliest possible date of adoption: June 21, 2026'),
 absent('effective','Does the target proposal state an adopted effective date?',3,'Target §151.1001 notice begins input page 1 bottom heading, continues page 2, ends page 3 at TRD-202601979 and diamonds; neighboring TREC notice excluded.')])
fields('B06',[
 f('agency','Which agency proposes Broker Responsibility Advisory Committee changes?','Texas Real Estate Commission',1,'The T exas Real Estate Commission (TREC) proposes amend-',False),
 f('citation','Which citation belongs to the target notice?','22 TAC §535.46',1,'22 TAC §535.46'),
 f('source_id','What is the target native TRD identifier?','TRD-202601973',2,'TRD-202601973'),
 f('comment_duration','What relative public comment deadline is stated?',{'days':30,'day_basis':None,'anchor':'publication in Texas Register','computed_date':None},2,'The deadline for \ncomments is 30 days after publication in the Texas Register.'),
 f('publication','What issue publication date anchors the relative deadline?','2026-05-22',1,'May 22, 2026 51 TexReg 3501',True,'Page footer'),
 f('filing','What filing date belongs to TRD-202601973?','2026-05-08',2,'Filed with the Office of the Secretary of State on May 8, 2026.'),
 f('earliest_adoption','What earliest possible adoption date is supplied?','2026-06-21',2,'Earliest possible date of adoption: June 21, 2026'),
 absent('close_clock','Does the target notice state a comment-close clock time?',2,'Target §535.46 starts input page 1 after TEA diamonds and ends page 2 at TRD-202601973/diamonds; do not use neighboring TEA window.')])
fields('B07',[
 f('agency','Which agency proposes License Designation changes?','Texas Optometry Board',1,'The T exas Optometry Board proposes amendments',False),
 f('citation','Which rule citation belongs to this target notice?','22 TAC §271.12',1,'22 TAC §271.12'),
 f('source_id','What native TRD identifier belongs to License Designation?','TRD-202602105',2,'TRD-202602105'),
 f('comment_duration','What relative public comment deadline applies?',{'days':30,'day_basis':None,'anchor':'publication in Texas Register','computed_date':None},2,'The deadline for furnishing com-\nments is thirty days after publication in the Texas Register.'),
 f('publication','What issue date anchors this relative duration?','2026-06-05',2,'June 5, 2026 51 TexReg 3771',True,'Page footer'),
 f('filing','What filing date belongs to TRD-202602105?','2026-05-19',2,'Filed with the Office of the Secretary of State on May 19, 2026.'),
 f('earliest_adoption','What earliest possible adoption date is supplied?','2026-07-05',2,'Earliest possible date of adoption: July 5, 2026'),
 absent('effective','Does the target License Designation proposal give an adopted effective date?',2,'Target §271.12 starts input page 1 after TRD-202602104 diamonds and ends input page 2 at TRD-202602105 diamonds; neighboring repeal excluded.')])
for uid,agency,ccr,tracking,termination,reason,pub in [
 ('B08','Colorado State Board of Education','1 CCR 301-28','2026-00317','2026-08-25','Hearing date unchanged - notice will be re-filed to correct an administrative error.','September 10, 2026'),
 ('B09','State Treasurer','8 CCR 1508-1','2026-00275','2026-08-05','The hearing will be rescheduled.  A new notification will be filed.','August 25, 2026')]:
 fields(uid,[
 f('agency','Which agency is named in this terminated-rulemaking notice?',agency,1,agency,False),
 f('citation','Which CCR number is terminated?',ccr,1,ccr),
 f('tracking','Which native tracking number is terminated?',tracking,1,tracking),
 f('event','What lifecycle event is identified?','terminated rulemaking',1,'Terminated Rulemaking'),
 f('termination_date','What date is labeled Termination date?',termination,1,'08/25/2026' if uid=='B08' else '08/05/2026'),
 f('scope_reason','What reason/scope does the termination supply?',reason,1,reason),
 absent('replacement_hearing','Does this termination supply a new scheduled hearing date?',1,'Entire one-page termination notice; reason preserves unchanged date or promises rescheduling but supplies no actual date.'),
 absent('comment_close','Does this termination supply a new comment-close date?',1,'Entire one-page termination notice.')])
fields('B10',[
 f('agency','Which agency adopted the retail marijuana tax rule?','Taxation Division',1,'Taxation Division',False),
 f('citation','Which CCR number belongs to the adopted rule?','1 CCR 201-18',1,'1 CCR 201-18'),
 f('event','Which lifecycle event does this notice identify?','permanent adoption',1,'Permanent Rules Adopted'),
 f('effective','What date is labeled Effective Date?','2026-09-30',1,'09/30/2026'),
 f('publication','What is the register publication date?','2026-09-10',1,'September 10, 2026',False,'Register footer'),
 absent('comment_close','Does this permanent-adoption notice state a comment-close date?',1,'Entire one-page adopted-notice header, original physical page 233; attached adopted-rule text excluded.'),
 absent('hearing','Does this permanent-adoption notice state a hearing date?',1,'Entire one-page adopted-notice header, original physical page 233.'),
 absent('filing','Does this permanent-adoption notice state a filing date?',1,'Entire one-page adopted-notice header, original physical page 233.')])
