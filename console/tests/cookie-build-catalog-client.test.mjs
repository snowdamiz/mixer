import assert from "node:assert/strict";
import { test } from "node:test";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

import { compileBuildSelectionTests } from "./helpers/build-selection-compiled.mjs";
const output = compileBuildSelectionTests();
const load = path => import(pathToFileURL(join(output, path)).href);
const { createCookieBuildCatalogClient } = await load("api/cookie-build-catalog-client.js");
const { createCookieBuildClient } = await load("api/cookie-build-client.js");
const { WorkspaceClientError } = await load("api/workspace-transport.js");
const { parseApplicationPage, parseBuildPage } = await load("domain/build-catalog.js");
const project = () => ({ organizationId: "org.A-1", projectId: "p_2" });
const application = () => ({ ...project(), applicationId: "app" });
const dto = (changes = {}) => ({ ...application(), buildId: "build", platform: "ios",
  sourceSha256: "a".repeat(64), toolchainLockSha256: "b".repeat(64), buildDefinitionSha256: "c".repeat(64),
  revision: 0, state: "queued", attempt: 1, maxAttempts: 3, failureCode: null, workerCompletionPending: false, ...changes });
const apps = (applications = [], nextCursor = null) => ({ ...project(), applications, nextCursor });
const builds = (rows = [], nextCursor = null) => ({ ...application(), builds: rows, nextCursor });
const json = value => new Response(JSON.stringify(value), { headers: { "content-type": "application/json" } });
const api = value => createCookieBuildCatalogClient({ fetch: async () => json(value) });
const safeError = code => error => {
  assert.ok(error instanceof WorkspaceClientError);
  assert.equal(error.code, code);
  assert.equal(error.message, `Workspace request ${code}`);
  assert.deepEqual(Object.keys(error).sort(), ["code", "name"]);
  assert.equal(error.cause, undefined);
  return true;
};
const cursor = value => Buffer.from(value).toString("base64url");
const continuation = cursor(JSON.stringify({ v: 1, kind: "applications", ...project(), lastApplicationId: "app" }));

test("authorized empty pages are frozen successes and full pages accept exactly 25 sorted rows", async () => {
  for (const count of [0, 25]) {
    const ids = Array.from({ length: count }, (_, i) => `app-${String(i).padStart(2, "0")}`);
    const a = await api(apps(ids.map(applicationId => ({ applicationId })), count ? continuation : null)).applications(project(), {});
    assert.equal(a.applications.length, count); assert.equal(a.nextCursor, count ? continuation : null);
    const b = await api(builds(ids.map(buildId => dto({ buildId })))).builds(application(), {});
    assert.equal(b.builds.length, count);
    for (const object of [a, a.applications, ...a.applications, b, b.builds, ...b.builds,
      ...b.builds.flatMap(row => [row.selection, row.snapshot, row.snapshot.report])]) assert(Object.isFrozen(object));
  }
});

test("all actual status variants reuse the detail decoder and preserve exact selections", async () => {
  for (const state of ["queued", "running", "cancelling", "reconciling", "succeeded", "failed", "cancelled", "timed_out"]) {
    const row = dto({ state, revision: 32, attempt: 3, failureCode: ["failed", "timed_out"].includes(state) ? "compiler_error" : null,
      workerCompletionPending: ["running", "cancelling", "reconciling"].includes(state) });
    const page = await api(builds([row])).builds(application(), {});
    const selected = page.builds[0]; assert.equal(selected.snapshot.report.state, state);
    let detailPath;
    const read = createCookieBuildClient({ fetch: async path => { detailPath = path; return json({ build: row }); } });
    assert.deepEqual(await read.read(selected.selection), selected.snapshot);
    const url = new URL(detailPath, "https://console.invalid");
    assert.equal(url.pathname, "/console-api/v1/builds"); assert.equal([...url.searchParams].length, 8);
    for (const [key, wire] of [["organizationId", "organization_id"], ["projectId", "project_id"], ["applicationId", "application_id"],
      ["buildId", "build_id"], ["platform", "platform"], ["sourceSha256", "source_sha256"],
      ["toolchainLockSha256", "toolchain_lock_sha256"], ["buildDefinitionSha256", "build_definition_sha256"]])
      assert.equal(url.searchParams.get(wire), row[key]);
  }
});

