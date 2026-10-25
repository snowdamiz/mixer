// Owned V2 fixtures. Every assertion runs through actual workerd fetch and SQLite.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
const here=process.env.MIXER_V2_RUN_DIR;
const bindings=JSON.parse(await readFile(join(here,'bindings.json'),'utf8'));
const {createHarness,cleanupReceipts}=await import(pathToFileURL(join(bindings.scratch,'hosted-worker-controller/test/acceptance-driver.mjs')));
const packet=JSON.parse(await readFile(join(bindings.scratch,'verification/hosted-worker-controller-contract/vectors.json'),'utf8'));
const clone=structuredClone,base=()=>clone(packet.cases[0].request),N=1900000000000000n,L=1950000000000000n,MAX=9223372036854775807n;
const clock=(n,error=1n,qualificationId='synthetic-verification-only')=>({nowUs:String(n),errorUs:String(error),qualified:true,qualificationId});
const obs=r=>{assert.equal(r.httpStatus,200);return r.body.observation;};
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function eventually(fn){for(let i=0;i<150;i++){if(await fn())return;await delay(10);}throw new Error('v2_barrier_timeout');}
const cases=[],test=(id,fn)=>cases.push({id,fn});
const ensure=async h=>{const r=base();r.command='ensure_started';await h.command(r);assert.equal((await h.snapshot()).phase,'inert');return r;};
const claim=h=>h.claim({instanceId:'instance-1',bootId:'boot-1'});
async function pendingClaim(h){await h.inject('after_claim_commit','barrier');const pending=claim(h);await eventually(async()=>!!(await h.raw()).settings.barrier);return {pending};}
function reportFor(row){return {identity:{provider:row.provider_kind,key:row.provider_key,immutableSha256:row.binding_hash},immutableSha256:row.binding_hash,instanceId:row.instance_id,bootId:row.boot_id,claimId:row.claim_id,operationId:row.operation_id,result:{outcome:'failed',class:'compiler',code:'compiler_error',diagnostic_sha256:'a'.repeat(64)},attestationSha256:'a'.repeat(64)};}
const core=row=>Object.fromEntries(['operation_id','binding','binding_hash','request_json','epoch','revision','owner','expiry_us','provider_kind','provider_key','claim_state','claim_id','instance_id','boot_id','desired','terminal_json','report_hash','pending_result_json','launch_dispatched'].map(k=>[k,row[k]]));

