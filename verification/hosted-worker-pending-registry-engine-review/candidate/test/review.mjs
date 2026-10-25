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
const results=[];
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function until(f){for(let i=0;i<80;i++){if(await f())return;await delay(5);}throw new Error('bounded_fixture_wait');}
const raw=h=>h.call('raw');
const registry=h=>h.call('registry',{command:'raw'});
const count=(r,k)=>r.calls.filter(c=>c.kind===k).length;
async function register(h){const r=await h.call('register');assert.equal(r.status,'registered');h.receipt=r.receipt;return r.receipt;}
function request(command='ensure_started',guard={}){return {...clone(base),command,guard:{...base.guard,...guard}};}
async function command(h,c='ensure_started',extra={}){return h.call('command',{request:request(c),receipt:h.receipt,...extra});}
async function ticket(h,version){const t=await h.call('reserve',{recordId:h.receipt.recordId,version,runId:'1'});assert.equal(t.status,'reserved');return t.ticket;}
async function run(id,fn){const h=await harness(base,fixed);try{const details=await fn(h);results.push({id,status:'passed',details});}catch(e){results.push({id,status:'failed',error:e.stack??String(e)});}finally{await h.close();}console.log(JSON.stringify(results.at(-1)));}

// These two controls preserve the incorrect behavior as a concrete counterexample,
// rather than making the runner stop before collecting independent passing controls.
await run('provider-mismatch-is-retained-dispatched-and-recovered-counterexample',async h=>{
 await register(h);
 const wrong={provider:'external-macos',key:fixed.operationKey,immutableSha256:fixed.immutableSha256};
 const response=await command(h,'ensure_started',{resource:wrong});
 const before=await raw(h);assert.equal(before.row.provider_kind,'external-macos');assert.equal(count(before,'launch'),1);assert.deepEqual(before.calls[0].identity,wrong);
 const t=await ticket(h,(await registry(h)).records[0].state_version);
 const recovery=await h.call('recoverKnown',{receipt:h.receipt,ticket:t});
 const after=await raw(h);assert.equal(recovery.status,'pending');assert.equal(count(after,'inspect'),1);assert.equal(after.fence.length,0);assert.equal(after.calls.at(-1).identity.provider,'external-macos');
 return {expected:'reject before initial row mutation; recovery quarantines mismatch',observed:response,recovery,rowProvider:before.row.provider_kind,fixtureProviderKind:'cloudflare-linux',platform:fixed.platform,launches:count(after,'launch'),inspects:count(after,'inspect'),fenceCount:after.fence.length,defectReproduced:true};
});

await run('result-verifier-await-accepts-independent-permanent-fence-counterexample',async h=>{
 await register(h);await command(h);assert.equal((await h.call('claim')).granted,true);
 await h.call('inject',{point:'during_report_verify'});const pending=h.call('report');await until(async()=>(await raw(h)).settings.blocked);
 const before=await raw(h);await h.call('fenceOnly');const fenced=await raw(h);assert.equal(fenced.row.state_version,before.row.state_version);assert.equal(fenced.row.quarantined,0);assert.equal(fenced.fence.length,1);
 await h.call('release');const response=await pending,after=await raw(h);
 assert.equal(response.status,'accepted');assert.ok(after.row.report_hash);assert.ok(after.row.pending_result_json);assert.equal(after.row.desired,'stop');assert.equal(after.fence.length,1);
 return {expected:'rejected after verifier await because independent permanent fence exists',observed:response,versionBefore:before.row.state_version,versionAfter:after.row.state_version,independentFencePersisted:true,pendingResultPersisted:true,defectReproduced:true};
});

