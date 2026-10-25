import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {harness,cleanup} from './harness.mjs';

const packet=resolve(import.meta.dirname,'../..');
const request=JSON.parse(await readFile(resolve(packet,'request.json'),'utf8'));
const digest=s=>createHash('sha256').update(s).digest('hex');
const identity={namespaceGeneration:'a'.repeat(64),environmentId:request.environment_id,poolId:request.pool_id,controllerId:request.controller_id,platform:request.ref.platform,operationKey:digest(JSON.stringify(['mixer-worker-controller-do-v1',request.environment_id,request.pool_id,request.controller_id,request.operation_id])),operationId:request.operation_id,immutableSha256:request.immutable_sha256};
const tests=[],results=[],observations={};
const test=(id,run)=>tests.push({id,run});
const raw=h=>h.call('raw');
const remote=h=>h.call('registry',{command:'raw'});
const registryMode=(h,mode)=>h.call('registry',{command:'mode',mode});
const cmd=(h,command='query',guard={})=>h.call('command',{request:{...structuredClone(request),command,guard:{...request.guard,...guard}},receipt:h.receipt});
function equalRows(actual,expected){assert.deepEqual(actual,expected,'every operation column must retain exact restored value');}
function rpcKinds(a){return a.rpcCalls.map(c=>c.kind);}
async function waitBlocked(h){for(let n=0;n<150;n++){if((await raw(h)).settings.blocked)return;await new Promise(r=>setTimeout(r,2));}throw new Error('bounded enrollment hold was not reached');}
async function create(h,phase){
  const reg=await h.call('register');assert.equal(reg.status,'registered');h.receipt=reg.receipt;
  if(phase==='stopped'){await h.call('drain',{value:true});await cmd(h,'stop');}
  else if(phase==='completed'){
    await cmd(h,'ensure_started');assert.equal((await h.call('claim')).granted,true);assert.equal((await h.call('report')).status,'accepted');await h.call('drain',{value:true});await h.call('reconcile');
  }else await cmd(h,'ensure_started');
  const value=await raw(h);assert.equal(value.row.phase,phase);assert.equal(value.row.track_outbox_json,null);assert.equal(value.row.registry_ack_version,value.row.state_version);assert.equal(value.fence.length,0);return value;
}
async function legacy(h,phase,version=2){
  const created=await create(h,phase),registry=await remote(h);
  const old=await h.call('reviewDowngradeOnly',{version});assert.equal(old.version,version);
  await h.restart(true);
  const migrated=await raw(h);
  assert.deepEqual(migrated.schema,[{version:3}]);assert.equal(migrated.row.quarantined,1);assert.equal(migrated.row.registry_ack_version,'0');
  for(const key of ['pending_identity_json','registration_json','effect_barrier_version','claim_barrier_version','track_outbox_json'])assert.equal(migrated.row[key],null,key);
  for(const key of Object.keys(old.row))if(key!=='quarantined')assert.deepEqual(migrated.row[key],old.row[key],key);
  if(version===1)assert.equal(migrated.row.clock_floor,old.row.clock_lower);
  assert.equal(migrated.fence.length,0);assert.deepEqual(migrated.calls,created.calls);assert.deepEqual(await remote(h),registry,'constructor migration must not register or track');
  return migrated;
}
async function deniedWithoutMutation(h,expected){
  const registry=await remote(h);
  assert.equal((await h.call('claim')).granted,false);
  assert.equal((await h.call('independentValidShapeReport')).status,'rejected');
  assert.deepEqual(await h.call('plain',{request}),{status:'error',code:'unavailable'});
  const after=await raw(h);equalRows(after.row,expected.row);assert.deepEqual(after.calls,expected.calls);assert.deepEqual(await remote(h),registry,'denied authority must not register or track');
}
async function conflictPreserves(h,before,registry){
  const reply=await h.call('enroll'),after=await raw(h);
  assert.deepEqual(reply,{status:'conflict'});equalRows(after.row,before.row);assert.deepEqual(after.calls,before.calls);assert.deepEqual(await remote(h),registry,'rejected shape must not call register or track');
  return {reply,before:before.row,after:after.row,fence:after.fence,registryRPCs:rpcKinds(registry)};
}

