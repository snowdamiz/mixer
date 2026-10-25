import assert from "node:assert/strict";
import {createHash,randomBytes} from "node:crypto";
import {readFile,mkdtemp,rm,writeFile} from "node:fs/promises";
import {join,resolve} from "node:path";
import {tmpdir} from "node:os";
import {pathToFileURL} from "node:url";
import {createRequire} from "node:module";
const require=createRequire(new URL("../../../../hosted-worker-controller/package.json",import.meta.url));
const {Miniflare}=require("miniflare");
import {cleanupReceipts,createHarness,options,observeOwned,processGone} from "./acceptance-driver.mjs";

const root=resolve(import.meta.dirname,"../../../.."),project=resolve(import.meta.dirname,"..");
const packet=JSON.parse(await readFile(join(root,"verification/hosted-worker-controller-contract/vectors.json"),"utf8"));
const original=JSON.parse(await readFile(join(root,"verification/hosted-worker-transport/cross-runtime-vectors.json"),"utf8"));
const controls=JSON.parse(await readFile(join(root,"verification/hosted-worker-controller-implementation/jason-control-vectors.json"),"utf8"));
const clone=v=>JSON.parse(JSON.stringify(v));
const base=()=>clone(packet.cases[0].request);
const sha=v=>createHash("sha256").update(v).digest("hex");
function seal(r){const f=r.ref,s=r.spec;const prefix=JSON.stringify(["mixer-build-operation-v1",r.guard.record_id,f.organization_id,f.project_id,f.application_id,f.build_id,f.platform,f.attempt]);r.operation_id=sha(prefix.slice(0,-1)+","+f.fence+"]");r.immutable_sha256=sha(JSON.stringify(["mixer-worker-binding-v1",r.operation_id,r.guard.record_id,[f.organization_id,f.project_id,f.application_id,f.build_id,f.platform,f.attempt,f.fence],[s.organization_id,s.project_id,s.application_id,s.build_id,s.platform,s.source.kind,s.source.sha256,s.source.reference,s.toolchain_lock_sha256,s.build_definition_sha256],r.deadline_ms]));return r;}
const guard=(r,fields)=>({...clone(r),guard:{...clone(r.guard),...fields}});
const obs=r=>{assert.equal(r.httpStatus,200);return r.body.observation;};
const launchCount=h=>h.calls().filter(c=>c.kind==="launch").length;
const stopCount=h=>h.calls().filter(c=>c.kind==="stop").length;
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function eventually(fn){for(let i=0;i<80;i++){if(await fn())return;await delay(10);}throw new Error("fixture_condition_timeout");}
const cases=[];
const test=(id,fn)=>cases.push({id,fn});
const results=[];

