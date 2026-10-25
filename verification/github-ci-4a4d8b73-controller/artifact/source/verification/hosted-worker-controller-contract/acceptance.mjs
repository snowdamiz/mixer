/**
 * Independently authored contract tests, not a controller implementation.
 * node acceptance.mjs --vectors checks packet fixtures using Node only.
 * node acceptance.mjs --candidate /absolute/test/acceptance-driver.mjs runs a
 * separately assigned candidate. With neither option, exit 77 means PENDING.
 *
 * Candidate exports createHarness({fixture, nowUs, errorUs, clockQualified}).
 * All decimal times/epochs/fences are strings. Harness methods:
 * command(request, {credential="valid"}={}) -> {httpStatus, body|null};
 * rawCommand(Uint8Array, options={}) -> same reply using actual bounded decoder;
 * snapshot() -> {exists, desired, epoch, revision, owner, expiryUs, providerKey,
 *   phase, claimState, terminal}; calls() -> immutable provider call array;
 * setClock({nowUs,errorUs,qualified}); restart(); close();
 * inject(point, behavior); reconcile(); claim({bootId,instanceId}) -> {granted};
 * deliverProvider({state,definitive,descendantsGone,launchesSettled});
 * fireAlarm(); setGuard(request.guard).
 *
 * inject points: after_intent, after_dispatch, after_provider_effect,
 * before_claim_grant, after_claim_commit; behavior: crash, timeout, pause.
 * A fault returns HTTP 200/uncertain or rejects as an owned injected fault.
 * pause retains a delayed provider effect; deliverProvider releases its outcome.
 * calls contain {kind:launch|inspect|stop, providerKey}. Test-only harness must
 * use the actual candidate plus SQLite-backed DO runtime storage. These methods
 * must never be reachable through the deployment entry point.
 */
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { pathToFileURL } from "node:url";

const packet = new URL("./", import.meta.url);
const vectors = JSON.parse(await readFile(new URL("vectors.json", packet), "utf8"));
const clone = value => JSON.parse(JSON.stringify(value));
const sha = value => createHash("sha256").update(value, "utf8").digest("hex");
const max = 9223372036854775807n;
const decimal = (value, min=1n, upper=max) => {
  assert.equal(typeof value, "string");
  assert.match(value, /^(0|[1-9][0-9]*)$/);
  const n = BigInt(value);
  assert(n >= min && n <= upper);
  return n;
};
const arrayBytes = value => JSON.stringify(value);
function computedBytes(r) {
  const s = r.spec, f = r.ref, g = r.guard;
  const oldPrefix = ["mixer-build-operation-v1",g.record_id,
    f.organization_id,f.project_id,f.application_id,f.build_id,f.platform,f.attempt];
  const operation = JSON.stringify(oldPrefix).slice(0,-1) + "," + decimal(f.fence) + "]";
  const binding = arrayBytes(["mixer-worker-binding-v1",r.operation_id,g.record_id,
    [f.organization_id,f.project_id,f.application_id,f.build_id,f.platform,f.attempt,f.fence],
    [s.organization_id,s.project_id,s.application_id,s.build_id,s.platform,s.source.kind,
      s.source.sha256,s.source.reference,s.toolchain_lock_sha256,s.build_definition_sha256],
    r.deadline_ms]);
  return {operation,binding};
}

function verifyVectors() {
  assert.equal(vectors.version, 1);
  assert.equal(vectors.scope, "contract-fixtures-not-controller-or-Jason-qualification");
  assert(vectors.cases.length >= 5);
  for (const v of vectors.cases) {
    const {operation,binding} = computedBytes(v.request);
    assert.equal(operation, v.operation_json);
    assert.equal(binding, v.binding_json);
    assert.equal(sha(operation), v.request.operation_id);
    assert.equal(sha(binding), v.request.immutable_sha256);
    assert.equal(Buffer.byteLength(operation), v.operation_utf8_bytes);
    assert.equal(Buffer.byteLength(binding), v.binding_utf8_bytes);
    assert.equal(typeof v.request.ref.fence, "string");
    decimal(v.request.ref.fence);
    decimal(v.request.guard.expires_at_us);
  }
  for (const n of vectors.invalid_decimals) assert.throws(() => decimal(n));
  assert.equal(Number("9007199254740993"), Number("9007199254740992"));
  assert.notEqual(decimal("9007199254740993"), decimal("9007199254740992"));
  return {fixture_cases:vectors.cases.length,negative_decimals:vectors.invalid_decimals.length};
}

