// Independent synthetic fixtures; imports only the sealed scratch candidate.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
const here=import.meta.dirname;
const bindings=JSON.parse(await readFile(join(here,'bindings.json'),'utf8'));
const scratch=bindings.scratch,project=bindings.project??join(scratch,'hosted-worker-controller');
const {createHarness,cleanupReceipts}=await import(pathToFileURL(join(project,'test/acceptance-driver.mjs')));
const packet=JSON.parse(await readFile(join(scratch,'verification/hosted-worker-controller-contract/vectors.json'),'utf8'));
const clone=v=>structuredClone(v),base=()=>clone(packet.cases[0].request);
const obs=v=>{assert.equal(v.httpStatus,200);return v.body.observation;};
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function eventually(fn){for(let i=0;i<150;i++){if(await fn())return;await delay(10);}throw new Error('independent_barrier_timeout');}
const cases=[];const test=(id,fn)=>cases.push({id,fn});

for(const mode of ['epoch-owner-transfer','revision-advance'])test('claim-final-authority-'+mode,async(h,evidence)=>{
  const r=base();r.command='ensure_started';await h.command(r);
  await h.inject('after_claim_commit','barrier');
  const pending=h.claim({instanceId:'instance-1',bootId:'boot-1'});
  await eventually(async()=>!!(await h.raw()).settings.barrier);
  const consumed=(await h.raw()).row;
  const next=clone(r);next.command='query';
  Object.assign(next.guard,mode==='epoch-owner-transfer'?{epoch:'2',owner_id:'successor'}:{revision:'1'});
  const query=await h.command(next);
  const after=(await h.raw()).row;
  await h.control('release',{});
  const grant=await pending;
  evidence.push({consumed_guard:{epoch:consumed.epoch,revision:consumed.revision,owner:consumed.owner},current_guard:{epoch:after.epoch,revision:after.revision,owner:after.owner},query_observation:obs(query),grant,claim_state:after.claim_state});
  assert.equal(grant.granted,false,'a callback consumed under superseded authority must not grant after the new watermark commits');
});
test('stop-during-claim-final-check-denies-and-persists',async(h,evidence)=>{
  const r=base();r.command='ensure_started';await h.command(r);
  await h.inject('after_claim_commit','barrier');
  const pending=h.claim({instanceId:'instance-1',bootId:'boot-1'});
  await eventually(async()=>!!(await h.raw()).settings.barrier);
  const next=clone(r);next.command='stop';next.guard.epoch='2';next.guard.owner_id='successor';
  await h.command(next);await h.control('release',{});
  assert.equal((await pending).granted,false);await h.restart();
  assert.equal((await h.claim({instanceId:'instance-1',bootId:'boot-1'})).granted,false);
  assert.equal((await h.snapshot()).desired,'stop');assert.equal((await h.snapshot()).claimState,'consumed');
  evidence.push(await h.snapshot());
});
test('malformed-and-incomplete-drain-evidence-stays-occupied',async(h,evidence)=>{
  const r=base();r.command='stop';await h.command(r);
  for(const partial of [{state:'absent',definitive:true,descendantsGone:true,launchesSettled:false},{state:'absent',definitive:true,descendantsGone:false,launchesSettled:true},{state:'absent',definitive:false,descendantsGone:true,launchesSettled:true},{state:'absent',definitive:true,descendantsGone:true,launchesSettled:true,extra:'invalid'}]){
    await h.deliverProvider(partial);await h.reconcile();assert.equal((await h.snapshot()).terminal,null);
  }
  assert.equal((await h.snapshot()).desired,'stop');
  await h.deliverProvider({state:'absent',definitive:true,descendantsGone:true,launchesSettled:true});
  await h.reconcile();assert.equal((await h.snapshot()).terminal.status,'stopped');
  evidence.push(await h.snapshot());
});
test('exact-maximum-epoch-and-zero-revision-after-transfer',async(h,evidence)=>{
  const r=base();r.guard.epoch='9007199254740993';r.guard.revision='32';await h.command(r);
  const next=clone(r);next.guard.epoch='9223372036854775807';next.guard.revision='0';next.guard.owner_id='successor';
  assert.deepEqual(obs(await h.command(next)),{status:'absent'});
  const row=(await h.raw()).row;assert.equal(row.epoch,'9223372036854775807');assert.equal(row.revision,'0');
  const before=clone(row);assert.deepEqual(obs(await h.command(r)),{status:'error',code:'stale'});assert.deepEqual((await h.raw()).row,before);
  evidence.push({epoch:row.epoch,revision:row.revision,sqlTypes:(await h.raw()).sqlTypes});
});
test('quarantine-and-unqualified-clock-do-not-grant',async(h,evidence)=>{
  const r=base();r.command='ensure_started';await h.command(r);await h.control('quarantine',{});
  await h.restart();assert.equal((await h.claim({instanceId:'instance-1',bootId:'boot-1'})).granted,false);
  assert.equal((await h.raw()).row.quarantined,1);assert.equal((await h.snapshot()).claimState,'unissued');
  evidence.push(await h.snapshot());
});
test('later-effect-clock-sample-must-fence-rollback-before-claim',async(h,evidence)=>{
  const r=base();r.command='ensure_started';await h.command(r);
  await h.control('clock',{nowUs:'1950000000000000',errorUs:'1',qualified:true});
  await h.reconcile();
  const afterLaterEffect=(await h.raw()).row;
  await h.control('clock',{nowUs:'1920000000000000',errorUs:'1',qualified:true});
  const grant=await h.claim({instanceId:'instance-1',bootId:'boot-1'});
  const afterRollback=(await h.raw()).row;
  evidence.push({later_effect_clock_now_us:'1950000000000000',persisted_clock_lower_us:afterLaterEffect.clock_lower,rollback_clock_now_us:'1920000000000000',grant,quarantined:afterRollback.quarantined});
  assert.equal(grant.granted,false,'rollback behind a qualified effect sample must quarantine before a new claim');
  assert.equal(afterRollback.quarantined,1);
});

const results=[];
for(const {id,fn}of cases){let h;const evidence=[];try{
  h=await createHarness({fixture:base(),nowUs:'1900000000000000',errorUs:'1',clockQualified:true});
  await fn(h,evidence);results.push({id,status:'passed',evidence});
}catch(e){results.push({id,status:'failed',evidence,error:{name:e.name,message:e.message,stack:e.stack}});}
finally{await h?.close();}console.log(JSON.stringify(results.at(-1)));}
const report={status:results.some(r=>r.status==='failed')?'failed':'passed',scope:'independent-local-workerd-SQLite-synthetic-regressions',frozen_source_tree_sha256:bindings.source_tree_sha256,results,cleanup:cleanupReceipts};
await writeFile(join(here,'regression-report.json'),JSON.stringify(report,null,2)+'\n');
process.exitCode=report.status==='failed'?1:0;
