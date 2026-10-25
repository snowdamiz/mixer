import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {harness,cleanup} from './harness.mjs';
const root=resolve(import.meta.dirname,'../../../..'),packet=resolve(import.meta.dirname,'../..');
const vectors=JSON.parse(await readFile(join(root,'verification/hosted-worker-pending-registry-contract/identity-vectors.json'),'utf8'));
const sha=s=>createHash('sha256').update(s).digest('hex');
const generation='a'.repeat(64),hashB='b'.repeat(64),pending={kind:'pending',nextDueUs:null};
function make(n,fields={}){const v={namespaceGeneration:generation,environmentId:'components',poolId:'pool',controllerId:'controller',platform:'android',operationId:sha('component-'+n),immutableSha256:hashB,...fields};v.operationKey=sha(JSON.stringify(['mixer-worker-controller-do-v1',v.environmentId,v.poolId,v.controllerId,v.operationId]));return v;}
function bucket(n,count,fields={}){const a=[];for(let i=0;a.length<count;i++){const v=make(n+'-'+i,fields);if(parseInt(v.operationKey[0],16)===n%16)a.push(v);}return a;}
const shard=i=>parseInt(i.operationKey[0],16);
async function reg(h,i){const r=await h.call('register',{shard:shard(i),identity:i});assert(['registered','duplicate'].includes(r.status),JSON.stringify(r));return r.receipt;}
const inspect=(h,r)=>h.call('registryInspect',{shard:r.shard,recordId:r.recordId});
const track=(h,r,v,p=pending)=>h.call('track',{shard:r.shard,input:{receipt:r,stateVersion:v,projection:p}});
const scan=(h,s,after=0,limit=32)=>h.call('scan',{shard:s,cursor:{afterAllocationIndex:after},limit});
const reserve=(h,r,v,runId)=>h.call('reserve',{shard:r.shard,recordId:r.recordId,version:v,runId});
const finish=(h,t,d)=>h.call('finish',{shard:t.receipt.shard,ticket:t,disposition:d});
const pause=ms=>new Promise(r=>setTimeout(r,ms));
async function eventually(fn){for(let i=0;i<100;i++){if(await fn())return;await pause(10);}throw new Error('fixture_poll_timeout');}
const cases=[];const test=(id,fn)=>cases.push({id,fn});
const observations={};

test('canonical-17-vectors-and-closed-identities',async h=>{
 assert.equal(vectors.valid.length,17);for(const v of vectors.valid){const r=await h.call('hash',{identity:v.identity});assert.equal(r.digest,v.identity_digest);assert.equal(Buffer.from(r.bytes).toString('hex'),v.identity_bytes_hex);assert.equal(r.shard,v.shard);const receipt=await reg(h,v.identity);assert.equal(receipt.shard,v.shard);assert.match(receipt.recordId,/^[0-9a-f]{32}$/);}
 assert.equal(new Set(vectors.valid.map(v=>v.shard)).size,16);
 for(const v of vectors.invalid){const r=await h.call('register',{shard:0,identity:v.identity});assert.equal(r.status,'conflict');}
 const base=vectors.valid[0].identity;for(const v of [{...base,namespaceGeneration:'c'.repeat(64)},{...base,platform:'linux'},{...base,environmentId:'x'.repeat(129)},{...base,environmentId:'e\u0301'},{...base,operationKey:'d'.repeat(64)}])assert.equal((await h.call('register',{shard:0,identity:v})).status,'conflict');
 assert.equal((await h.call('register',{shard:1,identity:base})).status,'conflict');assert.equal((await h.call('registryInspect',{shard:0,recordId:null})).count[0].n,1);
 observations.identityVectors=17;
});