const scenarios = [];
const scenario = (id, fn) => scenarios.push({id, fn});
const nonce = "0123456789abcdef0123456789abcdef";
const base = () => clone(vectors.cases[0].request);
const withGuard = (r, fields) => ({...clone(r),guard:{...clone(r.guard),...fields}});
const observation = reply => {
  assert.equal(reply.httpStatus, 200);
  return reply.body.observation;
};
const isStale = reply => assert.deepEqual(observation(reply), {status:"error",code:"stale"});
const fault = async fn => {
  try { const reply = await fn(); assert.deepEqual(observation(reply),{status:"error",code:"uncertain"}); }
  catch (error) { if (error?.name !== "InjectedFault") throw error; }
};
const launchCount = h => h.calls().filter(c=>c.kind==="launch").length;

scenario("authentication-before-ledger", async h => {
  const r = base();
  const reply = await h.command(r,{credential:"invalid"});
  assert.notEqual(reply.httpStatus,200);
  assert.equal((await h.snapshot()).exists,false);
  assert.equal(h.calls().length,0);
});
scenario("malformed-wire-zero-mutation", async h => {
  const r=base(), raw=JSON.stringify(r), enc=new TextEncoder();
  const malformed=[
    raw.replace('"version":1','"version":1.0'),
    raw.replace('"version":1','"version":1e0'),
    raw.replace('"version":1','"version":1,"vers\\u0069on":1'),
    raw.replace('"fence":"1"','"fence":"1","fence":"2"'),
    raw.replace('"fence":"1"','"fence":1'),
    raw.replace('"fence":"1"','"fence":"01"'),
    raw.replace('"fence":"1"','"fence":"9223372036854775808"'),
    raw.replace('"attempt":1','"attempt":1.0'),
    raw.slice(0,-1)+',"extra":true}',
    raw.replace('"reference":"main"','"reference":"'+'a'.repeat(8193)+'"'),
    raw.replace('"version":1','"version":'+ '['.repeat(9)+'1'+']'.repeat(9)),
    ' '.repeat(16385),
  ].map(x=>enc.encode(x));
  malformed.push(new Uint8Array([0x7b,0xff,0x7d]));
  for(const bytes of malformed) {
    const reply=await h.rawCommand(bytes);
    assert.notEqual(reply.httpStatus,200);
    assert.equal((await h.snapshot()).exists,false);
    assert.equal(h.calls().length,0);
  }
});
scenario("machine-and-ref-scope-rejection", async h => {
  for(const key of ["environment_id","controller_id","pool_id"]) {
    const bad=base();bad[key]="other";
    assert.notEqual((await h.command(bad)).httpStatus,200);
  }
  const bad=base();bad.ref.project_id="other";
  assert.notEqual((await h.command(bad)).httpStatus,200);
  assert.equal((await h.snapshot()).exists,false);assert.equal(h.calls().length,0);
});
scenario("query-binds-without-launch", async h => {
  const r = base();
  assert.deepEqual(observation(await h.command(r)),{status:"absent"});
  assert.equal((await h.snapshot()).exists,true);
  assert.equal(launchCount(h),0);
});
scenario("exact-current-nonce-guard-echo", async h => {
  const r = base(); r.request_id=nonce;
  const reply = await h.command(r);
  const {spec,deadline_ms,...echo}=r;
  const {observation:ignored,...actual}=reply.body;
  assert.deepEqual(actual,echo);
  const newer = withGuard(r,{expires_at_us:"2000000000001001"});
  newer.request_id="fedcba9876543210fedcba9876543210";
  const second = await h.command(newer);
  assert.equal(second.body.request_id,newer.request_id);
  assert.deepEqual(second.body.guard,newer.guard);
});
scenario("immutable-conflict-zero-effect", async h => {
  const r=base(); await h.command(r); const before=await h.snapshot(), count=h.calls().length;
  const bad=clone(r);bad.spec.source.reference="changed";
  const reply=await h.command(bad);
  assert.notEqual(reply.httpStatus,200);
  assert.deepEqual(await h.snapshot(),before);
  assert.equal(h.calls().length,count);
});
scenario("older-pair-no-provider-query", async h => {
  const r=withGuard(base(),{epoch:"9007199254740993",revision:"5"});
  await h.command(r); const count=h.calls().length, before=await h.snapshot();
  isStale(await h.command(withGuard(r,{epoch:"9007199254740992",revision:"32"})));
  assert.equal(h.calls().length,count);assert.deepEqual(await h.snapshot(),before);
});
scenario("same-epoch-owner-conflict", async h => {
  const r=base();await h.command(r);const count=h.calls().length;
  isStale(await h.command(withGuard(r,{owner_id:"other",revision:"32"})));
  assert.equal(h.calls().length,count);
});
scenario("equal-pair-only-forward-expiry", async h => {
  const r=base();await h.command(r);
  await h.command(withGuard(r,{expires_at_us:"2000000000001001"}));
  const s=await h.snapshot(); assert.equal(s.expiryUs,"2000000000001001");
  isStale(await h.command(withGuard(r,{expires_at_us:"2000000000000999"})));
  assert.equal((await h.snapshot()).expiryUs,"2000000000001001");
});
scenario("higher-epoch-lower-revision", async h => {
  const r=withGuard(base(),{epoch:"9007199254740992",revision:"32"});await h.command(r);
  const next=withGuard(r,{epoch:"9007199254740993",revision:"0",owner_id:"next-owner"});
  await h.command(next);const s=await h.snapshot();
  assert.equal(s.epoch,next.guard.epoch);assert.equal(s.revision,"0");assert.equal(s.owner,"next-owner");
});
scenario("unqualified-clock-fails-closed", async h => {
  h.setClock({nowUs:"1900000000000000",errorUs:"1",qualified:false});
  const r=base();r.command="ensure_started";
  assert.deepEqual(observation(await h.command(r)),{status:"error",code:"unavailable"});
  assert.equal(launchCount(h),0);
});
scenario("expiry-upper-bound-equality", async h => {
  const r=base();r.command="ensure_started";
  h.setClock({nowUs:"2000000000000999",errorUs:"1",qualified:true});
  isStale(await h.command(r));assert.equal(launchCount(h),0);
});
scenario("duplicate-ensure-single-launch", async h => {
  const r=base();r.command="ensure_started";
  await Promise.all([h.command(r),h.command({...clone(r),request_id:nonce})]);
  assert.equal(launchCount(h),1);
  const keys=new Set(h.calls().map(c=>c.providerKey));assert.equal(keys.size,1);
});
scenario("stop-before-ensure-permanent", async h => {
  const r=base();r.command="stop";await h.command(r);
  await h.deliverProvider({state:"absent",definitive:true,descendantsGone:true,launchesSettled:true});
  await h.reconcile();await h.restart();
  const later=withGuard(r,{epoch:"2",owner_id:"next"});later.command="ensure_started";
  const o=observation(await h.command(later));assert.equal(o.status,"stopped");
  assert.equal(launchCount(h),0);assert.equal((await h.snapshot()).desired,"stop");
});
scenario("timeout-absent-never-relaunch", async h => {
  const r=base();r.command="ensure_started";h.inject("after_dispatch","timeout");
  await fault(()=>h.command(r));await h.restart();
  await h.deliverProvider({state:"absent",definitive:false,descendantsGone:false,launchesSettled:false});
  for(let i=0;i<3;i++){await h.command(r);await h.reconcile();}
  assert.equal(launchCount(h),1);
});
scenario("delayed-launch-after-stop-no-claim", async h => {
  const r=base();r.command="ensure_started";h.inject("after_dispatch","pause");
  await fault(()=>h.command(r));
  const stop=withGuard(r,{epoch:"2",owner_id:"next"});stop.command="stop";await h.command(stop);
  await h.deliverProvider({state:"inert",definitive:false,descendantsGone:false,launchesSettled:false});
  assert.equal((await h.claim({bootId:"boot-1",instanceId:"instance-1"})).granted,false);
  assert.equal((await h.snapshot()).desired,"stop");assert.equal(launchCount(h),1);
});
scenario("claim-consumed-before-lost-grant", async h => {
  const r=base();r.command="ensure_started";await h.command(r);
  await h.deliverProvider({state:"inert",definitive:false,descendantsGone:false,launchesSettled:true});
  h.inject("after_claim_commit","crash");
  await fault(()=>h.claim({bootId:"boot-1",instanceId:"instance-1"}));await h.restart();
  assert.equal((await h.snapshot()).claimState,"consumed");
  assert.equal((await h.claim({bootId:"boot-1",instanceId:"instance-1"})).granted,false);
  assert.equal((await h.claim({bootId:"boot-2",instanceId:"instance-2"})).granted,false);
});
scenario("stop-ack-not-descendant-proof", async h => {
  const r=base();r.command="stop";await h.command(r);
  await h.deliverProvider({state:"absent",definitive:false,descendantsGone:false,launchesSettled:false});
  const o=observation(await h.command(r));assert.equal(o.status,"error");assert.equal(o.code,"uncertain");
  assert.notEqual((await h.snapshot()).phase,"stopped");
});
scenario("intent-crash-restart-keeps-identity", async h => {
  const r=base();r.command="ensure_started";h.inject("after_intent","crash");
  await fault(()=>h.command(r));const key=(await h.snapshot()).providerKey;
  assert(key);await h.restart();await h.command(r);
  assert.equal((await h.snapshot()).providerKey,key);
  assert(launchCount(h)<=1);
});
scenario("duplicate-alarm-retains-single-effect", async h => {
  const r=base();r.command="ensure_started";await h.command(r);
  await h.fireAlarm();await h.fireAlarm();await h.restart();await h.fireAlarm();
  assert.equal(launchCount(h),1);
});

