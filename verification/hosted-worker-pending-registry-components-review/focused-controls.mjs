import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {mkdtemp, rm, stat, writeFile} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import {join, resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {killOwnedWorkerd, selectOwnedWorkerd} from '../../hosted-worker-controller/test/owned-workerd-identity.mjs';
const root = resolve(import.meta.dirname, '../..');
const require = createRequire(join(root, 'hosted-worker-controller/package.json'));
const {Miniflare, Log, LogLevel} = require('miniflare');
const workerd = require('workerd').default;
const cleanup = [], results = [], observations = {};
const sha = value => createHash('sha256').update(value).digest('hex');
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function eventually(fn) { for(let i=0;i<100;i++) { if(await fn()) return; await pause(10); } throw new Error('review_poll_timeout'); }
function identity(shard, salt) {
  for(let n=0;;n++) {
    const i={namespaceGeneration:'a'.repeat(64),environmentId:'review-components',poolId:'pool',controllerId:'controller',platform:'ios',operationId:sha(salt+':'+n),immutableSha256:'b'.repeat(64)};
    i.operationKey=sha(JSON.stringify(['mixer-worker-controller-do-v1',i.environmentId,i.poolId,i.controllerId,i.operationId]));
    if(parseInt(i.operationKey[0],16)===shard)return i;
  }
}
function observedOwned() {
  const p=spawnSync('/bin/ps',['-axo','pid=,ppid=,comm='],{encoding:'utf8',timeout:5000,maxBuffer:8388608});
  assert.equal(p.status,0);
  const processes=p.stdout.trim().split('\n').map(line=>{const m=line.trim().match(/^(\d+)\s+(\d+)\s+(.+)$/);assert(m);return {pid:Number(m[1]),parentPid:Number(m[2]),command:m[3]};}).filter(x=>x.pid!==p.pid);
  return selectOwnedWorkerd({ownerPid:process.pid,executable:workerd,platform:process.platform,processes});
}
const absent = pid => {try{process.kill(pid,0);return false;}catch(e){if(e.code==='ESRCH')return true;throw e;}};
async function harness() {
  const persist=await mkdtemp(join(tmpdir(),'mixer-pending-components-review-owned-'));
  const options={modules:true,scriptPath:join(import.meta.dirname,'worker.mjs'),modulesRules:[{type:'ESModule',include:['**/*.js','**/*.mjs'],fallthrough:true},{type:'Text',include:['**/*.sql'],fallthrough:true}],compatibilityDate:'2026-07-30',durableObjects:{PENDING_REGISTRY:{className:'TestRegistry',useSQLite:true},PENDING_AUDIT:{className:'ReviewAudit',useSQLite:true},OPERATIONS:{className:'FixtureRecovery',useSQLite:true}},durableObjectsPersist:persist,bindings:{MIXER_PENDING_CONFIG:JSON.stringify({generation:'a'.repeat(64),operationsNamespace:'component-operation-test',registryNamespace:'component-registry-test'})},log:new Log(LogLevel.ERROR)};
  let mf=new Miniflare(options);const identities=[];
  try{await mf.ready;identities.push(observedOwned());}catch(e){await mf.dispose().catch(()=>{});await rm(persist,{recursive:true,force:true});throw e;}
  return {
    async call(action,args={}) {const r=await mf.dispatchFetch('https://excluded.test/__test/components',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({action,...args})});return r.json();},
    async restart() {cleanup.push({kind:'SIGKILL',...killOwnedWorkerd(workerd)});await mf.dispose().catch(()=>{});mf=new Miniflare(options);await mf.ready;identities.push(observedOwned());},
    async close(){await mf.dispose();await rm(persist,{recursive:true,force:true});const storageRemoved=await stat(persist).then(()=>false,e=>e.code==='ENOENT'),allOwnedPidsAbsent=identities.every(i=>absent(i.pid));cleanup.push({persist,storageRemoved,disposed:true,ownedProcesses:identities,allOwnedPidsAbsent,ownedTaskCancellationClaimed:false});assert(storageRemoved&&allOwnedPidsAbsent);},
  };
}
const register=async(h,i)=>{const r=await h.call('register',{identity:i,shard:parseInt(i.operationKey[0],16)});assert.equal(r.status,'registered');return r.receipt;};
const row=async(h,r)=>(await h.call('registryInspect',{shard:r.shard,recordId:r.recordId})).row;
async function control(id, fn) {let h;const started=performance.now();try{h=await harness();await fn(h);results.push({id,status:'passed',elapsedMs:performance.now()-started});}catch(e){results.push({id,status:'failed',error:e.stack,elapsedMs:performance.now()-started});}finally{if(h)await h.close();}console.log(JSON.stringify(results.at(-1)));}