test("all-36-original-Elixir-vectors-in-workerd",async()=>{
  assert.equal(original.vectors.length,36);
  for(const r of original.vectors){
    const h=await createHarness({fixture:r,nowUs:"1700000000000000",errorUs:"1",clockQualified:true});
    try{
      const reply=await h.command(r);assert.deepEqual(obs(reply),{status:"absent"});
      const {spec,deadline_ms,...echo}=r,{observation,...actual}=reply.body;assert.deepEqual(actual,echo);
      const raw=await h.raw();assert.equal(raw.row.epoch,r.guard.epoch);assert.equal(raw.row.expiry_us,r.guard.expires_at_us);
      assert.deepEqual(raw.sqlTypes,[{epoch:"text",revision:"text",expiry:"text",state_version:"text"}]);
      assert.equal(launchCount(h),0);
    }finally{await h.close();}
  }
});
test("Jason-control-escapes-and-Unicode-printable-boundaries",async()=>{
  assert.equal(controls.vectors.length,24);
  for(const v of controls.vectors){
    assert.equal(sha(v.operation_json),v.request.operation_id);assert.equal(sha(v.binding_json),v.request.immutable_sha256);
    const h=await createHarness({fixture:v.request,nowUs:"1900000000000000",errorUs:"1",clockQualified:true});
    try{const response=await h.command(v.request);if(v.printable)assert.deepEqual(obs(response),{status:"absent"});else {assert.equal(response.httpStatus,400);assert.equal((await h.snapshot()).exists,false);}}
    finally{await h.close();}
  }
});
test("production-entry-auth-codec-before-disabled-clock",async()=>{
  const persist=await mkdtemp(join(tmpdir(),"mixer-controller-production-owned-")),mf=new Miniflare(options(persist,true));let ownedProcess=null;
  try{
    await mf.ready;ownedProcess=observeOwned();const r=base(),token=Buffer.alloc(32,0x31).toString("base64url");
    const call=(body,authorization="Bearer "+token,path="/internal/mixer-build-worker/v1")=>mf.dispatchFetch("https://controller.test"+path,{method:"POST",headers:{Authorization:authorization,"Content-Type":"application/json"},body});
    assert.equal((await call(JSON.stringify(r),"Bearer invalid")).status,401);
    assert.equal((await call(JSON.stringify(r).replace('"version":1','"version":1.0'))).status,400);
    for(const command of ["query","ensure_started","stop"]){const q={...r,command};const response=await call(JSON.stringify(q));assert.equal(response.status,200);const body=await response.json();assert.deepEqual(body.observation,{status:"error",code:"unavailable"});assert.equal(body.command,command);assert.equal(body.request_id,q.request_id);}
    assert.equal((await call("{}",undefined,"/__test/claim")).status,404);
  }finally{await mf.dispose();await rm(persist,{recursive:true,force:true});cleanupReceipts.push({persist,productionBundle:true,disposed:true,storageRemoved:true,ownedProcesses:ownedProcess?[ownedProcess]:[],allOwnedPidsAbsent:ownedProcess?processGone(ownedProcess.pid):true});}
});
test("additional-closed-shape-and-string-adversaries",async h=>{
  const r=base();const mutations=[
    v=>v.version=true,v=>v.command="constructor",v=>v.request_id="A".repeat(32),v=>v.operation_id="A".repeat(64),
    v=>v.ref.attempt=0,v=>v.ref.attempt=6,v=>v.ref.fence="-1",v=>v.deadline_ms="1e3",v=>v.guard.revision="33",v=>v.guard.revision="00",
    v=>v.guard.epoch="9223372036854775808",v=>v.guard.record_id="AAAAAAAA-0000-4000-8000-000000000001",v=>v.guard.owner_id="\u0000",
    v=>v.spec.source.kind="url",v=>v.spec.source.reference="",v=>v.spec.source.reference="x".repeat(1025),
    v=>v.spec.toolchain_lock_sha256="a".repeat(63),v=>v.ref.organization_id="\ud800",v=>v.ref.organization_id="\u007f",v=>v.ref.organization_id="\u0080",
    v=>v.ref.project_id="😀".repeat(33),v=>v.guard.extra=true,v=>v.spec.source.extra=true,v=>delete v.ref.fence,v=>v.spec.platform="ios",
    v=>v.environment_id="env\n",v=>v.pool_id="😀",v=>v.spec=null,v=>v.ref=[],v=>v.guard={__proto__:{epoch:"1"}},
  ];
  for(const mutate of mutations){const bad=clone(r);mutate(bad);assert.notEqual((await h.command(bad)).httpStatus,200);}
  const raw=JSON.stringify(r);
  for(const payload of ["\ufeff"+raw,raw+"{}",raw.replace('"reference":"main"','"reference":"main","refe\\u0072ence":"main"'),raw.replace('"revision":"0"','"revision":"0","revision":"1"'),raw.replace('"version":1','"__proto__":{},"version":1'),raw.replace('"version":1','"version":'+'['.repeat(8)+'1'+']'.repeat(8))]){
    assert.notEqual((await h.rawCommand(new TextEncoder().encode(payload))).httpStatus,200);
  }
  assert.equal((await h.snapshot()).exists,false);assert.equal(h.calls().length,0);
});
test("parser-container-depth-token-and-raw-string-boundaries",async h=>{
  const parse=source=>h.control("parse",{bytes:Array.from(new TextEncoder().encode(source))});
  assert.equal((await parse('['.repeat(8)+']'.repeat(8))).accepted,true);
  assert.equal((await parse('['.repeat(9)+']'.repeat(9))).accepted,false);
  assert.equal((await parse('{"s":"'+'a'.repeat(8192)+'"}')).accepted,true);
  assert.equal((await parse('{"s":"'+'a'.repeat(8193)+'"}')).accepted,false);
  assert.equal((await parse('['+Array(511).fill('0').join(',')+']')).accepted,true);
  assert.equal((await parse('['+Array(512).fill('0').join(',')+']')).accepted,false);
});
test("auth-ambiguity-and-managed-metadata",async h=>{
  const raw=new TextEncoder().encode(JSON.stringify(base()));
  const token=Buffer.alloc(32,0x31).toString("base64url");
  for(const auth of ["Bearer "+token+",Bearer "+token,"bearer "+token,"Bearer "+token+"=","Bearer "+token.slice(0,-1)+"R"," Bearer "+token]){
    // Headers trims surrounding whitespace; omitted leading whitespace control
    // is covered at the actual managed-ingress gate, not inferred from Fetch.
    if(auth.startsWith(" "))continue;
    assert.equal((await h.rawCommand(raw,{headers:{Authorization:auth}})).httpStatus,401);
  }
  assert.equal((await h.rawCommand(raw,{headers:{"Content-Type":"application/json, application/json"}})).httpStatus,400);
  const ok=await h.rawCommand(raw,{headers:{"CF-Ray":"synthetic","X-Forwarded-For":"127.0.0.1","X-Organization":"other"}});
  assert.deepEqual(obs(ok),{status:"absent"});
});
test("valid-rehashed-immutable-conflict",async h=>{
  const r=base();await h.command(r);const before=await h.raw(),count=h.calls().length;
  for(const mutate of [v=>v.spec.source.reference="changed",v=>v.deadline_ms="2100000000001",v=>v.spec.build_definition_sha256="f".repeat(64)]){
    const bad=clone(r);mutate(bad);seal(bad);assert.equal(bad.operation_id,r.operation_id);assert.equal((await h.command(bad)).httpStatus,400);
    assert.deepEqual((await h.raw()).row,before.row);assert.equal(h.calls().length,count);
  }
});
test("32-concurrent-duplicates-one-launch",async h=>{
  const r=base();r.command="ensure_started";
  const replies=await Promise.all(Array.from({length:32},()=>h.command({...r,request_id:randomBytes(16).toString("hex")})));
  assert(replies.every(x=>x.httpStatus===200));assert.equal(launchCount(h),1);
  assert.equal(new Set(h.calls().map(c=>c.providerKey)).size,1);
});
test("stop-commits-during-inflight-launch",async h=>{
  await h.control("hold",{value:true});const r=base();r.command="ensure_started";
  const launching=h.command(r);await eventually(async()=>{const raw=await h.raw();return raw.row?.launch_dispatched===1;});
  const stop=guard(r,{epoch:"2",owner_id:"next"});stop.command="stop";
  assert.deepEqual(obs(await h.command(stop)),{status:"error",code:"uncertain"});
  assert.equal((await h.snapshot()).desired,"stop");
  await h.deliverProvider({state:"inert",instanceId:"instance-1",bootId:"boot-1",definitive:false,descendantsGone:false,launchesSettled:false});await launching;
  assert.equal((await h.claim({instanceId:"instance-1",bootId:"boot-1"})).granted,false);
  await h.reconcile();assert.equal(launchCount(h),1);assert(stopCount(h)>=1);
});
test("provider-timeout-keeps-identity-and-aborts-owned-wait",async h=>{
  await h.control("hold",{value:true});const r=base();r.command="ensure_started";
  const started=performance.now();assert.deepEqual(obs(await h.command(r)),{status:"error",code:"uncertain"});
  assert(performance.now()-started>=1800);assert(performance.now()-started<3500);
  const key=(await h.snapshot()).providerKey;await h.control("hold",{value:false});await h.restart();await h.command(r);
  assert.equal(launchCount(h),1);assert.equal((await h.snapshot()).providerKey,key);
});
test("query-transfer-cannot-authorize-old-launch-intent",async h=>{
  const r=base();r.command="ensure_started";h.inject("after_intent","crash");await h.command(r);assert.equal(launchCount(h),0);
  const next=guard(r,{epoch:"2",owner_id:"next"});next.command="query";await h.command(next);assert.equal(launchCount(h),0);
  next.command="ensure_started";await h.command(next);assert.equal(launchCount(h),1);
});
test("post-lock-and-pre-effect-expiry-recheck",async h=>{
  const r=base();r.command="ensure_started";
  await h.control("sequence",{sequence:[{nowUs:"1900000000000000",errorUs:"1",qualified:true},{nowUs:"2000000000001000",errorUs:"1",qualified:true}]});
  await h.command(r);assert.equal(launchCount(h),0);
  await h.control("clock",{nowUs:"1900000000000000",errorUs:"1",qualified:true});await h.command(r);assert.equal(launchCount(h),1);
});
test("clock-rollback-quarantines-without-fence-regression",async h=>{
  const r=base();await h.command(r);h.setClock({nowUs:"1800000000000000",errorUs:"1",qualified:true});
  assert.deepEqual(obs(await h.command(r)),{status:"error",code:"unavailable"});
  const raw=await h.raw();assert.equal(raw.row.quarantined,1);assert.equal(raw.row.epoch,"1");assert.equal(h.calls().length,0);
});
test("concurrent-claims-grant-at-most-once",async h=>{
  const r=base();r.command="ensure_started";await h.command(r);
  const claims=await Promise.all(Array.from({length:16},()=>h.claim({instanceId:"instance-1",bootId:"boot-1"})));
  assert.equal(claims.filter(c=>c.granted).length,1);const raw=await h.raw();assert.equal(raw.row.claim_state,"consumed");
  await h.restart();assert.equal((await h.claim({instanceId:"instance-1",bootId:"boot-1"})).granted,false);
});
test("claim-final-expiry-consumes-without-regrant",async h=>{
  const r=base();r.command="ensure_started";await h.command(r);
  await h.control("sequence",{sequence:[{nowUs:"1900000000000000",errorUs:"1",qualified:true},{nowUs:"2000000000001000",errorUs:"1",qualified:true}]});
  assert.equal((await h.claim({instanceId:"instance-1",bootId:"boot-1"})).granted,false);
  assert.equal((await h.snapshot()).claimState,"consumed");
  await h.control("clock",{nowUs:"1900000000000000",errorUs:"1",qualified:true});await h.command(guard(r,{epoch:"2",owner_id:"next"}));
  assert.equal((await h.claim({instanceId:"instance-1",bootId:"boot-1"})).granted,false);
});
test("wrong-boot-and-binding-cannot-claim",async h=>{
  const r=base();r.command="ensure_started";await h.command(r);
  assert.equal((await h.claim({instanceId:"other",bootId:"boot-1"})).granted,false);
  const row=(await h.raw()).row;
  assert.equal((await h.control("rawClaim",{identity:{provider:row.provider_kind,key:row.provider_key,immutableSha256:row.binding_hash},instanceId:"instance-1",bootId:"boot-1",immutableSha256:"f".repeat(64)})).granted,false);
  assert.equal((await h.snapshot()).claimState,"unissued");
  assert.equal((await h.control("rawClaim",{identity:{provider:row.provider_kind,key:row.provider_key,immutableSha256:row.binding_hash},instanceId:"instance-1",bootId:"boot-1",immutableSha256:row.binding_hash,extra:true})).granted,false);
});
test("sqlite-rollback-and-bounded-audit",async h=>{
  const r=base();await h.command(r);const rollback=await h.control("rollback",{});assert.deepEqual(rollback.before,rollback.after);
  for(let i=0;i<80;i++)await h.command({...r,request_id:randomBytes(16).toString("hex")});
  assert.equal((await h.raw()).audit[0].count,32);
});
test("actual-runtime-alarm-without-customer-HTTP",async h=>{
  const r=base();r.command="ensure_started";await h.command(r);
  // No fetch/control calls during this interval: the runtime's persisted alarm
  // must execute itself, independently of a manually invoked test method.
  await delay(1350);
  const raw=await h.raw();assert(raw.settings.alarmTicks>=1);assert(raw.alarm!==null);
  assert.equal(launchCount(h),1);
});
test("deadline-alarm-stops-without-live-coordinator",async h=>{
  const r=base();r.command="ensure_started";await h.command(r);
  await h.control("clock",{nowUs:"2100000000000001",errorUs:"0",qualified:true});await h.fireAlarm();
  assert.equal((await h.snapshot()).desired,"stop");assert(stopCount(h)>=1);assert.equal(launchCount(h),1);
});
test("persisted-stop-enforced-with-unqualified-clock",async h=>{
  const r=base();r.command="stop";await h.command(r);const count=stopCount(h);
  await h.control("clock",{nowUs:"1900000000000000",errorUs:"1",qualified:false});await h.fireAlarm();
  assert(stopCount(h)>count);assert.equal((await h.snapshot()).desired,"stop");
});
test("terminal-report-needs-objects-and-definitive-drain",async h=>{
  const r=base();r.command="ensure_started";await h.command(r);await h.claim({instanceId:"instance-1",bootId:"boot-1"});
  const row=(await h.raw()).row;
  const result={outcome:"succeeded",artifacts:["unsigned_native_binary","guest_artifact","resource_inventory","debug_symbols","compatibility_report","sbom","provenance"].map((kind,i)=>({kind,sha256:String(i+1).repeat(64),size_bytes:"9223372036854775807"}))};
  const report={identity:{provider:row.provider_kind,key:row.provider_key,immutableSha256:row.binding_hash},immutableSha256:row.binding_hash,instanceId:row.instance_id,bootId:row.boot_id,claimId:row.claim_id,operationId:row.operation_id,result,attestationSha256:"a".repeat(64)};
  assert.equal((await h.control("report",report)).status,"rejected");await h.control("objects",{value:true});
  assert.equal((await h.control("report",{...report,extra:true})).status,"rejected");
  for(const invalid of [{...result,artifacts:result.artifacts.slice(1)},{...result,artifacts:result.artifacts.map((a,i)=>i===1?{...a,kind:result.artifacts[0].kind}:a)},
    {outcome:"failed",class:"compiler",code:"worker_lost",diagnostic_sha256:"a".repeat(64)}]){
    assert.equal((await h.control("report",{...report,result:invalid})).status,"rejected");
  }
  assert.equal((await h.control("report",report)).status,"accepted");assert.equal((await h.control("report",report)).status,"duplicate");
  assert.equal((await h.control("report",{...report,attestationSha256:"b".repeat(64)})).status,"rejected");
  await h.reconcile();assert.equal((await h.snapshot()).terminal,null);
  await h.deliverProvider({state:"absent",definitive:true,descendantsGone:true,launchesSettled:true});await h.reconcile();
  assert.deepEqual((await h.snapshot()).terminal,{status:"completed",result});await h.restart();
  assert.deepEqual(obs(await h.command(guard(r,{epoch:"2",owner_id:"next"}))),{status:"completed",result});assert.equal(launchCount(h),1);
});
test("newer-stop-rejects-old-terminal-report",async h=>{
  const r=base();r.command="ensure_started";await h.command(r);await h.claim({instanceId:"instance-1",bootId:"boot-1"});
  const row=(await h.raw()).row,stop=guard(r,{epoch:"2",owner_id:"next"});stop.command="stop";await h.command(stop);await h.control("objects",{value:true});
  const report={identity:{provider:row.provider_kind,key:row.provider_key,immutableSha256:row.binding_hash},immutableSha256:row.binding_hash,instanceId:row.instance_id,bootId:row.boot_id,claimId:row.claim_id,operationId:row.operation_id,result:{outcome:"failed",class:"compiler",code:"compiler_error",diagnostic_sha256:"a".repeat(64)},attestationSha256:"a".repeat(64)};
  assert.equal((await h.control("report",report)).status,"rejected");assert.equal((await h.raw()).row.pending_result_json,null);
});
test("restore-quarantine-keeps-consumed-claim",async h=>{
  const r=base();r.command="ensure_started";await h.command(r);await h.claim({instanceId:"instance-1",bootId:"boot-1"});
  await h.control("quarantine",{});await h.restart();
  assert.deepEqual(obs(await h.command(guard(r,{epoch:"2",owner_id:"next"}))),{status:"error",code:"unavailable"});
  assert.equal((await h.snapshot()).claimState,"consumed");assert.equal(launchCount(h),1);
});
test("SIGKILL-after-durable-intent-before-provider",async h=>{
  const r=base();r.command="ensure_started";h.inject("after_intent","barrier");
  const pending=h.command(r).catch(()=>null);await eventually(async()=>!!(await h.raw()).settings.barrier);
  const before=(await h.raw()).row;assert.equal(before.launch_dispatched,0);
  await h.hardRestart();await pending;const next=await h.command(r);
  assert.equal(next.httpStatus,200);assert.equal((await h.snapshot()).providerKey,before.provider_key);assert.equal(launchCount(h),1);
});
test("SIGKILL-after-consumed-claim-before-grant",async h=>{
  const r=base();r.command="ensure_started";await h.command(r);h.inject("after_claim_commit","barrier");
  const pending=h.claim({instanceId:"instance-1",bootId:"boot-1"}).catch(()=>null);await eventually(async()=>!!(await h.raw()).settings.barrier);
  assert.equal((await h.snapshot()).claimState,"consumed");await h.hardRestart();await pending;
  assert.equal((await h.claim({instanceId:"instance-1",bootId:"boot-1"})).granted,false);assert.equal(launchCount(h),1);
});
test("SIGKILL-after-provider-effect-before-ledger-ack",async h=>{
  const r=base();r.command="ensure_started";h.inject("after_provider_effect","barrier");
  const pending=h.command(r).catch(()=>null);await eventually(async()=>!!(await h.raw()).settings.barrier);
  const before=(await h.raw()).row;assert.equal(before.launch_dispatched,1);await h.hardRestart();await pending;
  await h.command(r);assert.equal(launchCount(h),1);assert.equal((await h.snapshot()).providerKey,before.provider_key);
});
test("SIGKILL-keeps-permanent-stop-terminal",async h=>{
  const r=base();r.command="stop";await h.command(r);
  await h.deliverProvider({state:"absent",definitive:true,descendantsGone:true,launchesSettled:true});await h.reconcile();
  assert.equal((await h.snapshot()).terminal.status,"stopped");await h.hardRestart();
  const next=guard(r,{epoch:"2",owner_id:"next"});next.command="ensure_started";
  assert.equal(obs(await h.command(next)).status,"stopped");assert.equal(launchCount(h),0);
});