test("only the two relative GET routes, exact filters and confidential cookie settings are used", async () => {
  const paths = [];
  const client = createCookieBuildCatalogClient({ fetch: async (path, init) => {
    paths.push(path); assert.equal(init.method, "GET"); assert.equal(init.credentials, "same-origin");
    assert.equal(init.cache, "no-store"); assert.equal(init.redirect, "error"); assert.equal(init.referrerPolicy, "no-referrer");
    assert.deepEqual([...new Headers(init.headers)], [["accept", "application/json"]]); assert.equal(init.body, undefined);
    return json(path.startsWith("/console-api/v1/applications?") ? apps() : builds());
  } });
  await client.applications(project(), { cursor: continuation }); await client.builds(application(), {});
  assert.deepEqual(paths, [`/console-api/v1/applications?organization_id=org.A-1&project_id=p_2&cursor=${encodeURIComponent(continuation)}`,
    "/console-api/v1/build-catalog?organization_id=org.A-1&project_id=p_2&application_id=app"]);
  assert.deepEqual(Object.keys(client), ["applications", "builds"]); assert(Object.isFrozen(client));
});

test("scope and page intent are captured before await; later mutation cannot change validation", async () => {
  for (const method of ["applications", "builds"]) {
    let release, seen;
    const client = createCookieBuildCatalogClient({ fetch: path => { seen = path; return new Promise(resolve => { release = resolve; }); } });
    const scope = method === "applications" ? project() : application(); const page = { cursor: continuation };
    const pending = client[method](scope, page);
    scope.organizationId = "foreign"; scope.projectId = "foreign"; if (method === "builds") scope.applicationId = "foreign";
    page.cursor = cursor("changed");
    await new Promise(resolve => setImmediate(resolve));
    assert(seen.includes("organization_id=org.A-1")); assert(seen.endsWith(`cursor=${continuation}`));
    release(json(method === "applications" ? apps([{ applicationId: "app" }]) : builds([dto()])));
    assert.equal((await pending).organizationId, "org.A-1");
  }
});

test("closed request records reject hidden/symbol keys, prototypes and accessors without invoking them", async () => {
  let calls = 0, getters = 0;
  const client = createCookieBuildCatalogClient({ fetch: async () => { calls++; return json(apps()); } });
  const scopeCases = [null, [], {}, { ...project(), applicationId: "app" }, Object.assign(Object.create({ authority: true }), project())];
  const hidden = project(); Object.defineProperty(hidden, "extra", { value: true }); scopeCases.push(hidden);
  scopeCases.push({ ...project(), [Symbol("authority")]: true });
  const accessor = project(); Object.defineProperty(accessor, "organizationId", { enumerable: true, get() { getters++; return "org.A-1"; } }); scopeCases.push(accessor);
  for (const scope of scopeCases) await assert.rejects(client.applications(scope, {}), safeError("invalid_request"));
  const pages = [undefined, null, [], { limit: 25 }, { filter: "*" }, { cursor: undefined }, { [Symbol("cursor")]: "x" }, Object.create({ cursor: continuation })];
  const getterPage = {}; Object.defineProperty(getterPage, "cursor", { enumerable: true, get() { getters++; return continuation; } }); pages.push(getterPage);
  for (const page of pages) await assert.rejects(client.applications(project(), page), safeError("invalid_request"));
  const getterOptions = {}; Object.defineProperty(getterOptions, "fetch", { enumerable: true, get() { getters++; return globalThis.fetch; } });
  for (const options of [null, [], { baseURL: "https://evil.invalid" }, { token: "secret" }, { headers: {} }, { credentials: "include" },
    { sort: "newest" }, { timeoutMs: 0 }, { timeoutMs: 30001 }, { fetch: 1 }, getterOptions, Object.create({ timeoutMs: 1 })])
    assert.throws(() => createCookieBuildCatalogClient(options), safeError("invalid_request"));
  assert.equal(getters, 0); assert.equal(calls, 0);
});

