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
const test=(id,fn)=>cases.push({id,fn}),raw=h=>h.call('raw'),registry=h=>h.call('registry',{command:'raw'}),mode=(h,mode,skip=0)=>h.call('registry',{command:'mode',mode,skip});
const note=x=>observations[current]={...observations[current],...x};
async function until(f){for(let i=0;i<100;i++){if(await f())return;await new Promise(r=>setTimeout(r,4));}throw new Error('migration_bounded_wait_exhausted');}
const request=(command='query')=>({...base,command});
const command=(h,cmd='ensure_started')=>h.call('command',{request:request(cmd),receipt:h.receipt});
async function registered(h){const v=await h.call('register');assert.equal(v.status,'registered');h.receipt=v.receipt;}
async function terminal(h,phase){
 await registered(h);
 if(phase==='completed'){await command(h);assert.equal((await h.call('claim')).granted,true);assert.equal((await h.call('report')).status,'accepted');}
 await h.call('drain',{value:true});await mode(h,'drop_before_once',2);
 if(phase==='stopped')assert.equal((await command(h,'stop')).status,'stopped');else await h.call('reconcile');
 const s=await raw(h);assert.equal(s.row.phase,phase);assert.ok(s.row.track_outbox_json);return s;
}
async function exactAck(h,phase){if(phase==='nonterminal'){await registered(h);await command(h);assert.equal((await raw(h)).row.terminal_json,null);}else await terminal(h,phase);assert.deepEqual(await h.call('flush'),{flushed:true});const s=await raw(h);assert.equal(s.row.registry_ack_version,s.row.state_version);assert.equal(s.row.track_outbox_json,null);return s;}
async function migrated(h,phase,version){await exactAck(h,phase);const original=await raw(h),m=await h.call('legacy',{version}),after=await raw(h);assert.equal(after.row.quarantined,1);assert.equal(after.row.registry_ack_version,'0');for(const k of ['pending_identity_json','registration_json','effect_barrier_version','claim_barrier_version','track_outbox_json'])assert.equal(after.row[k],null);const changed=new Set(['quarantined','pending_identity_json','registration_json','registry_ack_version','effect_barrier_version','claim_barrier_version','track_outbox_json',...(version===1?['clock_floor']:[])]);for(const k of Object.keys(original.row))if(!changed.has(k))assert.deepEqual(after.row[k],original.row[k],k);if(version===1)assert.equal(after.row.clock_floor,original.row.clock_lower);assert.equal(after.fence.length,0);return {original,m,after};}
async function assertNoAuthority(h,before,entry){
 if(entry==='plain')assert.deepEqual(await h.call('plain',{request:request()}),{status:'error',code:'unavailable'});
 if(entry==='registered')assert.deepEqual(await command(h,'query'),{status:'error',code:'unavailable'});
 if(entry==='claim')assert.equal((await h.call('claim')).granted,false);
 if(entry==='report')assert.equal((await h.call('independentValidShapeReport')).status,'rejected');
 if(entry==='reconcile')await h.call('reconcile');
 if(entry==='recover')await h.call('migrationRecover');
 if(entry==='public')assert.equal(await h.publicFetch(),404);
 const after=await raw(h);assert.deepEqual(after.row,before.row);assert.deepEqual(after.calls,before.calls);return after;
}
for(const phase of ['stopped','completed'])for(const version of [1,2])for(const boundary of ['direct','recover','softRestart','hardRestart'])test(`schema${version}-${phase}-${boundary}-explicit-enrollment`,async h=>{
 const m=await migrated(h,phase,version);if(boundary==='recover')await h.call('migrationRecover');if(boundary==='softRestart')await h.restart();if(boundary==='hardRestart')await h.restart(true);
 const before=await raw(h),remote=await registry(h);assert.deepEqual(before.row,m.after.row);assert.equal(before.fence.length,0);assert.deepEqual(await h.call('flush'),{flushed:false});assert.deepEqual((await raw(h)).row,before.row);
 assert.equal((await h.call('enroll')).status,'enrolled');const after=await raw(h);assert.equal(after.row.quarantined,1);assert.equal(after.row.state_version,String(BigInt(before.row.state_version)+1n));assert.equal(after.row.registry_ack_version,'0');assert.ok(after.row.pending_identity_json);assert.ok(after.row.registration_json);assert.equal(after.fence.length,0);const changed=new Set(['pending_identity_json','registration_json','state_version','track_outbox_json']);for(const k of Object.keys(before.row))if(!changed.has(k))assert.deepEqual(after.row[k],before.row[k],k);
 assert.deepEqual(JSON.parse(after.row.track_outbox_json),{stateVersion:after.row.state_version,nextDueUs:null,terminal:{phase,exactJson:before.row.terminal_json}});assert.deepEqual(after.calls,before.calls);assert.deepEqual((await registry(h)).records,remote.records);await h.restart(true);const restarted=await raw(h);assert.deepEqual(restarted.row,after.row);assert.equal(restarted.fence.length,0);note({m,before,after,restarted,automaticRegistrationOrAuthorityClaimed:false});
});
for(const phase of ['stopped','completed'])for(const entry of ['plain','registered','claim','report','reconcile','recover','public'])test(`${phase}-unenrolled-legacy-no-${entry}-authority`,async h=>{
 const m=await migrated(h,phase,2),before=await raw(h),remote=await registry(h);const after=await assertNoAuthority(h,before,entry);assert.deepEqual((await registry(h)).records,remote.records);if(entry==='registered'){assert.equal(after.fence.length,1);assert.equal((await h.call('enroll')).status,'conflict');}else assert.equal(after.fence.length,0);note({m,before,after});
});
const deviations=['identityOnly','receiptOnly','emptyIdentity','emptyReceipt','emptyBoth','malformedBoth','shapeBoth','effectBarrier','claimBarrier','nonquarantined','ackPositive','versionZero','versionNoncanonical','versionNegative','versionOverflow','versionUnknown','fullRegistration'];
for(const phase of ['stopped','completed'])for(const version of [1,2])for(const field of deviations)test(`schema${version}-${phase}-deviation-${field}`,async h=>{
 await migrated(h,phase,version);await h.call('migrationMutation',{field});const before=await raw(h);assert.equal((await h.call('enroll')).status,'conflict');const after=await raw(h);assert.deepEqual(after.row,before.row);assert.equal(after.fence.length,1);assert.deepEqual(after.calls,before.calls);await h.restart(true);const restarted=await raw(h);assert.deepEqual(restarted.row,before.row);assert.deepEqual(restarted.fence,after.fence);note({before,after,restarted});
});
for(const phase of ['stopped','completed'])for(const field of ['malformedTerminal','terminalDuplicateStatus','terminalUnknownStatus','terminalInvalidBody','terminalArray','terminalNull','missingTerminal','rowPhase','terminalNextDue'])test(`${phase}-migrated-hostile-${field}`,async h=>{
 await migrated(h,phase,2);await h.call('terminalMutation',{field});const before=await raw(h);assert.equal((await h.call('enroll')).status,'conflict');const after=await raw(h);assert.deepEqual(after.row,before.row);assert.equal(after.fence.length,1);assert.deepEqual(after.calls,before.calls);note({before,after});
});
for(const phase of ['stopped','completed'])for(const field of ['wrongProvider','wrongBinding','changedIdentity'])test(`${phase}-explicit-full-identity-${field}`,async h=>{
 await migrated(h,phase,2);await h.call('migrationMutation',{field});const before=await raw(h),remote=await registry(h);assert.equal((await h.call('enroll')).status,'conflict');const after=await raw(h);assert.deepEqual(after.row,before.row);assert.deepEqual(after.calls,before.calls);assert.deepEqual((await registry(h)).records,remote.records);note({before,after});
});
for(const phase of ['stopped','completed'])for(const field of ['changedOwner','changedIdentity','wrongProvider','wrongBinding','identityOnly','effectBarrier','claimBarrier','nonquarantined'])test(`${phase}-explicit-current-row-await-${field}`,async h=>{
 await migrated(h,phase,2);await h.call('migrationEnrollmentHold');const pending=h.call('enroll');await until(async()=>(await raw(h)).settings.blocked);await h.call('migrationMutation',{field});const before=await raw(h);await h.call('release');assert.equal((await pending).status,'conflict');const after=await raw(h);assert.deepEqual(after.row,before.row);assert.deepEqual(after.calls,before.calls);note({before,after});
});
for(const phase of ['stopped','completed'])test(`${phase}-existing-permanent-fence-retained`,async h=>{
 await migrated(h,phase,2);await h.call('fenceOnly');const before=await raw(h);assert.equal((await h.call('enroll')).status,'conflict');await h.restart(true);assert.equal((await h.call('enroll')).status,'conflict');const after=await raw(h);assert.deepEqual(after.row,before.row);assert.deepEqual(after.fence,before.fence);assert.deepEqual(after.calls,before.calls);note({before,after});
});
for(const phase of ['stopped','completed'])test(`${phase}-migration-MAX-no-wrap-or-partial-enrollment`,async h=>{
 await migrated(h,phase,2);await h.call('maxVersion');const before=await raw(h),remote=await registry(h);assert.equal((await h.call('enroll')).status,'unavailable');const after=await raw(h);assert.deepEqual(after.row,before.row);assert.equal(after.fence.length,0);assert.deepEqual((await registry(h)).records,remote.records);await h.restart(true);assert.deepEqual((await raw(h)).row,before.row);note({before,after});
});
for(const phase of ['stopped','completed','nonterminal'])for(const boundary of ['ordinary','maxAhead','maxAheadPending'])test(`${phase}-${boundary}-durable-ACK-ahead-full-row-fence`,async h=>{
 const original=await exactAck(h,phase);await h.call('migrationMutation',{field:boundary==='ordinary'?'regressAcknowledged':boundary});const before=await raw(h),remote=await registry(h);assert.ok(BigInt(before.row.registry_ack_version)>BigInt(before.row.state_version));assert.deepEqual(await h.call('flush'),{flushed:false});const after=await raw(h);assert.deepEqual(after.row,before.row);assert.equal(after.fence.length,1);assert.equal(after.fence[0].reason,'track_history_regressed');assert.equal(after.fence[0].observed_version,before.row.state_version);assert.deepEqual(after.calls,before.calls);assert.deepEqual((await registry(h)).records,remote.records);await h.restart(true);let restarted=await raw(h);assert.deepEqual(restarted.row,before.row);assert.deepEqual(restarted.fence,after.fence);await h.call('flush');assert.equal((await h.call('claim')).granted,false);assert.equal((await h.call('independentValidShapeReport')).status,'rejected');restarted=await raw(h);assert.deepEqual(restarted.row,before.row);note({original,before,after,restarted,remoteCommitRollbackClaimed:false});
});
for(const phase of ['stopped','completed','nonterminal'])for(const boundary of ['ordinary','MAX'])test(`${phase}-${boundary}-valid-ACK-equality`,async h=>{
 await exactAck(h,phase);if(boundary==='MAX')await h.call('migrationMutation',{field:'maxEqual'});const before=await raw(h);assert.deepEqual(await h.call('flush'),{flushed:true});const after=await raw(h);assert.deepEqual(after.row,before.row);assert.equal(after.fence.length,0);assert.deepEqual(after.calls,before.calls);note({before,after,remoteEqualityInferredFromRestore:false});
});
for(const phase of ['stopped','completed','nonterminal'])for(const field of ['ackNoncanonical','ackNegative','ackOverflow','ackUnknown','versionNoncanonical','versionNegative','versionOverflow','versionUnknown'])test(`${phase}-invalid-history-${field}`,async h=>{
 await exactAck(h,phase);await h.call('migrationMutation',{field});const before=await raw(h);assert.deepEqual(await h.call('flush'),{flushed:false});const after=await raw(h);assert.deepEqual(after.row,before.row);assert.equal(after.fence.length,1);assert.deepEqual(after.calls,before.calls);await h.restart(true);assert.deepEqual((await raw(h)).row,before.row);note({before,after});
});
for(const phase of ['stopped','completed','nonterminal'])test(`${phase}-pending-outbox-lower-ACK-remains-deliverable`,async h=>{
 if(phase==='nonterminal'){await registered(h);await mode(h,'unavailable');await command(h);await mode(h,'normal');}else await terminal(h,phase);let before=await raw(h);if(!before.row.track_outbox_json){await h.call('quarantineOnly');throw new Error('fixture_pending_required');}await h.call('migrationMutation',{field:'pendingAckLower'});before=await raw(h);assert.ok(BigInt(before.row.registry_ack_version)<BigInt(before.row.state_version));assert.deepEqual(await h.call('flush'),{flushed:true});const after=await raw(h);assert.equal(after.fence.length,0);assert.equal(after.row.state_version,before.row.state_version);assert.equal(after.row.registry_ack_version,before.row.state_version);assert.equal(after.row.track_outbox_json,null);assert.deepEqual(after.calls,before.calls);note({before,after});
});
for(const version of [1,2])for(const boundary of ['direct','recover','hardRestart'])test(`schema${version}-nonterminal-${boundary}-explicit-enrollment-quarantine`,async h=>{
 await migrated(h,'nonterminal',version);const migratedRow=(await raw(h)).row;if(boundary==='recover')await h.call('migrationRecover');if(boundary==='hardRestart')await h.restart(true);const before=await raw(h);assert.deepEqual(before.row,migratedRow);assert.equal(before.fence.length,0);assert.equal((await h.call('enroll')).status,'enrolled');const after=await raw(h);assert.equal(after.row.quarantined,1);assert.equal(after.row.state_version,String(BigInt(before.row.state_version)+1n));assert.equal(JSON.parse(after.row.track_outbox_json).terminal,null);assert.equal(after.row.registry_ack_version,'0');assert.equal(after.fence.length,0);assert.deepEqual(after.calls,before.calls);assert.equal((await h.call('claim')).granted,false);assert.equal((await h.call('independentValidShapeReport')).status,'rejected');note({before,after});
});
for(const field of ['identityOnly','receiptOnly','emptyIdentity','emptyReceipt','emptyBoth','malformedBoth','shapeBoth','effectBarrier','claimBarrier','nonquarantined','versionZero','versionUnknown'])test(`nonterminal-explicit-deviation-${field}`,async h=>{
 await migrated(h,'nonterminal',2);await h.call('migrationMutation',{field});const before=await raw(h);assert.equal((await h.call('enroll')).status,'conflict');const after=await raw(h);assert.deepEqual(after.row,before.row);assert.deepEqual(after.calls,before.calls);note({before,after});
});
for(const phase of ['stopped','completed'])test(`${phase}-explicit-fence-during-await`,async h=>{
 await migrated(h,phase,2);await h.call('migrationEnrollmentHold');const pending=h.call('enroll');await until(async()=>(await raw(h)).settings.blocked);await h.call('fenceOnly');const before=await raw(h);await h.call('release');assert.equal((await pending).status,'conflict');const after=await raw(h);assert.deepEqual(after.row,before.row);assert.deepEqual(after.fence,before.fence);assert.deepEqual(after.calls,before.calls);note({before,after});
});
const selected=process.env.MIXER_MIGRATION_FILTER,chosen=selected?cases.filter(c=>c.id.includes(selected)):cases;if(!chosen.length)throw new Error('unknown_migration_case');
for(const c of chosen){let h;current=c.id;try{h=await harness(base,fixed);await c.fn(h);results.push({id:c.id,status:'passed'});}catch(e){results.push({id:c.id,status:'failed',error:e.stack??String(e)});}finally{if(h)try{await h.close();}catch(e){results.push({id:c.id+'-cleanup',status:'failed',error:e.stack??String(e)});}}console.log(JSON.stringify(results.at(-1)));}
const report={schema:1,status:results.every(r=>r.status==='passed')?'passed':'failed',actualWorkerd:true,actualSQLite:true,groupsDefined:cases.length,groupsRun:chosen.length,groupsPassed:results.filter(r=>r.status==='passed').length,results,observations,cleanup};await writeFile(process.env.MIXER_MIGRATION_REPORT??resolve(import.meta.dirname,'../../migration-report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,groupsRun:report.groupsRun,groupsPassed:report.groupsPassed}));if(report.status!=='passed')process.exitCode=1;
