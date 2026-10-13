// Execute only inside functions.exec after the parent supplies run configuration.
// No upload or parse occurs without BOTH explicit authorization and immutable freeze hash.
const ROOT = '/private/tmp/docketclock-expanded-benchmark-2026-10-05/firecrawl/recovery-1';
const PY = '/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3';
const ORDER = ['A','B'].flatMap(lane => Array.from({length:10},(_,i)=>lane+String(i+1).padStart(2,'0')));
const cfg = load('firecrawl_run_config');
if (!cfg || cfg.explicit_run_authorized !== true || !cfg.freeze_path || !/^[a-f0-9]{64}$/.test(cfg.freeze_sha256 || '')) {
  throw new Error('Blocked: immutable parent freeze and explicit run authorization are required. No provider call made.');
}
const shellQuote = x => "'" + String(x).replace(/'/g,"'\\''") + "'";
const preflight = await tools.exec_command({cmd:PY+' '+shellQuote(ROOT+'/verify_freeze.py')+' '+shellQuote(cfg.freeze_path)+' '+shellQuote(cfg.freeze_sha256),max_output_tokens:12000});
if (preflight.exit_code !== 0) throw new Error('Freeze/input preflight failed; no provider call made.');
const corpus = JSON.parse(preflight.output);
if (corpus.fixtures.map(f=>f.fixture_id).join(',')!==ORDER.join(',')) throw new Error('Freeze does not contain exact A01..A10,B01..B10 order.');
const utc = ()=>new Date().toISOString();
const write = async (path,value) => {
  const s=typeof value==='string'?value:JSON.stringify(value,null,2)+'\n';
  await tools.apply_patch('*** Begin Patch\n*** Add File: '+ROOT+'/'+path+'\n+'+s.split('\n').join('\n+')+'\n*** End Patch');
};
// Add File contributes a newline. Exact raw markdown is saved separately through the helper,
// using transient non-echoing PTY stdin (never a credential file).
const writeMarkdownExact = async (fid,markdown) => {
  // apply_patch does not preserve a missing terminal newline; helper reads JSON over pipe.
  const launched=await tools.exec_command({cmd:PY+' '+shellQuote(ROOT+'/write_markdown.py')+' '+shellQuote(ROOT+'/'+fid+'/markdown.md'),tty:true,yield_time_ms:1000,max_output_tokens:1000});
  if (!launched.session_id || !launched.output.includes('"stdin_ready":true')) throw new Error('Markdown writer did not open non-echoing stdin');
  const finished=await tools.write_stdin({session_id:launched.session_id,chars:JSON.stringify({markdown})+'\n',yield_time_ms:1000,max_output_tokens:1000});
  if (finished.exit_code!==0) throw new Error('Exact markdown capture failed');
  return JSON.parse(finished.output);
};
const body = r => {
  if(r.structuredContent) return r.structuredContent;
  for(const item of r.content||[]) if(item.type==='text') {try{return JSON.parse(item.text);}catch{}}
  return r;
};
const secretStrings = p => {
  const list=[];
  const visit=x=>{if(typeof x==='string'&&x.length>8)list.push(x);else if(x&&typeof x==='object')Object.values(x).forEach(visit);};
  visit(p.upload?.uploadUrl);visit(p.upload?.uploadRef);visit(p.upload?.headers);visit(p.upload?.fields);
  visit(p.nextToolCall?.arguments?.uploadRef);
  return [...new Set(list)].filter(x=>!['application/pdf','text/plain','application/octet-stream'].includes(x)).sort((a,b)=>b.length-a.length);
};
const sanitized = (value,secrets) => {
  const replace=s=>{for(const token of secrets)s=s.split(token).join('[REDACTED_UPLOAD_SECRET]');return s;};
  const visit=x=> {
    if(typeof x==='string') {try {const parsed=JSON.parse(x);if(parsed&&typeof parsed==='object')return JSON.stringify(visit(parsed));}catch{}return replace(x);}
    if(Array.isArray(x))return x.map(visit);
    if(x&&typeof x==='object')return Object.fromEntries(Object.entries(x).map(([k,v])=>[k,/^(uploadUrl|uploadRef|command|headers|fields)$/i.test(k)?'[REDACTED_UPLOAD_INSTRUCTIONS]':visit(v)]));
    return x;
  };
  return visit(value);
};
const markdownFrom = p => {
  const strings=[];
  const walk=x=>{if(!x||typeof x!=='object')return;if(typeof x.markdown==='string')strings.push(x.markdown);for(const [k,v]of Object.entries(x))if(k!=='markdown'&&v&&typeof v==='object')walk(v);};
  walk(p.data||p);
  const distinct=[...new Set(strings)];return distinct.length===1?distinct[0]:null;
};
const reported = p => {
  const usage=[],identifiers=[];
  const walk=(x,path)=>{if(!x||typeof x!=='object')return;for(const[k,v]of Object.entries(x)){
    const key=path+'/'+k;
    if(/credit|usage|tokens|pagesProcessed|pageCount/i.test(k)&&v!==null&&typeof v!=='object')usage.push({path:key,value:v});
    if(/^(id|jobId|scrapeId|scrape_id|version|parserVersion|modelVersion)$/i.test(k)&&v!==null&&typeof v!=='object')identifiers.push({path:key,value:v});
    if(v&&typeof v==='object')walk(v,key);
  }};walk(p,'');return {usage:usage.length?usage:null,identifiers:identifiers.length?identifiers:null};
};
await write('preflight.json',corpus);
await write('run-request.json',{execution_amendment:'../../execution-amendment-1.json',recovery_for:['A01','A02','A03','A04'],started_at:utc(),freeze_path:cfg.freeze_path,freeze_sha256:cfg.freeze_sha256,order:ORDER,max_concurrent:2,stop_after_consecutive_operational_failures:3,settings:{formats:['markdown'],parsers:['pdf'],onlyMainContent:false,pdfOptions:{maxPages:'exact input_page_count per frozen unit'}},hints:false,structured_extraction:false,timeout_retry:false});
let submitted=0,active=[],completionSequence=0,consecutiveFailures=0,stopped=false;
const outcomes=[];
async function runOne(f) {
  const id=f.fixture_id,started=utc(),t=Date.now();let stage='phase_one',secrets=[];
  const request1={filePath:f.input_path,contentType:'application/pdf',declaredSizeBytes:f.input_bytes};
  await write(id+'/phase-one-request.json',{request:request1,input_sha256:f.input_sha256,input_page_count:f.input_page_count,started_at:id==='A01'&&load('firecrawl_first_phase')?load('firecrawl_first_phase').started_at:started});
  try {
    let tick=Date.now();
    const cachedFirst=id==='A01'?load('firecrawl_first_phase'):null;
    const r1=cachedFirst?cachedFirst.response:await tools.mcp__codex_apps__firecrawl_firecrawl_parse(request1),p1=body(r1);
    const phaseOneMs=cachedFirst?cachedFirst.elapsed_ms:Date.now()-tick;
    const phaseOneStart=cachedFirst?cachedFirst.started_at:started;
    if(cachedFirst)store('firecrawl_first_phase',null);
    secrets=secretStrings(p1);
    await write(id+'/phase-one-response.redacted.json',{response:sanitized(r1,secrets),redaction:'Upload URLs, references, commands, headers and form credentials redacted; transient original existed in memory only.',elapsed_ms:phaseOneMs,started_at:phaseOneStart,ended_at:utc()});
    if(r1.isError||p1.success===false||!p1.upload?.uploadUrl||!p1.upload?.uploadRef) return {fixture_id:id,success:false,failure_stage:stage,reason:'No usable hosted upload instructions',started_at:started,ended_at:utc(),elapsed_ms:Date.now()-t};
    stage='upload';tick=Date.now();
    const uploadStarted=utc();
    const process=await tools.exec_command({cmd:PY+' '+shellQuote(ROOT+'/upload_transfer.py')+' --input '+shellQuote(f.input_path)+' --sha256 '+shellQuote(f.input_sha256),sandbox_permissions:'require_escalated',justification:'Upload identical frozen public notice PDF bytes to the authorized Firecrawl hosted document parser.',tty:true,yield_time_ms:1000,max_output_tokens:1000});
    if(!process.session_id || !process.output.includes('"stdin_ready":true')) throw new Error('Upload transfer did not open non-echoing stdin');
    let uploaded=await tools.write_stdin({session_id:process.session_id,chars:JSON.stringify(p1.upload)+'\n',yield_time_ms:1000,max_output_tokens:1000});
    while(uploaded.session_id) uploaded=await tools.write_stdin({session_id:uploaded.session_id,chars:'',yield_time_ms:1000,max_output_tokens:1000});
    const upload=JSON.parse(uploaded.output);
    await write(id+'/upload-receipt.json',{...upload,started_at:uploadStarted,ended_at:utc(),local_wall_ms:Date.now()-tick,credential_capture:'signed transport instructions supplied to process stdin only; never written to lane files'});
    if(!upload.success) return {fixture_id:id,success:false,failure_stage:stage,reason:upload.error_type||'Upload HTTP failure',upload,started_at:started,ended_at:utc(),elapsed_ms:Date.now()-t};
    stage='parse';const request2={uploadRef:p1.upload.uploadRef,formats:['markdown'],parsers:['pdf'],onlyMainContent:false,pdfOptions:{maxPages:f.input_page_count}};
    const parseStart=utc();tick=Date.now();
    await write(id+'/parse-request.redacted.json',{request:{...request2,uploadRef:'[REDACTED_UPLOAD_REFERENCE]'},input_sha256:f.input_sha256,input_bytes:f.input_bytes,started_at:parseStart});
    const r2=await tools.mcp__codex_apps__firecrawl_firecrawl_parse(request2),parseEnd=utc(),parseMs=Date.now()-tick,p2=body(r2);
    let finalResponse=r2;const serialized=JSON.stringify(r2),leaked=secrets.some(s=>serialized.includes(s));
    if(leaked) finalResponse=sanitized(r2,secrets);
    await write(id+'/parse-response.json',finalResponse);
    await write(id+'/parse-capture.json',{started_at:parseStart,ended_at:parseEnd,wall_ms:parseMs,input_sha256:f.input_sha256,settings:{formats:['markdown'],parsers:['pdf'],onlyMainContent:false,pdfOptions:{maxPages:f.input_page_count}},response_unmodified:!leaked,redaction_exception:leaked?'Provider echoed upload credential; secret exclusion takes priority over raw-response retention':null,reported:reported(p2)});
    const markdown=markdownFrom(p2),success=!r2.isError&&p2.success!==false&&!p2.error&&markdown!==null&&markdown.length>0;
    let exact=null;if(success)exact=await writeMarkdownExact(id,markdown);
    return {fixture_id:id,success,failure_stage:success?null:stage,reason:success?null:'Final response failed or lacked one nonempty document markdown string',started_at:started,ended_at:utc(),elapsed_ms:Date.now()-t,parse_wall_ms:parseMs,input_pages:f.input_page_count,input_sha256:f.input_sha256,exact_markdown_capture:exact,reported:reported(p2)};
  } catch(error) {
    // Exception text may contain upload tokens; do not persist or print it.
    return {fixture_id:id,success:false,failure_stage:stage,reason:'Operational exception',exception_class:error?.name||'UnknownError',started_at:started,ended_at:utc(),elapsed_ms:Date.now()-t};
  }
}
function launch(){const f=corpus.fixtures[submitted++];active.push({id:f.fixture_id,promise:runOne(f)});}
while(submitted<corpus.fixtures.length&&active.length<2)launch();
while(active.length){
  const result=await Promise.race(active.map(x=>x.promise));active=active.filter(x=>x.id!==result.fixture_id);
  result.completion_sequence=++completionSequence;consecutiveFailures=result.success?0:consecutiveFailures+1;
  result.consecutive_failures_after_completion=consecutiveFailures;outcomes.push(result);
  await write(result.fixture_id+'/outcome.json',result);
  notify(result.fixture_id+': '+(result.success?'captured markdown':'operational failure at '+result.failure_stage));
  if(consecutiveFailures>=3)stopped=true;
  if(!stopped&&submitted<corpus.fixtures.length)launch();
  await yield_control();
}
const skipped=corpus.fixtures.slice(submitted).map(f=>({fixture_id:f.fixture_id,reason:'Provider stopped after three consecutive operational failures'}));
await write('results.json',{ended_at:utc(),freeze_sha256:cfg.freeze_sha256,submitted,completed:outcomes.length,operational_successes:outcomes.filter(x=>x.success).length,operational_failures:outcomes.filter(x=>!x.success).length,stopped,completion_order_basis:'completed collection pipelines, including phase-one/upload failures; already-in-flight jobs are retained after stop',completion_order:outcomes.map(x=>x.fixture_id),outcomes,skipped});
text({completed:outcomes.length,operational_successes:outcomes.filter(x=>x.success).length,stopped,skipped:skipped.length});