test("all scope identifiers use exact bounded ASCII grammar", async () => {
  for (const key of ["organizationId", "projectId", "applicationId"]) for (const value of ["", "x".repeat(129), "é", "a/b", "a?b", "a\n", null, 4])
    await assert.rejects(api(builds()).builds({ ...application(), [key]: value }, {}), safeError("invalid_request"));
  const full = { organizationId: "A".repeat(128), projectId: "_-.", applicationId: "Z9" };
  assert.equal((await api({ ...full, builds: [], nextCursor: null }).builds(full, {})).applicationId, "Z9");
});

test("opaque cursors enforce canonical base64url and decoded bounds on requests and responses", async () => {
  const valid = [continuation, cursor("opaque, not authenticated JSON"), cursor(Buffer.alloc(1024, 255))];
  for (const value of valid) {
    assert.equal((await api(apps([], value)).applications(project(), { cursor: value })).nextCursor, value);
  }
  for (const value of ["", "A", "AB", "AA=", "a+b/", "a b", "é", "A".repeat(1401), cursor(Buffer.alloc(1025)), null, 2]) {
    await assert.rejects(api(apps()).applications(project(), { cursor: value }), safeError("invalid_request"));
    if (value !== null) await assert.rejects(api(apps([], value)).applications(project(), {}), safeError("invalid_response"));
  }
});

test("exact envelope and row keys, parent equality and dense arrays fail closed", () => {
  for (const [value, expected, parse] of [[apps([{ applicationId: "app" }]), project(), parseApplicationPage], [builds([dto()]), application(), parseBuildPage]]) {
    for (const key of Object.keys(value)) { const changed = structuredClone(value); delete changed[key]; assert.throws(() => parse(changed, expected)); }
    assert.throws(() => parse({ ...value, extra: true }, expected));
    for (const key of Object.keys(expected)) assert.throws(() => parse({ ...value, [key]: "foreign" }, expected));
    const hidden = structuredClone(value); Object.defineProperty(hidden, "private", { value: true }); assert.throws(() => parse(hidden, expected));
    const field = parse === parseApplicationPage ? "applications" : "builds";
    const row = value[field][0];
    assert.throws(() => parse({ ...value, [field]: [{ ...row, extra: true }] }, expected));
    const sparse = new Array(1); assert.throws(() => parse({ ...value, [field]: sparse }, expected));
    const hiddenRow = { ...row }; Object.defineProperty(hiddenRow, "private", { value: true });
    assert.throws(() => parse({ ...value, [field]: [hiddenRow] }, expected));
    const symbolRow = { ...row, [Symbol("private")]: true }; assert.throws(() => parse({ ...value, [field]: [symbolRow] }, expected));
    let gets = 0; const accessor = { ...row }; Object.defineProperty(accessor, Object.keys(row)[0], { enumerable: true, get() { gets++; return "secret"; } });
    assert.throws(() => parse({ ...value, [field]: [accessor] }, expected)); assert.equal(gets, 0);
  }
});

test("25-row limit, duplicate keys and C ordering reject the entire page", async () => {
  for (const ids of [["b", "a"], ["a", "a"], Array.from({ length: 26 }, (_, i) => `a${String(i).padStart(2, "0")}`)]) {
    await assert.rejects(api(apps(ids.map(applicationId => ({ applicationId })))).applications(project(), {}), safeError("invalid_response"));
    await assert.rejects(api(builds(ids.map(buildId => dto({ buildId })))).builds(application(), {}), safeError("invalid_response"));
  }
  assert.equal((await api(builds([dto({ platform: "android" }), dto({ platform: "ios" })])).builds(application(), {})).builds.length, 2);
  await assert.rejects(api(builds([dto({ platform: "ios" }), dto({ platform: "android" })])).builds(application(), {}), safeError("invalid_response"));
  assert.deepEqual((await api(apps(["A", "Z", "_", "a"].map(applicationId => ({ applicationId })))).applications(project(), {})).applications.map(x => x.applicationId), ["A", "Z", "_", "a"]);
});