const args=process.argv.slice(2);
if(args[0]==="--vectors") {
  const output=verifyVectors();
  console.log(JSON.stringify({status:"passed",scope:"packet-byte-vectors-only",...output}));
} else if(args[0]==="--candidate" && args.length===2) {
  verifyVectors();
  const {createHarness}=await import(pathToFileURL(args[1]).href);
  assert.equal(typeof createHarness,"function");
  const results=[];
  for(const v of vectors.cases) {
    const h=await createHarness({fixture:clone(v.request),nowUs:"1900000000000000",errorUs:"1",clockQualified:true});
    try {
      const reply=await h.command(clone(v.request));
      assert.deepEqual(observation(reply),{status:"absent"});
      assert.equal(reply.body.operation_id,v.request.operation_id);
      assert.equal(reply.body.immutable_sha256,v.request.immutable_sha256);
      assert.deepEqual(reply.body.ref,v.request.ref);
      results.push({id:"wire-vector-"+v.name,status:"passed"});
    } finally {await h.close();}
  }
  for(const {id,fn} of scenarios) {
    const h=await createHarness({fixture:base(),nowUs:"1900000000000000",errorUs:"1",clockQualified:true});
    try {await fn(h);results.push({id,status:"passed"});}
    finally {await h.close();}
  }
  console.log(JSON.stringify({status:"passed",scope:"candidate-contract-tests-platform-evidence-separate",results}));
} else if(args[0]==="--inventory") {
  console.log(JSON.stringify({version:1,scenarios:scenarios.map(x=>x.id)}));
} else {
  console.log(JSON.stringify({status:"pending",reason:"no-controller-candidate-assigned",scenarios:scenarios.length}));
  process.exitCode=77;
}
