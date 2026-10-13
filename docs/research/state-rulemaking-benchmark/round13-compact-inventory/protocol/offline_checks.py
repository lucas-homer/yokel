"""Full synthetic offline outputs and request sizing. No R12 response/prefix/candidate input."""
import math
from compact import *

source=(ROOT.parents[1]/'round12-automated-scope/source/26-19-016.txt').read_bytes().decode('utf-8')
table=span_table(source);req=build(source)
assert reconstruct(source,table).encode()==source.encode()
(ROOT/'span-table.json').write_bytes(canonical(table))
(ROOT/'schema.json').write_text(json.dumps(schema(source,table),indent=2)+'\n')
# This is the exact sole A request candidate; it is never dispatched here.
(ROOT/'offline-request.json').write_bytes(canonical(req['body']))
profiles=[]
for name,n,slen,clen,uncertain in [('representative32',32,55,12,4),('representative64',64,55,12,8),('stressed96',96,75,30,16),('stressed128',128,100,50,32)]:
    units=[]
    for i in range(1,n+1):
        q=1 if i<=uncertain else 0
        # Purely dimensional synthetic statements, not source facts or model discoveries.
        units.append(dict(i=i,k=8,s=('Synthetic atomic assertion '+str(i)+': ').ljust(slen,'x'),m=0,c=('if applicable').ljust(clen,'x') if i%4==0 else '',d=[],b=[],e=[table['rows'][(i-1)%len(table['rows'])][0]],q=q,r='Synthetic uncertainty retained.' if q else ''))
    # One typed endpoint + two separate role assertions + full relationship per complete fixture.
    units[0].update(k=4,s='Synthetic shared endpoint.',q=0,r='')
    units[1].update(k=5,s='Synthetic actor submits comments to endpoint.',d=[1],q=0,r='')
    units[2].update(k=5,s='Synthetic actor requests accommodations at endpoint.',d=[1],q=0,r='')
    units[3].update(k=7,s='Synthetic relation preserves distinct role members.',b=[2,3],q=0,r='')
    output=dict(v=VERSION,h=source_hash(source),t=digest(table),u=units,z='END')
    expanded=expand(output,source,table);assert canonical(contract(expanded,source,table))==canonical(output)
    raw=canonical(output)
    (ROOT/(name+'.json')).write_bytes(raw)
    sensitivity={}
    for ratio in [2,3,4]:
        estimate=math.ceil(len(raw)/ratio)+256
        sensitivity[str(ratio)]=dict(estimated_tokens_including_reasoning_allowance=estimate,remaining_tokens=8192-estimate,cap_fraction=estimate/8192)
    profiles.append(dict(name=name,units=n,assertion_dimension=slen,conditional_text_dimension=clen,uncertainty_units=sum(u['q']!=0 for u in units),full_output_bytes=len(raw),full_output_characters=len(raw.decode()),expanded_bytes=len(canonical(expanded)),compact_sha256=digest(output),exact_semantic_roundtrip=True,estimates_bytes_per_token=sensitivity))
result=dict(interpretation='Complete synthetic annotation fixtures only, not evidence of source atomicity, entailment, model performance or completeness. No invalid response prefix used.',source_sha256=source_hash(source),span_table_sha256=digest(table),partition_spans=len(table['rows']),source_utf8_bytes=len(source.encode()),source_reconstruction_exact=True,request_body_bytes=req['body_bytes'],request_guarded_bytes=req['guarded_bytes'],request_sha256=req['request_sha256'],output_cap=8192,estimator=dict(tokenizer='No tiktoken/tokenizers available in existing Python; no installation/network used.',method='UTF-8 byte ratios 2/3/4 bytes per token, each plus 256 token reasoning/envelope allowance. Ratios are sensitivity assumptions, not a reliable upper bound or model-matched tokenization.',recommended_targets='Representative fixture <=70% cap; stressed <=85% under chosen ratio. Primary must choose/freeze ratio/threshold and release decision. No unconditional fit guarantee.'),profiles=profiles)
(ROOT/'offline-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
