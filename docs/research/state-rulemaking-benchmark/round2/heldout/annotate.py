"""Collector-authored source annotations; no parser outputs consumed."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re
R=Path(__file__).parent
inventory=json.loads((R/'source-inventory.json').read_text());units={x['fixture_id']:x for x in inventory}
meta={
'H01':('Wisconsin DNR second hearing, FWP-22-24 (CR 25-088)','WI-DNR-permanent-rule-hearing-notice','lifecycle_change',['born-digital standalone','bold section headings','second hearing and prior period'],'second public hearing on proposed permanent rule','Entire two-page hearing notice, including written-comment paragraph on page2. Linked rule and hearing appearance form are not included.'),
'H02':('Maine DMR Chapter34 whiting effort restrictions, 2026-P188','ME-SOS-MAPA-3','scanned_filled_form',['born-digital filled MAPA-3 form','label-value fields','payment table continuation'],'proposed routine technical rule','Complete two-page MAPA-3 form. Original pages3–18 proposed rule text and supporting material excluded; no absence claim extends beyond form.'),
'H03':('Iowa ARC0619D state unit on aging and area agency contracts','IA-ARC-standalone-notice-intended-action','clean_standalone_pdf',['born-digital standalone','hearing time/location columns','underlined additions and struck deletions'],'notice of intended action / proposed amendments','Entire three-page official ARC PDF including proposed rule text. Regulatory-analysis historical dates must not become notice publication or current hearing dates.'),
'H04':('Kansas BIDS proposed administrative regulations, Doc054172','KS-Register-2026-single-column-sans','dense_register_layout',['born-digital single-column register','two-page continuation','document number at end'],'hearing on proposed permanent amendments','Original physical pages62–63 comprise complete BIDS notice through Doc.No.054172. Adjacent notices and unrelated register entries excluded.'),
'H05':('Oregon OBLPCT April9 proposed rules','OR-SOS-OARD-proposed-rulemaking-fiscal-form','scanned_filled_form',['born-digital filed form','boxed filing stamp','multi-column contact fields'],'notice of proposed rulemaking','Complete two-page notice/need/fiscal-impact section through RULES PROPOSED list. First attached rule heading appears at page2 bottom; substantive rule text original3–6 excluded. Absences apply to notice, not rule attachment.'),
'H06':('Minnesota Board of Electricity dual notice RD-04985','MN-State-Register-proposed-rules-dual-notice','dense_register_layout',['dense single-column register','boxed general instructions','notice continuation','neighbor notice begins on final page'],'dual notice of proposed permanent amendment and conditional hearing','Target starts input1 below boxed general Proposed Rules instructions, continues input2–3 and input4 through Trevor Turek signature and rule1315.0200. Exclude following Marriage and Family Therapy notice. General box retained as context and conflicting maximum-day wording is explicitly recorded.'),
'H07':('Utah filing58107 proposed repeal R18-1','UT-State-Digest-substantive-change-form','dense_register_layout',['register tables','filled filing type','anticipated effective disclaimer','neighbor starts on final page'],'proposed repeal / notice of substantive change','Original9–11 printed5–7. Target filing58107 R18-1 starts first page and ends input3 agency authorization box. Neighbor filing58106 R18-2 begins below and is excluded. Digest lacks full proposed rule text.'),
'H08':('Alaska Board of Game June12 proposed changes notice','AK-BOG-proposed-change-with-additional-info','clean_standalone_pdf',['standalone notice plus filled additional information','checkbox selections','conditional hearing extension','cost table'],'proposed amendments','Complete four-page notice and additional-regulation-information form. Separate proposed regulations linked by notice are not included.')}
F={k:[] for k in units}
def norm(s):return re.sub(r'\s+',' ',s).strip()
def add(k,fid,q,value,page,quote,region,critical=True,answer='present',group=None,note='',basis='source_text'):
 u=units[k];text=(R/k/f'native-page-{page}.txt').read_text()
 assert not quote or norm(quote) in norm(text),(k,fid,quote)
 f=dict(field_id=fid,question=q,expected_value=value,answerability=answer,critical=critical,input_page=page,original_page=u['original_physical_pages'][page-1],region=region,source_quote=quote,basis=basis,semantic_group_id=group or fid,critical_reason='Preserves target identity, lifecycle, date role, precision or participation condition.' if critical else 'Supporting agency or source context; not included in strict critical gate.',expected_value_shape=type(value).__name__,accepted_equivalences=['Equivalent date/time/number/capitalization/whitespace forms preserving role, precision, conditions and scope.','No inferred timezone, calculated relative date, changed proposed/final status or borrowed neighboring value.'],decisive_evidence=note or 'Preserve value with stated role and target scope.',notice_scope_boundaries=meta[k][5],source_pages_viewed=list(range(1,u['input_page_count']+1)),absence_scope_if_applicable=None)
 if answer=='not_stated':f['absence_scope_if_applicable']=meta[k][5];f['basis']='full_scope_absence';f['decisive_evidence']=note or 'Relevant complete notice scope must survive; silence alone is insufficient.'
 F[k].append(f)
def absent(k,fid,q,page,note=''):add(k,fid,q,None,page,None,'Complete target notice',answer='not_stated',note=note)
# H01
add('H01','agency','Which agency gives the notice?','Department of Natural Resources',1,'The Department of Natural Resources announces','Opening paragraph',False)
add('H01','source_id','Which rulemaking IDs identify the second hearing?',['FWP-22-24','CR 25-088'],1,'FWP-22-24 (CR 25-\n088)','Rule Information')
add('H01','event','What event is announced?','second public hearing on a permanent rule to revise chapters NR1 and45',1,'it will hold a second public hearing on a \npermanent rule to revise chs. NR 1 and 45','Opening')
add('H01','hearing','When is the second hearing?','January 30, 2026, 12 p.m.',1,'Date: January 30, 2026 \nTime: 12 p.m.','Hearing Information')
add('H01','prior_period','What initial public-comment period is distinguished?','December 8, 2025 to January 12, 2026',1,'initial comment period from Dec. 8, 2025, to Jan. \n12, 2026','Rule Information')
add('H01','comment_close','What is the written-comment receipt deadline?','on or before January 30, 2026',2,'Comments on the proposed rule must be received on or before Jan. 30, 2026.','Submittal of Written Comments')
add('H01','change_scope','Which sections are intended to be removed from the final version?','Sections4 and6, climbing-related definitions; future rulemaking intended',1,'the department intends to remove SECTIONS 4 and 6 (climbing-related definitions) of \nthe rule from the final version','Rule Information')
absent('H01','close_clock','Does the notice state a written-comment cutoff time?',2,'No comment clock is stated; hearing noon must not be transferred to written comments.')
absent('H01','effective','Does the complete notice supply an effective date?',1)
# H02
add('H02','agency','Which agency proposes the rule?','Department of Marine Resources',1,'AGENCY: Department of Marine Resources','Agency',False)
add('H02','citation','Which chapter and target title are stated?','Chapter34 Groundfish: Whiting/Silver Hake Commercial Effort Restrictions',1,'CHAPTER NUMBER AND RULE TITLE: Chapter 34, Groundfish [Whiting/Silver Hake \n(Merluccius bilinearis) Commercial Effort Restrictions]','Chapter and title')
add('H02','source_id','What proposal filing number is given?','2026-P188',1,'PROPOSAL FILING NUMBER: 2026-P188','Filing number')
add('H02','event','What lifecycle/type is given?','Notice of Agency Rulemaking Proposal; Routine Technical',1,'Notice of Agency Rulemaking Proposal','Heading',note='Proposal, not adopted rule; type Routine Technical separately visible in form.')
add('H02','hearing','What does PUBLIC HEARING state?','None',1,'PUBLIC HEARING: None.','Public Hearing',answer='explicit_negative')
add('H02','comment_close','What is the comment deadline?','Sunday, September 13, 2026',1,'COMMENT DEADLINE: Sunday, September 13, 2026','Comment deadline')
add('H02','payment_approval','What date belongs to payment approval rather than rule filing/publication?','August6,2026',1,'Approved for Payment: Deirdre Gilbert Date: 8/6/2026','Payment approval',False)
absent('H02','close_clock','Does the form supply a comment deadline clock time?',1)
absent('H02','effective','Does the form supply a rule effective date?',1)
# H03
add('H03','agency','Which department proposes the amendments?','Department of Health and Human Services / Human Services Department[441]',1,'HUMAN SERVICES DEPARTMENT[441]','Heading',False)
add('H03','source_id','What ARC identifier is printed?','ARC0619D',1,'ARC 0619D','Top right')
add('H03','event','What action and stage are proposed?','Notice of Intended Action; amend Chapters226 and227',1,'Notice of Intended Action','Heading',note='Opening paragraph proposes amendments to both named chapters; no final adoption.')
add('H03','comment_close','When must comments be received?','October20,2026 at4:30p.m.',2,'must be received by the Department no later than 4:30 p.m. on October 20, 2026.','Public Comment')
add('H03','hearing','When is the current public hearing?','October20,2026,10–10:30a.m.',2,'October 20, 2026\n10 to 10:30 a.m.','Public Hearing')
add('H03','prior_hearing','When was the earlier regulatory-analysis hearing?','September8,2026',1,'A public hearing was held on the following date(s):\n   September 8, 2026','Regulatory Analysis',note='Historical analysis hearing, not current hearing.')
add('H03','analysis_publication','When was the Regulatory Analysis published?','August19,2026',1,'A Regulatory Analysis for this rulemaking was published in the Iowa Administrative Bulletin on \nAugust 19, 2026.','Regulatory Analysis',note='Publication of analysis; not the current notice publication date.')
absent('H03','timezone','Does this notice state the comment/hearing timezone?',2)
absent('H03','effective','Does the notice assign a final effective date to these amendments?',1,'No final effective date; background State Plan45-day submission and federal October1,2025 references are not this rulemaking effective date.')
# H04
add('H04','agency','Which board proposes the regulations?','Kansas State Board of Indigents’ Defense Services',1,'Board of Indigents’ Defense Services','Heading',False)
add('H04','source_id','What document number ends the notice?','054172',2,'Doc. No. 054172','Notice end')
add('H04','event','What action/stage is this?','Hearing on proposed permanent regulations/amendments',1,'Notice of Hearing on Proposed Administrative Regulations','Heading')
add('H04','hearing','When will the public hearing be conducted?','July15,2026 at1:00p.m.',1,'A public hearing will be conducted at 1:00 p.m. Wednesday, July 15, 2026','Opening')
add('H04','publication','What register issue date accompanies the notice?','May14,2026',1,'Volume 45 - Issue 20 - May 14, 2026','Register header')
add('H04','comment_relative','What comment-period duration and submission boundary are stated?','60-day notice constitutes public comment period; written comments prior to hearing',1,'This 60-day notice of the public hearing shall constitute a public comment period','Second paragraph',note='Following sentence says written comments prior to hearing; preserve both without calculating an absolute close.')
add('H04','accommodation_relative','How far in advance should accommodation requests be made?','at least five working days in advance of hearing',1,'Requests \nfor accommodation to participate in the hearing should be made at least five working days in advance of the \nhearing','Accommodation paragraph')
absent('H04','effective','Does the complete notice state an effective date?',1)
absent('H04','timezone','Is a hearing timezone explicitly supplied?',1)
# H05
add('H05','agency','Which board is named?','Oregon Board of Licensed Professional Counselors and Therapists',1,'OREGON BOARD OF LICENSED PROFESSIONAL COUNSELORS AND THERAPISTS','Agency header',False)
add('H05','citation','What rules are listed as proposed?',['833-020-0041','833-020-0081','833-050-0011','833-110-0031'],2,'RULES PROPOSED: \n833-020-0041, 833-020-0081, 833-050-0011, 833-110-0031','Rules proposed list')
add('H05','event','What stage is stated by the document heading?','Notice of Proposed Rulemaking',1,'NOTICE OF PROPOSED RULEMAKING','Heading')
add('H05','filing','What timestamp is labeled FILED?','April9,2026 11:32AM',1,'FILED\n04/09/2026 11:32 AM','Boxed stamp',basis='visual_mark')
add('H05','comment_close','What is the last day/time to offer comment?','May21,2026 5:00PM',1,'LAST DAY AND TIME TO OFFER COMMENT TO AGENCY: 05/21/2026 5:00 PM','Comment deadline')
add('H05','hearing','What hearing date and time range are stated?','May21,2026 9:00AM–11:00AM',1,'DATE: 05/21/2026 \nTIME: 9:00 AM - 11:00 AM','Hearing fields')
absent('H05','timezone','Does the notice explicitly state a deadline/hearing timezone?',1)
absent('H05','effective','Does the retained notice state an effective date?',1)
# H06
add('H06','agency','Which board issues the dual notice?','Minnesota Board of Electricity',1,'Minnesota Board of Electricity','Target heading',False)
add('H06','source_id','Which Revisor and CAH identifiers belong to this target?',['RD-04985','5-9065-41611'],1,'Revisor’s ID Number RD-04985; CAH docket number 5-9065-41611','Target subtitle')
add('H06','event','What lifecycle/action does the target announce?','Dual notice of intent to adopt proposed permanent amendment, with conditional hearing',1,'Proposed Permanent Rule Adopting the 2026 National Electrical Code; DUAL NOTICE:','Target heading')
add('H06','comment_close','When are written comments and hearing requests due?','June3,2026 at4:30p.m.',1,'until 4:30 p.m. on Wednesday, June 3, \n2026.','Introduction')
add('H06','conditional_hearing','When is the hearing and under what request threshold?','June17,2026 at9:30a.m.;25 or more written requests by June3,2026 4:30p.m.; may cancel if insufficient requests remain',1,'If\t25\tor\tmore\tpersons\tsubmit\ta\twritten\trequest\tfor\ta\thearing\ton\tthe\trules\tby\t4:30 p.m. on Wednesday, \nJune 3, 2026,\tthe\tBoard\twill\thold\ta\tvirtual\tpublic\thearing\ton\tWednesday, June 17, 2026, at 9:30 a.m.','Hearing',note='Read with withdrawal/cancellation clauses on input3; scheduled hearing is conditional, not unconditional.')
add('H06','posthearing_window','What initial window does the target notice provide after a hearing ends?','five working days after public hearing ends, if hearing held',3,'five\tworking\tdays\tafter\tthe\tpublic\thearing\tends.','Hearing Procedure',note='Relative to actual hearing end; do not compute an absolute close. May be extended by ALJ.')
add('H06','extension_max_conflict','Do retained source statements consistently define the maximum extended posthearing period?','Unresolved: general register box20 calendar days; target Hearing Procedure20 working days',3,'no\tmore\tthan\t20\tworking\tdays.','Hearing Procedure and input1 general box',answer='uncertain',note='Source wording differs: input1 general box says up to20 calendar days; target input3 says no more than20 working days. Preserve both roles; no legal resolution. Critical reference uncertainty excludes strict gate eligibility.')
F['H06'][-1]['conflicting_evidence']=[dict(input_page=1,original_page=5,region='General register box',source_quote='extend the period for receiving comments up to 20 calendar days.'),dict(input_page=3,original_page=7,region='Target Hearing Procedure',source_quote='no more than 20 working days.')]
add('H06','publication','What publication date appears in retained register footers?','May4,2026',1,'Minnesota State Register, Monday 4 May 2026','Footer')
add('H06','order_date','What date accompanies the chair’s order?','April27,2026',4,'Date:\tApril\t27,\t2026','Order signature')
absent('H06','effective','Does the target notice state a final effective date?',4)
# H07
add('H07','agency','Which agency title catchline is printed?','Government Operations, Data Privacy',1,'Title catchline: Government Operations, Data Privacy','Agency information',False)
add('H07','source_id','What filing ID belongs to R18-1?','58107',1,'TYPE OF FILING: Repeal Filing ID: 58107','Filing header')
add('H07','citation','What rule is targeted?','R18-1 Relief from Data Privacy Requirements',1,'R18-1. Relief from Data Privacy Requirements','Rule catchline')
add('H07','event','What filing type and scope are proposed?','Repeal in entirety, proposed substantive change',1,'This filing repeals the rule in its entirety.','Summary',note='Under Notices of Proposed Rules; not a completed repeal.')
add('H07','comment_close','Until what date will comments be accepted?','August31,2026',3,'A. Comments will be accepted until: 08/31/2026','Public Notice Information')
add('H07','anticipated_effective','What date MAY the change become effective, and what disclaimer accompanies it?','September8,2026 anticipated; explicitly NOT effective date',3,'This rule change MAY become effective on: \n(NOTE: This is the date the agency anticipates making the filing \neffective. It is NOT the effective date) \n09/08/2026','Effective Date Information',note='Anticipated possible date only; cannot assert final effective status.')
add('H07','authorization_date','What date is attached to agency authorization?','June30,2026',3,'Marvin Dodge, Commissioner Date: 06/30/2026','Agency Authorization')
add('H07','publication','What Digest publication date is printed?','August1,2026',1,'UTAH STATE DIGEST, August 01, 2026','Footer')
absent('H07','hearing','Does target filing58107 give a public hearing date?',3)
absent('H07','close_clock','Does target filing58107 give a comment cutoff clock time?',3)
# H08
add('H08','agency','Which agency proposes the amendments?','Alaska Board of Game',1,'IN THE REGULATIONS OF THE ALASKA BOARD OF GAME','Heading',False)
add('H08','source_id','What Department of Law file number is provided?','2026200173',3,'Department of Law file number, if any: 2026200173','Additional info item4')
add('H08','citation','Which four provisions are proposed to be amended?',['5 AAC92.510','5 AAC92.550','5 AAC92.126(b)','5 AAC92.085'],1,'5 AAC 92.126(b) is proposed to be amended','Numbered summary',note='All four numbered provisions in input1; preserve (b) specificity there rather than broader grouped92.126 on input3.')
add('H08','event','What stage does the notice announce?','proposed regulation amendments, not final adoption',1,'NOTICE OF PROPOSED CHANGES','Heading')
add('H08','comment_close','When must written comments be received?','July16,2026 8:00a.m.',1,'The comments must be received not later than 8:00 a.m. on \nThursday, July 16, 2026.','Written comment deadline')
add('H08','hearing','What initial hearing dates and daily times are stated?','July22–23,2026 8:30a.m.–5:30p.m.',1,'The hearing will be held from 8:30 a.m. to 5:30 p.m.','Oral hearing',note='Date range July22–23 in preceding sentence. Do not confuse separate written-comment deadline with hearing participation.')
add('H08','extension_condition','What optional hearing extension and eligibility condition are stated?','Might extend to July24,8:30a.m.–5:30p.m.,same location, to accommodate those present before1:00p.m.July22 who lacked opportunity to comment',1,'might be extended to July 24, \nfrom 8:30 am to 5:30 p. m. at the same location to accommodate those present before 1: 00 p.m. \non July 22, who did not have an opportunity to comment.','Oral hearing')
add('H08','notice_date','What date accompanies the signed notice?','June12,2026',2,'Date: June 12, 2026','Signature block')
absent('H08','timezone','Does the complete notice state a timezone for comments/hearing?',1)
absent('H08','effective','Does the complete notice supply a final effective date?',2)
for k,fields in F.items():
 u=units[k];title,family,bucket,layout,event,scope=meta[k]
 assert 6<=len(fields)<=10 and sum(f['critical'] and f['answerability']!='uncertain' for f in fields)>=4
 u.update(source_title=title,template_family=family,primary_bucket=bucket,bucket=bucket,layout_features=layout,event_type=event,notice_scope_boundaries=scope,package_limitations=scope,selection_reason='Purposive accessible official example from a new state/publication family; chosen from source content before round2 parser output exposure.',reference_path=f'{k}/collector-reference.json',reference_fields=len(fields),critical_fields=sum(f['critical'] for f in fields),reference_gate_eligible=not any(f['critical'] and f['answerability']=='uncertain' for f in fields),uncertain_critical_fields=[f['field_id'] for f in fields if f['critical'] and f['answerability']=='uncertain'])
 reference=dict(fixture_id=k,reference_version='collector-source-v1',collector_kind='agent source annotations, not human gold labels',independent_review_status='pending',new_vendor_outputs_inspected=False,native_text_used_for_navigation_and_quote_transcription=True,complete_input_images_inspected=True,input_sha256=u['input_sha256'],state=u['state'],primary_bucket=bucket,template_family=family,notice_scope_boundaries=scope,package_limitations=scope,reference_fields=fields)
 (R/k/'collector-reference.json').write_text(json.dumps(reference,ensure_ascii=False,indent=2)+'\n')
 fixture=dict(u);fixture['reference_fields']=fields;(R/k/'fixture.json').write_text(json.dumps(fixture,ensure_ascii=False,indent=2)+'\n')
(R/'source-inventory.json').write_text(json.dumps(list(units.values()),ensure_ascii=False,indent=2)+'\n')
print('annotations',sum(len(v) for v in F.values()))
