import assert from "node:assert/strict";
import { after, test } from "node:test";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const supplied = process.env.MIXER_BUILD_CLIENT_COMPILED;
const output = supplied ?? mkdtempSync(join(tmpdir(), "mixer-cookie-build-client-"));
if (!supplied) {
  after(() => rmSync(output, { recursive: true, force: true }));
  try {
    execFileSync(process.execPath, [join(root, "node_modules/typescript/bin/tsc"),
      "src/api/cookie-build-client.ts", "src/api/workspace-client.ts", "--outDir", output,
      "--target", "ES2022", "--module", "ESNext", "--moduleResolution", "Bundler", "--strict",
      "--skipLibCheck", "--noUncheckedIndexedAccess", "--exactOptionalPropertyTypes"], { cwd: root, stdio: "pipe" });
  } catch (error) { rmSync(output, { recursive: true, force: true }); throw error; }
  writeFileSync(join(output, "package.json"), '{"type":"module"}\n');
}
const load = path => import(pathToFileURL(join(output, path)).href);
const { createCookieBuildClient } = await load("api/cookie-build-client.js");
const { WorkspaceClientError } = await load("api/workspace-client.js");
const { buildLogTarget, parseBuildRead, snapshotBuildReadSelection } = await load("domain/build-read.js");
const { summarizeBuildOverview } = await load("domain/build-overview.js");
const keys = ["organizationId", "projectId", "applicationId", "buildId", "platform",
  "sourceSha256", "toolchainLockSha256", "buildDefinitionSha256"];
const wireKeys = ["organization_id", "project_id", "application_id", "build_id", "platform",
  "source_sha256", "toolchain_lock_sha256", "build_definition_sha256"];
const selected = () => ({ organizationId: "org.A-1", projectId: "p_2", applicationId: "app", buildId: "build",
  platform: "ios", sourceSha256: "a".repeat(64), toolchainLockSha256: "b".repeat(64), buildDefinitionSha256: "c".repeat(64) });
const dto = (changes = {}) => ({ build: { ...selected(), revision: 0, state: "queued", attempt: 1, maxAttempts: 3,
  failureCode: null, workerCompletionPending: false, ...changes } });
const json = value => new Response(JSON.stringify(value), { headers: { "content-type": "application/json" } });
const apiFor = value => createCookieBuildClient({ fetch: async () => json(value) });
const safeError = code => error => {
  assert.ok(error instanceof WorkspaceClientError);
  assert.equal(error.code, code);
  assert.equal(error.message, `Workspace request ${code}`);
  assert.deepEqual(Object.keys(error).sort(), ["code", "name"]);
  assert.equal(error.cause, undefined);
  return true;
};

test("all eight states produce frozen display reports with exact failure/null semantics", async () => {
  for (const state of ["queued", "running", "cancelling", "reconciling", "succeeded", "failed", "cancelled", "timed_out"]) {
    const failed = ["failed", "timed_out"].includes(state);
    const value = dto({ state, revision: 32, attempt: 3, failureCode: failed ? "worker_timeout" : null,
      workerCompletionPending: ["running", "cancelling", "reconciling"].includes(state) });
    const client = apiFor(value);
    const result = await client.read(selected());
    const { revision, failureCode, ...rest } = value.build;
    assert.deepEqual(result, { revision, report: { ...rest, ...(failed ? { failureCode } : {}) } });
    assert.ok(Object.isFrozen(client)); assert.ok(Object.isFrozen(result)); assert.ok(Object.isFrozen(result.report));
    assert.deepEqual(Object.keys(client), ["read", "readLogs"]);
    assert.throws(() => { result.report.buildId = "other"; }, TypeError);
  }
});

test("fixed relative request has exactly eight equality filters and confidential cookie settings", async () => {
  const selection = { ...selected(), organizationId: "A".repeat(128), platform: "android" };
  let calls = 0;
  const client = createCookieBuildClient({ fetch: async (path, init) => {
    calls++;
    assert.equal(path, "/console-api/v1/builds?" + keys.map((key, i) => `${wireKeys[i]}=${encodeURIComponent(selection[key])}`).join("&"));
    const url = new URL(path, "https://console.invalid/workspace");
    assert.equal(url.origin, "https://console.invalid"); assert.equal(url.pathname, "/console-api/v1/builds");
    assert.deepEqual([...url.searchParams.keys()], wireKeys);
    for (const [key, value] of Object.entries({ method: "GET", credentials: "same-origin", redirect: "error", cache: "no-store", referrerPolicy: "no-referrer" })) assert.equal(init[key], value);
    assert.deepEqual(init.headers, { accept: "application/json" }); assert.equal(Object.hasOwn(init, "body"), false);
    assert.ok(init.signal instanceof AbortSignal);
    return json(dto(selection));
  } });
  assert.equal(calls, 0);
  assert.equal((await client.read(selection)).report.organizationId, selection.organizationId);
  assert.equal(calls, 1);
});

