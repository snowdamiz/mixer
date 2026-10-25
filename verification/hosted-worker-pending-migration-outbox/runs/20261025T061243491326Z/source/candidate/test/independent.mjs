import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {harness,cleanup} from './harness.mjs';
const root=resolve(import.meta.dirname,'../../../..');
const base=JSON.parse(await readFile(resolve(root,'verification/hosted-worker-controller-contract/vectors.json'),'utf8')).cases[0].request;
const sha=x=>createHash('sha256').update(x).digest('hex');
const fixed={namespaceGeneration:'a'.repeat(64),environmentId:base.environment_id,poolId:base.pool_id,controllerId:base.controller_id,platform:base.ref.platform,operationKey:sha(JSON.stringify(['mixer-worker-controller-do-v1',base.environment_id,base.pool_id,base.controller_id,base.operation_id])),operationId:base.operation_id,immutableSha256:base.immutable_sha256};
const cases=[],results=[],observations={};let current='';
const test=(id,fn)=>cases.push({id,fn});
const raw=h=>h.call('raw'),registry=h=>h.call('registry',{command:'raw'}),mode=(h,mode,skip=0)=>h.call('registry',{command:'mode',mode,skip});
const note=x=>observations[current]={...observations[current],...x};
async function until(f){for(let i=0;i<100;i++){if(await f())return;await new Promise(r=>setTimeout(r,4));}throw new Error('review_bounded_wait_exhausted');}
async function registered(h){const v=await h.call('register');assert.equal(v.status,'registered');h.receipt=v.receipt;}
const request=(command='query',guard={})=>({...base,command,guard:{...base.guard,...guard}});
const command=(h,cmd='ensure_started',guard={})=>h.call('command',{request:request(cmd,guard),receipt:h.receipt});
async function terminal(h,phase='stopped'){
 await registered(h);
 if(phase==='completed'){await command(h);assert.equal((await h.call('claim')).granted,true);assert.equal((await h.call('report')).status,'accepted');}
 await h.call('drain',{value:true});await mode(h,'drop_before_once',2);
 if(phase==='stopped')assert.equal((await command(h,'stop')).status,'stopped');else await h.call('reconcile');
 const s=await raw(h);assert.equal(s.row.phase,phase);assert.equal(JSON.parse(s.row.terminal_json).status,phase);assert.ok(s.row.track_outbox_json);assert.equal((await registry(h)).records[0].pending,1);return s;
}
async function reserve(h){const r=(await registry(h)).records[0],v=await h.call('reserve',{recordId:h.receipt.recordId,version:r.state_version,runId:'1'});assert.equal(v.status,'reserved');return v.ticket;}