let failed=false;
try{
  // Reuse the frozen test file unmodified and retain every cleanup receipt in
  // this process; no test outcome or contract is rewritten to fit the candidate.
  const argv=process.argv;process.argv=[argv[0],join(root,"verification/hosted-worker-controller-contract/acceptance.mjs"),"--candidate",join(project,"test/acceptance-driver.mjs")];
  try{await import(pathToFileURL(join(root,"verification/hosted-worker-controller-contract/acceptance.mjs")).href);}finally{process.argv=argv;}
  results.push({id:"frozen-20-scenarios-plus-five-fixtures",status:"passed"});
  for(const {id,fn} of cases){
    const h=id.startsWith("all-36-")||id.startsWith("Jason-control-")||id.startsWith("production-entry-")?null:await createHarness({fixture:base(),nowUs:"1900000000000000",errorUs:"1",clockQualified:true});
    try{await fn(h);results.push({id,status:"passed"});console.log(JSON.stringify({test:id,status:"passed"}));}
    finally{await h?.close();}
  }
}catch(error){failed=true;console.error(error);process.exitCode=1;}
finally{
  const report={status:failed?"failed":"passed",scope:"local-workerd-SQLite-and-finite-fixture-provider-only",results,cleanup:cleanupReceipts,
    limitations:["no-real-provider","no-qualified-production-clock","no-ingress-EOF-qualification","no-runner-credential-or-sandbox-qualification","no-independent-restore-anchor","no-R2-signing-store-or-GA"]};
  const reportPath=process.env.MIXER_CONTROLLER_TEST_REPORT??join(root,"verification/hosted-worker-controller-implementation/test-report.json");
  await writeFile(reportPath,JSON.stringify(report,null,2)+"\n");
  console.log(JSON.stringify({status:report.status,tests:results.length,cleanupReceipts:cleanupReceipts.length}));
}