test("every 14-field DTO slot is required and invalid identity/status values cannot become a selection", async () => {
  for (const key of Object.keys(dto())) { const row = dto(); delete row[key]; await assert.rejects(api(builds([row])).builds(application(), {}), safeError("invalid_response")); }
  const invalid = [{ organizationId: "foreign" }, { projectId: "foreign" }, { applicationId: "foreign" }, { buildId: "a/b" },
    { platform: "web" }, { sourceSha256: "A".repeat(64) }, { toolchainLockSha256: "b".repeat(63) }, { buildDefinitionSha256: "g".repeat(64) },
    { revision: -1 }, { revision: 33 }, { revision: 0.5 }, { revision: "1" }, { state: "ready" }, { attempt: 0 }, { attempt: 4 },
    { maxAttempts: 6 }, { maxAttempts: 1.5 }, { failureCode: "compiler_error" }, { state: "failed", failureCode: null },
    { state: "failed", failureCode: "secret" }, { workerCompletionPending: true }, { state: "running", workerCompletionPending: false }];
  for (const change of invalid) await assert.rejects(api(builds([dto(change)])).builds(application(), {}), safeError("invalid_response"));
});

test("HTTP failures redact bodies, never parse error pages, and preserve unchanged transport mapping", async () => {
  for (const [status, code] of [[400, "invalid_response"], [401, "unauthenticated"], [403, "permission_denied"], [404, "not_found"], [503, "unavailable"]]) {
    let cancelled = false;
    const stream = new ReadableStream({ cancel() { cancelled = true; } });
    const client = createCookieBuildCatalogClient({ fetch: async () => new Response(stream, { status }) });
    await assert.rejects(client.builds(application(), {}), safeError(code)); assert(cancelled);
  }
  await assert.rejects(createCookieBuildCatalogClient({ fetch: async () => { throw new Error("PRIVATE_TOKEN_URL"); } }).applications(project(), {}), safeError("unavailable"));
});

test("response ceiling, malformed UTF8/JSON and stream chunk/read ceilings cancel and release", async () => {
  for (const make of [() => new Response("private"), () => new Response("{", { headers: { "content-type": "application/json" } }),
    () => new Response(new Uint8Array([255]), { headers: { "content-type": "application/json" } }),
    () => new Response("{}", { headers: { "content-type": "application/json", "content-length": "262145" } })])
    await assert.rejects(createCookieBuildCatalogClient({ fetch: async () => make() }).applications(project(), {}), safeError("invalid_response"));
  for (const size of [65536, 0]) {
    let reads = 0, cancelled = false;
    const stream = new ReadableStream({ pull(c) { reads++; c.enqueue(new Uint8Array(size)); }, cancel() { cancelled = true; } });
    await assert.rejects(createCookieBuildCatalogClient({ fetch: async () => new Response(stream, { headers: { "content-type": "application/json" } }) }).builds(application(), {}), safeError("invalid_response"));
    assert(cancelled); assert.equal(stream.locked, false); assert(reads <= (size ? 6 : 4097));
  }
});

test("abort and deadlines settle noncooperative fetch/body and late bodies are cancelled", async () => {
  let calls = 0; const pre = new AbortController(); pre.abort();
  await assert.rejects(createCookieBuildCatalogClient({ fetch: async () => { calls++; return json(apps()); } }).applications(project(), {}, pre.signal), safeError("aborted"));
  assert.equal(calls, 0);
  for (const phase of ["fetch", "body"]) for (const mode of ["abort", "deadline"]) {
    let release, cancelled = false;
    const stream = new ReadableStream({ cancel() { cancelled = true; } }); const controller = new AbortController();
    const client = createCookieBuildCatalogClient({ timeoutMs: mode === "deadline" ? 20 : 1000,
      fetch: phase === "body" ? async () => new Response(stream, { headers: { "content-type": "application/json" } }) : () => new Promise(resolve => { release = resolve; }) });
    const pending = client.applications(project(), {}, controller.signal);
    await new Promise(resolve => setImmediate(resolve)); if (mode === "abort") controller.abort();
    await assert.rejects(pending, safeError(mode === "abort" ? "aborted" : "unavailable"));
    if (phase === "fetch") release(new Response(stream, { headers: { "content-type": "application/json" } }));
    await new Promise(resolve => setImmediate(resolve)); assert(cancelled); assert.equal(stream.locked, false);
  }
});