test('durable-registration-lost-ACK-and-precommit-SIGKILL',async h=>{
 const i=bucket(0,1)[0];await h.call('registryConfigure',{shard:0,setting:{mode:'register_before_hold',milliseconds:0}});
 const pre=h.call('register',{shard:0,identity:i}).catch(()=>null);await pause(60);assert.equal((await h.call('registryInspect',{shard:0,recordId:null})).count[0].n,0);await h.restart(true);await pre;
 await h.call('registryConfigure',{shard:0,setting:{mode:'register_ack_hold',milliseconds:0}});const ack=h.call('register',{shard:0,identity:i}).catch(()=>null);let before;
 await eventually(async()=>{const p=await scan(h,0);if(p.records?.length){before=p.records[0].receipt;return true;}return false;});
 await h.restart(true);await ack;await h.call('registryConfigure',{shard:0,setting:{mode:'none',milliseconds:0}});const after=await h.call('register',{shard:0,identity:i});assert.equal(after.status,'duplicate');assert.deepEqual(after.receipt,before);assert.equal((await inspect(h,before)).meta[0].allocated,1);observations.lostRegistrationReceipt=before;
});

test('TEXT-versions-order-conflict-retention-and-track-lost-ACK',async h=>{
 const i=bucket(0,1)[0],r=await reg(h,i);await h.call('registryConfigure',{shard:0,setting:{mode:'track_ack_hold',milliseconds:0}});const p=track(h,r,'9007199254740993').catch(()=>null);await eventually(async()=>(await inspect(h,r)).row.state_version==='9007199254740993');await h.restart(true);await p;await h.call('registryConfigure',{shard:0,setting:{mode:'none',milliseconds:0}});
 assert.deepEqual(await track(h,r,'9007199254740993'),{status:'duplicate',stateVersion:'9007199254740993'});assert.deepEqual(await track(h,r,'9007199254740992'),{status:'stale',stateVersion:'9007199254740993'});assert.equal((await track(h,r,'9007199254740993',{kind:'pending',nextDueUs:'9223372036854775807'})).status,'conflict');
 for(const version of ['9007199254740994','9223372036854775807'])assert.equal((await track(h,r,version,{kind:'pending',nextDueUs:'9223372036854775807'})).status,'accepted');
 assert.equal((await track(h,r,'9223372036854775808')).status,'conflict');assert.equal((await track(h,r,'01')).status,'conflict');assert.equal((await inspect(h,r)).row.version_type,'text');assert.equal((await scan(h,0)).records.length,1);
 const j=bucket(1,1)[0],s=await reg(h,j),t=(await reserve(h,s,'0','1')).ticket;const terminal={kind:'terminal',nextDueUs:null,phase:'stopped',evidenceSha256:sha('{"terminal":"exact fixture bytes"}')};await h.call('registryConfigure',{shard:1,setting:{mode:'track_ack_hold',milliseconds:0}});const lostTerminal=track(h,s,'1',terminal).catch(()=>null);await eventually(async()=>(await inspect(h,s)).row.pending===0);await h.restart(true);await lostTerminal;await h.call('registryConfigure',{shard:1,setting:{mode:'none',milliseconds:0}});assert.equal((await track(h,s,'1',terminal)).status,'duplicate');assert.equal(await finish(h,t,{status:'pending',stateVersion:'0'}),'stale');assert.equal((await track(h,s,'2')).status,'conflict');assert.equal((await scan(h,1)).records.length,0);await h.restart(true);assert.equal((await reg(h,j)).recordId,s.recordId);assert.equal((await inspect(h,s)).row.pending,0);assert.equal((await track(h,s,'1',terminal)).status,'duplicate');assert.equal((await inspect(h,s)).meta[0].allocated,1);
 const diff={...i,immutableSha256:'c'.repeat(64)};assert.equal((await h.call('register',{shard:0,identity:diff})).status,'conflict');
});