// Independently authored driver: none of the producer's 400 test bodies run.
for(const phase of ['stopped','completed'])for(const max of [false,true])for(const boundary of ['beforeSnapshot','beforeRPC','remoteCommitted'])test(`${phase}-${max?'MAX':'ordinary'}-${boundary}-original-phase-regression`,async h=>{
 await terminal(h,phase);if(max)await h.call('maxVersion');const good=await raw(h),remoteBefore=(await registry(h)).records[0];let pending;
 if(boundary==='beforeRPC'){await h.call('inject',{point:'before_track'});pending=h.call('flush');await until(async()=>(await raw(h)).settings.blocked);}
 if(boundary==='remoteCommitted'){await mode(h,'hold_after_once');pending=h.call('flush');await until(async()=>(await registry(h)).settings.blocked);assert.equal((await registry(h)).records[0].pending,0);}
 await h.call('terminalMutation',{field:'outboxPhase'});const corrupt=await raw(h);
 if(boundary==='beforeRPC')await h.call('release');if(boundary==='remoteCommitted')await h.call('registry',{command:'release'});
 assert.deepEqual(await(pending??h.call('flush')),{flushed:false});const after=await raw(h),remote=(await registry(h)).records[0];
 assert.deepEqual(after.row,corrupt.row);assert.equal(after.fence[0].reason,'track_terminal_inconsistent');assert.equal(after.fence.length,1);assert.equal(after.calls.length,good.calls.length);
 if(boundary==='remoteCommitted'){assert.equal(remote.pending,0);const p=JSON.parse(remote.projection_json);assert.equal(p.phase,phase);assert.equal(p.evidenceSha256,sha(good.row.terminal_json));}else assert.deepEqual(remote,remoteBefore);
 note({good,corrupt,after,remote,remoteCommitRollbackClaimed:false});
});
for(const phase of ['stopped','completed'])for(const max of [false,true])for(const entry of ['registered','plain','constructor','quarantine','enroll','recovery','claim','report','reconcile'])test(`${phase}-${max?'MAX':'ordinary'}-malformed-plus-provider-${entry}`,async h=>{
 await terminal(h,phase);if(max)await h.call('maxVersion');const ticket=entry==='recovery'?await reserve(h):null;
 await h.call('terminalMutation',{field:'malformedTerminalAndProvider'});const before=await raw(h);
 if(entry==='registered')assert.deepEqual(await command(h,'query',{epoch:'2',owner_id:'independent-new-owner'}),{status:'error',code:'unavailable'});
 if(entry==='plain')assert.deepEqual(await h.call('plain',{request:request('query',{epoch:'2',owner_id:'independent-new-owner'})}),{status:'error',code:'unavailable'});
 if(entry==='constructor')await h.restart(true);
 if(entry==='quarantine')await h.call('quarantine');if(entry==='enroll')assert.equal((await h.call('enroll')).status,'conflict');
 if(entry==='recovery')assert.equal((await h.call('recoverKnown',{receipt:h.receipt,ticket})).status,'quarantined');
 if(entry==='claim')assert.equal((await h.call('claim')).granted,false);if(entry==='report')assert.equal((await h.call('independentValidShapeReport')).status,'rejected');if(entry==='reconcile')await h.call('reconcile');
 const after=await raw(h);assert.deepEqual(after.row,before.row);assert.equal(after.fence.length,1);assert.equal(after.fence[0].reason,'track_terminal_inconsistent');assert.equal(after.calls.length,before.calls.length);note({before,after});
});
for(const kind of ['escapedDuplicate','extraTerminalField','duplicateResult','tooManyBytes'])test(`strict-exact-terminal-parser-${kind}`,async h=>{
 await terminal(h,kind==='duplicateResult'?'completed':'stopped');await h.call('independentTerminalBytes',{kind});const before=await raw(h);assert.deepEqual(await h.call('flush'),{flushed:false});const after=await raw(h);assert.deepEqual(after.row,before.row);assert.equal(after.fence[0].reason,'track_terminal_inconsistent');assert.equal((await registry(h)).records[0].pending,1);note({before,after});
});
test('valid-escaped-and-reordered-terminal-bytes-hash-without-normalization',async h=>{
 await terminal(h);await h.call('independentTerminalBytes',{kind:'validEscapedStatus'});const before=await raw(h);assert.deepEqual(JSON.parse(before.row.terminal_json),{status:'stopped',diagnostic_sha256:'d'.repeat(64)});assert.deepEqual(await h.call('flush'),{flushed:true});const after=await raw(h),remote=(await registry(h)).records[0];assert.equal(after.row.terminal_json,before.row.terminal_json);assert.equal(after.fence.length,0);assert.equal(JSON.parse(remote.projection_json).evidenceSha256,sha(before.row.terminal_json));assert.notEqual(sha(before.row.terminal_json),sha(JSON.stringify(JSON.parse(before.row.terminal_json))));note({before,after,remote});
});
for(const phase of ['stopped','completed'])test(`${phase}-same-version-independent-ACK`,async h=>{
 await terminal(h,phase);const before=await raw(h);await mode(h,'hold_after_once');const old=h.call('flush');await until(async()=>(await registry(h)).settings.blocked);assert.deepEqual(await h.call('flush'),{flushed:true});const independent=await raw(h);await h.call('registry',{command:'release'});assert.deepEqual(await old,{flushed:false});const after=await raw(h);assert.deepEqual(after.row,independent.row);assert.equal(after.row.state_version,before.row.state_version);assert.equal(after.row.registry_ack_version,before.row.state_version);assert.equal(after.row.track_outbox_json,null);assert.equal(after.fence.length,0);note({before,independent,after});
});
for(const phase of ['stopped','completed'])test(`${phase}-newer-version-terminal-replay-during-old-ACK`,async h=>{
 await terminal(h,phase);const before=await raw(h);await mode(h,'hold_after_once');const old=h.call('flush');await until(async()=>(await registry(h)).settings.blocked);
 assert.equal((await command(h,'query',{epoch:'2',owner_id:'independent-replay-owner'})).status,phase);const newer=await raw(h);assert.ok(BigInt(newer.row.state_version)>BigInt(before.row.state_version));assert.equal(newer.row.track_outbox_json,null);await h.call('registry',{command:'release'});assert.deepEqual(await old,{flushed:false});const after=await raw(h);assert.deepEqual(after.row,newer.row);assert.equal(after.fence.length,0);const remote=(await registry(h)).records[0];assert.equal(remote.state_version,newer.row.state_version);assert.equal(remote.pending,0);assert.equal(JSON.parse(remote.projection_json).evidenceSha256,sha(before.row.terminal_json));note({before,newer,after,remote});
});
for(const max of [false,true])test(`${max?'MAX':'ordinary'}-preserved-fence-transaction-rollback-durability-first-writer`,async h=>{
 await terminal(h);if(max)await h.call('maxVersion');const before=await raw(h);assert.equal((await h.call('independentPreserveFence',{rollback:true})).rolledBack,true);assert.deepEqual((await raw(h)).row,before.row);assert.equal((await raw(h)).fence.length,0);
 const committed=await h.call('independentPreserveFence');assert.deepEqual(committed.before,committed.after);const fenced=await raw(h);assert.equal(fenced.fence.length,1);assert.equal(fenced.fence[0].identity_bytes,'independent-review-identity');assert.equal(fenced.fence[0].reason,'independent_review_first');await h.restart(true);let after=await raw(h);assert.deepEqual(after.row,before.row);assert.deepEqual(after.fence,fenced.fence);assert.deepEqual(await command(h,'query',{epoch:'2',owner_id:'fenced-terminal-owner'}),{status:'error',code:'unavailable'});assert.equal((await h.call('claim')).granted,false);assert.equal((await h.call('independentValidShapeReport')).status,'rejected');after=await raw(h);assert.deepEqual(after.row,before.row);note({before,fenced,after});
});
test('SQLite-ACK-callback-throw-rolls-back-and-exact-ACK-does-not-version',async h=>{
 await terminal(h);const before=await raw(h);const rejected=await h.call('reviewAckGuard',{mode:'throw'});assert.equal(rejected.threw,true);assert.equal(rejected.cleared,false);assert.deepEqual((await raw(h)).row,before.row);const allowed=await h.call('reviewAckGuard',{mode:'allow'});assert.equal(allowed.cleared,true);const after=await raw(h);assert.equal(after.row.state_version,before.row.state_version);assert.equal(after.row.registry_ack_version,before.row.state_version);assert.equal(after.row.track_outbox_json,null);note({before,rejected,allowed,after});
});
test('nonterminal-MAX-independent-fence-survives-corrected-provider-and-hard-restart',async h=>{
 await registered(h);await command(h);assert.equal((await h.call('claim')).granted,true);await h.call('maxVersion');const before=await raw(h),ticket=await reserve(h);assert.equal(before.row.desired,'run');assert.equal(before.row.terminal_json,null);assert.equal(before.row.claim_state,'consumed');
 await h.call('providerMismatch');const corrupt=await raw(h);assert.deepEqual(await h.call('flush'),{flushed:false});let after=await raw(h);assert.deepEqual(after.row,corrupt.row);assert.equal(after.row.quarantined,0);assert.equal(after.fence.length,1);
 await h.call('restoreProvider');await h.restart(true);const restored=await raw(h);assert.deepEqual(restored.row,before.row);assert.deepEqual(restored.fence,after.fence);
 assert.deepEqual(await command(h,'query',{epoch:'2',owner_id:'independent-max-owner'}),{status:'error',code:'unavailable'});assert.equal((await h.call('claim')).granted,false);assert.equal((await h.call('report')).status,'rejected');assert.equal((await h.call('recoverKnown',{receipt:h.receipt,ticket})).status,'quarantined');await h.call('reconcile');await h.call('reconcile');after=await raw(h);assert.deepEqual(after.row,before.row);assert.equal(after.calls.length,before.calls.length);note({before,corrupt,restored,after});
});
for(const field of ['malformedOutbox','malformedTerminalAndProvider'])for(const boundary of ['effectFinal','providerAcceptance','claimFinal','reportAcceptance'])test(`${field}-delayed-${boundary}`,async h=>{
 await registered(h);await command(h);if(boundary!=='claimFinal')assert.equal((await h.call('claim')).granted,true);let pending;
 if(boundary==='reportAcceptance'){await h.call('inject',{point:'during_report_verify'});pending=h.call('report');await until(async()=>(await raw(h)).settings.blocked);}
 if(boundary==='claimFinal'){await h.call('inject',{point:'after_claim_commit'});pending=h.call('claim');await until(async()=>(await raw(h)).settings.blocked);}
 if(boundary==='effectFinal'||boundary==='providerAcceptance'){assert.equal((await h.call('report')).status,'accepted');await h.call('drain',{value:true});if(boundary==='effectFinal')await mode(h,'hold_after_once',1);else await h.call('inject',{point:'after_provider_effect'});pending=h.call('reconcile');await until(async()=>boundary==='effectFinal'?(await registry(h)).settings.blocked:(await raw(h)).settings.blocked);}
 await h.call('terminalMutation',{field});const corrupt=await raw(h);if(boundary==='effectFinal')await h.call('registry',{command:'release'});else await h.call('release');const outcome=await pending;if(boundary==='claimFinal')assert.equal(outcome.granted,false);if(boundary==='reportAcceptance')assert.equal(outcome.status,'rejected');const after=await raw(h);assert.deepEqual(after.row,corrupt.row);assert.equal(after.fence[0].reason,'track_terminal_inconsistent');assert.equal(after.calls.length,corrupt.calls.length);note({corrupt,outcome,after});
});
for(const phase of ['stopped','completed'])test(`${phase}-ACK-sync-mutation-preserves-already-committed-ACK`,async h=>{
 await terminal(h,phase);const before=await raw(h);await h.call('terminalAckSyncMutation');assert.deepEqual(await h.call('flush'),{flushed:false});const after=await raw(h);assert.equal(after.row.state_version,before.row.state_version);assert.equal(after.row.registry_ack_version,before.row.state_version);assert.equal(after.row.track_outbox_json,null);assert.equal(after.row.terminal_json,before.row.terminal_json);assert.equal(after.fence[0].reason,'track_terminal_inconsistent');assert.equal((await registry(h)).records[0].pending,0);note({before,after,localACKRollbackClaimed:false});
});
test('valid-committed-stop-owned-cleanup-survives-independent-fence-and-outages',async h=>{
 await registered(h);await command(h,'stop');const before=await raw(h);assert.equal(before.row.desired,'stop');assert.equal(before.row.terminal_json,null);await h.call('fenceOnly');await mode(h,'unavailable');await h.call('clock',{now:before.settings.clock,qualified:false});await h.call('drain',{value:true});await h.call('reconcile');const after=await raw(h);assert.ok(after.calls.filter(c=>c.kind==='stop').length>before.calls.filter(c=>c.kind==='stop').length);assert.equal(after.calls.filter(c=>c.kind==='launch').length,0);assert.equal(after.row.phase,'stop_pending');assert.equal(after.row.terminal_json,null);assert.equal(after.fence.length,1);assert.ok(after.row.track_outbox_json);assert.equal((await h.call('claim')).granted,false);note({before,after,terminalAdmissionClaimed:false});
});
for(const phase of ['stopped','completed'])for(const version of [1,2])test(`probe-schema${version}-${phase}-terminal-explicit-enrollment`,async h=>{
 await terminal(h,phase);assert.deepEqual(await h.call('flush'),{flushed:true});const original=await raw(h);const migrated=await h.call('legacy',{version});assert.equal(migrated.after.phase,phase);assert.equal(migrated.after.terminal_json,original.row.terminal_json);assert.equal(migrated.after.registry_ack_version,'0');assert.equal(migrated.after.track_outbox_json,null);assert.equal(migrated.after.quarantined,1);const enrolled=await h.call('enroll'),after=await raw(h);note({original,migrated,enrolled,after,contractExpected:'enrolled with existing row quarantine retained'});assert.equal(enrolled.status,'enrolled');assert.equal(after.row.quarantined,1);assert.equal(after.row.terminal_json,original.row.terminal_json);
});
for(const phase of ['stopped','completed'])test(`probe-${phase}-missing-outbox-ack-ahead-history-regression`,async h=>{
 await terminal(h,phase);assert.deepEqual(await h.call('flush'),{flushed:true});const original=await raw(h);await h.call('independentAckAhead');const restored=await raw(h);assert.ok(BigInt(restored.row.registry_ack_version)>BigInt(restored.row.state_version));const outcome=await h.call('flush'),after=await raw(h);note({original,restored,outcome,after,remote:(await registry(h)).records[0],contractExpected:'fail closed and retain independent history fence'});assert.deepEqual(outcome,{flushed:false});assert.equal(after.fence.length,1);
});
const selected=process.env.MIXER_INDEPENDENT_FILTER,chosen=selected?cases.filter(c=>c.id.includes(selected)):cases;
if(!chosen.length)throw new Error('unknown_independent_case');
for(const c of chosen){let h;current=c.id;try{h=await harness(base,fixed);await c.fn(h);results.push({id:c.id,status:'passed'});}catch(e){results.push({id:c.id,status:'failed',error:e.stack??String(e)});}finally{if(h)try{await h.close();}catch(e){results.push({id:c.id+'-cleanup',status:'failed',error:e.stack??String(e)});}}console.log(JSON.stringify(results.at(-1)));}
const report={schema:1,status:results.every(r=>r.status==='passed')?'passed':'findings',actualWorkerd:true,actualSQLite:true,groupsDefined:cases.length,groupsRun:chosen.length,groupsPassed:results.filter(r=>r.status==='passed').length,results,observations,cleanup};
await writeFile(process.env.MIXER_INDEPENDENT_REPORT??resolve(import.meta.dirname,'../../independent-report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,groupsRun:report.groupsRun,groupsPassed:report.groupsPassed}));if(report.status!=='passed')process.exitCode=1;