// R1174: retain the five passed independent groups and original inherited-application reproduction.
{
const create = createCookieBuildCatalogClient, parseA = parseApplicationPage, parseB = parseBuildPage;
const { snapshotCatalogPageRequest } = await load("domain/build-catalog.js");
const { parseBuildRead } = await load("domain/build-read.js");
const P=()=>({organizationId:'Org',projectId:'Proj'}), A=()=>({...P(),applicationId:'App'});
const dto=(x={})=>({...A(),buildId:'B',platform:'ios',sourceSha256:'a'.repeat(64),toolchainLockSha256:'b'.repeat(64),buildDefinitionSha256:'c'.repeat(64),revision:32,state:'queued',attempt:1,maxAttempts:5,failureCode:null,workerCompletionPending:false,...x});
const apps=(rows=[],nextCursor=null)=>({...P(),applications:rows,nextCursor});
const builds=(rows=[],nextCursor=null)=>({...A(),builds:rows,nextCursor});
const response=x=>new Response(JSON.stringify(x),{headers:{'content-type':'application/json'}});
const invalid=fn=>assert.throws(fn,TypeError);
const frozen=x=>{if(x&&typeof x==='object'){assert(Object.isFrozen(x));for(const y of Object.values(x))frozen(y)}};
const check=(name,fn)=>test('R1170: '+name,fn);
check('canonical cursor trailing bits padding and 1024-byte boundary',async()=>{
 for(const n of [1,2,3,1023,1024]){const c=Buffer.alloc(n,255).toString('base64url');assert.equal(snapshotCatalogPageRequest({cursor:c}).cursor,c);assert.equal(parseA(apps([],c),P()).nextCursor,c)}
 for(const c of ['A','AB','A_','AA=','AAA=','____=','AA\n',Buffer.alloc(1025).toString('base64url'),'A'.repeat(1401)]){invalid(()=>snapshotCatalogPageRequest({cursor:c}));invalid(()=>parseA(apps([],c),P()))}
 for(const [canonical,noncanonical]of [['AA','AB'],['AAA','AAB']]){assert.deepEqual(Buffer.from(canonical,'base64url'),Buffer.from(noncanonical,'base64url'));invalid(()=>snapshotCatalogPageRequest({cursor:noncanonical}))}
});
check('closed records and arrays reject foreign prototypes hidden keys symbols and getters',async()=>{
 let gets=0,calls=0;const client=create({fetch:async()=>{calls++;return response(apps())}});
 const getter=(obj,key)=>Object.defineProperty(obj,key,{enumerable:true,configurable:true,get(){gets++;throw Error('getter invoked')}});
 const badScopes=[Object.assign(Object.create({x:1}),P()),getter(P(),'organizationId'),Object.defineProperty(P(),'hidden',{value:1}),{...P(),[Symbol('x')]:1}];
 for(const s of badScopes)await assert.rejects(client.applications(s,{}),e=>e.code==='invalid_request');
 for(const p of [getter({},'cursor'),Object.create({cursor:'AA'}),Object.defineProperty({},'x',{value:1})])await assert.rejects(client.applications(P(),p),e=>e.code==='invalid_request');
 for(const o of [getter({},'fetch'),Object.assign(Object.create({fetch:()=>{calls++}}),{}),{token:'x'},{baseURL:'https://invalid'}])assert.throws(()=>create(o),e=>e.code==='invalid_request');
 for(const key of Object.keys(dto()))invalid(()=>parseB(builds([getter(dto(),key)]),A()));
 invalid(()=>parseA(getter(apps(),'applications'),P()));
 invalid(()=>parseA(apps([Object.assign(Object.create({x:1}),{applicationId:'X'})]),P()));
 const dense=[{applicationId:'X'}];Object.defineProperty(dense,'0',{enumerable:true,get(){gets++;return {applicationId:'X'}}});invalid(()=>parseA(apps(dense),P()));
 invalid(()=>parseA(apps(new Array(1)),P()));invalid(()=>parseA(apps(Object.assign([],{extra:1})),P()));
 assert.equal(gets,0);assert.equal(calls,0);
});
check('C ordering duplicate identities and 25 versus 26 rows',()=>{
 const ids=['-','.','0','A','Z','_','a','z'];assert.deepEqual(parseA(apps(ids.map(applicationId=>({applicationId}))),P()).applications.map(x=>x.applicationId),ids);
 for(const ids of [['a','Z'],['a','a'],Array.from({length:26},(_,i)=>String(i).padStart(2,'0'))]){invalid(()=>parseA(apps(ids.map(applicationId=>({applicationId}))),P()));invalid(()=>parseB(builds(ids.map(buildId=>dto({buildId}))),A()))}
 assert.equal(parseA(apps(Array.from({length:25},(_,i)=>({applicationId:String(i).padStart(2,'0')}))),P()).applications.length,25);
 assert.equal(parseB(builds([dto({platform:'android'}),dto()]),A()).builds.length,2);invalid(()=>parseB(builds([dto(),dto({platform:'android'})]),A()));
});
check('all fourteen DTO fields all eight states exact parents and immutable eight-field selections',()=>{
 const keys=['organizationId','projectId','applicationId','buildId','platform','sourceSha256','toolchainLockSha256','buildDefinitionSha256'];
 assert.equal(Object.keys(dto()).length,14);
 for(const state of ['queued','running','cancelling','reconciling','succeeded','failed','cancelled','timed_out']){
  const row=dto({state,workerCompletionPending:['running','cancelling','reconciling'].includes(state),failureCode:['failed','timed_out'].includes(state)?'test_failure':null});
  const page=parseB(builds([row]),A());const selected=page.builds[0];assert.deepEqual(Object.keys(selected.selection).sort(),[...keys].sort());assert.deepEqual(selected.snapshot,parseBuildRead({build:row},selected.selection));frozen(page);
  row.buildId='changed';row.sourceSha256='f'.repeat(64);assert.equal(selected.selection.buildId,'B');assert.equal(selected.selection.sourceSha256,'a'.repeat(64));assert.throws(()=>{selected.selection.buildId='bad'},TypeError);
 }
 for(const key of Object.keys(dto())){const row=dto();delete row[key];invalid(()=>parseB(builds([row]),A()))}
 for(const key of ['organizationId','projectId','applicationId']){invalid(()=>parseB(builds([dto({[key]:'Else'})]),A()));invalid(()=>parseB({...builds(),[key]:'Else'},A()))}
 for(const change of [{revision:33},{revision:NaN},{state:'unknown'},{attempt:0},{attempt:6},{maxAttempts:6},{failureCode:'compiler_error'},{state:'failed'},{workerCompletionPending:true},{sourceSha256:'A'.repeat(64)},{toolchainLockSha256:'0'.repeat(63)},{buildDefinitionSha256:'g'.repeat(64)}])invalid(()=>parseB(builds([dto(change)]),A()));
});
check('synchronous scope page and options capture under reentrant fetch',async()=>{
 for(const method of ['applications','builds']){
  let url;const scope=method==='applications'?P():A();const page={cursor:'AA'};
  const options={timeoutMs:2000,fetch:async(u,init)=>{url=u;scope.organizationId='Else';scope.projectId='Else';if(method==='builds')scope.applicationId='Else';page.cursor='AQ';assert.equal(init.credentials,'same-origin');assert.equal(init.method,'GET');return response(method==='applications'?apps():builds([dto()]))}};
  const c=create(options);options.fetch=()=>{throw Error('changed option used')};const promise=c[method](scope,page);scope.organizationId='BeforeFetch';page.cursor='Ag';const out=await promise;
  assert.equal(out.organizationId,'Org');assert(url.includes('organization_id=Org&project_id=Proj'));assert(url.endsWith('cursor=AA'));
 }
 const c=create({fetch:async()=>new Response('',{status:400})});await assert.rejects(c.applications(P(),{}),e=>e.code==='invalid_response');
});
check('applications route ignores inherited applicationId on Object.prototype',async()=>{
 let url;const c=create({fetch:async u=>{url=u;return response(apps())}});
 const before=Object.getOwnPropertyDescriptor(Object.prototype,'applicationId');assert.equal(before,undefined);
 try{Object.defineProperty(Object.prototype,'applicationId',{value:'Inherited-App',configurable:true});await c.applications(P(),{});assert.equal(url,'/console-api/v1/applications?organization_id=Org&project_id=Proj')}
 finally{delete Object.prototype.applicationId;assert.equal(Object.getOwnPropertyDescriptor(Object.prototype,'applicationId'),before)}
});

}