test('scan-pure-reserve-backoff-dedup-and-stale-CAS',async h=>{
 const r=await reg(h,bucket(0,1)[0]);let run=1;let q=await reserve(h,r,'0',String(run++));assert.equal(q.status,'reserved');const t=q.ticket;assert.equal(await finish(h,t,{status:'empty_orphan'}),'accepted');
 const before=(await inspect(h,r)).row;assert.equal(before.skip_visits,1);for(let n=0;n<4;n++)await scan(h,0);assert.deepEqual((await inspect(h,r)).row,before);
 const id=String(run++);assert.equal((await reserve(h,r,'0',id)).status,'backoff');assert.equal((await reserve(h,r,'0',id)).status,'duplicate');assert.equal((await inspect(h,r)).row.skip_visits,0);const newer=(await reserve(h,r,'0',String(run++))).ticket;assert.equal(await finish(h,t,{status:'pending',stateVersion:'0'}),'stale');assert.equal((await reserve(h,r,'0','1')).status,'duplicate');
 assert.equal((await track(h,r,'1')).status,'accepted');assert.equal(await finish(h,newer,{status:'pending',stateVersion:'1'}),'stale');assert.equal((await reserve(h,r,'0',String(run++))).status,'stale');const fresh=(await reserve(h,r,'1',String(run++))).ticket;assert.equal(await finish(h,{...fresh,extra:true},{status:'unavailable'}),'unavailable');assert.equal(await finish(h,fresh,{status:'pending',stateVersion:'1',extra:true}),'unavailable');assert.equal(await finish(h,fresh,{status:'pending',stateVersion:'1'}),'accepted');assert.equal(await finish(h,fresh,{status:'unavailable'}),'stale');
 assert.equal((await inspect(h,r)).row.failures,0);
});

test('failure-saturation-permanent-attention-and-counter-overflow',async h=>{
 const r=await reg(h,bucket(0,1)[0]);let run=1,attempts=0,visits=0,maxGap=0,gap=0;
 while(attempts<35){const q=await reserve(h,r,'0',String(run++));visits++;gap++;if(q.status==='reserved'){maxGap=Math.max(maxGap,gap);gap=0;attempts++;assert.equal(await finish(h,q.ticket,{status:'empty_orphan'}),'accepted');const x=(await inspect(h,r)).row;assert.equal(x.failures,Math.min(attempts,32));assert.equal(x.needs_attention,attempts>=8?1:0);assert(x.skip_visits<=7);}else assert.equal(q.status,'backoff');}
 assert.equal(maxGap,8);let q;do{q=await reserve(h,r,'0',String(run++));}while(q.status==='backoff');assert.equal(await finish(h,q.ticket,{status:'pending',stateVersion:'0'}),'accepted');assert.equal((await inspect(h,r)).row.needs_attention,0);
 await h.call('registryMax',{shard:0,recordId:r.recordId});const before=(await inspect(h,r)).row;assert.equal((await reserve(h,r,'0',String(run++))).status,'unavailable');assert.deepEqual((await inspect(h,r)).row,before);await h.restart(true);assert.equal((await inspect(h,r)).row.attempt_sequence,'9223372036854775807');observations.attention={attempts,visits,maxGap};
});

test('32-record-page-wrap-and-maximum-legal-bytes',async h=>{
 const values=bucket(0,34,{environmentId:'"'.repeat(128),poolId:'\\'.repeat(128),controllerId:'x'.repeat(128)});const receipts=[];for(const i of values)receipts.push(await reg(h,i));assert.equal((await scan(h,0)).records.length,32);
 const p=await scan(h,0,30);assert.equal(p.wrapped,true);assert.deepEqual(p.records.map(r=>r.receipt.allocationIndex),[31,32,33,34,...Array.from({length:28},(_,n)=>n+1)]);assert.equal(new Set(p.records.map(r=>r.receipt.allocationIndex)).size,32);const bytes=Buffer.byteLength(JSON.stringify(p));assert(bytes<=65536);observations.maximumLegalPageBytes=bytes;
 assert.equal((await scan(h,0,34,1)).records[0].receipt.allocationIndex,1);assert.equal((await h.call('scan',{shard:0,cursor:{afterAllocationIndex:0},limit:33})).rejected,true);
});

