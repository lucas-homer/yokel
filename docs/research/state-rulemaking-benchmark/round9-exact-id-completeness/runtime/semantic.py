"""Deterministic aggregation of externally reviewed scope/mappings; no semantic discovery or approval."""
from collections import deque
import common as c
from response import CATEGORIES
AUDIT_SCHEMA=c.read(c.PROTO/'semantic-audit-input.schema.json')
REVIEW_SCHEMA=c.read(c.PROTO/'offline-audit-review.schema.json')
def fields(record):
    result={}
    def visit(item,pointer):
        for key,value in item.items():
            if key in ('id','evidence'):continue
            escaped=key.replace('~','~0').replace('/','~1');path=pointer+'/'+escaped
            if key in ('timing','components'):
                for n,child in enumerate(value):visit(child,path+'/'+str(n))
            else:result[path]=value
    for category in CATEGORIES:
        for n,item in enumerate(record[category]):visit(item,f'/{category}/{n}')
    return result

def aggregate(source_text,record,audit=None,review=None):
    codes=set();details=[]
    def issue(code,detail):codes.add(code);details.append(detail)
    def finish():
        invalid=codes-{'semantic_defect'}
        status='unverified' if invalid else 'not_complete' if 'semantic_defect' in codes else 'complete_supported'
        claimed=isinstance(record,dict) and isinstance(record.get('coverage'),dict) and record['coverage'].get('status')=='claimed_complete'
        return {'semantic_status':status,'complete_supported':status=='complete_supported','review_required':status!='complete_supported','diagnostic_codes':sorted(codes),'diagnostics':details,'coverage_claim_status':('corroborated' if status=='complete_supported' else 'contradicted' if status=='not_complete' else 'unverified') if claimed else 'not_claimed_complete','production_eligible':False,'action_ready':False,'semantic_discovery_performed':False}
    try:
        if not isinstance(source_text,str) or not isinstance(record,dict) or c.p.schema_errors(record,c.p.RECORD_SCHEMA):issue('audit_invalid','original R7 record/source shape');return finish()
        if record['source_text_sha256']!=c.file_hash_bytes(source_text.encode()):issue('binding_mismatch','record source hash')
        if c.p.relationship_errors(record):issue('audit_invalid','original record relationships')
        def evidence(entries):
            for e in entries:
                if set(e)!={'start','end','quote'} or type(e['start']) is not int or type(e['end']) is not int or not 0<=e['start']<e['end']<=len(source_text) or source_text[e['start']:e['end']]!=e['quote']:issue('pointer_or_evidence_invalid','exact source evidence differs')
        def record_evidence(node):
            if isinstance(node,dict):
                for key,value in node.items():
                    if key=='evidence':evidence(value)
                    else:record_evidence(value)
            elif isinstance(node,list):
                for child in node:record_evidence(child)
        record_evidence(record)
        if c.p.review_reasons(record):issue('acceptance_guard','original R7 review guard remains')
        if audit is None:issue('audit_missing','audit absent');return finish()
        if not isinstance(audit,dict) or c.p.schema_errors(audit,AUDIT_SCHEMA):issue('audit_invalid','audit closed schema');return finish()
        if review is None:issue('audit_unapproved','review absent')
        elif not isinstance(review,dict) or c.p.schema_errors(review,REVIEW_SCHEMA):issue('audit_unapproved','review closed schema')
        else:
            entries=review['entries'];names=[entry['audit_id'] for entry in entries]
            if len(names)!=len(set(names)):issue('audit_unapproved','duplicate review audit identities')
            matches=[entry for entry in entries if entry['audit_id']==audit['audit_id']]
            if len(matches)!=1:issue('audit_unapproved','exactly one review endorsement required')
            else:
                entry=matches[0];author=audit['provenance']['author'].strip();a=entry['primary_reviewer'];b=entry['independent_reviewer']
                if entry['decision']!='approved' or not isinstance(a,str) or not isinstance(b,str) or not a.strip() or not b.strip() or len({a.strip(),b.strip(),author})!=3 or not entry['review_note'].strip():issue('audit_unapproved','distinct external reviewers/approval required')
                bindings={'audit_sha256':c.digest(audit),'record_sha256':c.digest(record),'source_text_sha256':c.file_hash_bytes(source_text.encode()),'source_reference_sha256':c.digest(audit['source_reference'])}
                if any(entry[key]!=value for key,value in bindings.items()):issue('binding_mismatch','review hashes are stale')
        source_hash=c.file_hash_bytes(source_text.encode());reference=audit['source_reference']
        if audit['document_id']!=record['document_id'] or reference['document_id']!=record['document_id'] or audit['source_text_sha256']!=source_hash or reference['source_text_sha256']!=source_hash or audit['record_sha256']!=c.digest(record) or audit['source_reference_sha256']!=c.digest(reference):issue('binding_mismatch','audit source/record/reference bindings')
        scope=reference['scope']
        if scope['status']!='complete' or scope['reviewed_start']!=0 or scope['reviewed_end']!=len(source_text) or scope['exclusions'] or scope['unresolved_questions']:issue('source_scope_incomplete','entire reviewed source scope unavailable')
        claim_scope=audit['claim_coverage']
        if claim_scope['status']!='complete' or claim_scope['enumeration']!='r7-semantic-fields-v1' or claim_scope['unreviewed_pointers']:issue('claim_scope_incomplete','complete field review unavailable')
        units=reference['units'];rows=audit['source_dispositions'];checks=audit['candidate_claim_checks'];inventory=fields(record)
        def index(values,key,code):
            names=[row[key] for row in values]
            if not values or len(names)!=len(set(names)):issue(code,'empty or duplicate '+key)
            return {row[key]:row for row in values}
        unit_map=index(units,'source_unit_id','source_set_mismatch');row_map=index(rows,'source_unit_id','source_set_mismatch');claim_map=index(checks,'claim_id','claim_set_mismatch');pointer_map=index(checks,'record_pointer','claim_set_mismatch')
        if set(unit_map)!=set(row_map):issue('source_set_mismatch','exact source unit set differs')
        if set(pointer_map)!=set(inventory):issue('claim_set_mismatch','exact semantic field set differs')
        for unit in units:evidence(unit['source_evidence'])
        for check in checks:
            pointer=check['record_pointer'];links=check['source_unit_ids']
            if pointer not in inventory or (pointer in inventory and check['value_sha256']!=c.digest(inventory[pointer])):issue('pointer_or_evidence_invalid','nonoperative pointer or wrong whole-field value')
            if len(links)!=len(set(links)) or not set(links)<=set(unit_map):issue('mapping_inconsistent','candidate source links')
            if check['disposition']=='supported' and pointer in inventory and inventory[pointer] not in (None,'',[],{}) and not links:issue('mapping_inconsistent','positive supported field lacks source basis')
            if check['disposition']=='unknown':issue('semantic_unknown','candidate field support unknown')
            elif check['disposition']=='unsupported':issue('semantic_defect','candidate field unsupported')
        indegree={u:0 for u in unit_map};dependents={u:[] for u in unit_map}
        for unit in units:
            ident=unit['source_unit_id'];deps=unit['required_source_unit_ids']
            if len(deps)!=len(set(deps)) or ident in deps or not set(deps)<=set(unit_map):issue('dependency_invalid','missing/self/duplicate source dependency')
            for dep in set(deps)&set(unit_map):indegree[ident]+=1;dependents[dep].append(ident)
        queue=deque(x for x,n in indegree.items() if n==0);visited=0
        while queue:
            node=queue.popleft();visited+=1
            for child in dependents[node]:
                indegree[child]-=1
                if indegree[child]==0:queue.append(child)
        if visited!=len(unit_map):issue('dependency_invalid','source dependency cycle')
        for row in rows:
            unit_id=row['source_unit_id'];pointers=row['semantic_record_pointers'];claim_ids=row['candidate_claim_ids'];status=row['disposition']
            if len(pointers)!=len(set(pointers)) or len(claim_ids)!=len(set(claim_ids)) or not set(pointers)<=set(inventory) or not set(claim_ids)<=set(claim_map):issue('pointer_or_evidence_invalid','source mapping pointer/claim identity')
            if {claim_map[i]['record_pointer'] for i in claim_ids if i in claim_map}!=set(pointers):issue('mapping_inconsistent','source pointers and candidate claims differ')
            if status=='omitted' and (pointers or claim_ids):issue('mapping_inconsistent','omitted row has operative assertion')
            if status=='matched':
                if not pointers or not claim_ids or not any(inventory[x] not in (None,'',[],{}) for x in pointers if x in inventory):issue('mapping_inconsistent','matched source lacks positive operative assertion')
                for ident in claim_ids:
                    if ident in claim_map and (claim_map[ident]['disposition']!='supported' or unit_id not in claim_map[ident]['source_unit_ids']):issue('mapping_inconsistent','matched source lacks reverse supported claim link')
                for dep in unit_map.get(unit_id,{}).get('required_source_unit_ids',[]):
                    if row_map.get(dep,{}).get('disposition')!='matched':issue('dependency_invalid','matched source has nonmatched required endpoint')
            if status=='unknown':issue('semantic_unknown','source disposition unknown')
            elif status in ('omitted','mismatched'):issue('semantic_defect','source obligation not fully represented')
        return finish()
    except (ValueError,KeyError,TypeError,AttributeError,IndexError,RecursionError):issue('audit_invalid','invalid bounded semantic input');return finish()

def aggregate_json(source_json,record_json,audit_json=None,review_json=None):
    try:return aggregate(c.strict(source_json),c.strict(record_json),c.strict(audit_json) if audit_json is not None else None,c.strict(review_json) if review_json is not None else None)
    except ValueError:return {'semantic_status':'unverified','complete_supported':False,'review_required':True,'diagnostic_codes':['audit_invalid'],'production_eligible':False,'action_ready':False,'semantic_discovery_performed':False}
