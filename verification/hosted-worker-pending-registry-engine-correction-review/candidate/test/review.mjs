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
const cases=[],results=[];
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function until(f){for(let i=0;i<80;i++){if(await f())return;await delay(5);}throw new Error('bounded_fixture_wait');}
const raw=h=>h.call('raw');
const registry=h=>h.call('registry',{command:'raw'});
const count=(r,k)=>r.calls.filter(c=>c.kind===k).length;
async function register(h){const r=await h.call('register');assert.equal(r.status,'registered');h.receipt=r.receipt;return r.receipt;}
function request(command='ensure_started',guard={}){return {...clone(base),command,guard:{...base.guard,...guard}};}
async function command(h,c='ensure_started',extra={}){return h.call('command',{request:request(c),receipt:h.receipt,...extra});}
const mode=(h,mode,skip=0)=>h.call('registry',{command:'mode',mode,skip});
function test(id,fn){cases.push({id,fn});}
function fenced(r){assert.equal(r.row.provider_kind,'external-macos');assert.equal(r.row.quarantined,1);assert.equal(r.fence.length,1);assert.equal(r.row.pending_result_json,null);assert.equal(r.row.report_hash,null);}

test('wrong-provider-first-start-query-stop-all-reject-before-row',async h=>{
 await register(h);const resource={provider:'external-macos',key:fixed.operationKey,immutableSha256:fixed.immutableSha256};
 for(const c of ['ensure_started','query','stop']){assert.deepEqual(await command(h,c,{resource}),{status:'error',code:'unavailable'});const r=await raw(h);assert.equal(r.row,null);assert.equal(r.calls.length,0);assert.equal(r.fence.length,0);}
});
for(const action of ['flush','claim','report','enroll'])test('retained-wrong-provider-'+action+'-fences',async h=>{
 await register(h);await command(h);if(action==='report')assert.equal((await h.call('claim')).granted,true);const before=await raw(h);await h.call('providerMismatch');
 const response=await h.call(action);if(action==='claim')assert.equal(response.granted,false);if(action==='report')assert.equal(response.status,'rejected');if(action==='enroll')assert.equal(response.status,'conflict');
 const after=await raw(h);fenced(after);assert.equal(after.calls.length,before.calls.length);assert.equal(after.row.provider_key,before.row.provider_key);
});
test('constructor-recovery-provider-mismatch-fences-without-action',async h=>{
 await register(h);await command(h);const before=await raw(h);await h.call('providerMismatch');await h.restart();const after=await raw(h);fenced(after);assert.equal(after.calls.length,before.calls.length);
});
for(const c of ['ensure_started','stop'])test('provider-mismatch-during-final-dispatch-barrier-'+c,async h=>{
 await register(h);await mode(h,'hold_after_once',1);const pending=command(h,c);await until(async()=>(await registry(h)).settings.blocked);const before=await raw(h);await h.call('providerMismatch');await h.call('registry',{command:'release'});await pending;
 const after=await raw(h);fenced(after);assert.equal(after.calls.length,before.calls.length);assert.equal(after.row.terminal_json,null);
});
test('provider-mismatch-after-provider-observation-fences-without-acceptance',async h=>{
 await register(h);await h.call('inject',{point:'after_provider_effect'});const pending=command(h);await until(async()=>(await raw(h)).settings.blocked);const before=await raw(h);assert.equal(count(before,'launch'),1);await h.call('providerMismatch');await h.call('release');await pending;
 const after=await raw(h);fenced(after);assert.equal(after.row.instance_id,null);assert.equal(after.calls.length,1);
});
test('provider-mismatch-after-consumed-claim-commit-never-grants',async h=>{
 await register(h);await command(h);await h.call('inject',{point:'after_claim_commit'});const pending=h.call('claim');await until(async()=>(await raw(h)).settings.blocked);const before=await raw(h);assert.equal(before.row.claim_state,'consumed');await h.call('providerMismatch');await h.call('release');assert.equal((await pending).granted,false);
 const after=await raw(h);fenced(after);assert.equal(after.row.claim_id,before.row.claim_id);assert.equal(after.row.claim_state,'consumed');assert.equal(after.calls.length,before.calls.length);
});
test('provider-mismatch-during-enrollment-register-await-fences',async h=>{
 await register(h);await command(h,'query');await mode(h,'review_register_hold');const pending=h.call('enroll');await until(async()=>(await registry(h)).settings.blocked);const before=await raw(h);await h.call('providerMismatch');await h.call('registry',{command:'release'});assert.equal((await pending).status,'conflict');const after=await raw(h);fenced(after);assert.equal(after.row.registration_json,before.row.registration_json);assert.equal(after.calls.length,0);
});