test('fixed-4096-capacity-permanent-slots-existing-track-and-audit',async h=>{
 const values=bucket(0,4097);let last;for(let n=0;n<4096;n+=64){const list=await h.call('registerBatch',{shard:0,identities:values.slice(n,n+64)});assert.equal(list.length,64);for(const x of list)assert.equal(x.status,'registered');last=list.at(-1).receipt;}
 assert.equal(last.allocationIndex,4096);assert.equal((await h.call('register',{shard:0,identity:values[4095]})).status,'duplicate');assert.equal((await h.call('register',{shard:0,identity:values[4096]})).status,'capacity');assert.equal((await inspect(h,last)).meta[0].allocated,4096);
 const term={kind:'terminal',nextDueUs:null,phase:'completed',evidenceSha256:hashB};assert.equal((await track(h,last,'1',term)).status,'accepted');assert.equal((await track(h,last,'1',term)).status,'duplicate');const p=await scan(h,0,4094);assert.equal(p.records[0].receipt.allocationIndex,4095);assert.equal(p.records[1].receipt.allocationIndex,1);const a=await h.call('audit');assert.equal(a.wakesStarted,8);assert.equal((await h.call('register',{shard:0,identity:values[4096]})).status,'capacity');await h.restart(true);assert.equal((await inspect(h,last)).count[0].n,4096);observations.capacity={accepted:4096,overflow:'capacity',retainedAfterRestart:4096};
});

test('all-16-shard-fair-cursors-eight-wakes-and-independent-scheduled-entry',async h=>{
 assert.equal(await h.publicFetch(),404);const all=[];for(let s=0;s<16;s++){const a=bucket(s,33);for(const i of a){const r=await reg(h,i);all.push({i,r});}}
 let starts=0;for(let n=0;n<80;n++){const result=await h.scheduled();assert.equal(result.outcome,'ok');const raw=await h.call('auditInspect'),current=JSON.parse(raw.meta[0].current_json).summary;assert(current.pages<=16&&current.examined<=512&&current.wakesStarted<=8);assert.equal(current.wakesStarted,8);assert.equal(raw.meta[0].next_shard,(n+1)%16);starts+=current.wakesStarted;if(n===0){assert.equal(JSON.parse(raw.meta[0].cursors)[0],8);assert.equal((await h.call('recoveryInspect',{operationKey:all[8].i.operationKey})).calls,0);}if(n===19)await h.restart(true);}
 for(const {i} of all)assert((await h.call('recoveryInspect',{operationKey:i.operationKey})).calls>=1);const raw=await h.call('auditInspect');assert.equal(raw.ring.length,32);observations.fairness={population:528,scheduledInvocations:80,totalStarts:starts,allVisited:true};
});

test('automatic-orphan-attention-revisit-success-with-no-customer-HTTP',async h=>{
 const i=bucket(0,1)[0],r=await reg(h,i);await h.call('recoveryConfigure',{operationKey:i.operationKey,mode:'empty_orphan'});for(let n=0;n<50;n++)await h.scheduled();const row=(await inspect(h,r)).row;assert(row.failures>=8);assert.equal(row.needs_attention,1);const before=(await h.call('recoveryInspect',{operationKey:i.operationKey})).calls;assert(before>=8);await h.call('recoveryConfigure',{operationKey:i.operationKey,mode:'pending'});for(let n=0;n<8;n++)await h.scheduled();assert((await h.call('recoveryInspect',{operationKey:i.operationKey})).calls>before);assert.equal((await inspect(h,r)).row.failures,0);assert.equal((await inspect(h,r)).row.pending,1);
});

