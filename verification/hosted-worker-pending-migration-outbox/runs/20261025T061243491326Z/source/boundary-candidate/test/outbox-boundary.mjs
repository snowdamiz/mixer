import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {harness,cleanup} from './harness.mjs';
const packet=resolve(import.meta.dirname,'../..');
const base=JSON.parse(await readFile(resolve(packet,'request.json'),'utf8'));
const sha=value=>createHash('sha256').update(value).digest('hex');
const fixed={namespaceGeneration:'a'.repeat(64),environmentId:base.environment_id,poolId:base.pool_id,controllerId:base.controller_id,platform:base.ref.platform,operationKey:sha(JSON.stringify(['mixer-worker-controller-do-v1',base.environment_id,base.pool_id,base.controller_id,base.operation_id])),operationId:base.operation_id,immutableSha256:base.immutable_sha256};
const results=[],observations={};
const raw=h=>h.call('raw');
const remote=h=>h.call('registry',{command:'raw'});
const command=(h,command)=>h.call('command',{request:{...structuredClone(base),command},receipt:h.receipt});
async function legacyTerminal(h,phase){
 const registration=await h.call('register');assert.equal(registration.status,'registered');h.receipt=registration.receipt;
 if(phase==='completed'){await command(h,'ensure_started');assert.equal((await h.call('claim')).granted,true);assert.equal((await h.call('report')).status,'accepted');await h.call('drain',{value:true});await h.call('reconcile');}
 else{await h.call('drain',{value:true});await command(h,'stop');}
 const terminal=await raw(h);assert.equal(terminal.row.phase,phase);assert.equal(terminal.row.track_outbox_json,null);assert.equal(terminal.row.registry_ack_version,terminal.row.state_version);
 const downgrade=await h.call('reviewDowngradeOnly',{version:2});assert.equal(downgrade.version,2);await h.restart(true);
 const migrated=await raw(h);assert.equal(migrated.schema[0].version,3);assert.equal(migrated.row.quarantined,1);assert.equal(migrated.row.registry_ack_version,'0');assert.ok(BigInt(migrated.row.state_version)>0n);assert.equal(migrated.row.terminal_json,terminal.row.terminal_json);assert.deepEqual(migrated.calls,terminal.calls);
 for(const field of ['pending_identity_json','registration_json','effect_barrier_version','claim_barrier_version','track_outbox_json'])assert.equal(migrated.row[field],null,field);
 for(const [field,value] of Object.entries(downgrade.row))if(field!=='quarantined')assert.deepEqual(migrated.row[field],value,field);
 assert.equal(migrated.fence.length,0);return migrated;
}
for(const phase of ['stopped','completed'])for(const form of ['missing','empty','malformed'])for(const boundary of ['direct','restart']){
 const id=`${phase}-${form}-outbox-${boundary}-enrollment-boundary`;let h;
 try{
  h=await harness(base,fixed);const migrated=await legacyTerminal(h,phase);await h.call('outboxBoundaryBytes',{form});const restored=await raw(h),expected={missing:null,empty:'',malformed:'{'}[form];assert.equal(restored.row.track_outbox_json,expected);
  for(const field of Object.keys(migrated.row))if(field!=='track_outbox_json')assert.deepEqual(restored.row[field],migrated.row[field],field);
  const remoteBefore=await remote(h);if(boundary==='restart'){await h.restart(true);const restarted=await raw(h);assert.deepEqual(restarted.row,restored.row);assert.deepEqual(restarted.calls,restored.calls);assert.deepEqual((await remote(h)).records,remoteBefore.records);if(form==='missing')assert.equal(restarted.fence.length,0);else assert.equal(restarted.fence[0].reason,'track_terminal_inconsistent');}
  const before=await raw(h),response=await h.call('enroll'),after=await raw(h);
  assert.equal(response.status,form==='missing'?'enrolled':'conflict');assert.deepEqual(after.calls,before.calls);assert.equal(after.row.quarantined,1);
  if(form==='missing'){
   assert.equal(after.row.state_version,String(BigInt(before.row.state_version)+1n));assert.equal(after.row.registry_ack_version,'0');assert.ok(after.row.pending_identity_json);assert.ok(after.row.registration_json);assert.deepEqual(JSON.parse(after.row.track_outbox_json),{stateVersion:after.row.state_version,nextDueUs:null,terminal:{phase,exactJson:before.row.terminal_json}});assert.equal(after.fence.length,0);
   for(const field of Object.keys(before.row))if(!['state_version','pending_identity_json','registration_json','track_outbox_json'].includes(field))assert.deepEqual(after.row[field],before.row[field],field);
  }else{
   assert.deepEqual(after.row,before.row);assert.equal(after.row.track_outbox_json,expected);assert.equal(after.fence.length,1);assert.equal(after.fence[0].reason,'track_terminal_inconsistent');assert.deepEqual((await remote(h)).records,remoteBefore.records);
  }
  await h.restart(true);const durable=await raw(h);assert.deepEqual(durable.row,after.row);assert.deepEqual(durable.fence,after.fence);assert.deepEqual(durable.calls,after.calls);
  assert.equal((await h.call('claim')).granted,false);assert.equal((await h.call('independentValidShapeReport')).status,'rejected');const denied=await raw(h);assert.deepEqual(denied.row,after.row);assert.deepEqual(denied.calls,after.calls);
  observations[id]={restored:restored.row,response,after:after.row,fence:after.fence,durable:durable.row,noProviderEffect:true,quarantineRetained:true};results.push({id,status:'passed'});console.log('PASS '+id);
 }catch(error){results.push({id,status:'failed',error:error.stack??String(error)});console.log('FAIL '+id+' '+error.message);}
 finally{if(h)try{await h.close();}catch(error){results.push({id:id+'-cleanup',status:'failed',error:error.stack??String(error)});}}
}
const report={status:results.every(x=>x.status==='passed')?'passed':'failed',groupsRun:12,groupsPassed:results.filter(x=>x.status==='passed').length,results,observations,cleanup,scope:'actual workerd/SQLite, genuine schema-2 migration, finite missing/null versus empty/malformed bytes, explicit enrollment and owned hard restart'};
await writeFile(process.env.OUTBOX_BOUNDARY_REPORT??resolve(packet,'outbox-boundary-report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,groupsRun:report.groupsRun,groupsPassed:report.groupsPassed}));process.exitCode=report.status==='passed'?0:1;
