import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {harness,cleanup,makeIdentity} from './entry-harness.mjs';
const root=resolve(import.meta.dirname,'../../../..');
const vectors=JSON.parse(await readFile(resolve(root,'verification/hosted-worker-controller-contract/vectors.json'),'utf8'));
const base=()=>structuredClone(vectors.cases[0].request);
const count=v=>v.counts.find(x=>x.kind==='engine')?.n??0;
const inspect=(h,r)=>h.call('inspect',{r});
const cases=[],results=[],observations={};let failure=null;
const test=(id,fn)=>cases.push({id,fn});
async function migrated(h,r){
 assert.equal((await h.command(r)).status,200);
 await h.call('mutate',{r,kind:'migration'});await h.restart(true);
 const raw=await inspect(h,r);assert.equal(raw.row.pending_identity_json,null);assert.equal(raw.row.registration_json,null);assert.equal(raw.row.quarantined,1);return raw;
}
function enrollmentPreservesHistory(before,after){
 const changed=['pending_identity_json','registration_json','state_version','track_outbox_json','registry_ack_version'];
 for(const k of Object.keys(before))if(!changed.includes(k))assert.deepEqual(after[k],before[k],k);
 assert.equal(after.quarantined,1);assert(after.pending_identity_json);assert(after.registration_json);
}
test('missing-enrollment-does-not-select-context-or-create-row',async h=>{
 const r=base(),i=makeIdentity(r);assert.equal(await h.call('enroll',{i}),'missing');const raw=await inspect(h,r);assert.equal(raw.row,null);assert.equal(count(raw),0);
});
for(const kind of ['immutable-digest','platform'])test('migrated-rejected-'+kind+'-then-correct-without-restart',async h=>{
 const r=base(),before=await migrated(h,r),i=makeIdentity(r),bad={...i,...(kind==='immutable-digest'?{immutableSha256:'b'.repeat(64)}:{platform:i.platform==='ios'?'android':'ios'})};
 assert.equal(await h.call('enroll',{i:bad}),'conflict');const rejected=await inspect(h,r);assert.deepEqual(rejected.row,before.row);assert.equal(count(rejected),count(before));assert.equal(rejected.fenced,before.fenced);
 assert.equal(await h.call('enroll',{i}),'enrolled');const accepted=await inspect(h,r);assert.equal(count(accepted),count(before)+1);enrollmentPreservesHistory(before.row,accepted.row);
 observations[kind]={rejectedNewEngines:count(rejected)-count(before),laterCorrect:'enrolled',restartBetweenRejectedAndCorrect:false};
});
test('binding-sha-mismatch-rejects-without-context-or-row-change',async h=>{
 const r=base();await migrated(h,r);await h.call('mutate',{r,kind:'binding-sha-mismatch'});const before=await inspect(h,r);
 assert.equal(await h.call('enroll',{i:makeIdentity(r)}),'conflict');const after=await inspect(h,r);assert.deepEqual(after.row,before.row);assert.equal(after.fenced,before.fenced);assert.equal(count(after),count(before));
});
test('full-row-change-across-await-rejects-before-context-selection',async h=>{
 const r=base(),before=await migrated(h,r),i=makeIdentity(r);
 const rejected=await h.call('enroll-row-change',{i});assert.deepEqual(rejected,{status:'conflict',trace:['snapshot-read','row-history-changed']});
 const changed=await inspect(h,r);assert.deepEqual(changed.row,{...before.row,failures:before.row.failures+1});assert.equal(count(changed),count(before));assert.equal(changed.fenced,before.fenced);
 assert.equal(await h.call('enroll',{i}),'enrolled');const accepted=await inspect(h,r);assert.equal(count(accepted),count(before)+1);enrollmentPreservesHistory(changed.row,accepted.row);
 observations.changedAcrossAwait={...rejected,rejectedNewEngines:count(changed)-count(before),laterCorrect:'enrolled',restartBetweenRejectedAndCorrect:false};
});
test('retained-context-rejection-keeps-engine-and-all-row-bytes',async h=>{
 const r=base();await h.command(r);await h.restart(true);const before=await inspect(h,r),i=makeIdentity(r);
 assert.equal(await h.call('enroll',{i:{...i,immutableSha256:'b'.repeat(64)}}),'conflict');const rejected=await inspect(h,r);assert.deepEqual(rejected.row,before.row);assert.equal(count(rejected),count(before));assert.equal(rejected.fenced,before.fenced);
 assert.equal(await h.call('enroll',{i}),'enrolled');const accepted=await inspect(h,r);assert.equal(count(accepted),count(before));assert.equal(accepted.row.pending_identity_json,before.row.pending_identity_json);assert.equal(accepted.row.registration_json,before.row.registration_json);assert.equal(accepted.row.quarantined,before.row.quarantined);
});
try{for(const {id,fn} of cases){const h=await harness();const started=performance.now();try{await fn(h);results.push({id,status:'passed',elapsedMs:performance.now()-started});console.log(JSON.stringify(results.at(-1)));}catch(e){results.push({id,status:'failed',error:e.stack,elapsedMs:performance.now()-started});throw e;}finally{await h.close();}}}catch(e){failure=e.stack;console.error(e);process.exitCode=1;}finally{
 await writeFile(process.env.MIXER_ADMISSION_REPORT??resolve(import.meta.dirname,'../../admission-report.json'),JSON.stringify({status:failure?'failed':'passed',groupsRun:results.length,groupsPassed:results.filter(x=>x.status==='passed').length,results,observations,cleanup,failure,scope:'ordinary local functional regression only; finite test-only row mutation across hash await; actual local workerd SQLite; synthetic provider/clock; interrupted independent review not resumed'},null,2)+'\n');
}