async function withCatalogPrototype(key, descriptor, control) {
  const originalDescriptor = Object.getOwnPropertyDescriptor(Object.prototype, key);
  try {
    Object.defineProperty(Object.prototype, key, { ...descriptor, configurable: true });
    await control();
  } finally {
    if (originalDescriptor === undefined) delete Object.prototype[key];
    else Object.defineProperty(Object.prototype, key, originalDescriptor);
    assert.deepEqual(Object.getOwnPropertyDescriptor(Object.prototype, key), originalDescriptor);
  }
}

test("R1174: inherited cursor is omitted and an own cursor remains exact on both routes", async () => {
  await withCatalogPrototype("cursor", { value: "AQ", writable: true }, async () => {
    const paths = [];
    const client = createCookieBuildCatalogClient({ fetch: async path => {
      paths.push(path); return json(path.startsWith("/console-api/v1/applications?") ? apps() : builds());
    } });
    await client.applications(project(), {});
    await client.builds(application(), {});
    await client.applications(project(), { cursor: "AA" });
    await client.builds(application(), { cursor: "AA" });
    assert.deepEqual(paths, [
      "/console-api/v1/applications?organization_id=org.A-1&project_id=p_2",
      "/console-api/v1/build-catalog?organization_id=org.A-1&project_id=p_2&application_id=app",
      "/console-api/v1/applications?organization_id=org.A-1&project_id=p_2&cursor=AA",
      "/console-api/v1/build-catalog?organization_id=org.A-1&project_id=p_2&application_id=app&cursor=AA",
    ]);
  });
});