test('final-grant-exact-time-is-durable-after-response-and-SIGKILL',async(h,e)=>{
 await ensure(h);const {pending}=await pendingClaim(h);
 await h.control('clock',clock(L));await h.control('release',{});
 const granted=await pending;assert.equal(granted.granted,true);await h.hardRestart();
 const row=(await h.raw()).row;assert.equal(row.claim_id,granted.claimId);assert.equal(row.claim_state,'consumed');assert.equal(row.clock_lower,String(L-1n));assert.equal(row.clock_upper,String(L+1n));assert.equal(row.clock_floor,String(L-1n));
 assert.equal((await claim(h)).granted,false);
 await h.control('clock',clock(N+100n));const q=base();q.command='query';assert.deepEqual(obs(await h.command(q)),{status:'error',code:'unavailable'});assert.equal((await h.raw()).row.quarantined,1);e.push({granted,row});
});
test('equal-pair-forward-expiry-renewal-denies-old-callback-permanently',async(h,e)=>{
 const r=await ensure(h),{pending}=await pendingClaim(h);const next=clone(r);next.command='query';next.guard.expires_at_us=String(BigInt(r.guard.expires_at_us)+100n);await h.command(next);await h.control('release',{});
 assert.equal((await pending).granted,false);await h.hardRestart();assert.equal((await claim(h)).granted,false);assert.equal((await h.snapshot()).claimState,'consumed');e.push((await h.raw()).row);
});
test('rejected-wrong-owner-request-does-not-cancel-current-grant',async h=>{
 const r=await ensure(h),{pending}=await pendingClaim(h);const before=(await h.raw()).row;const stale=clone(r);stale.command='query';stale.guard.revision='1';stale.guard.owner_id='other';
 assert.deepEqual(obs(await h.command(stale)),{status:'error',code:'stale'});assert.deepEqual((await h.raw()).row,before);await h.control('release',{});assert.equal((await pending).granted,true);
});
for(const field of ['claim_id','instance_id','boot_id','provider_key','provider_kind','operation_id','binding_hash','binding'])test('final-grant-compares-exact-'+field,async(h,e)=>{
 await ensure(h);const {pending}=await pendingClaim(h);await h.control('claimIdentityFixture',{field});await h.control('release',{});assert.equal((await pending).granted,false);assert.equal((await h.raw()).row.claim_state,'consumed');e.push({field,row:(await h.raw()).row});
});
for(const mode of ['expired','unqualified','rollback'])test('final-grant-'+mode+'-denies-with-permanent-consumption',async(h,e)=>{
 const r=await ensure(h),{pending}=await pendingClaim(h);
 await h.control('clock',mode==='expired'?clock(BigInt(r.guard.expires_at_us),0n):mode==='unqualified'?{...clock(L),qualified:false}:clock(N-100n));await h.control('release',{});
 assert.equal((await pending).granted,false);const row=(await h.raw()).row;assert.equal(row.claim_state,'consumed');if(mode==='rollback')assert.equal(row.quarantined,1);
 await h.restart();assert.equal((await claim(h)).granted,false);e.push({mode,row});
});
test('later-reconcile-sample-survives-SIGKILL-and-rejects-rollback',async(h,e)=>{
 await ensure(h);await h.control('clock',clock(L));await h.reconcile();await h.hardRestart();
 const before=(await h.raw()).row;assert.equal(before.clock_floor,String(L-1n));await h.control('clock',clock(N+100n));assert.equal((await claim(h)).granted,false);assert.equal((await h.raw()).row.quarantined,1);e.push({before,after:(await h.raw()).row});
});
test('provider-observation-callback-retains-new-qualified-time',async(h,e)=>{
 const r=base();r.command='ensure_started';await h.inject('after_provider_effect','barrier');const pending=h.command(r);await eventually(async()=>!!(await h.raw()).settings.barrier);
 await h.control('clock',clock(L));await h.control('release',{});await pending;assert.equal((await h.snapshot()).phase,'inert');await h.restart();assert.equal((await h.raw()).row.clock_floor,String(L-1n));
 await h.control('clock',clock(N+100n));assert.equal((await claim(h)).granted,false);assert.equal((await h.raw()).row.quarantined,1);e.push((await h.raw()).row);
});
test('pre-provider-final-check-retains-qualified-time',async(h,e)=>{
 const r=base();r.command='ensure_started';await h.control('clock',clock(L));await h.control('sequence',{sequence:[clock(N),clock(N),clock(L)]});await h.command(r);
 assert.equal((await h.raw()).row.clock_floor,String(L-1n));assert.equal(h.calls().filter(x=>x.kind==='launch').length,1);e.push((await h.raw()).row);
});
test('report-acceptance-sample-persists-with-stop-and-consumed-identity',async(h,e)=>{
 await ensure(h);assert.equal((await claim(h)).granted,true);const report=reportFor((await h.raw()).row);await h.control('objects',{value:true});await h.control('clock',clock(L));
 assert.equal((await h.control('report',report)).status,'accepted');await h.hardRestart();const row=(await h.raw()).row;assert.equal(row.clock_floor,String(L-1n));assert.equal(row.desired,'stop');assert.equal(row.claim_state,'consumed');assert(row.report_hash);assert(row.pending_result_json);
 await h.control('clock',{...clock(N),qualified:false});await h.deliverProvider({state:'absent',definitive:true,descendantsGone:true,launchesSettled:true});await h.reconcile();assert.equal((await h.snapshot()).terminal.status,'completed');e.push(row);
});
test('time-history-write-preserves-result-state-version-CAS',async(h,e)=>{
 await ensure(h);await claim(h);const report=reportFor((await h.raw()).row);await h.control('objects',{value:true});await h.inject('before_object_verify_return','barrier');const pending=h.control('report',report);await eventually(async()=>!!(await h.raw()).settings.barrier);
 const before=(await h.raw()).row;await h.control('clock',clock(L));await h.reconcile();const during=(await h.raw()).row;assert(BigInt(during.state_version)>BigInt(before.state_version));await h.control('release',{});assert.equal((await pending).status,'rejected');assert.equal((await h.raw()).row.report_hash,null);
 assert.equal((await h.control('report',report)).status,'accepted');e.push({beforeVersion:before.state_version,afterVersion:during.state_version,clockFloor:during.clock_floor});
});
test('newer-stop-during-result-verifier-preserves-stop-wins',async h=>{
 const r=await ensure(h);await claim(h);const report=reportFor((await h.raw()).row);await h.control('objects',{value:true});await h.inject('before_object_verify_return','barrier');const pending=h.control('report',report);await eventually(async()=>!!(await h.raw()).settings.barrier);
 const stop=clone(r);stop.command='stop';stop.guard.epoch='2';stop.guard.owner_id='successor';await h.command(stop);await h.control('release',{});assert.equal((await pending).status,'rejected');assert.equal((await h.raw()).row.report_hash,null);assert.equal((await h.snapshot()).desired,'stop');
});
test('overlapping-intervals-preserve-latest-exact-sample-without-ratcheting-history',async(h,e)=>{
 const r=base();await h.command(r);const first=(await h.raw()).row;await h.control('clock',clock(N,50n,'qualified-second'));await h.command(r);const overlapping=(await h.raw()).row;
 assert.equal(overlapping.clock_lower,String(N-50n));assert.equal(overlapping.clock_upper,String(N+50n));assert.equal(overlapping.clock_floor,first.clock_floor);assert.equal(overlapping.clock_qualification,'qualified-second');await h.restart();
 await h.control('clock',clock(N-50n,40n,'qualified-third'));assert.deepEqual(obs(await h.command(r)),{status:'error',code:'unavailable'});const after=(await h.raw()).row;assert.equal(after.quarantined,1);assert.equal(after.clock_floor,first.clock_floor);assert.equal(after.clock_lower,overlapping.clock_lower);e.push({first,overlapping,after});
});
test('interval-touching-history-floor-is-accepted-without-clamping',async(h,e)=>{
 const r=base();await h.command(r);await h.control('clock',clock(N-51n,50n));assert.deepEqual(obs(await h.command(r)),{status:'absent'});const row=(await h.raw()).row;
 assert.equal(row.clock_lower,String(N-101n));assert.equal(row.clock_upper,String(N-1n));assert.equal(row.clock_floor,String(N-1n));assert.equal(row.quarantined,0);e.push(row);
});
test('qualification-id-change-cannot-reset-historical-floor',async h=>{
 const r=base();await h.command(r);await h.control('clock',clock(N-100n,1n,'different-qualified-receipt'));assert.deepEqual(obs(await h.command(r)),{status:'error',code:'unavailable'});assert.equal((await h.raw()).row.quarantined,1);
});
test('expired-and-stale-requests-retain-zero-write-semantics',async h=>{
 const r=base();await h.command(r);const before=(await h.raw()).row;await h.control('clock',clock(L));const expired=clone(r);expired.guard.expires_at_us=String(N-1n);assert.deepEqual(obs(await h.command(expired)),{status:'error',code:'stale'});assert.deepEqual((await h.raw()).row,before);
 const newerExpired=clone(r);newerExpired.guard.epoch='2';newerExpired.guard.owner_id='successor';newerExpired.guard.expires_at_us=String(L-1n);assert.deepEqual(obs(await h.command(newerExpired)),{status:'error',code:'stale'});assert.deepEqual((await h.raw()).row,before);
});
test('expiry-uses-exact-new-sample-rather-than-historical-floor',async h=>{
 const r=base();r.command='ensure_started';r.guard.expires_at_us=String(N+5n);await h.command(r);assert.equal((await h.snapshot()).phase,'inert');await h.control('clock',clock(N,10n));assert.equal((await claim(h)).granted,false);assert.equal((await h.snapshot()).claimState,'unissued');
});
test('maximum-int64-clock-floor-keeps-exact-TEXT-and-no-wraparound',async(h,e)=>{
 const r=base();r.guard.expires_at_us=String(MAX);r.deadline_ms=String(MAX);const f=r.ref,s=r.spec;r.immutable_sha256=createHash('sha256').update(JSON.stringify(['mixer-worker-binding-v1',r.operation_id,r.guard.record_id,[f.organization_id,f.project_id,f.application_id,f.build_id,f.platform,f.attempt,f.fence],[s.organization_id,s.project_id,s.application_id,s.build_id,s.platform,s.source.kind,s.source.sha256,s.source.reference,s.toolchain_lock_sha256,s.build_definition_sha256],r.deadline_ms])).digest('hex');
 await h.control('clock',clock(MAX-2n,0n));assert.deepEqual(obs(await h.command(r)),{status:'absent'});await h.restart();const row=(await h.raw()).row;assert.equal(row.clock_floor,String(MAX-2n));assert.deepEqual((await h.control('schemaInfo',{})).floorType,[{value:'text'}]);await h.control('clock',clock(MAX-3n,0n));assert.deepEqual(obs(await h.command(r)),{status:'error',code:'unavailable'});e.push(row);
});
test('invalid-clock-upper-overflow-is-unavailable-without-write',async h=>{
 const r=base();await h.command(r);const row=(await h.raw()).row;await h.control('clock',clock(MAX,1n));assert.deepEqual(obs(await h.command(r)),{status:'error',code:'unavailable'});assert.deepEqual((await h.raw()).row,row);
});
test('state-version-overflow-rolls-back-claim-and-time-history-atomically',async(h,e)=>{
 await ensure(h);await h.control('stateVersionMaxFixture',{});const before=(await h.raw()).row;await h.control('clock',clock(L));assert.notEqual((await claim(h)).granted,true);assert.deepEqual((await h.raw()).row,before);assert.equal(before.claim_state,'unissued');e.push(before);
});
test('final-state-version-overflow-never-returns-grant-or-resets-consumption',async(h,e)=>{
 await ensure(h);const {pending}=await pendingClaim(h);await h.control('stateVersionMaxFixture',{});const before=(await h.raw()).row;await h.control('clock',clock(L));await h.control('release',{});assert.notEqual((await pending).granted,true);assert.deepEqual((await h.raw()).row,before);assert.equal(before.claim_state,'consumed');await h.restart();assert.equal((await claim(h)).granted,false);e.push(before);
});
for(const mode of ['unissued','consumed','stop-consumed','terminal-stop'])test('schema1-'+mode+'-migration-preserves-identity-and-quarantines',async(h,e)=>{
 const r=await ensure(h);if(mode!=='unissued')await claim(h);if(mode.includes('stop')){const stop=clone(r);stop.command='stop';await h.command(stop);}
 if(mode==='terminal-stop'){await h.deliverProvider({state:'absent',definitive:true,descendantsGone:true,launchesSettled:true});await h.reconcile();assert.equal((await h.snapshot()).terminal.status,'stopped');}
 const before=(await h.raw()).row;await h.control('schema1Fixture',{});await h.restart();const after=(await h.raw()).row;
 assert.deepEqual(core(after),core(before));assert.equal(after.quarantined,1);assert.equal(after.clock_floor,before.clock_lower);assert(BigInt(after.state_version)>BigInt(before.state_version));assert.deepEqual((await h.control('schemaInfo',{})).schema,[{version:2}]);assert.equal((await claim(h)).granted,false);
 const next=clone(r);next.guard.epoch='2';next.guard.owner_id='successor';assert.deepEqual(obs(await h.command(next)),{status:'error',code:'unavailable'});
 if(mode==='stop-consumed'){await h.control('clock',{...clock(N-100n),qualified:false});await h.deliverProvider({state:'absent',definitive:true,descendantsGone:true,launchesSettled:true});const count=h.calls().filter(x=>x.kind==='stop').length;await h.reconcile();assert(h.calls().filter(x=>x.kind==='stop').length>count);assert.equal((await h.snapshot()).terminal.status,'stopped');assert.equal((await h.snapshot()).claimState,'consumed');}
 e.push({mode,before,after});
});
test('empty-schema1-upgrades-without-inventing-or-quarantining-operation',async h=>{
 await h.control('schema1Fixture',{});await h.restart();assert.deepEqual(await h.snapshot(),{exists:false});assert.deepEqual((await h.control('schemaInfo',{})).schema,[{version:2}]);assert.deepEqual(obs(await h.command(base())),{status:'absent'});assert.equal((await h.raw()).row.quarantined,0);
});
test('unknown-schema-is-unavailable-and-preserves-all-row-bytes',async(h,e)=>{
 await ensure(h);await claim(h);const before=(await h.raw()).row;await h.control('unknownSchemaFixture',{});assert.deepEqual(await h.control('unknownSchemaCheck',{}),{unavailable:true});assert.deepEqual((await h.raw()).row,before);e.push(before);
});
test('rollback-quarantine-can-still-enforce-committed-stop',async(h,e)=>{
 const r=await ensure(h);await claim(h);r.command='stop';await h.command(r);await h.control('clock',clock(N-100n));await h.reconcile();assert.equal((await h.raw()).row.quarantined,1);assert.equal((await h.snapshot()).desired,'stop');
 await h.control('clock',{...clock(N-100n),qualified:false});await h.deliverProvider({state:'absent',definitive:true,descendantsGone:true,launchesSettled:true});const count=h.calls().filter(x=>x.kind==='stop').length;await h.reconcile();assert(h.calls().filter(x=>x.kind==='stop').length>count);assert.equal((await h.snapshot()).terminal.status,'stopped');assert.equal((await h.snapshot()).claimState,'consumed');assert.equal((await claim(h)).granted,false);e.push((await h.raw()).row);
});
const results=[];
for(const {id,fn}of cases){let h;const evidence=[];try{
 h=await createHarness({fixture:base(),nowUs:String(N),errorUs:'1',clockQualified:true});await fn(h,evidence);results.push({id,status:'passed',evidence});
}catch(error){results.push({id,status:'failed',evidence,error:{name:error.name,message:error.message,stack:error.stack}});}finally{await h?.close();}console.log(JSON.stringify(results.at(-1)));}
const report={status:results.every(x=>x.status==='passed')?'passed':'failed',scope:'V2-local-workerd-SQLite-exact-claim-time-history-migration-tests-only',source_tree_sha256:bindings.source_tree_sha256,results,cleanup:cleanupReceipts};await writeFile(join(here,'focused-report.json'),JSON.stringify(report,null,2)+'\n');process.exitCode=report.status==='passed'?0:1;