test("every selection dimension binds response scope and digests to caller intent", async () => {
  for (const key of keys) {
    const value = key === "platform" ? "android" : key.endsWith("Sha256") ? "d".repeat(64) : "foreign";
    await assert.rejects(apiFor(dto({ [key]: value })).read(selected()), safeError("invalid_response"));
  }
  const selection = selected();
  assert.deepEqual(snapshotBuildReadSelection(selection), selection);
  assert.ok(Object.isFrozen(snapshotBuildReadSelection(selection)));
  for (const revision of [0, 1, 31, 32]) assert.equal(parseBuildRead(dto({ revision }), selection).revision, revision);
});

test("closed top-level and all fourteen required fields reject missing and additional data", async () => {
  for (const key of Object.keys(dto().build)) {
    const value = dto(); delete value.build[key];
    await assert.rejects(apiFor(value).read(selected()), safeError("invalid_response"));
  }
  for (const value of [null, [], {}, { build: null }, { build: [] }, { ...dto(), authority: true },
    dto({ token: "private" }), dto({ revision: undefined })]) {
    await assert.rejects(apiFor(value).read(selected()), safeError("invalid_response"));
  }
});

test("revision bounds and unsafe integers fail closed", async () => {
  for (const revision of [-1, 33, 0.5, "1", null, Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER + 1, 1e100]) {
    await assert.rejects(apiFor(dto({ revision })).read(selected()), safeError("invalid_response"));
  }
  const raw = JSON.stringify(dto()).replace('"revision":0', '"revision":9007199254740993');
  await assert.rejects(createCookieBuildClient({ fetch: async () => new Response(raw, { headers: { "content-type": "application/json" } }) }).read(selected()), safeError("invalid_response"));
});

test("display validator rejects invalid state attempts pending flags and failure enums", async () => {
  for (const changes of [{ state: "published" }, { attempt: 0 }, { attempt: 1.5 }, { attempt: 4 },
    { maxAttempts: 6 }, { maxAttempts: 0 }, { maxAttempts: "3" }, { workerCompletionPending: true },
    { state: "running", workerCompletionPending: false }, { workerCompletionPending: "false" },
    { failureCode: "compiler_error" }, { state: "failed", failureCode: null },
    { state: "timed_out", failureCode: "private" }, { state: "failed", failureCode: 2 }]) {
    await assert.rejects(apiFor(dto(changes)).read(selected()), safeError("invalid_response"));
  }
  for (const failureCode of ["worker_unavailable", "worker_lost", "dependency_transport", "artifact_transport",
    "worker_timeout", "compiler_error", "test_failure", "policy_rejection", "invalid_input", "unknown_failure"]) {
    assert.equal((await apiFor(dto({ state: "failed", failureCode })).read(selected())).report.failureCode, failureCode);
  }
});

test("invalid selection and forbidden client options perform no fetch", async () => {
  let calls = 0;
  const client = createCookieBuildClient({ fetch: async () => { calls++; return json(dto()); } });
  const bad = [null, [], {}, { ...selected(), extra: true }];
  for (const key of keys) { const value = selected(); delete value[key]; bad.push(value); }
  for (const key of ["organizationId", "projectId", "applicationId", "buildId"]) {
    for (const value of ["", "x".repeat(129), "a/b", " ", "é", "a\n", "a?b", "a%2fb", null, 1]) bad.push({ ...selected(), [key]: value });
  }
  for (const key of ["sourceSha256", "toolchainLockSha256", "buildDefinitionSha256"]) {
    for (const value of ["a".repeat(63), "a".repeat(65), "A".repeat(64), "g".repeat(64), null]) bad.push({ ...selected(), [key]: value });
  }
  bad.push({ ...selected(), platform: "web" });
  for (const input of bad) await assert.rejects(client.read(input), safeError("invalid_request"));
  for (const options of [null, [], { baseURL: "https://evil.invalid" }, { token: "private" }, { apiOrigin: "https://evil.invalid" },
    { accessToken: () => "private" }, { headers: {} }, { credentials: "include" }, { timeoutMs: 0 }, { timeoutMs: 30001 },
    { timeoutMs: 1.5 }, { fetch: "wrong" }]) assert.throws(() => createCookieBuildClient(options), safeError("invalid_request"));
  assert.equal(calls, 0);
});