for(const phase of ['stopped','completed'])for(const version of [1,2])test(`schema-${version}-${phase}-exact-null-migration-enrolls-with-quarantine`,async h=>{
  const before=await legacy(h,phase,version),registry=await remote(h);
  await h.call('migrationRecover');await deniedWithoutMutation(h,before);await h.restart(true);
  equalRows((await raw(h)).row,before.row);assert.deepEqual(await remote(h),registry);
  assert.deepEqual(await h.call('enroll'),{status:'enrolled'});
  const after=await raw(h),r=after.row;
  assert.equal(r.quarantined,1);assert.equal(r.state_version,String(BigInt(before.row.state_version)+1n));assert.equal(r.registry_ack_version,'0');
  assert.ok(r.pending_identity_json);assert.ok(r.registration_json);
  assert.deepEqual(JSON.parse(r.track_outbox_json),{stateVersion:r.state_version,nextDueUs:null,terminal:{phase,exactJson:before.row.terminal_json}});
  for(const key of Object.keys(before.row))if(!['pending_identity_json','registration_json','state_version','track_outbox_json'].includes(key))assert.deepEqual(r[key],before.row[key],key);
  assert.deepEqual(after.calls,before.calls);assert.equal(after.fence.length,0);
  const remoteAfter=await remote(h);assert.deepEqual(remoteAfter.records,registry.records);assert.deepEqual(rpcKinds(remoteAfter).slice(registry.rpcCalls.length),['register']);
  await deniedWithoutMutation(h,after);await h.restart(true);equalRows((await raw(h)).row,r);assert.deepEqual(await remote(h),remoteAfter);
  observations[`schema-${version}-${phase}`]={before:before.row,after:r,quarantineRetained:true,implicitRegistryCalls:0};
});

for(const phase of ['stopped','completed'])for(const timing of ['direct','restart'])test(`${phase}-valid-reintroduced-outbox-${timing}-rejects-before-registration`,async h=>{
  await legacy(h,phase);await h.call('reviewRestore',{scenario:'extraOutbox'});const before=await raw(h),registry=await remote(h);
  assert.deepEqual(JSON.parse(before.row.track_outbox_json),{stateVersion:before.row.state_version,nextDueUs:null,terminal:{phase,exactJson:before.row.terminal_json}});
  if(timing==='restart'){await h.restart(true);equalRows((await raw(h)).row,before.row);assert.equal((await raw(h)).fence.length,0);assert.deepEqual(await remote(h),registry);}
  observations[`${phase}-valid-outbox-${timing}`]=await conflictPreserves(h,before,registry);
  assert.equal((await raw(h)).fence.length,0,'valid outbox is not projection corruption');
  await deniedWithoutMutation(h,before);await h.restart(true);equalRows((await raw(h)).row,before.row);assert.deepEqual(await remote(h),registry);
});

for(const phase of ['stopped','completed'])for(const form of ['empty','malformed'])for(const timing of ['direct','restart'])test(`${phase}-${form}-outbox-${timing}-preserves-row-and-fences`,async h=>{
  await legacy(h,phase);await h.call('outboxBoundaryBytes',{form});const before=await raw(h),registry=await remote(h);
  assert.equal(before.row.track_outbox_json,form==='empty'?'':'{');
  if(timing==='restart')await h.restart(true);
  observations[`${phase}-${form}-${timing}`]=await conflictPreserves(h,before,registry);
  const after=await raw(h);assert.equal(after.fence.length,1);assert.equal(after.fence[0].reason,'track_terminal_inconsistent');
  await h.restart(true);equalRows((await raw(h)).row,before.row);assert.deepEqual((await raw(h)).fence,after.fence);
});

for(const phase of ['stopped','completed'])test(`${phase}-valid-registered-pending-outbox-remains-enrollable`,async h=>{
  await create(h,phase);await registryMode(h,'unavailable');await cmd(h,'query',{epoch:'2',owner_id:'acceptance-registered'});await registryMode(h,'normal');
  const before=await raw(h),registry=await remote(h);assert.ok(before.row.pending_identity_json);assert.ok(before.row.registration_json);assert.ok(before.row.track_outbox_json);assert.ok(BigInt(before.row.registry_ack_version)<BigInt(before.row.state_version));assert.equal(before.row.quarantined,0);
  assert.deepEqual(await h.call('enroll'),{status:'enrolled'});const after=await raw(h),r=after.row;
  assert.equal(r.state_version,String(BigInt(before.row.state_version)+1n));assert.equal(r.registry_ack_version,r.state_version);assert.equal(r.track_outbox_json,null);
  for(const key of Object.keys(before.row))if(!['state_version','registry_ack_version','track_outbox_json'].includes(key))assert.deepEqual(r[key],before.row[key],key);
  assert.equal(after.fence.length,0);assert.deepEqual(after.calls,before.calls);
  assert.deepEqual(rpcKinds(await remote(h)).slice(registry.rpcCalls.length),['register','track']);
  await h.restart(true);equalRows((await raw(h)).row,r);observations[`${phase}-registered-pending`]={before:before.row,after:r};
});

for(const field of ['identityOnly','receiptOnly','emptyBoth','malformedBoth'])test(`partial-${field}-null-outbox-still-rejects`,async h=>{
  await legacy(h,'stopped');await h.call('migrationMutation',{field});const before=await raw(h),registry=await remote(h);
  observations[`partial-${field}`]=await conflictPreserves(h,before,registry);
  await h.restart(true);equalRows((await raw(h)).row,before.row);
});

