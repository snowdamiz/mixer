import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {harness,cleanup} from './harness.mjs';
const root=resolve(import.meta.dirname,'../../../..');
const base=JSON.parse(await readFile(resolve(root,'verification/hosted-worker-controller-contract/vectors.json'),'utf8')).cases[0].request;
const sha=s=>createHash('sha256').update(s).digest('hex');
const fixed={namespaceGeneration:'a'.repeat(64),environmentId:base.environment_id,poolId:base.pool_id,controllerId:base.controller_id,platform:base.ref.platform,operationKey:sha(JSON.stringify(['mixer-worker-controller-do-v1',base.environment_id,base.pool_id,base.controller_id,base.operation_id])),operationId:base.operation_id,immutableSha256:base.immutable_sha256};
const cases=[],results=[],observations={};
const test=(id,fn)=>cases.push({id,fn});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn){for(let i=0;i<100;i++){if(await fn())return;await sleep(4);}throw new Error('terminal_bounded_wait');}
const raw=h=>h.call('raw'),registry=h=>h.call('registry',{command:'raw'}),mode=(h,mode,skip=0)=>h.call('registry',{command:'mode',mode,skip});
async function registered(h){const x=await h.call('register');assert.ok(['registered','duplicate'].includes(x.status));h.receipt=x.receipt;}
const command=(h,command='ensure_started',guard={})=>h.call('command',{request:{...base,command,guard:{...base.guard,...guard}},receipt:h.receipt});
async function terminal(h,phase='stopped'){
 await registered(h);
 if(phase==='completed'){await command(h);assert.equal((await h.call('claim')).granted,true);assert.equal((await h.call('report')).status,'accepted');}
 await h.call('drain',{value:true});await mode(h,'drop_before_once',2);
 if(phase==='stopped')await command(h,'stop');else await h.call('reconcile');
 const b=await raw(h);assert.equal(b.row.phase,phase);assert.equal(JSON.parse(b.row.terminal_json).status,phase);assert.ok(b.row.track_outbox_json);assert.equal((await registry(h)).records[0].pending,1);return b;
}
const fields=['outboxPhase','rowPhase','rowAndOutboxPhase','terminalStatus','missingTerminal','missingProjectionTerminal','missingBothTerminal','pendingPhase','terminalNextDue','projectionNextDue','malformedTerminal','terminalArray','terminalNull','terminalUnknownStatus','terminalDuplicateStatus','terminalInvalidBody','exactJsonMismatch','projectionFalse','projectionMissingField','malformedOutbox','missingOutbox','malformedTerminalAndProvider'];
for(const phase of ['stopped','completed'])for(const boundary of ['snapshot','before_track','committed_ack'])for(const field of fields){
 test(`${phase}-${boundary}-${field}`,async h=>{
  const b=await terminal(h,phase),rec=(await registry(h)).records[0];let p;
  if(boundary==='before_track'){await h.call('inject',{point:'before_track'});p=h.call('flush');await until(async()=>(await raw(h)).settings.blocked);}
  if(boundary==='committed_ack'){await mode(h,'hold_after_once');p=h.call('flush');await until(async()=>(await registry(h)).settings.blocked);assert.equal((await registry(h)).records[0].pending,0);}
  await h.call('terminalMutation',{field});const restored=await raw(h);
  if(boundary==='before_track')await h.call('release');if(boundary==='committed_ack')await h.call('registry',{command:'release'});
  assert.deepEqual(await(p??h.call('flush')),{flushed:false});const a=await raw(h),remote=(await registry(h)).records[0];
  assert.deepEqual(a.row,restored.row);assert.equal(a.fence.length,1);assert.equal(a.fence[0].reason,'track_terminal_inconsistent');assert.equal(a.calls.length,b.calls.length);assert.equal(a.row.registry_ack_version,b.row.registry_ack_version);assert.equal(remote.pending,boundary==='committed_ack'?0:1);
  if(boundary!=='committed_ack')assert.equal(remote.state_version,rec.state_version);
  else{const projection=JSON.parse(remote.projection_json);assert.equal(projection.phase,phase);assert.equal(projection.evidenceSha256,sha(b.row.terminal_json));}
  observations[`${phase}-${boundary}-${field}`]={rowUnchanged:true,outboxRetained:a.row.track_outbox_json===restored.row.track_outbox_json,fence:a.fence,registryPending:remote.pending,remoteCancellationClaimed:false};
 });
}
for(const phase of ['stopped','completed'])for(const max of [false,true]){
 test(`${phase}-${max?'MAX':'normal'}-positive-exact-digest-and-independent-progress`,async h=>{
  await terminal(h,phase);if(max)await h.call('maxVersion');const b=await raw(h);
  await h.call('inject',{point:'before_track'});const p=h.call('flush');await until(async()=>(await raw(h)).settings.blocked);
  assert.deepEqual(await h.call('flush'),{flushed:true});await h.call('release');assert.deepEqual(await p,{flushed:false});
  let a=await raw(h);assert.equal(a.row.track_outbox_json,null);assert.equal(a.row.state_version,b.row.state_version);assert.equal(a.row.registry_ack_version,b.row.state_version);assert.equal(a.fence.length,0);
  const projection=JSON.parse((await registry(h)).records[0].projection_json);assert.equal(projection.phase,phase);assert.equal(projection.evidenceSha256,sha(b.row.terminal_json));assert.deepEqual(await h.call('flush'),{flushed:true});
  if(max){await h.call('repeatMaxOutbox');assert.deepEqual(await h.call('flush'),{flushed:true});}else{await command(h,'query',{epoch:'2',owner_id:'terminal-new-owner'});a=await raw(h);assert.ok(BigInt(a.row.state_version)>BigInt(b.row.state_version));assert.equal(a.row.track_outbox_json,null);assert.equal(a.row.terminal_json,b.row.terminal_json);}
 });
 for(const field of ['outboxPhase','malformedTerminal','malformedTerminalAndProvider'])for(const boundary of ['snapshot','committed_ack'])test(`${phase}-${max?'MAX':'normal'}-${boundary}-${field}-restore-hard-restart-fence`,async h=>{
  await terminal(h,phase);if(max)await h.call('maxVersion');const b=await raw(h);await h.call('rememberTerminal');let p;
  if(boundary==='committed_ack'){await mode(h,'hold_after_once');p=h.call('flush');await until(async()=>(await registry(h)).settings.blocked);}
  await h.call('terminalMutation',{field});const restored=await raw(h);if(p)await h.call('registry',{command:'release'});
  assert.deepEqual(await(p??h.call('flush')),{flushed:false});const fenced=await raw(h);assert.deepEqual(fenced.row,restored.row);assert.equal(fenced.row.quarantined,0);assert.equal(fenced.fence.length,1);
  await h.call('restoreTerminal');await h.restart(true);let a=await raw(h);assert.deepEqual(a.row,b.row);assert.deepEqual(a.fence,fenced.fence);assert.ok(a.alarm!==null);assert.deepEqual(await h.call('flush'),{flushed:false});assert.equal((await h.call('claim')).granted,false);assert.equal((await h.call('report')).status,'rejected');
  assert.deepEqual(await command(h,'query',{epoch:'2',owner_id:'terminal-restored-owner'}),{status:'error',code:'unavailable'});a=await raw(h);assert.deepEqual(a.row,b.row);assert.equal(a.calls.length,b.calls.length);
 });
}
for(const field of ['unexpectedTerminal','terminalPhaseWithoutEvidence'])test(`pending-${field}-presence-fails-closed`,async h=>{
 await registered(h);await mode(h,'unavailable');await command(h,'query');const b=await raw(h);assert.equal(b.row.terminal_json,null);await h.call('terminalMutation',{field});const restored=await raw(h);assert.deepEqual(await h.call('flush'),{flushed:false});const a=await raw(h);assert.deepEqual(a.row,restored.row);assert.equal(a.fence.length,1);assert.equal((await registry(h)).records[0].pending,1);
});
test('pending-null-terminal-positive-flow',async h=>{await registered(h);await mode(h,'unavailable');await command(h,'query');const b=await raw(h);assert.equal(JSON.parse(b.row.track_outbox_json).terminal,null);await mode(h,'normal');assert.deepEqual(await h.call('flush'),{flushed:true});assert.equal((await raw(h)).fence.length,0);assert.equal((await registry(h)).records[0].pending,1);});
for(const phase of ['stopped','completed'])test(`${phase}-post-ack-sync-terminal-mutation-fences-without-rewriting`,async h=>{await terminal(h,phase);const b=await raw(h);await h.call('terminalAckSyncMutation');assert.deepEqual(await h.call('flush'),{flushed:false});const a=await raw(h);assert.equal(a.fence.length,1);assert.equal(a.row.terminal_json,b.row.terminal_json);assert.equal(a.row.registry_ack_version,b.row.state_version);assert.equal(a.row.track_outbox_json,null);assert.equal(a.row.state_version,b.row.state_version);assert.equal((await registry(h)).records[0].pending,0);});
const selected=process.env.MIXER_TERMINAL_CASE,chosen=selected?cases.filter(c=>c.id===selected):cases;if(!chosen.length)throw new Error('unknown_terminal_case');
for(const c of chosen){let h;try{h=await harness(base,fixed);await c.fn(h);results.push({id:c.id,status:'passed'});}catch(e){results.push({id:c.id,status:'failed',error:e.stack??String(e)});}finally{if(h)try{await h.close();}catch(e){results.push({id:c.id+'-cleanup',status:'failed',error:e.stack??String(e)});}}console.log(JSON.stringify(results.at(-1)));}
const report={schema:1,status:results.every(r=>r.status==='passed')?'passed':'failed',scope:'Terminal consistency actual workerd SQLite finite excluded fixture',groupsDefined:cases.length,groupsRun:chosen.length,groupsPassed:results.filter(r=>r.status==='passed').length,results,observations,cleanup};
await writeFile(process.env.MIXER_TERMINAL_REPORT??resolve(import.meta.dirname,'../../terminal-report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,groupsRun:report.groupsRun,groupsPassed:report.groupsPassed}));if(report.status!=='passed')process.exitCode=1;