test("all primitive selection values are captured before async transport", async () => {
  const selection = selected(), original = selected();
  let release;
  const client = createCookieBuildClient({ fetch: () => new Promise(resolve => { release = resolve; }) });
  const pending = client.read(selection);
  for (const key of keys) selection[key] = key === "platform" ? "android" : key.endsWith("Sha256") ? "d".repeat(64) : "changed";
  await new Promise(resolve => setImmediate(resolve));
  release(json(dto()));
  const result = await pending;
  for (const key of keys) assert.equal(result.report[key], original[key]);
  let releaseForeign;
  const foreign = createCookieBuildClient({ fetch: () => new Promise(resolve => { releaseForeign = resolve; }) });
  const mutable = selected(), denied = foreign.read(mutable);
  mutable.organizationId = "changed";
  await new Promise(resolve => setImmediate(resolve)); releaseForeign(json(dto({ organizationId: "changed" })));
  await assert.rejects(denied, safeError("invalid_response"));
});

test("HTTP and dependency errors remain closed and redact all private text", async () => {
  for (const [status, code] of [[401, "unauthenticated"], [403, "permission_denied"], [404, "not_found"],
    [429, "unavailable"], [503, "unavailable"], [302, "invalid_response"], [400, "invalid_response"]]) {
    await assert.rejects(createCookieBuildClient({ fetch: async () => new Response("private secret URL", { status }) }).read(selected()), safeError(code));
  }
  for (const error of [new Error("token=private; https://private.invalid"),
    Object.assign(new WorkspaceClientError("unavailable"), { message: "private" })]) {
    await assert.rejects(createCookieBuildClient({ fetch: async () => { throw error; } }).read(selected()), safeError("unavailable"));
  }
});

test("invalid media UTF8 JSON redirects and oversized bodies fail closed", async () => {
  for (const make of [() => new Response(JSON.stringify(dto())),
    () => new Response(new Uint8Array([255]), { headers: { "content-type": "application/json" } }),
    () => new Response("{", { headers: { "content-type": "application/json" } }),
    () => new Response(" ".repeat(262145), { headers: { "content-type": "application/json" } }),
    () => new Response("{}", { headers: { "content-type": "application/json", "content-length": "262145" } }),
    () => { const r = json(dto()); Object.defineProperty(r, "redirected", { value: true }); return r; }]) {
    await assert.rejects(createCookieBuildClient({ fetch: async () => make() }).read(selected()), safeError("invalid_response"));
  }
});

test("bounded stream bytes and read count cancel and release reader", async () => {
  for (const size of [65536, 0]) {
    let reads = 0, cancelled = false;
    const stream = new ReadableStream({ pull(c) { reads++; c.enqueue(new Uint8Array(size)); },
      cancel() { cancelled = true; return new Promise(() => {}); } });
    await assert.rejects(createCookieBuildClient({ fetch: async () => new Response(stream, { headers: { "content-type": "application/json" } }) }).read(selected()), safeError("invalid_response"));
    assert.equal(cancelled, true); assert.equal(stream.locked, false); assert.ok(reads <= (size ? 6 : 4097));
  }
});

test("preabort avoids fetch and cancellation/deadline settle noncooperative fetch", async () => {
  let calls = 0;
  const pre = new AbortController(); pre.abort();
  await assert.rejects(createCookieBuildClient({ fetch: async () => { calls++; return json(dto()); } }).read(selected(), pre.signal), safeError("aborted"));
  assert.equal(calls, 0);
  for (const mode of ["abort", "deadline"]) {
    let release, cancelled = false;
    const controller = new AbortController();
    const client = createCookieBuildClient({ timeoutMs: mode === "deadline" ? 20 : 1000,
      fetch: () => new Promise(resolve => { release = resolve; }) });
    const pending = client.read(selected(), controller.signal);
    await new Promise(resolve => setImmediate(resolve));
    if (mode === "abort") controller.abort();
    await assert.rejects(pending, safeError(mode === "abort" ? "aborted" : "unavailable"));
    release(new Response(new ReadableStream({ cancel() { cancelled = true; } }), { headers: { "content-type": "application/json" } }));
    await new Promise(resolve => setImmediate(resolve)); assert.equal(cancelled, true);
  }
});

