import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {harness,cleanup} from './harness.mjs';
const root=resolve(import.meta.dirname,'../../../..');
const base=JSON.parse(await readFile(resolve(root,'verification/hosted-worker-controller-contract/vectors.json'),'utf8')).cases[0].request;
const sha=s=>createHash('sha256').update(s).digest('hex');
const clone=v=>JSON.parse(JSON.stringify(v));
const fixed={namespaceGeneration:'a'.repeat(64),environmentId:base.environment_id,poolId:base.pool_id,controllerId:base.controller_id,platform:base.ref.platform,operationKey:sha(JSON.stringify(['mixer-worker-controller-do-v1',base.environment_id,base.pool_id,base.controller_id,base.operation_id])),operationId:base.operation_id,immutableSha256:base.immutable_sha256};
const changed=(r,fields)=>({...clone(r),...fields,guard:{...r.guard,...fields.guard}});
const wait=ms=>new Promise(r=>setTimeout(r,ms));
async function until(f){for(let i=0;i<80;i++){if(await f())return;await wait(5);}throw new Error('bounded_fixture_wait');}
const cases=[],results=[];
function test(id,fn){cases.push({id,fn});}
async function registered(h){const r=await h.call('register');assert.ok(['registered','duplicate'].includes(r.status));h.receipt=r.receipt;return r.receipt;}
async function command(h,command='ensure_started',fields={}){h.request=changed(base,{command,...fields});return h.call('command',{request:h.request,receipt:h.receipt});}
const raw=h=>h.call('raw');
const registry=h=>h.call('registry',{command:'raw'});
const mode=(h,mode,skip=0)=>h.call('registry',{command:'mode',mode,skip});
const count=(r,k)=>r.calls.filter(c=>c.kind===k).length;
async function ticket(h,version){const s=await h.call('reserve',{recordId:h.receipt.recordId,version,runId:'1'});assert.equal(s.status,'reserved');return s.ticket;}

