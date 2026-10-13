"""Offline research fixture normalization; never reads expectations or model answers."""
import json, re, hashlib
from pathlib import Path
P=Path(__file__).resolve().parent

def main():
    manifest=json.loads((P/'manifest.json').read_text())
    by_id={a['artifact_id']:a for a in manifest}
    for a in manifest:
        path=(P/a['path']).resolve()
        if not path.is_relative_to(P) or hashlib.sha256(path.read_bytes()).hexdigest()!=a['sha256']:
            raise ValueError('Artifact integrity failure: '+a['artifact_id'])
    text=(P/'derived/firecrawl.md').read_text()
    out=[]
    def add(pred,value,quote,kind='deterministic',artifact='pdf-firecrawl-text',locator='one-page form',subject='proceeding',suffix='form'):
        if kind!='manual_visual' and quote not in (P/by_id[artifact]['path']).read_text():
            raise ValueError('Evidence quote missing')
        out.append(dict(schema_version='state-spike-v1',observation_id='pdf-'+pred,jurisdiction='US-MS',source_record_id='00027305a',subject={'kind':subject,'id':'research:ms:00027305a:'+suffix},predicate=pred,value=value,evidence=[{'artifact_id':artifact,'locator':locator,'quote':quote,'support':'visual_review' if kind=='manual_visual' else 'text_exact'}],method={'kind':kind,'name':'reviewed-form-regions' if kind=='manual_visual' else 'guarded-captured-clauses','version':'1'},review_state='reviewed_for_research' if kind=='manual_visual' else 'candidate',warnings=['Research form fixture only; source search and complete attachment coverage untested']))
    m=re.search(r'AGENCY NAME([^|\n]+)',text)
    if m: add('agency',m[1].strip(),m[0])
    m=re.search(r'Name or number of rule\(s\):([^|\n]+)',text)
    if m and re.fullmatch(r'Rule \d+\.\d+',m[1].strip()): add('rule_citations',[m[1].strip()],m[0])
    m=re.search(r'within [a-z-]+ \((\d+)\) days after (the filing of this notice of proposed rule adoption)',text)
    eligibility=re.search(r'If an oral proceeding is not scheduled, an oral proceeding must be held if a written request for an oral proceeding is submitted by a political subdivision, an agency or ten \(10\) or more persons\.',text)
    if m and eligibility:
        add('hearing_request_duration',{'kind':'relative','duration':int(m[1]),'unit':'days','anchor':m[2],'day_basis':None,'computed_close':None},m[0],subject='participation_window',suffix='hearing-request')
        out[-1]['evidence'].append({'artifact_id':'pdf-firecrawl-text','locator':'one-page form, ORAL PROCEEDING conditional eligibility sentence','quote':eligibility[0],'support':'text_exact'})
        out[-1]['warnings'].append('Hearing-request eligibility applies to a political subdivision, an agency, or ten or more persons when no oral proceeding is scheduled. Eligibility is retained in exact evidence but is not yet a separately typed field; this is not an unconditional individual right to require a hearing.')
    m=re.search(r'At any time within the [a-z-]+ \((\d+)\) day public comment period, written submissions[^.]+\.',text)
    if m: add('comment_duration',{'kind':'relative','duration':int(m[1]),'unit':'days','anchor':None,'day_basis':None,'computed_close':None},m[0],subject='participation_window',suffix='public-comment')
    review=json.loads((P/'derived/visual-review.json').read_text())
    if review['method']!='manual_visual' or review['image_sha256']!=by_id['pdf-page-image']['sha256']: raise ValueError('Invalid visual review provenance')
    for a in review['assertions']:
        if a['predicate'] not in ('event_type','rule_action','hearing_status','filing_date'): raise ValueError('Unexpected reviewed field')
        add(a['predicate'],a['value'],a['note'],'manual_visual','pdf-page-image',a['region'],a['subject_kind'],a['subject_suffix'])
    required={'agency','rule_citations','hearing_request_duration','comment_duration','event_type','rule_action','hearing_status','filing_date'}
    present={o['predicate'] for o in out}
    missing=sorted(required-present)
    diagnostic={'status':'needs_review' if missing else 'complete_for_selected_template',
                'missing_critical_predicates':missing,'observations_emitted':len(out),
                'scope':'Expected critical clauses/visual assertions in this selected form template, not a universal PDF schema'}
    if missing:
        for o in out:
            o['review_state']='needs_review'
            o['warnings'].append('Incomplete selected template: missing '+', '.join(missing))
    (P/'normalization-diagnostics.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
    (P/'observations.json').write_text(json.dumps(out,indent=2)+'\n')
    if missing:
        raise SystemExit('REVIEW REQUIRED: missing critical clause/assertion(s): '+', '.join(missing))
    print(f'{len(out)} observations; all manifest hashes and exact-text evidence validated')

if __name__=='__main__': main()