test("R1174: inherited applicationId never changes applications and genuine builds keep the captured own field", async () => {
  await withCatalogPrototype("applicationId", { value: "Inherited-App", writable: true }, async () => {
    const paths = [];
    const client = createCookieBuildCatalogClient({ fetch: async path => {
      paths.push(path); return json(path.startsWith("/console-api/v1/applications?") ? apps() : builds());
    } });
    await client.applications(project(), {});
    await client.builds(application(), {});
    await assert.rejects(client.builds(project(), {}), safeError("invalid_request"));
    await assert.rejects(client.applications(application(), {}), safeError("invalid_request"));
    assert.deepEqual(paths, [
      "/console-api/v1/applications?organization_id=org.A-1&project_id=p_2",
      "/console-api/v1/build-catalog?organization_id=org.A-1&project_id=p_2&application_id=app",
    ]);
  });
});

test("R1174: inherited optional getters are unread and own accessors and fake scopes refuse without reads", async () => {
  let gets = 0, calls = 0;
  const denied = () => { gets++; throw new Error("accessor invoked"); };
  await withCatalogPrototype("applicationId", { get: denied }, async () => {
    await withCatalogPrototype("cursor", { get: denied }, async () => {
      const paths = [];
      const client = createCookieBuildCatalogClient({ fetch: async path => {
        calls++; paths.push(path); return json(path.startsWith("/console-api/v1/applications?") ? apps() : builds());
      } });
      await client.applications(project(), {});
      await client.builds(application(), {});
      await client.applications(project(), { cursor: "AA" });
      const fake = Object.assign(Object.create({ applicationId: "app" }), project());
      const ownAccessor = Object.defineProperty(application(), "applicationId", { enumerable: true, get: denied });
      const pageAccessor = Object.defineProperty({}, "cursor", { enumerable: true, get: denied });
      await assert.rejects(client.builds(fake, {}), safeError("invalid_request"));
      await assert.rejects(client.builds(ownAccessor, {}), safeError("invalid_request"));
      await assert.rejects(client.applications(project(), pageAccessor), safeError("invalid_request"));
      assert.deepEqual(paths, [
        "/console-api/v1/applications?organization_id=org.A-1&project_id=p_2",
        "/console-api/v1/build-catalog?organization_id=org.A-1&project_id=p_2&application_id=app",
        "/console-api/v1/applications?organization_id=org.A-1&project_id=p_2&cursor=AA",
      ]);
      assert.equal(gets, 0); assert.equal(calls, 3);
    });
  });
  assert.equal(gets, 0);
});