test('new-row-requires-validated-preregistration-and-default-unavailable',async h=>{
 assert.deepEqual(await h.call('plain',{request:base}),{status:'error',code:'unavailable'});assert.equal((await raw(h)).row,null);
 await registered(h);
 assert.deepEqual(await h.call('defaultUnavailable',{request:base,receipt:h.receipt}),{status:'error',code:'unavailable'});assert.equal((await raw(h)).row,null);
 assert.deepEqual(await h.call('command',{request:base,receipt:{...h.receipt,recordId:'f'.repeat(32)}}),{status:'error',code:'unavailable'});assert.equal((await raw(h)).row,null);
 assert.deepEqual(await command(h,'query'),{status:'absent'});assert.ok((await raw(h)).row.registration_json);
});
test('lost-registration-ack-retries-same-permanent-slot-before-row',async h=>{
 await mode(h,'register_lost');assert.equal((await h.call('register')).status,'unavailable');assert.equal((await raw(h)).row,null);
 const before=(await registry(h)).records[0];assert.equal(before.state_version,'0');
 await mode(h,'normal');await registered(h);assert.equal(h.receipt.recordId,before.record_id);assert.equal((await registry(h)).records.length,1);
 await command(h);assert.equal(count(await raw(h),'launch'),1);
});
test('lost-track-ack-blocks-launch-and-replays-exact-latest-outbox',async h=>{
 await registered(h);await mode(h,'lost_once');await command(h);
 const before=await raw(h);assert.equal(count(before,'launch'),0);assert.ok(before.row.track_outbox_json);assert.equal(before.row.registry_ack_version,'0');
 assert.equal((await registry(h)).records[0].state_version,before.row.state_version);
 await h.call('reconcile');const after=await raw(h);assert.equal(count(after,'launch'),1);assert.equal(after.row.track_outbox_json,null);
});
test('ack-metadata-does-not-generate-state-or-recursive-outbox',async h=>{
 await registered(h);await command(h,'query');const a=await raw(h);
 await h.call('flush');const b=await raw(h);await h.call('flush');const c=await raw(h);
 assert.equal(b.row.state_version,a.row.state_version);assert.equal(c.row.state_version,b.row.state_version);assert.equal(c.row.track_outbox_json,null);assert.equal(c.row.registry_ack_version,c.row.state_version);
});
test('out-of-order-old-ack-cannot-erase-newer-stop-projection',async h=>{
 await registered(h);await mode(h,'hold_after_once');const pending=command(h).catch(e=>({error:e.message}));
 await until(async()=>(await registry(h)).settings.blocked);
 await command(h,'stop',{guard:{epoch:'2',owner_id:'stop-owner'}});const newer=await raw(h);assert.equal(newer.row.desired,'stop');assert.ok(newer.row.track_outbox_json);
 await h.call('flush');const acked=await raw(h);assert.equal(acked.row.registry_ack_version,acked.row.state_version);
 await h.call('registry',{command:'release'});await pending;
 const after=await raw(h);assert.equal(count(after,'launch'),0);assert.ok(BigInt(after.row.registry_ack_version)>=BigInt(acked.row.registry_ack_version));assert.equal(after.row.desired,'stop');
});
test('newer-command-during-dispatch-barrier-invalidates-old-effect',async h=>{
 await registered(h);await mode(h,'hold_after_once',1);const pending=command(h);await until(async()=>(await registry(h)).settings.blocked);
 const dispatched=(await raw(h)).row;assert.equal(dispatched.launch_dispatched,1);
 await command(h,'query',{guard:{epoch:'2',owner_id:'new-owner'}});await h.call('registry',{command:'release'});await pending;
 assert.equal(count(await raw(h),'launch'),0);await h.call('reconcile');const after=await raw(h);assert.equal(count(after,'launch'),0);assert.equal(count(after,'inspect'),1);
});
test('dispatch-barrier-wait-rechecks-qualified-expiry',async h=>{
 await registered(h);await mode(h,'hold_after_once',1);const pending=command(h);await until(async()=>(await registry(h)).settings.blocked);
 await h.call('clock',{now:base.guard.expires_at_us});await h.call('registry',{command:'release'});await pending;
 const r=await raw(h);assert.equal(count(r,'launch'),0);assert.equal(r.row.launch_dispatched,1);assert.ok(BigInt(r.row.registry_ack_version)>=BigInt(r.row.effect_barrier_version));
});
test('claim-barrier-wait-rechecks-qualified-expiry-and-keeps-consumption',async h=>{
 await registered(h);await command(h);await mode(h,'hold_after_once');const pending=h.call('claim');await until(async()=>(await registry(h)).settings.blocked);
 await h.call('clock',{now:base.guard.expires_at_us});await h.call('registry',{command:'release'});assert.deepEqual(await pending,{granted:false});
 const r=await raw(h);assert.equal(r.row.claim_state,'consumed');assert.equal(count(r,'launch'),1);assert.equal((await h.call('claim')).granted,false);
});
test('claim-final-clock-write-may-have-newer-unacked-outbox',async h=>{
 await registered(h);await command(h);const granted=await h.call('claim');assert.equal(granted.granted,true);
 const r=await raw(h);assert.equal(r.row.registry_ack_version,r.row.claim_barrier_version);assert.equal(BigInt(r.row.state_version),BigInt(r.row.claim_barrier_version)+1n);assert.equal(JSON.parse(r.row.track_outbox_json).stateVersion,r.row.state_version);
 const version=r.row.state_version;await h.call('flush');const after=await raw(h);assert.equal(after.row.state_version,version);assert.equal(after.row.track_outbox_json,null);
});
test('retained-stop-cleans-up-during-registry-and-clock-outage',async h=>{
 await registered(h);await command(h);await command(h,'stop',{guard:{epoch:'2',owner_id:'stop-owner'}});
 const before=await raw(h);await mode(h,'unavailable');await h.call('clock',{now:'1900000000000000',qualified:false});await h.call('drain',{value:true});await h.call('reconcile');
 const after=await raw(h);assert.ok(count(after,'stop')>count(before,'stop'));assert.equal(after.row.terminal_json,null);assert.equal(after.row.phase,'stop_pending');assert.ok(after.row.track_outbox_json);assert.equal(count(after,'launch'),1);
 await mode(h,'normal');await h.call('clock',{now:base.guard.expires_at_us});await h.call('reconcile');const recovered=await raw(h);assert.equal(JSON.parse(recovered.row.terminal_json).status,'stopped');assert.equal(count(recovered,'launch'),1);
});
test('terminal-evidence-tracks-exact-local-bytes-and-lost-ack-replays',async h=>{
 await registered(h);await command(h);assert.equal((await h.call('claim')).granted,true);assert.equal((await h.call('report')).status,'accepted');
 await h.call('drain',{value:true});await mode(h,'lost_once',2);await h.call('reconcile');
 let r=await raw(h);assert.equal(JSON.parse(r.row.terminal_json).status,'completed');assert.ok(r.row.track_outbox_json);assert.ok(BigInt(r.row.registry_ack_version)<BigInt(r.row.state_version));
 // Delivery can lose either dispatch or terminal ACK; retain terminal bytes until
 // the exact registry terminal version is accepted, then duplicate replay is safe.
 await h.call('flush');r=await raw(h);const rec=(await registry(h)).records[0],p=JSON.parse(rec.projection_json);assert.equal(rec.pending,0);assert.equal(p.kind,'terminal');assert.equal(p.evidenceSha256,sha(r.row.terminal_json));assert.equal(rec.state_version,r.row.state_version);assert.equal(r.row.track_outbox_json,null);
 const launches=count(r,'launch');await h.restart(true);await h.call('reconcile');assert.equal(count(await raw(h),'launch'),launches);
});
test('version-zero-orphan-is-read-only-and-remains-pending',async h=>{
 await registered(h);const t=await ticket(h,'0');assert.deepEqual(await h.call('recoverKnown',{receipt:h.receipt,ticket:t}),{status:'empty_orphan'});
 const r=await raw(h);assert.equal(r.row,null);assert.equal(r.fence.length,0);assert.equal(r.calls.length,0);assert.equal((await registry(h)).records[0].pending,1);
});
test('positive-missing-ledger-persists-fence-without-authority',async h=>{
 await registered(h);await command(h);const v=(await registry(h)).records[0].state_version,t=await ticket(h,v);await h.call('deleteRow');
 assert.deepEqual(await h.call('recoverKnown',{receipt:h.receipt,ticket:t}),{status:'quarantined'});let r=await raw(h);assert.equal(r.row,null);assert.equal(r.fence.length,1);
 assert.equal((await h.call('enroll')).status,'missing');await h.restart(true);assert.deepEqual(await command(h),{status:'error',code:'unavailable'});r=await raw(h);assert.equal(r.row,null);assert.equal(r.fence.length,1);
});
test('regressed-ledger-and-registry-ahead-never-reconstruct-authority',async h=>{
 await registered(h);await command(h);const v=(await registry(h)).records[0].state_version,t=await ticket(h,v);await h.call('regress');
 assert.deepEqual(await h.call('recoverKnown',{receipt:h.receipt,ticket:t}),{status:'quarantined'});const r=await raw(h);assert.equal(r.row.quarantined,1);assert.equal(r.fence.length,1);assert.equal(count(r,'launch'),1);
});
test('registry-newer-watermark-quarantines-flush',async h=>{
 await registered(h);await command(h);const row=(await raw(h)).row;
 assert.equal((await h.call('forceTrack',{input:{receipt:h.receipt,stateVersion:String(BigInt(row.state_version)+10n),projection:{kind:'pending',nextDueUs:null}}})).status,'accepted');
 await command(h,'query');await h.call('flush');const r=await raw(h);assert.equal(r.row.quarantined,1);assert.equal(r.fence.length,1);assert.equal(count(r,'launch'),1);
});
for(const version of [1,2])test('schema-'+version+'-migration-preserves-v2-safety-and-enrollment-quarantine',async h=>{
 await registered(h);await command(h);await h.call('claim');const m=await h.call('legacy',{version});
 for(const [key,value] of Object.entries(m.before)){if(['pending_identity_json','registration_json','registry_ack_version','effect_barrier_version','claim_barrier_version','track_outbox_json','quarantined'].includes(key))continue;if(key==='clock_floor'&&version===1){assert.equal(m.after.clock_floor,m.before.clock_lower);continue;}assert.deepEqual(m.after[key],value,key);}
 assert.equal(m.after.quarantined,1);assert.equal(m.after.registration_json,null);assert.equal((await h.call('enroll')).status,'enrolled');const r=await raw(h);assert.equal(r.row.quarantined,1);assert.ok(r.row.registration_json);assert.equal((await h.call('claim')).granted,false);
 await h.call('reconcile');assert.equal(count(await raw(h),'launch'),1);
});
test('legacy-durable-stop-cleanup-survives-migration-outage',async h=>{
 await registered(h);await command(h,'stop');await h.call('legacy',{version:2});await mode(h,'unavailable');await h.call('drain',{value:true});await h.call('clock',{now:'1900000000000000',qualified:false});await h.call('reconcile');
 const r=await raw(h);assert.equal(r.row.quarantined,1);assert.equal(r.row.terminal_json,null);assert.equal(r.row.phase,'stop_pending');assert.ok(r.row.track_outbox_json);assert.equal(count(r,'launch'),0);
});
test('partial-metadata-and-missing-safety-table-fail-closed',async h=>{
 await registered(h);await command(h);const r=await h.call('partialMetadata');assert.equal(r.unavailable,true);assert.ok(r.row);assert.equal(r.row.provider_key,fixed.operationKey);assert.equal(r.row.launch_dispatched,1);
});
test('schema3-missing-safety-table-is-unavailable',async h=>{assert.equal((await h.call('missingSafetyTable')).unavailable,true);});
test('SIGKILL-durable-intent-recovers-persisted-outbox-on-known-identity',async h=>{
 await registered(h);await h.call('inject',{point:'after_intent'});const pending=command(h).catch(()=>null);await until(async()=>(await raw(h)).settings.blocked);
 const before=await raw(h);assert.equal(before.row.launch_dispatched,0);assert.ok(before.row.track_outbox_json);assert.equal((await registry(h)).records[0].state_version,'0');
 await h.restart(true);await pending;const t=await ticket(h,'0');assert.equal((await h.call('recoverKnown',{receipt:h.receipt,ticket:t})).status,'pending');const after=await raw(h);assert.equal(count(after,'launch'),1);assert.equal(after.row.provider_key,before.row.provider_key);assert.equal(after.row.track_outbox_json,null);
});
test('preregistration-wait-cannot-refresh-expired-authority',async h=>{
 await registered(h);await h.call('inject',{point:'after_registration_validated'});const pending=command(h);await until(async()=>(await raw(h)).settings.blocked);
 await h.call('clock',{now:base.guard.expires_at_us});await h.call('release');assert.deepEqual(await pending,{status:'error',code:'stale'});assert.equal((await raw(h)).row,null);assert.equal((await registry(h)).records[0].state_version,'0');
});
test('retained-registration-does-not-reregister-existing-stop',async h=>{
 await registered(h);await command(h);await mode(h,'register_unavailable');await command(h,'stop',{guard:{epoch:'2',owner_id:'stop-owner'}});const r=await raw(h);assert.equal(r.row.desired,'stop');assert.equal(count(r,'stop'),1);assert.equal(count(r,'launch'),1);
});
test('concurrent-newer-stop-wins-consumed-claim-barrier',async h=>{
 await registered(h);await command(h);await mode(h,'hold_after_once');const pending=h.call('claim');await until(async()=>(await registry(h)).settings.blocked);
 await command(h,'stop',{guard:{epoch:'2',owner_id:'stop-owner'}});await h.call('registry',{command:'release'});assert.deepEqual(await pending,{granted:false});const r=await raw(h);assert.equal(r.row.desired,'stop');assert.equal(r.row.claim_state,'consumed');assert.equal(count(r,'launch'),1);
});
test('recovery-full-identity-disagreement-persists-quarantine',async h=>{
 await registered(h);await command(h);const v=(await registry(h)).records[0].state_version,t=await ticket(h,v);
 assert.deepEqual(await h.call('recoverKnown',{identity:{...fixed,immutableSha256:'f'.repeat(64)},receipt:h.receipt,ticket:t}),{status:'quarantined'});const r=await raw(h);assert.equal(r.fence.length,1);assert.equal(r.row.quarantined,1);assert.equal(count(r,'launch'),1);
});
test('recovery-retained-receipt-disagreement-persists-quarantine',async h=>{
 await registered(h);await command(h);const v=(await registry(h)).records[0].state_version,t=await ticket(h,v);
 assert.deepEqual(await h.call('recoverKnown',{receipt:{...h.receipt,recordId:'f'.repeat(32)},ticket:t}),{status:'quarantined'});const r=await raw(h);assert.equal(r.fence.length,1);assert.equal(r.row.quarantined,1);
});
test('terminal-hash-recheck-rejects-newer-local-version-before-track',async h=>{
 await registered(h);await command(h,'stop');await h.call('drain',{value:true});await mode(h,'drop_before_once',2);await h.call('reconcile');
 const before=await raw(h);assert.ok(before.row.terminal_json);assert.ok(before.row.track_outbox_json);assert.equal((await registry(h)).records[0].pending,1);
 await h.call('inject',{point:'before_track'});const flushing=h.call('flush');await until(async()=>(await raw(h)).settings.blocked);
 await command(h,'query',{guard:{epoch:'2',owner_id:'terminal-reader'}});const newer=await raw(h);assert.ok(BigInt(newer.row.state_version)>BigInt(before.row.state_version));assert.equal(newer.row.terminal_json,before.row.terminal_json);
 await h.call('release');assert.deepEqual(await flushing,{flushed:false});assert.equal((await registry(h)).records[0].pending,1);await h.call('flush');const rec=(await registry(h)).records[0];assert.equal(rec.state_version,newer.row.state_version);assert.equal(JSON.parse(rec.projection_json).evidenceSha256,sha(newer.row.terminal_json));
});
test('clock-rollback-quarantines-without-new-launch-or-claim',async h=>{
 await registered(h);await command(h);const before=await raw(h);await h.call('clock',{now:'1800000000000000'});await h.call('reconcile');const r=await raw(h);assert.equal(r.row.quarantined,1);assert.equal(r.row.clock_floor,before.row.clock_floor);assert.equal(count(r,'launch'),1);assert.equal((await h.call('claim')).granted,false);
});
test('SIGKILL-consumed-claim-outbox-never-regrants',async h=>{
 await registered(h);await command(h);await h.call('inject',{point:'after_claim_commit'});const pending=h.call('claim').catch(()=>null);await until(async()=>(await raw(h)).settings.blocked);
 const before=await raw(h);assert.equal(before.row.claim_state,'consumed');assert.ok(before.row.track_outbox_json);await h.restart(true);await pending;assert.equal((await h.call('claim')).granted,false);const r=await raw(h);assert.equal(r.row.claim_id,before.row.claim_id);assert.equal(r.row.claim_state,'consumed');assert.equal(count(r,'launch'),1);
});
test('higher-terminal-clock-version-keeps-identical-permanent-projection',async h=>{
 await registered(h);await h.call('drain',{value:true});await command(h,'stop');const before=await raw(h);assert.equal((await registry(h)).records[0].pending,0);assert.ok(before.row.terminal_json);
 await command(h,'query',{guard:{epoch:'2',owner_id:'terminal-reader'}});assert.deepEqual(await h.call('flush'),{flushed:true});const after=await raw(h),rec=(await registry(h)).records[0];assert.equal(after.row.quarantined,0);assert.equal(rec.pending,0);assert.equal(rec.state_version,after.row.state_version);assert.equal(after.row.terminal_json,before.row.terminal_json);assert.equal(JSON.parse(rec.projection_json).evidenceSha256,sha(after.row.terminal_json));
});
let failed=false;
try{for(const {id,fn} of cases){const h=await harness(base,fixed);try{await fn(h);results.push({id,status:'passed'});console.log(JSON.stringify({id,status:'passed'}));}catch(e){results.push({id,status:'failed',error:e.stack??String(e)});throw e;}finally{await h.close();}}}catch(e){failed=true;console.error(e);process.exitCode=1;}
finally{const report={status:failed?'failed':'passed',scope:'isolated actual-workerd/SQLite operation plus fixed registry component binding; excluded clock/provider/hooks; automatic alarms suppressed',cases:cases.length,results,cleanup,limitations:['no-public-ingress-or-scheduled-entry-wiring','no-production-qualified-clock-or-provider','no-schedule-installation','no-native-or-physical-device-evidence','no-deployment-or-GA-acceptance']};await writeFile(process.env.MIXER_PENDING_ENGINE_REPORT??resolve(import.meta.dirname,'../../test-report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,groups:results.length,cleanup:cleanup.length}));}