test("body deadline and abort cancel pending read and release stream", async () => {
  for (const mode of ["deadline", "abort"]) {
    let cancelled = false;
    const stream = new ReadableStream({ cancel() { cancelled = true; } });
    const controller = new AbortController();
    const client = createCookieBuildClient({ timeoutMs: mode === "deadline" ? 20 : 1000,
      fetch: async () => new Response(stream, { headers: { "content-type": "application/json" } }) });
    const pending = client.read(selected(), controller.signal);
    await new Promise(resolve => setImmediate(resolve));
    if (mode === "abort") controller.abort();
    await assert.rejects(pending, safeError(mode === "abort" ? "aborted" : "unavailable"));
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(cancelled, true); assert.equal(stream.locked, false);
  }
});

test("each build read reaches session boundary afresh", async () => {
  let current = dto(), calls = 0;
  const client = createCookieBuildClient({ fetch: async () => { calls++; return current ? json(current) : new Response(null, { status: 401 }); } });
  const first = await client.read(selected()); current = null;
  await assert.rejects(client.read(selected()), safeError("unauthenticated"));
  current = dto({ state: "succeeded", revision: 2 });
  assert.equal((await client.read(selected())).report.state, "succeeded");
  assert.equal(first.report.state, "queued"); assert.equal(calls, 3);
});

const selection={organizationId:"org-a",projectId:"project-a",applicationId:"fieldlog",buildId:"build-a",platform:"ios",sourceSha256:"a".repeat(64),toolchainLockSha256:"b".repeat(64),buildDefinitionSha256:"c".repeat(64)};
const reviewedDto=()=>({build:{...selection,revision:0,state:"queued",attempt:1,maxAttempts:2,failureCode:null,workerCompletionPending:false}});
test("R1134 strict ID/digest boundaries, hidden keys and null semantics",()=>{
 for(const id of ["/","é","a b","a\n","a".repeat(129),"",null]) assert.throws(()=>snapshotBuildReadSelection({...selection,buildId:id}));
 for(const sha of ["A".repeat(64),"a".repeat(63),"a".repeat(65),"g".repeat(64)]) assert.throws(()=>snapshotBuildReadSelection({...selection,sourceSha256:sha}));
 for(const key of Reflect.ownKeys(reviewedDto().build)){const v=reviewedDto();delete v.build[key];assert.throws(()=>parseBuildRead(v,selection));}
 const v=reviewedDto();Object.defineProperty(v.build,"hidden",{value:true});assert.throws(()=>parseBuildRead(v,selection));
 const sym=reviewedDto();sym.build[Symbol("authority")]=true;assert.throws(()=>parseBuildRead(sym,selection));
 for(const revision of [-1,33,0.5,NaN,Infinity,Number.MAX_SAFE_INTEGER+1,"0",null])assert.throws(()=>parseBuildRead({build:{...reviewedDto().build,revision}},selection));
 for(const state of ["queued","running","cancelling","reconciling","succeeded","cancelled"]){const v=reviewedDto();v.build.state=state;v.build.workerCompletionPending=["running","cancelling","reconciling"].includes(state);const p=parseBuildRead(v,selection);assert.equal(Object.hasOwn(p.report,"failureCode"),false);v.build.failureCode="compiler_error";assert.throws(()=>parseBuildRead(v,selection));}
 for(const state of ["failed","timed_out"]){const v=reviewedDto();v.build.state=state;assert.throws(()=>parseBuildRead(v,selection));v.build.failureCode="compiler_error";assert.equal(parseBuildRead(v,selection).report.failureCode,"compiler_error");}
});
test("R1134 immutable intent survives delayed body and redacts parser exceptions",async()=>{
 let release;const pending=new Promise(r=>release=r);const input={...selection};
 const client=createCookieBuildClient({fetch:async()=>{await pending;return new Response(JSON.stringify(reviewedDto()),{headers:{"content-type":"application/json"}});}});
 const result=client.read(input);input.buildId="mutated";release();const snapshot=await result;assert.equal(snapshot.report.buildId,"build-a");assert(Object.isFrozen(snapshot.report));
 const {organizationId,projectId,applicationId,...target}=selection;
 assert.equal(summarizeBuildOverview({scope:{organizationId,projectId,applicationId},expected:[target],reports:[snapshot.report]}).reportedCount,1);
 const bad=createCookieBuildClient({fetch:async()=>new Response("SECRET_COOKIE_TOKEN",{headers:{"content-type":"application/json"}})});
 await assert.rejects(bad.read(selection),e=>e.code==="invalid_response"&&!String(e.stack).includes("SECRET_COOKIE_TOKEN"));
});

