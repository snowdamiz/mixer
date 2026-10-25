// Independent adversarial decisions through copied workerd/SQLite only.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
const here=process.env.MIXER_V2_RUN_DIR,bindings=JSON.parse(await readFile(join(here,'bindings.json'),'utf8'));
const {createHarness,cleanupReceipts}=await import(pathToFileURL(join(bindings.scratch,'hosted-worker-controller/test/acceptance-driver.mjs')));
const vectors=JSON.parse(await readFile(join(bindings.scratch,'verification/hosted-worker-controller-contract/vectors.json'),'utf8'));
const clone=structuredClone,base=()=>clone(vectors.cases[0].request),N=1900000000000000n,L=1950000000000000n;
const clock=(n,error=1n,qualificationId='independent-local-qualification')=>({nowUs:String(n),errorUs:String(error),qualified:true,qualificationId});
const obs=r=>{assert.equal(r.httpStatus,200);return r.body.observation;};
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function barrier(h){for(let i=0;i<150;i++){if((await h.raw()).settings.barrier)return;await delay(10);}throw new Error('independent_barrier_timeout');}
const cases=[],test=(id,fn)=>cases.push({id,fn});
async function ensure(h){const r=base();r.command='ensure_started';await h.command(r);assert.equal((await h.snapshot()).phase,'inert');return r;}
const claim=h=>h.claim({instanceId:'instance-1',bootId:'boot-1'});
// Avoid returning the promise directly from an async helper, which would await it.
async function pause(h){await h.inject('after_claim_commit','barrier');const pending=claim(h);await barrier(h);return {pending};}
function reportFor(r){return {identity:{provider:r.provider_kind,key:r.provider_key,immutableSha256:r.binding_hash},immutableSha256:r.binding_hash,instanceId:r.instance_id,bootId:r.boot_id,claimId:r.claim_id,operationId:r.operation_id,result:{outcome:'failed',class:'compiler',code:'compiler_error',diagnostic_sha256:'a'.repeat(64)},attestationSha256:'a'.repeat(64)};}
const core=r=>Object.fromEntries(['operation_id','binding','binding_hash','request_json','epoch','revision','owner','expiry_us','provider_kind','provider_key','claim_state','claim_id','instance_id','boot_id','desired','terminal_json','report_hash','pending_result_json','launch_dispatched'].map(k=>[k,r[k]]));