for(const phase of ['stopped','completed'])for(const mutation of ['validOutbox','empty','malformed','rowFailureCount','wrongProvider'])test(`${phase}-enrollment-await-${mutation}-restored-row-wins`,async h=>{
  await legacy(h,phase);await h.call('migrationEnrollmentHold');const pending=h.call('enroll');await waitBlocked(h);
  const registry=await remote(h);
  if(mutation==='validOutbox')await h.call('reviewRestore',{scenario:'extraOutbox'});
  else if(mutation==='empty'||mutation==='malformed')await h.call('outboxBoundaryBytes',{form:mutation});
  else await h.call('reviewRestore',{scenario:mutation});
  const restored=await raw(h);await h.call('release');const reply=await pending;assert.deepEqual(reply,{status:'conflict'});
  const after=await raw(h),remoteAfter=await remote(h);equalRows(after.row,restored.row);assert.deepEqual(after.calls,restored.calls);assert.deepEqual(remoteAfter.records,registry.records);assert.deepEqual(rpcKinds(remoteAfter).slice(registry.rpcCalls.length),['register'],'only the requested explicit registration round trip occurs');
  if(mutation==='validOutbox'||mutation==='rowFailureCount')assert.equal(after.fence.length,0);
  else assert.equal(after.fence[0].reason,mutation==='wrongProvider'?'provider_binding_conflict':'track_terminal_inconsistent');
  await h.restart(true);equalRows((await raw(h)).row,restored.row);assert.deepEqual((await raw(h)).fence,after.fence);assert.deepEqual(await remote(h),remoteAfter);
  observations[`${phase}-await-${mutation}`]={reply,restored:restored.row,after:after.row,fence:after.fence,remoteNewRecord:false,remoteRollbackClaimed:false};
});

for(const phase of ['stopped','completed'])test(`${phase}-null-migration-MAX-refuses-without-register-or-wrap`,async h=>{
  await legacy(h,phase);await h.call('maxVersion');const before=await raw(h),registry=await remote(h);assert.equal(before.row.state_version,'9223372036854775807');
  assert.deepEqual(await h.call('enroll'),{status:'unavailable'});equalRows((await raw(h)).row,before.row);assert.deepEqual(await remote(h),registry);assert.equal((await raw(h)).fence.length,0);await h.restart(true);equalRows((await raw(h)).row,before.row);
});

for(const phase of ['stopped','completed'])test(`${phase}-retained-real-ACK-ahead-preserves-history`,async h=>{
  await create(h,phase);const registry=await remote(h);await h.call('reviewRestore',{scenario:'lowerStateAfterACK'});const before=await raw(h);
  assert.deepEqual(await h.call('flush'),{flushed:false});equalRows((await raw(h)).row,before.row);assert.deepEqual((await raw(h)).calls,before.calls);assert.deepEqual(await remote(h),registry);assert.equal((await raw(h)).fence[0].reason,'track_history_regressed');await h.restart(true);equalRows((await raw(h)).row,before.row);
});

test('committed-nonterminal-stop-keeps-owned-cleanup-under-fence-and-outages',async h=>{
  await create(h,'inert');await cmd(h,'stop',{epoch:'2',owner_id:'acceptance-stop'});const before=await raw(h);assert.equal(before.row.desired,'stop');assert.equal(before.row.terminal_json,null);
  await h.call('reviewRestore',{scenario:'newFence'});await registryMode(h,'unavailable');await h.call('clock',{now:'1900000000000000',qualified:false});await h.call('drain',{value:true});await h.call('reconcile');
  const after=await raw(h);assert.ok(after.calls.filter(x=>x.kind==='stop').length>before.calls.filter(x=>x.kind==='stop').length);assert.equal(after.row.terminal_json,null);assert.equal(after.fence[0].reason,'review_restore_fence');assert.equal((await h.call('claim')).granted,false);assert.equal((await h.call('independentValidShapeReport')).status,'rejected');observations.stopCleanup={beforeCalls:before.calls,afterCalls:after.calls,fence:after.fence,terminal:after.row.terminal_json};
});

for(const t of tests){let h;try{h=await harness(request,identity);await t.run(h);results.push({id:t.id,status:'passed'});console.log('PASS '+t.id);}catch(e){results.push({id:t.id,status:'failed',error:e.stack??String(e)});console.log('FAIL '+t.id+' '+e.message);}finally{if(h)try{await h.close();}catch(e){results.push({id:t.id+'-cleanup',status:'failed',error:e.stack??String(e)});}}}
const report={schema:1,status:results.every(x=>x.status==='passed')?'passed':'failed',groupsRun:tests.length,groupsPassed:results.filter(x=>x.status==='passed').length,results,observations,cleanup};
await writeFile(process.env.REVIEW_REPORT??resolve(packet,'acceptance-report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,run:report.groupsRun,passed:report.groupsPassed}));process.exitCode=report.status==='passed'?0:1;