const snapshotFields=['epoch','revision','expiry_us','clock_lower','clock_upper','clock_qualification','clock_floor','claim_state','phase','effect_id','effect_kind','effect_request_json','effect_state','effect_barrier_version','launch_dispatched','quarantined','desired','report_hash','pending_result_json','terminal_json'];
for(const field of snapshotFields)test('verifier-await-same-version-restore-'+field+'-rejects',async h=>{
 await register(h);await command(h);assert.equal((await h.call('claim')).granted,true);await h.call('inject',{point:'during_report_verify'});const pending=h.call('report');await until(async()=>(await raw(h)).settings.blocked);const before=await raw(h);await h.call('reviewMutation',{field});const restored=await raw(h);assert.notEqual(restored.row[field],before.row[field]);assert.equal(restored.row.state_version,before.row.state_version);
 await h.call('release');assert.equal((await pending).status,'rejected');const after=await raw(h);assert.equal(after.row.state_version,restored.row.state_version);assert.equal(after.row.report_hash,restored.row.report_hash);assert.equal(after.row.pending_result_json,restored.row.pending_result_json);assert.equal(after.row.desired,restored.row.desired);
});
for(const field of ['registration_json','pending_identity_json','binding','binding_hash','provider_key','provider_kind','operation_id','claim_id','instance_id','boot_id','claim_barrier_version','owner','request_json'])test('verifier-await-retained-identity-'+field+'-rejects',async h=>{
 await register(h);await command(h);assert.equal((await h.call('claim')).granted,true);await h.call('inject',{point:'during_report_verify'});const pending=h.call('report');await until(async()=>(await raw(h)).settings.blocked);const before=await raw(h);await h.call('reportBindingMutation',{field});assert.equal((await raw(h)).row.state_version,before.row.state_version);await h.call('release');assert.equal((await pending).status,'rejected');const after=await raw(h);assert.equal(after.row.report_hash,null);assert.equal(after.row.pending_result_json,null);if(field==='provider_kind')fenced(after);
});
test('verifier-await-independent-permanent-fence-rejects',async h=>{
 await register(h);await command(h);await h.call('claim');await h.call('inject',{point:'during_report_verify'});const pending=h.call('report');await until(async()=>(await raw(h)).settings.blocked);const before=await raw(h);await h.call('fenceOnly');const restored=await raw(h);assert.equal(restored.row.state_version,before.row.state_version);assert.equal(restored.row.quarantined,0);await h.call('release');assert.equal((await pending).status,'rejected');const after=await raw(h);assert.equal(after.row.state_version,before.row.state_version);assert.equal(after.row.report_hash,null);assert.equal(after.row.pending_result_json,null);assert.equal(after.row.desired,'run');
});
test('verifier-await-delivery-only-ack-outbox-progress-accepts',async h=>{
 await register(h);await command(h);await h.call('claim');await h.call('inject',{point:'during_report_verify'});const pending=h.call('report');await until(async()=>(await raw(h)).settings.blocked);const before=await raw(h);assert.ok(before.row.track_outbox_json);await h.call('flush');const delivered=await raw(h);assert.equal(delivered.row.state_version,before.row.state_version);assert.equal(delivered.row.track_outbox_json,null);assert.equal(delivered.row.registry_ack_version,delivered.row.state_version);await h.call('release');assert.equal((await pending).status,'accepted');const after=await raw(h);assert.equal(after.row.desired,'stop');assert.ok(after.row.report_hash);assert.ok(after.row.pending_result_json);assert.equal(after.fence.length,0);
});
test('same-version-provider-restore-during-terminal-track-boundary',async h=>{
 await register(h);await h.call('drain',{value:true});await mode(h,'drop_before_once',2);await command(h,'stop');const initial=await raw(h);assert.ok(initial.row.terminal_json);assert.ok(initial.row.track_outbox_json);assert.equal((await registry(h)).records[0].pending,1);
 await h.call('inject',{point:'before_track'});const pending=h.call('flush');await until(async()=>(await raw(h)).settings.blocked);const before=await raw(h);await h.call('providerMismatch');const restored=await raw(h);assert.equal(restored.row.state_version,before.row.state_version);await h.call('release');const response=await pending;const after=await raw(h),rec=(await registry(h)).records[0];
 const mismatchBypassed=after.row.provider_kind==='external-macos'&&after.row.quarantined===0&&after.fence.length===0&&rec.pending===0&&after.row.track_outbox_json===null;
 if(mismatchBypassed)return {productStatus:'changes-required',finding:'P1-provider-mismatch-after-pre-track-await-not-fenced',response,version:after.row.state_version,provider:after.row.provider_kind,quarantined:after.row.quarantined,fenceCount:after.fence.length,registryPending:rec.pending,trackOutbox:after.row.track_outbox_json};
 fenced(after);assert.equal(rec.pending,1);return {productStatus:'passed'};
});
for(const {id,fn} of cases){const h=await harness(base,fixed);try{const details=await fn(h);results.push({id,status:'passed',details:details??null});}catch(e){results.push({id,status:'failed',error:e.stack??String(e)});}finally{await h.close();}console.log(JSON.stringify(results.at(-1)));}
const findings=results.filter(r=>r.details?.productStatus==='changes-required');
const report={schema:1,status:results.some(r=>r.status==='failed')?'harness-failed':findings.length?'changes-required':'focused-review-passed',scope:'independent focused actual workerd/SQLite controls on byte-identical correction production source; excluded finite fixtures',cases:cases.length,harnessAssertionsPassed:results.filter(r=>r.status==='passed').length,productFindings:findings.length,results,cleanup,original54Rerun:false,live71Rerun:false,live20Rerun:false};
await writeFile(resolve(import.meta.dirname,'../../report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,cases:cases.length,productFindings:findings.length,cleanup:cleanup.length}));
if(results.some(r=>r.status==='failed'))process.exitCode=1;