test('same-authority-query-with-fresh-nonce-preserves-prospective-grant',async(h,e)=>{
 const r=await ensure(h),{pending}=await pause(h);const q=clone(r);q.command='query';q.request_id='b'.repeat(32);const response=await h.command(q);assert.equal(response.body.request_id,q.request_id);await h.control('release',{});const g=await pending;assert.equal(g.granted,true);await h.hardRestart();assert.equal((await claim(h)).granted,false);e.push({response,g,row:(await h.raw()).row});
});
test('rejected-equal-pair-expiry-shrink-preserves-paused-grant-and-row',async(h,e)=>{
 const r=await ensure(h),{pending}=await pause(h),before=(await h.raw()).row,q=clone(r);q.command='query';q.guard.expires_at_us=String(BigInt(q.guard.expires_at_us)-1n);assert.deepEqual(obs(await h.command(q)),{status:'error',code:'stale'});assert.deepEqual((await h.raw()).row,before);await h.control('release',{});assert.equal((await pending).granted,true);e.push(before);
});
for(const mode of ['higher-epoch-same-owner','higher-revision-changed-expiry'])test('final-grant-denies-'+mode,async(h,e)=>{
 const r=await ensure(h),{pending}=await pause(h),q=clone(r);q.command='query';if(mode==='higher-epoch-same-owner')q.guard.epoch='2';else {q.guard.revision='1';q.guard.expires_at_us=String(BigInt(q.guard.expires_at_us)-1n);}
 await h.command(q);await h.control('release',{});assert.equal((await pending).granted,false);await h.hardRestart();assert.equal((await claim(h)).granted,false);e.push((await h.raw()).row);
});
test('overlapping-final-claim-sample-is-exact-durable-and-retains-history-floor',async(h,e)=>{
 await ensure(h);const before=(await h.raw()).row,{pending}=await pause(h);await h.control('clock',clock(N-51n,50n));await h.control('release',{});const g=await pending;assert.equal(g.granted,true);await h.hardRestart();const row=(await h.raw()).row;
 assert.equal(row.clock_lower,String(N-101n));assert.equal(row.clock_upper,String(N-1n));assert.equal(row.clock_floor,before.clock_floor);assert.equal(row.claim_id,g.claimId);await h.control('clock',clock(N-2n,0n));const q=base();assert.deepEqual(obs(await h.command(q)),{status:'error',code:'unavailable'});assert.equal((await h.raw()).row.quarantined,1);e.push({before,g,row});
});
test('rollback-at-final-effect-check-never-dispatches-and-persists-quarantine',async(h,e)=>{
 const r=base();r.command='ensure_started';await h.control('sequence',{sequence:[clock(N),clock(N),clock(N-100n)]});await h.command(r);assert.equal(h.calls().length,0);const row=(await h.raw()).row;assert.equal(row.quarantined,1);assert.equal(row.launch_dispatched,1);assert.equal(row.claim_state,'unissued');await h.hardRestart();assert.equal((await claim(h)).granted,false);assert.equal(h.calls().length,0);e.push(row);
});
test('rollback-at-provider-observation-retains-occupancy-and-blocks-claim',async(h,e)=>{
 const r=base();r.command='ensure_started';await h.inject('after_provider_effect','barrier');const pending=h.command(r);await barrier(h);await h.control('clock',clock(N-100n));await h.control('release',{});await pending;const row=(await h.raw()).row;assert.equal(row.quarantined,1);assert.equal(row.terminal_json,null);assert.equal(row.claim_state,'unissued');assert.equal(h.calls().filter(x=>x.kind==='launch').length,1);await h.restart();assert.equal((await claim(h)).granted,false);e.push(row);
});
test('invalid-provider-observation-still-persists-qualified-decision-history',async(h,e)=>{
 await ensure(h);await h.deliverProvider({state:'inert',extra:'closed-shape-failure'});await h.control('clock',clock(L));await h.reconcile();await h.hardRestart();const row=(await h.raw()).row;assert.equal(row.clock_floor,String(L-1n));assert.equal(row.effect_state,'uncertain');assert.equal(row.terminal_json,null);await h.control('clock',clock(N+100n));assert.equal((await claim(h)).granted,false);assert.equal((await h.raw()).row.quarantined,1);e.push(row);
});
for(const mode of ['expired','rollback','unqualified'])test('late-report-'+mode+'-never-accepts-result',async(h,e)=>{
 const r=await ensure(h);await claim(h);const report=reportFor((await h.raw()).row);await h.control('objects',{value:true});await h.inject('before_object_verify_return','barrier');const pending=h.control('report',report);await barrier(h);
 await h.control('clock',mode==='expired'?clock(BigInt(r.guard.expires_at_us),0n):mode==='rollback'?clock(N-100n):{...clock(L),qualified:false});await h.control('release',{});assert.equal((await pending).status,'rejected');const row=(await h.raw()).row;assert.equal(row.report_hash,null);assert.equal(row.pending_result_json,null);assert.equal(row.claim_state,'consumed');if(mode==='rollback')assert.equal(row.quarantined,1);await h.restart();assert.equal((await h.raw()).row.report_hash,null);e.push(row);
});
test('exact-accepted-report-retry-is-retained-after-complete-drain-and-unqualified-time',async(h,e)=>{
 await ensure(h);await claim(h);const report=reportFor((await h.raw()).row);await h.control('objects',{value:true});assert.equal((await h.control('report',report)).status,'accepted');await h.control('clock',{...clock(L),qualified:false});await h.deliverProvider({state:'absent',definitive:true,descendantsGone:true,launchesSettled:true});await h.reconcile();await h.hardRestart();assert.equal((await h.snapshot()).terminal.status,'completed');assert.equal((await h.control('report',report)).status,'duplicate');const different=clone(report);different.attestationSha256='b'.repeat(64);assert.equal((await h.control('report',different)).status,'rejected');e.push((await h.raw()).row);
});
test('schema1-revoked-stop-preserves-identity-and-drains-without-qualified-clock',async(h,e)=>{
 const r=await ensure(h);r.command='stop';await h.command(r);const before=(await h.raw()).row;assert.equal(before.claim_state,'revoked');await h.control('schema1Fixture',{});await h.restart();const migrated=(await h.raw()).row;assert.deepEqual(core(migrated),core(before));assert.equal(migrated.quarantined,1);await h.control('clock',{...clock(N-100n),qualified:false});await h.deliverProvider({state:'absent',definitive:true,descendantsGone:true,launchesSettled:true});await h.reconcile();await h.hardRestart();assert.equal((await h.snapshot()).terminal.status,'stopped');assert.equal((await h.raw()).row.claim_state,'revoked');assert.equal((await claim(h)).granted,false);e.push({before,migrated,after:(await h.raw()).row});
});
test('schema1-retained-accepted-result-drains-while-quarantined-without-new-acceptance',async(h,e)=>{
 await ensure(h);await claim(h);const report=reportFor((await h.raw()).row);await h.control('objects',{value:true});assert.equal((await h.control('report',report)).status,'accepted');const before=(await h.raw()).row;await h.control('schema1Fixture',{});await h.restart();assert.deepEqual(core((await h.raw()).row),core(before));assert.equal((await h.raw()).row.quarantined,1);await h.control('clock',{...clock(N),qualified:false});await h.deliverProvider({state:'absent',definitive:true,descendantsGone:true,launchesSettled:true});await h.reconcile();const row=(await h.raw()).row;assert.equal(row.report_hash,before.report_hash);assert.equal(row.pending_result_json,before.pending_result_json);assert.equal(JSON.parse(row.terminal_json).status,'completed');assert.equal((await h.control('report',report)).status,'rejected');assert.equal((await claim(h)).granted,false);e.push({before,after:row});
});
test('clock-uncertainty-width-boundary-uses-actual-interval-and-rejects-oversize-without-write',async(h,e)=>{
 const r=base();await h.command(r);await h.control('clock',clock(N,1_000_000n));assert.deepEqual(obs(await h.command(r)),{status:'absent'});const before=(await h.raw()).row;assert.equal(before.clock_lower,String(N-1_000_000n));assert.equal(before.clock_upper,String(N+1_000_000n));await h.control('clock',clock(N,1_000_001n));assert.deepEqual(obs(await h.command(r)),{status:'error',code:'unavailable'});assert.deepEqual((await h.raw()).row,before);e.push(before);
});
test('stale-request-does-not-sample-or-rewrite-rollback-history',async(h,e)=>{
 const old=base(),newer=clone(old);newer.guard.epoch='2';newer.guard.owner_id='successor';await h.control('clock',clock(L));await h.command(newer);const before=(await h.raw()).row;await h.control('clock',clock(N));assert.deepEqual(obs(await h.command(old)),{status:'error',code:'stale'});assert.deepEqual((await h.raw()).row,before);assert.deepEqual(obs(await h.command(newer)),{status:'error',code:'unavailable'});const after=(await h.raw()).row;assert.equal(after.quarantined,1);assert.equal(after.clock_floor,before.clock_floor);assert.equal(after.epoch,'2');e.push({before,after});
});
test('schema1-migration-version-exhaustion-rolls-back-entire-ALTER-and-preserves-row',async(h,e)=>{
 await ensure(h);await claim(h);await h.control('stateVersionMaxFixture',{});await h.control('schema1Fixture',{});const before=(await h.raw()).row;assert.equal(Object.hasOwn(before,'clock_floor'),false);assert.equal(before.state_version,'9223372036854775807');
 assert.deepEqual(await h.control('unknownSchemaCheck',{}),{unavailable:true});const after=(await h.raw()).row;assert.deepEqual(after,before);assert.equal(Object.hasOwn(after,'clock_floor'),false);assert.equal(after.claim_state,'consumed');assert.equal(after.quarantined,0);assert.deepEqual(await h.control('unknownSchemaCheck',{}),{unavailable:true});assert.deepEqual((await h.raw()).row,before);e.push({before,after,migration_constructor:'unavailable; ALTER rolled back with failed version increment'});
});
const results=[];
for(const {id,fn}of cases){let h;const evidence=[];try{h=await createHarness({fixture:base(),nowUs:String(N),errorUs:'1',clockQualified:true});await fn(h,evidence);results.push({id,status:'passed',evidence});}catch(error){results.push({id,status:'failed',evidence,error:{name:error.name,message:error.message,stack:error.stack}});}finally{await h?.close();}console.log(JSON.stringify(results.at(-1)));}
const report={status:results.every(x=>x.status==='passed')?'passed':'failed',scope:'independent-local-actual-workerd-SQLite-authority-time-migration-stop-durability',source_tree_sha256:bindings.source_tree_sha256,results,cleanup:cleanupReceipts};await writeFile(join(here,'independent-report.json'),JSON.stringify(report,null,2)+'\n');process.exitCode=report.status==='passed'?0:1;