await run('independent-fence-during-dispatch-ack-blocks-provider-launch',async h=>{
 await register(h);await h.call('registry',{command:'mode',mode:'hold_after_once',skip:1});const pending=command(h);await until(async()=>(await registry(h)).settings.blocked);
 await h.call('fenceOnly');await h.call('registry',{command:'release'});await pending;
 const after=await raw(h);assert.equal(after.row.launch_dispatched,1);assert.equal(count(after,'launch'),0);assert.equal(after.fence.length,1);
 return {markedDispatched:true,providerLaunches:0,permanentFenceRetained:true};
});

await run('independent-fence-during-stop-observation-preserves-cleanup-without-terminal',async h=>{
 await register(h);await command(h,'stop');await h.call('drain',{value:true});await h.call('inject',{point:'after_provider_effect'});
 const pending=h.call('reconcile');await until(async()=>(await raw(h)).settings.blocked);const before=await raw(h);await h.call('fenceOnly');await h.call('release');await pending;
 const after=await raw(h);assert.ok(count(after,'stop')>=2);assert.equal(after.row.terminal_json,null);assert.equal(after.row.phase,'stop_pending');assert.equal(after.fence.length,1);assert.equal(after.row.desired,'stop');
 return {stops:count(after,'stop'),terminal:null,phase:after.row.phase,providerActionsThisInvocation:count(after,'stop')-count(before,'stop')+1};
});

await run('exact-effect-and-claim-barriers-above-safe-js-integer',async h=>{
 await register(h);await command(h,'query');const version='9007199254740993';
 const track=await h.call('forceTrack',{input:{receipt:h.receipt,stateVersion:version,projection:{kind:'pending',nextDueUs:null}}});assert.equal(track.status,'accepted');
 await h.call('largeVersion',{version});await command(h);const launched=await raw(h);assert.equal(count(launched,'launch'),1);assert.ok(BigInt(launched.row.effect_barrier_version)>BigInt(version));
 assert.equal((await h.call('claim')).granted,true);const after=await raw(h);assert.equal(after.row.registry_ack_version,after.row.claim_barrier_version);assert.equal(BigInt(after.row.state_version),BigInt(after.row.claim_barrier_version)+1n);
 return {seedVersion:version,effectBarrier:launched.row.effect_barrier_version,claimBarrier:after.row.claim_barrier_version,finalVersion:after.row.state_version,exactUnackedFinalClockProjection:JSON.parse(after.row.track_outbox_json).stateVersion};
});

await run('terminal-schema2-migration-and-enrollment-preserve-result-and-quarantine',async h=>{
 await register(h);await h.call('drain',{value:true});await command(h,'stop');const before=await raw(h);assert.ok(before.row.terminal_json);
 const migration=await h.call('legacy',{version:2});assert.equal(migration.after.terminal_json,before.row.terminal_json);assert.equal(migration.after.phase,'stopped');assert.equal(migration.after.state_version,before.row.state_version);assert.equal(migration.after.quarantined,1);assert.equal(migration.after.clock_floor,before.row.clock_floor);
 assert.equal((await h.call('enroll')).status,'enrolled');const after=await raw(h);assert.equal(after.row.terminal_json,before.row.terminal_json);assert.equal(after.row.quarantined,1);assert.equal((await h.call('claim')).granted,false);assert.equal(count(after,'launch'),0);
 return {terminalBytesUnchanged:true,phase:after.row.phase,quarantineRetained:true,claimRejected:true,launches:0};
});

const report={schema:1,status:results.some(r=>r.status!=='passed')?'failed':'completed-with-two-reproduced-defects',scope:'fresh actual workerd SQLite Engine/Ledger controls on byte-identical frozen production source with excluded independent review fixtures',cases:results.length,results,cleanup,limitations:['focused controls only; original32groups not rerun','prior71controllergroups20processcontrols not rerun','no public/scheduled wiring or deployed qualification','no native/cloud/publication'],expectedProductDefects:2};
await writeFile(resolve(import.meta.dirname,'../../report.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({status:report.status,cases:results.length,cleanupEntries:cleanup.length}));
if(results.some(r=>r.status!=='passed'))process.exitCode=1;