test('noncooperative-timeout-live-busy-real-interruption-and-later-settlement',async h=>{
 const values=bucket(0,9);const r=await reg(h,values[0]);for(const i of values.slice(1))await reg(h,i);await h.call('recoveryConfigure',{operationKey:values[0].operationKey,mode:'hold'});
 const start=performance.now(),running=h.call('audit');await eventually(async()=>(await h.call('recoveryInspect',{operationKey:values[0].operationKey})).calls===1);assert.equal((await h.call('audit')).status,'busy');const result=await running,elapsed=performance.now()-start;assert.equal(result.wakesStarted,1);assert.equal(result.status,'bounded');assert(result.needsAttention);assert(elapsed>=2400&&elapsed<4000);assert.equal((await h.call('audit')).status,'busy');assert.equal((await h.call('recoveryInspect',{operationKey:values[1].operationKey})).calls,0);assert.equal((await inspect(h,r)).row.disposition_json,null);
 await h.call('recoveryRelease',{operationKey:values[0].operationKey});await eventually(async()=>(await h.call('recoveryInspect',{operationKey:values[0].operationKey})).settled===1);assert.notEqual((await h.call('audit')).status,'busy');assert.equal((await inspect(h,r)).row.disposition_json,null);observations.noncooperative={elapsed,wakesStarted:1,settlementObserved:true,timeoutWasNotCancellation:true};
 // Actual SIGKILL while a run is in progress: cursor/ticket persist, no claimed cancellation.
 const j=bucket(1,1)[0],s=await reg(h,j);await h.call('recoveryConfigure',{operationKey:j.operationKey,mode:'hold'});const interrupted=h.call('audit').catch(()=>null);await eventually(async()=>(await h.call('recoveryInspect',{operationKey:j.operationKey})).calls===1);const before=await h.call('auditInspect');assert.equal(JSON.parse(before.meta[0].current_json).interrupted,true);await h.restart(true);await interrupted;const after=await h.call('auditInspect');assert.deepEqual(JSON.parse(after.meta[0].cursors),JSON.parse(before.meta[0].cursors));await h.call('recoveryConfigure',{operationKey:j.operationKey,mode:'pending'});await h.call('audit');assert((await inspect(h,s)).row.pending===1);assert((await h.call('auditInspect')).ring.some(x=>JSON.parse(x.receipt_json).interrupted));
});

test('shard-outage-reserve-finish-timeouts-and-schema-config-fences',async h=>{
 const a=bucket(0,1)[0],b=bucket(1,1)[0],r=await reg(h,a),s=await reg(h,b);await h.call('registryConfigure',{shard:0,setting:{mode:'scan_delay',milliseconds:350}});const out=await h.call('audit');assert(out.needsAttention);assert.equal((await h.call('recoveryInspect',{operationKey:b.operationKey})).calls,1);let raw=await h.call('auditInspect');assert.equal(JSON.parse(raw.meta[0].cursors)[0],0);await h.call('registryConfigure',{shard:0,setting:{mode:'none',milliseconds:0}});
 await h.call('registryConfigure',{shard:0,setting:{mode:'reserve_ack_delay',milliseconds:350}});const reservation=await h.call('audit');assert(reservation.needsAttention);assert.equal((await h.call('recoveryInspect',{operationKey:a.operationKey})).calls,0);assert((await inspect(h,r)).row.ticket_json);assert.equal((await inspect(h,r)).row.disposition_json,null);await pause(120);await h.call('registryConfigure',{shard:0,setting:{mode:'finish_ack_delay',milliseconds:350}});const finishResult=await h.call('audit');assert(finishResult.needsAttention);assert((await h.call('recoveryInspect',{operationKey:a.operationKey})).calls>=1);assert((await inspect(h,r)).row.disposition_json);assert((await h.call('auditInspect')).completions[0].value);await pause(120);await h.call('registryConfigure',{shard:0,setting:{mode:'none',milliseconds:0}});await h.call('audit');assert.equal((await h.call('auditInspect')).completions[0].value,null);
 await h.call('registryConflict',{shard:0});await h.restart(true);assert.equal((await h.call('register',{shard:0,identity:a})).status,'unavailable');assert.equal((await track(h,r,'1')).status,'unavailable');assert.equal((await scan(h,0)).rejected,true);assert.equal((await reg(h,b)).recordId,s.recordId);
});

