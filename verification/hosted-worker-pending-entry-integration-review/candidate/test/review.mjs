import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {harness,cleanup,makeIdentity,token} from './entry-harness.mjs';
const root=resolve(import.meta.dirname,'../../../..'),packet=JSON.parse(await readFile(resolve(root,'verification/hosted-worker-controller-contract/vectors.json'),'utf8'));
const base=()=>structuredClone(packet.cases[0].request),delay=ms=>new Promise(r=>setTimeout(r,ms));
const counts=(v,k)=>v.counts.find(x=>x.kind===k)?.n??0, inspect=(h,r)=>h.call('inspect',{r});
const ticket=p=>({runId:'1',wakeId:'4'.repeat(32),receipt:p,trackedVersion:'0',attemptSequence:'1'});
const cases=[],results=[],observations={};
const test=(id,options,fn)=>cases.push({id,options,fn});
async function registered(h,r){const i=makeIdentity(r),p=await h.call('register',{i});assert(['registered','duplicate'].includes(p.status));return {i,p:p.receipt};}
for(const kind of ['bad-binding','wrong-immutable-identity'])test('delayed-restore-'+kind+'-rejects-all-concurrent-admissions',{restoreDelay:180},async h=>{
 const r=base();r.command='ensure_started';await h.command(r);await h.call('mutate',{r,kind});const before=(await inspect(h,r)).row;await h.restart(true);
 const responses=await Promise.all(Array.from({length:16},()=>h.command(r)));assert(responses.every(v=>v.status===503));const after=await inspect(h,r);assert.deepEqual(after.row,before);assert.equal(after.fenced,true);assert.equal(counts(after,'engine'),1);assert.equal(counts(after,'launch'),1);
});
test('delayed-valid-restore-32-concurrent-fetches-share-one-engine',{restoreDelay:200},async h=>{
 const r=base();r.command='ensure_started';await h.command(r);const before=(await inspect(h,r)).row;await h.restart(true);const responses=await Promise.all(Array.from({length:32},()=>h.command(r)));assert(responses.every(v=>v.status===200));const after=await inspect(h,r);assert.equal(after.row.pending_identity_json,before.pending_identity_json);assert.equal(after.row.registration_json,before.registration_json);assert.equal(counts(after,'engine'),2);assert.equal(counts(after,'launch'),1);observations.delayedRestoreCounts=after.counts;
});
test('delayed-restore-recovery-enrollment-and-fetch-race-one-engine',{restoreDelay:180},async h=>{
 const r=base();r.command='ensure_started';await h.command(r);const {i,p}=await registered(h,r);await h.restart(true);const [commands,recoveries,enrolls]=await Promise.all([Promise.all(Array.from({length:8},()=>h.command(r))),Promise.all(Array.from({length:8},()=>h.call('recover',{i,p,t:ticket(p)}))),Promise.all(Array.from({length:8},()=>h.call('enroll',{i})))]);assert(commands.every(v=>v.status===200));assert(recoveries.every(v=>['pending','busy'].includes(v.status)));assert(enrolls.every(v=>['enrolled','conflict'].includes(v)));const after=await inspect(h,r);assert.equal(counts(after,'engine'),2);assert.equal(counts(after,'launch'),1);assert.equal(after.row.pending_identity_json,JSON.stringify(i));
});
test('32-first-calls-with-near-250ms-registration-one-engine',{registryMode:'edge-delay'},async h=>{
 const r=base();r.command='ensure_started';const replies=await Promise.all(Array.from({length:32},()=>h.command(r)));assert(replies.every(v=>v.status===200));const raw=await inspect(h,r);assert.equal(counts(raw,'engine'),1);assert.equal(counts(raw,'launch'),1);assert.equal(JSON.parse(raw.row.registration_json).allocationIndex,1);
});
test('abort-late-ack-settles-with-zero-operation-allocation',{outerMode:'abort-during',registryMode:'edge-delay'},async h=>{
 assert.equal((await h.command(base())).status,503);await delay(350);const events=await h.call('events');assert(events.some(v=>v[0]==='register-ack'));assert(!events.some(v=>v[0]==='operation-id'||v[0]==='operation-get'));observations.abortedLateAck=events.map(v=>v[0]);
});
test('four-second-body-budget-before-ack-no-late-allocation',{registryMode:'edge-delay',bodyDelay:3860},async h=>{
 const response=await h.command(base());assert.equal(response.status,503);assert(response.entryElapsed>=3800&&response.entryElapsed<4250);await delay(250);const e=await h.call('events');assert(e.some(v=>v[0]==='register-ack'));assert(!e.some(v=>v[0]==='operation-id'||v[0]==='operation-get'));observations.outerExpiredElapsed=response.entryElapsed;
});
test('held-effect-survives-entry-return-without-second-launch',{},async h=>{
 const r=base();r.command='ensure_started';await h.call('set',{r,value:'hold'});const pending=h.command(r);for(let n=0;n<100;n++){if(counts(await inspect(h,r),'launch'))break;await delay(10);}const a=await registered(h,r);await Promise.all(Array.from({length:16},()=>h.command(r)));const recovery=await h.call('recover',{...a,t:ticket(a.p)});assert.equal(recovery.status,'busy');await h.call('set',{r,value:'release'});await pending;const raw=await inspect(h,r);assert.equal(counts(raw,'engine'),1);assert.equal(counts(raw,'launch'),1);
});
test('unenrolled-migration-public-burst-does-not-fence-or-mutate-row',{},async h=>{
 const r=base();await h.command(r);await h.call('mutate',{r,kind:'migration'});await h.restart(true);const before=await inspect(h,r);await Promise.all(Array.from({length:32},()=>h.command(r)));const raw=await inspect(h,r);assert.deepEqual(raw.row,before.row);assert.equal(raw.fenced,false);assert.equal(counts(raw,'engine'),1);const {i}=await registered(h,r);assert.equal(await h.call('enroll',{i}),'enrolled');const after=await inspect(h,r);assert.equal(after.row.quarantined,1);assert.equal(after.row.claim_state,before.row.claim_state);assert.equal(counts(after,'launch'),0);
});
test('unenrolled-unquarantined-row-cannot-enroll-or-gain-claim',{},async h=>{
 const r=base();await h.command(r);await h.call('mutate',{r,kind:'unquarantined-unenrolled'});await h.restart(true);const before=(await inspect(h,r)).row;const {i}=await registered(h,r);assert.equal(await h.call('enroll',{i}),'conflict');const after=await inspect(h,r);assert.deepEqual(after.row,before);assert.equal((await h.call('claim',{r,payload:{}})).granted,false);assert.equal(await h.call('report',{r,payload:{}}),'rejected');
});
test('private-enrollment-row-identity-before-context-selection',{},async h=>{
 const r=base();await h.command(r);await h.call('mutate',{r,kind:'migration'});await h.restart(true);const before=(await inspect(h,r)).row;const {i}=await registered(h,r),bad={...i,immutableSha256:'b'.repeat(64)};
 assert.equal(await h.call('enroll',{i:bad}),'conflict');assert.deepEqual((await inspect(h,r)).row,before);const proper=await h.call('enroll',{i});observations.correctEnrollmentAfterConflictingPrivateIdentity=proper;assert.equal(proper,'enrolled');
});
for(const kind of ['claim','report','engine','ledger','state','inspectFixture','settingFixture','mutateFixture','createEngine'])test('production-RPC-hidden-'+kind,{production:true},async h=>{const r=base();await assert.rejects(()=>h.rpc(r,kind,[]));});
test('production-recovery-identity-only-cannot-launch-or-command',{production:true},async h=>{
 const r=base(),i=makeIdentity(r),p={identityDigest:'a'.repeat(64),namespaceGeneration:i.namespaceGeneration,recordId:'1'.repeat(32),shard:parseInt(i.operationKey[0],16),allocationIndex:1};assert.equal((await h.rpc(r,'recoverKnown',[{...i,command:'ensure_started'},p,ticket(p)])).status,'conflict');assert.equal(await h.rpc(r,'enrollExisting',[i]),'missing');r.command='ensure_started';assert.deepEqual((await h.command(r)).body.observation,{status:'error',code:'unavailable'});
});
let failed=0;for(const {id,options,fn} of cases){const h=await harness(options);const started=performance.now();try{await fn(h);results.push({id,status:'passed',elapsedMs:performance.now()-started});}catch(e){failed++;results.push({id,status:'failed',error:e.stack,elapsedMs:performance.now()-started});}finally{await h.close();}console.log(JSON.stringify(results.at(-1)));}
const report={status:failed?'failed':'passed',groupsRun:results.length,groupsPassed:results.length-failed,results,observations,cleanup,scope:'fresh independent local workerd SQLite; exact production source; excluded fixture effects and restore delay only; no deployment authority'};await writeFile(process.env.REVIEW_REPORT,JSON.stringify(report,null,2)+'\n');if(failed)process.exitCode=1;