test("retained build DTOs enforce the selected platform and per-role byte caps", () => {
  const kinds = ["unsigned_native_binary", "debug_symbols", "resource_inventory"];
  const mib = 1024 * 1024;

  for (const platform of ["ios", "android"]) {
    const selection = { ...selected(), platform };
    const query = keys.map((key, index) => `${wireKeys[index]}=${selection[key]}`).join("&");
    const artifacts = kinds.map((kind, index) => ({
      kind, sizeBytes: (platform === "android" && kind === kinds[0] ? 32 : 16) * mib,
      sha256: "def"[index].repeat(64), downloadPath: `/console-api/v1/build-artifacts/${kind}?${query}`,
    }));
    const value = dto({ ...selection, state: "native_succeeded", revision: 2, artifacts });
    const parse = () => parseBuildRead(value, selection);
    const snapshot = parse();
    assert.equal(snapshot.report.platform, platform);
    assert.equal(snapshot.report.state, "native_succeeded");
    assert.deepEqual(snapshot.artifacts, artifacts);
    assert.deepEqual(buildLogTarget({ selection, snapshot }), {
      selection, revision: 2, attempt: 1, state: "native_succeeded",
    });

    for (const artifact of artifacts) {
      artifact.sizeBytes++;
      assert.throws(parse, TypeError);
      artifact.sizeBytes--;
    }

    artifacts[0].sizeBytes = 27_795_723;
    if (platform === "android") assert.equal(parse().artifacts[0].sizeBytes, 27_795_723);
    else assert.throws(parse, TypeError);
    artifacts[0].sizeBytes = 1;

    const otherPlatform = platform === "ios" ? "android" : "ios";
    assert.throws(() => parseBuildRead(value, { ...selection, platform: otherPlatform }), TypeError);
    const originalPath = artifacts[0].downloadPath;
    artifacts[0].downloadPath = originalPath.replace(`platform=${platform}`, `platform=${otherPlatform}`);
    assert.throws(parse, TypeError);
    artifacts[0].downloadPath = originalPath;
    artifacts[0].kind = "guest_artifact";
    assert.throws(parse, TypeError);
    artifacts[0].kind = kinds[0];
    artifacts.pop();
    assert.throws(parse, TypeError);
    delete value.build.artifacts;
    assert.throws(parse, TypeError);
  }
});

const logTarget = (changes = {}) => ({
  selection: selected(), revision: 4, attempt: 1, state: "native_succeeded", ...changes,
});
const commandFinished = { event: "build_command_finished", exitCode: 0 };
const compilerFinished = {
  event: "compiler_finished", exitCode: 0, stdoutBytes: 300, stderrBytes: 0,
  tailTruncated: false, phases: ["compile", "package"],
};
const logsDto = (changes = {}) => ({
  buildLogs: { ...selected(), revision: 4, attempt: 1, maxAttempts: 3,
    state: "native_succeeded", failureCode: null, workerCompletionPending: false,
    events: [compilerFinished, commandFinished], ...changes },
});