await control('late-rejection-with-local-write-failure-and-lost-finish-ACK',async h=>{
  const i=identity(0,'late-failure'),r=await register(h,i);
  await h.call('recoveryConfigure',{operationKey:i.operationKey,mode:'hold_reject'});
  assert.equal((await h.call('audit')).wakesStarted,1);
  assert.equal((await h.call('audit')).status,'busy');
  await h.call('auditCompletionFault',{mode:'write'});
  await h.call('recoveryRelease',{operationKey:i.operationKey});
  await eventually(async()=>(await h.call('recoveryInspect',{operationKey:i.operationKey})).settled===1);
  assert.equal((await h.call('auditInspect')).completions[0].value,null);
  const j=identity(1,'healthy'),s=await register(h,j);
  assert.equal((await h.call('audit')).status,'unavailable');
  assert.equal((await h.call('recoveryInspect',{operationKey:j.operationKey})).calls,0);
  await h.call('auditCompletionFault',{mode:'none'});
  await h.call('registryConfigure',{shard:0,setting:{mode:'finish_ack_hold',milliseconds:0}});
  const recovered=await h.call('audit');
  assert(recovered.needsAttention);
  assert.equal((await row(h,r)).failures,1);
  const saved=(await h.call('auditInspect')).completions[0].value;
  assert(saved&&Buffer.byteLength(saved)<=2048);
  assert.equal(JSON.parse(saved).disposition.status,'unavailable');
  assert.equal((await h.call('recoveryInspect',{operationKey:j.operationKey})).calls,1);
  await h.restart();
  assert.equal((await h.call('auditInspect')).completions[0].value,saved);
  await h.call('registryConfigure',{shard:0,setting:{mode:'none',milliseconds:0}});
  await h.call('audit');
  assert.equal((await row(h,r)).failures,1);
  assert.equal((await h.call('auditInspect')).completions[0].value,null);
  assert.equal((await h.call('recoveryInspect',{operationKey:i.operationKey})).calls,1);
  assert((await h.call('recoveryInspect',{operationKey:j.operationKey})).calls>=2);
  observations.lateFailure={exactSavedBytes:saved,memoryFallback:true,unknownFinishAckRetained:true,restartRetained:true,finishNotDoubleCounted:true,healthyShardProgress:true};
});

await control('audit-missing-schema-meta-with-surviving-completion',async h=>{
  const i=identity(0,'missing-meta'),r=await register(h,i);
  await h.call('recoveryConfigure',{operationKey:i.operationKey,mode:'hold_unavailable'});
  assert.equal((await h.call('audit')).wakesStarted,1);
  await h.call('recoveryRelease',{operationKey:i.operationKey});
  await eventually(async()=>(await h.call('auditInspect')).completions[0].value!==null);
  const before=await h.call('auditInspect');
  const saved=before.completions[0].value;
  await h.call('reviewRemoveAuditMeta');
  await h.restart();
  const reopened=await h.call('auditInspect');
  const result=await h.call('audit');
  observations.missingMeta={previousRun:before.meta[0].run_sequence,survivingCompletion:saved,reinitializedMeta:reopened.meta,result,registryAfter:await row(h,r)};
  assert.equal(result.status,'unavailable','Unknown/missing audit schema metadata must fail closed, without reinitializing surviving safety tables');
});

const report={schema:1,status:results.every(r=>r.status==='passed')?'passed':'failed',scope:'independent-actual-workerd-cross-DO-SQLite-focused-components-only',results,observations,cleanup,engineIntegration:false,deployedQualification:false,gaAccepted:false};
await writeFile(join(import.meta.dirname,'focused-report.json'),JSON.stringify(report,null,2)+'\n');
process.exitCode=report.status==='passed'?0:1;