test('late-unavailable-and-rejection-retained-through-attention-and-success',async h=>{
 const i=bucket(0,1)[0],r=await reg(h,i);let attempts=0;
 for(let failures=1;failures<=8;failures++){
  await h.call('recoveryConfigure',{operationKey:i.operationKey,mode:failures%2?'hold_unavailable':'hold_reject'});
  let result;for(let visits=0;visits<8;visits++){result=await h.call('audit');if(result.wakesStarted===1)break;assert.equal(result.wakesStarted,0);}assert.equal(result.wakesStarted,1);attempts++;
  assert.equal((await inspect(h,r)).row.failures,failures-1);assert.equal((await h.call('recoveryInspect',{operationKey:i.operationKey})).settled,attempts-1);
  await h.call('recoveryRelease',{operationKey:i.operationKey});await eventually(async()=>(await h.call('recoveryInspect',{operationKey:i.operationKey})).settled===attempts);await eventually(async()=>(await h.call('auditInspect')).completions[0].value!==null);
  const saved=(await h.call('auditInspect')).completions[0].value;assert(Buffer.byteLength(saved)<=2048);assert.equal(JSON.parse(saved).disposition.status,'unavailable');
  if(failures===1){await h.restart(true);assert.equal((await h.call('auditInspect')).completions[0].value,saved);}
  const finishResult=await h.call('audit');assert.equal(finishResult.wakesStarted,0);const row=(await inspect(h,r)).row;assert.equal(row.failures,failures);assert.equal(row.needs_attention,failures>=8?1:0);assert.equal((await h.call('auditInspect')).completions[0].value,null);
 }
 await h.call('recoveryConfigure',{operationKey:i.operationKey,mode:'pending'});for(let visits=0;visits<8;visits++)await h.call('audit');assert.equal((await inspect(h,r)).row.failures,0);assert.equal((await inspect(h,r)).row.needs_attention,0);observations.lateCompletions={knownUnavailableOrRejected:8,attentionReached:true,durableRestart:true,automaticSuccess:true,slotCount:16,slotByteCap:2048};
});

test('completion-local-write-and-clear-failures-retain-exact-CAS',async h=>{
 const i=bucket(0,1)[0],r=await reg(h,i);await h.call('recoveryConfigure',{operationKey:i.operationKey,mode:'hold_unavailable'});await h.call('auditCompletionFault',{mode:'write'});assert.equal((await h.call('audit')).wakesStarted,1);await h.call('recoveryRelease',{operationKey:i.operationKey});await eventually(async()=>(await h.call('recoveryInspect',{operationKey:i.operationKey})).settled===1);
 assert.equal((await h.call('auditInspect')).completions[0].value,null);assert.equal((await h.call('audit')).status,'unavailable');assert.equal((await inspect(h,r)).row.failures,0);assert.equal((await h.call('recoveryInspect',{operationKey:i.operationKey})).calls,1);
 await h.call('auditCompletionFault',{mode:'clear'});assert.equal((await h.call('audit')).status,'unavailable');const saved=(await h.call('auditInspect')).completions[0].value;assert(saved);assert.equal((await inspect(h,r)).row.failures,1);await h.restart(true);assert.equal((await h.call('auditInspect')).completions[0].value,saved);await h.call('auditCompletionFault',{mode:'none'});const result=await h.call('audit');assert.equal(result.wakesStarted,0);assert.equal((await inspect(h,r)).row.failures,1);assert.equal((await h.call('auditInspect')).completions[0].value,null);observations.completionLocalFailures={actualSQLiteWriteAbort:true,memoryFallbackReplayed:true,actualSQLiteClearAbort:true,finishNotDoubleCounted:true,restartRetained:true};
});

test('completion-unavailable-shard-preserves-healthy-progress-and-newer-terminal',async h=>{
 const i=bucket(0,1)[0],r=await reg(h,i);await h.call('recoveryConfigure',{operationKey:i.operationKey,mode:'hold_unavailable'});assert.equal((await h.call('audit')).wakesStarted,1);await h.call('recoveryRelease',{operationKey:i.operationKey});await eventually(async()=>(await h.call('auditInspect')).completions[0].value!==null);
 await h.call('registryConfigure',{shard:0,setting:{mode:'finish_before_throw',milliseconds:0}});const j=bucket(1,1)[0];await reg(h,j);const cursor=JSON.parse((await h.call('auditInspect')).meta[0].cursors)[0];for(let n=0;n<3;n++){const result=await h.call('audit');assert(result.needsAttention);assert.equal(result.wakesStarted,1);assert.equal(JSON.parse((await h.call('auditInspect')).meta[0].cursors)[0],cursor);assert((await h.call('auditInspect')).completions[0].value);}
 assert.equal((await h.call('recoveryInspect',{operationKey:i.operationKey})).calls,1);assert.equal((await h.call('recoveryInspect',{operationKey:j.operationKey})).calls,3);
 const terminal={kind:'terminal',nextDueUs:null,phase:'stopped',evidenceSha256:hashB};assert.equal((await track(h,r,'1',terminal)).status,'accepted');await h.call('registryConfigure',{shard:0,setting:{mode:'none',milliseconds:0}});await h.restart(true);await h.call('audit');assert.equal((await h.call('auditInspect')).completions[0].value,null);const row=(await inspect(h,r)).row;assert.equal(row.pending,0);assert.equal(row.state_version,'1');assert.equal(row.failures,0);assert.equal((await h.call('recoveryInspect',{operationKey:i.operationKey})).calls,1);observations.shardCompletionBackpressure={unavailableShardStarts:1,healthyShardStarts:3,staleTerminalCleared:true};
});