test("terminal logs use the exact cookie GET and snapshot the selection before fetch", async () => {
  const target = logTarget();
  const client = createCookieBuildClient({ fetch: async (path, init) => {
    const original = selected();
    assert.equal(path, "/console-api/v1/build-logs?" +
      keys.map((key, index) => `${wireKeys[index]}=${original[key]}`).join("&"));
    for (const [key, value] of Object.entries({ method: "GET", credentials: "same-origin",
      cache: "no-store", redirect: "error", referrerPolicy: "no-referrer" })) assert.equal(init[key], value);
    assert.deepEqual(init.headers, { accept: "application/json" });
    assert.equal(Object.hasOwn(init, "body"), false);
    return json(logsDto());
  } });
  const pending = client.readLogs(target);
  target.selection.buildId = "mutated";
  target.revision = 8;
  const events = await pending;
  assert.deepEqual(events, [compilerFinished, commandFinished]);
  assert.ok(Object.isFrozen(events) && Object.isFrozen(events[0].phases));
  assert.deepEqual(await apiFor(logsDto({ state: "cancelled", events: [{ ...commandFinished, exitCode: -15 }] }))
    .readLogs(logTarget({ state: "cancelled" })), [{ ...commandFinished, exitCode: -15 }]);
});

test("logs reject invalid target before fetch and every mismatched build or attempt", async () => {
  const client = createCookieBuildClient({ fetch: async () => assert.fail("invalid target reached fetch") });
  for (const input of [null, logTarget({ selection: { ...selected(), buildId: "bad/id" } }),
    logTarget({ selection: { ...selected(), platform: "web" } }), logTarget({ state: "running" }),
    logTarget({ state: "reconciling" }), logTarget({ state: "succeeded" }), logTarget({ attempt: 0 }), logTarget({ attempt: 6 }),
    logTarget({ revision: 0 }), logTarget({ revision: 33 }), logTarget({ token: "private" })]) {
    await assert.rejects(client.readLogs(input), safeError("invalid_request"));
  }
  for (const key of keys) {
    const value = key === "platform" ? "android" : key.endsWith("Sha256") ? "d".repeat(64) : "foreign";
    await assert.rejects(apiFor(logsDto({ [key]: value })).readLogs(logTarget()), safeError("invalid_response"));
  }
  for (const changes of [{ revision: 3 }, { revision: 5 }, { attempt: 2 }, { state: "cancelled" },
    { state: "succeeded" }, { workerCompletionPending: true }, { maxAttempts: 0 }, { failureCode: "compiler_error" }]) {
    await assert.rejects(apiFor(logsDto(changes)).readLogs(logTarget()), safeError("invalid_response"));
  }
});

test("Android logs accept only a driver event or the CLI-only preflight shape", async () => {
  const platform = "android";
  const target = logTarget({ selection: { ...selected(), platform } });
  const driver = { ...compilerFinished, event: "android_driver_finished", phases: [] };
  const events = [driver, commandFinished];
  assert.deepEqual(await apiFor(logsDto({ platform, events })).readLogs(target), events);
  const preflight = [{ ...commandFinished, exitCode: 23 }];
  assert.deepEqual(await apiFor(logsDto({ platform, state: "cancelled", events: preflight }))
    .readLogs({ ...target, state: "cancelled" }), preflight);

  for (const step of [compilerFinished, { ...driver, phases: ["package"] }, { ...driver, stderr: "private" }]) {
    await assert.rejects(apiFor(logsDto({ platform, events: [step, commandFinished] }))
      .readLogs(target), safeError("invalid_response"));
  }
  await assert.rejects(apiFor(logsDto({ events })).readLogs(logTarget()), safeError("invalid_response"));
});

test("logs reject other envelopes, raw output and anything outside the retained event grammar", async () => {
  const invalid = [
    { build: logsDto().buildLogs }, { ...logsDto(), extra: true }, logsDto({ operationId: "private" }),
    ...[[], [compilerFinished], [commandFinished, compilerFinished], [commandFinished, commandFinished],
      [compilerFinished, commandFinished, commandFinished], [{ ...commandFinished, extra: "private" }],
      [{ ...commandFinished, exitCode: -256 }], [{ ...commandFinished, exitCode: 1.5 }],
      ...[{ exitCode: 256 }, { stdoutBytes: 2 ** 32 + 1 }, { stderrBytes: -1 }, { tailTruncated: 1 },
        { phases: ["link", "compile"] }, { phases: ["compile", "compile"] }, { phases: ["private"] },
        { rawOutput: "private" }].map(change => [{ ...compilerFinished, ...change }, commandFinished]),
    ].map(events => logsDto({ events })),
  ];
  for (const response of invalid) {
    await assert.rejects(apiFor(response).readLogs(logTarget()), safeError("invalid_response"));
  }
});