test('sixteen-pages-512-examinations-with-reserve-only-backoff',async h=>{
 for(let s=0;s<16;s++){const values=bucket(s,32);for(const i of values){const r=await reg(h,i),q=await reserve(h,r,'0','0');assert.equal(q.status,'reserved');assert.equal(await finish(h,q.ticket,{status:'empty_orphan'}),'accepted');}}
 const result=await h.call('audit');assert.equal(result.pages,16);assert.equal(result.examined,512);assert.equal(result.wakesStarted,0);assert.equal(result.status,'finished');observations.fullTraversal={pages:16,examined:512,wakes:0};
});

test('shared-24000ms-budget-counts-reserve-storage-waits',async h=>{
 for(let s=0;s<16;s++){const values=bucket(s,32);for(const i of values){const r=await reg(h,i),q=await reserve(h,r,'0','0');assert.equal(await finish(h,q.ticket,{status:'empty_orphan'}),'accepted');}await h.call('registryConfigure',{shard:s,setting:{mode:'reserve_ack_delay',milliseconds:220}});}
 const start=performance.now(),result=await h.call('audit'),elapsed=performance.now()-start;assert.equal(result.status,'bounded');assert.equal(result.wakesStarted,0);assert(result.examined<512&&result.examined>32);assert(elapsed>=20000&&elapsed<24000);observations.elapsedBudget={elapsedMs:elapsed,examined:result.examined,pages:result.pages,wakes:result.wakesStarted,registryWaitMs:220,maximumMs:24000};
});

test('audit-run-TEXT-max-fails-closed-and-empty-page-caps',async h=>{
 const result=await h.call('audit');assert.equal(result.pages,16);assert.equal(result.wakesStarted,0);assert.equal(result.examined,0);assert.equal(result.status,'finished');await h.call('auditMax');const before=await h.call('auditInspect');assert.equal((await h.call('audit')).status,'unavailable');const after=await h.call('auditInspect');assert.equal(after.meta[0].run_sequence,'9223372036854775807');assert.deepEqual(after.meta[0].cursors,before.meta[0].cursors);await h.restart(true);assert.equal((await h.call('audit')).status,'unavailable');
});

const results=[];let failed=false;const output=process.env.MIXER_PENDING_REPORT??join(packet,'test-report.json');
for(const {id,fn} of cases){let h;const started=performance.now();try{h=await harness();await fn(h);results.push({id,status:'passed',elapsedMs:performance.now()-started});console.log(JSON.stringify(results.at(-1)));}catch(e){failed=true;results.push({id,status:'failed',error:e.stack,elapsedMs:performance.now()-started});console.error(JSON.stringify(results.at(-1)));break;}finally{if(h)try{await h.close();}catch(e){failed=true;results.push({id:id+'-cleanup',status:'failed',error:e.stack});}}}
await writeFile(output,JSON.stringify({status:failed?'failed':'passed',scope:'actual-isolated-workerd-cross-DO-SQLite-components-with-excluded-synthetic-recovery-only',results,observations,cleanup,limitations:['real operation preregistration/outbox/barriers/recoverKnown and migration NOT implemented or qualified','no live scheduled entry wiring/deployed cron; excluded scheduled event only','no production provider/clock/auth ingress/restore/native/GA qualification','existing 20 identity + 71 controller groups unchanged; root coordinates their regression run']},null,2)+'\n');process.exitCode=failed?1:0;
