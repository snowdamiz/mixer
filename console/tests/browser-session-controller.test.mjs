import assert from "node:assert/strict";
import { after, test } from "node:test";
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { join } from "node:path";

const root = fileURLToPath(new URL("../", import.meta.url));
const cache = join(root, "node_modules/.cache"); mkdirSync(cache, { recursive: true });
const output = mkdtempSync(join(cache, "mixer-browser-session-controller-"));
after(() => { rmSync(output, { recursive: true, force: true }); assert.equal(existsSync(output), false); });
try {
  execFileSync(process.execPath, [join(root, "node_modules/typescript/bin/tsc"), "src/state/browser-session-controller.ts",
    "--target", "ES2022", "--module", "ESNext", "--moduleResolution", "Bundler", "--strict", "--skipLibCheck",
    "--noUncheckedIndexedAccess", "--exactOptionalPropertyTypes", "--outDir", output], { cwd: root, stdio: "pipe", timeout: 15000 });
} catch (error) {
  if (error.stdout) process.stderr.write(error.stdout);
  if (error.stderr) process.stderr.write(error.stderr);
  rmSync(output, { recursive: true, force: true }); throw error;
}
writeFileSync(join(output, "package.json"), '{"type":"module"}\n');
const { createBrowserSessionController } = await import(pathToFileURL(join(output, "state/browser-session-controller.js")));
const { WorkspaceClientError } = await import(pathToFileURL(join(output, "api/workspace-client.js")));
const csrf = "A".repeat(43), generation = "B".repeat(42) + "A";
const initialWall = 1700000000000;
const metadata = (changes = {}) => ({ state: "authenticated", generation, csrf_token: csrf, expires_at: initialWall / 1000 + 60, ...changes });
const orgs = { organizations: [{ id: "a", display_name: "Private studio", organization_roles: ["owner"] }], next_cursor: "NEXT" };
const projects = { projects: [{ organization_id: "a", id: "p", display_name: "Private project", roles: ["viewer"] }], next_cursor: null };
const response = value => new Response(JSON.stringify(value), { headers: { "content-type": "application/json", "cache-control": "no-store" } });
const flush = () => new Promise(resolve => setImmediate(resolve));
const deferred = () => { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };
const error = code => value => value instanceof WorkspaceClientError && value.code === code && value.message === `Workspace request ${code}`;
function controlled() {
  const calls = [];
  const fetch = (path, init) => { const pending = deferred(); calls.push({ path, ...init, ...pending }); return pending.promise; };
  return { calls, fetch };
}
async function withClock(run) {
  const date = Date.now, descriptor = Object.getOwnPropertyDescriptor(globalThis, "performance");
  const time = { wall: initialWall, mono: 100 };
  Date.now = () => time.wall;
  Object.defineProperty(globalThis, "performance", { configurable: true, value: { now: () => time.mono } });
  try { await run(time); } finally { Date.now = date; Object.defineProperty(globalThis, "performance", descriptor); }
}
async function ready(controller, api, value = metadata()) {
  controller.revalidate(); api.calls.at(-1).resolve(response(value)); await flush();
  assert.equal(controller.getSession().kind, "ready"); return controller.getSession();
}

test("controller starts frozen unavailable and exposes only closed actions, without a network request", async () => {
  const api = controlled(), controller = createBrowserSessionController({ fetch: api.fetch });
  assert.deepEqual(controller.getSession(), { kind: "unavailable" });
  assert.ok(Object.isFrozen(controller)); assert.ok(Object.isFrozen(controller.getSession()));
  assert.deepEqual(Object.keys(controller), ["getSession", "subscribe", "revalidate", "invalidate", "dispose"]);
  assert.equal(api.calls.length, 0); controller.dispose(); controller.dispose(); controller.revalidate();
  assert.equal(api.calls.length, 0);
  for (const invalid of [null, [], { session: {} }, { clock: () => 0 }, { fetch: false }, { [Symbol()]: 1 }]) {
    assert.throws(() => createBrowserSessionController(invalid), value => value.code === "invalid_request");
  }
});

test("valid signed-out is a fresh frozen capability; every other current outcome is unavailable", async () => {
  const api = controlled(), controller = createBrowserSessionController({ fetch: api.fetch });
  try {
    let previous;
    for (let i = 0; i < 2; i++) {
      controller.revalidate(); api.calls.at(-1).resolve(response({ state: "unauthenticated", csrf_token: csrf })); await flush();
      const value = controller.getSession(); assert.deepEqual(value, { kind: "unauthenticated" }); assert.ok(Object.isFrozen(value));
      assert.notEqual(value, previous); previous = value;
    }
    for (const value of [new Response(null, { status: 404 }), new Response("<html>fallback</html>", { headers: { "content-type": "text/html" } }), response({ state: "authenticated" })]) {
      controller.revalidate(); assert.equal(controller.getSession().kind, "unavailable"); api.calls.at(-1).resolve(value); await flush();
      assert.equal(controller.getSession().kind, "unavailable");
    }
    assert.ok(api.calls.every(call => call.path === "/auth/session"));
  } finally { controller.dispose(); }
});

test("same and changed server generation both replace the local epoch and abort old workspace calls synchronously", () => withClock(async () => {
  const api = controlled(), controller = createBrowserSessionController({ fetch: api.fetch });
  try {
    let current = await ready(controller, api);
    for (const next of [metadata(), metadata({ generation: "C".repeat(42) + "A" })]) {
      const prior = current, pending = prior.client.organizations(); await flush(); const call = api.calls.at(-1);
      let observed;
      call.signal.addEventListener("abort", () => { observed = controller.getSession().kind; });
      controller.revalidate();
      assert.equal(controller.getSession().kind, "unavailable"); assert.equal(observed, "unavailable"); assert.equal(call.signal.aborted, true);
      await assert.rejects(pending, error("aborted"));
      await assert.rejects(prior.client.projects("a"), error("aborted"));
      api.calls.at(-1).resolve(response(next)); await flush();
      current = controller.getSession(); assert.equal(current.kind, "ready"); assert.notEqual(current, prior); assert.notEqual(current.client, prior.client);
      call.resolve(response(orgs)); await flush(); assert.equal(controller.getSession(), current);
    }
    assert.ok(Object.isFrozen(current)); assert.ok(Object.isFrozen(current.client));
    assert.doesNotMatch(JSON.stringify(current), /csrf|generation|expires|AAAA/);
  } finally { controller.dispose(); }
}));

test("late superseded session success and rejection cannot admit even an equal generation", () => withClock(async () => {
  const api = controlled(), controller = createBrowserSessionController({ fetch: api.fetch });
  try {
    controller.revalidate(); const old = api.calls.at(-1);
    controller.revalidate(); const next = api.calls.at(-1);
    assert.equal(old.signal.aborted, true);
    next.resolve(response(metadata())); await flush(); const value = controller.getSession();
    old.resolve(response(metadata())); await flush(); assert.equal(controller.getSession(), value);
    controller.revalidate(); const rejected = api.calls.at(-1);
    controller.revalidate(); api.calls.at(-1).resolve(response(metadata())); await flush(); const last = controller.getSession();
    rejected.reject(Error("private old provider details")); await flush(); assert.equal(controller.getSession(), last);
  } finally { controller.dispose(); }
}));

test("actual cookie adapter preserves org/project scope, caller cancellation and closed transport failures", () => withClock(async () => {
  const api = controlled(), controller = createBrowserSessionController({ fetch: api.fetch });
  try {
    const value = await ready(controller, api), caller = new AbortController();
    const organizations = value.client.organizations({ limit: 1, cursor: "NEXT" }, caller.signal); await flush(); const first = api.calls.at(-1);
    assert.equal(first.path, "/console-api/v1/orgs?limit=1&cursor=NEXT");
    assert.equal(first.credentials, "same-origin"); assert.deepEqual(first.headers, { accept: "application/json" });
    first.resolve(response(orgs)); assert.deepEqual(await organizations, orgs);
    const projectOperation = value.client.projects("a", {}, caller.signal); await flush(); const second = api.calls.at(-1);
    assert.equal(second.path, "/console-api/v1/projects?organization_id=a"); second.resolve(response(projects));
    assert.deepEqual(await projectOperation, projects);
    const cancelled = value.client.organizations({}, caller.signal); await flush(); const third = api.calls.at(-1);
    caller.abort(); assert.equal(third.signal.aborted, true); await assert.rejects(cancelled, error("aborted"));
    assert.equal(controller.getSession(), value);
    third.reject(Error("late cancelled")); await flush();
    for (const [status, code] of [[403, "permission_denied"], [404, "not_found"], [503, "unavailable"]]) {
      const operation = value.client.organizations(); await flush(); api.calls.at(-1).resolve(new Response(null, { status }));
      await assert.rejects(operation, error(code)); assert.equal(controller.getSession(), value);
    }
  } finally { controller.dispose(); }
}));

test("a current actual workspace401 immediately removes outer ready and requires explicit revalidation", () => withClock(async () => {
  const api = controlled(), controller = createBrowserSessionController({ fetch: api.fetch });
  try {
    const value = await ready(controller, api);
    const first = value.client.organizations(), second = value.client.projects("a"); await flush(); const secondCall = api.calls.at(-1);
    api.calls.at(-2).resolve(new Response("private", { status: 401 }));
    await assert.rejects(first, error("unauthenticated"));
    assert.equal(controller.getSession().kind, "unavailable"); assert.equal(secondCall.signal.aborted, true);
    await assert.rejects(second, error("aborted")); await assert.rejects(value.client.organizations(), error("aborted"));
    assert.equal(api.calls.length, 3); secondCall.resolve(response(projects)); await flush();
    assert.equal(controller.getSession().kind, "unavailable");
    await ready(controller, api);
  } finally { controller.dispose(); }
}));

test("getSession and delegate dispatch synchronously enforce wall expiry, monotonic expiry and backwards clocks", () => withClock(async time => {
  for (const change of [() => { time.wall += 60000; }, () => { time.mono += 60000; }, () => { time.wall--; }, () => { time.mono -= 0.01; }]) {
    time.wall = initialWall; time.mono = 100;
    const api = controlled(), controller = createBrowserSessionController({ fetch: api.fetch });
    try {
      const value = await ready(controller, api); const pending = value.client.organizations(); await flush(); const call = api.calls.at(-1);
      change();
      assert.equal(controller.getSession().kind, "unavailable"); assert.equal(call.signal.aborted, true);
      await assert.rejects(pending, error("aborted"));
      const count = api.calls.length; await assert.rejects(value.client.projects("a"), error("aborted")); assert.equal(api.calls.length, count);
      call.resolve(response(orgs)); await flush();
    } finally { controller.dispose(); }
  }
}));

test("postawait publication independently rejects clock expiry and old failures", () => withClock(async time => {
  for (const outcome of ["success", "failure"]) {
    time.wall = initialWall; time.mono = 100;
    const api = controlled(), controller = createBrowserSessionController({ fetch: api.fetch });
    try {
      const value = await ready(controller, api), operation = value.client.organizations(); await flush(); const call = api.calls.at(-1);
      time.wall += 60000;
      if (outcome === "success") call.resolve(response(orgs)); else call.resolve(new Response(null, { status: 401 }));
      await assert.rejects(operation, error("aborted")); assert.equal(controller.getSession().kind, "unavailable");
    } finally { controller.dispose(); }
  }
}));

test("15minute maximum lifetime is captured before the session read rather than after its latency", () => withClock(async time => {
  const api = controlled(), controller = createBrowserSessionController({ fetch: api.fetch });
  try {
    controller.revalidate(); time.mono += 100; time.wall += 100;
    api.calls.at(-1).resolve(response(metadata({ expires_at: initialWall / 1000 + 3600 }))); await flush();
    const value = controller.getSession(); assert.equal(value.kind, "ready");
    time.mono = 900099.5; assert.equal(controller.getSession(), value);
    time.mono = 900100; assert.equal(controller.getSession().kind, "unavailable");
  } finally { controller.dispose(); }
}));

test("invalid start clocks, unsafe expiry arithmetic and already expired admission fail unavailable", () => withClock(async time => {
  for (const [wall, mono] of [[-1, 0], [0.5, 0], [NaN, 0], [Infinity, 0], [initialWall, -1], [initialWall, NaN], [initialWall, Infinity], [initialWall, Number.MAX_SAFE_INTEGER + 1]]) {
    time.wall = wall; time.mono = mono;
    const api = controlled(), controller = createBrowserSessionController({ fetch: api.fetch });
    controller.revalidate(); assert.equal(api.calls.length, 0); assert.equal(controller.getSession().kind, "unavailable"); controller.dispose();
  }
  for (const expires_at of [0, initialWall / 1000, Number.MAX_SAFE_INTEGER]) {
    time.wall = initialWall; time.mono = 100;
    const api = controlled(), controller = createBrowserSessionController({ fetch: api.fetch });
    controller.revalidate(); api.calls.at(-1).resolve(response(metadata({ expires_at }))); await flush();
    assert.equal(controller.getSession().kind, "unavailable"); controller.dispose();
  }
  time.wall = initialWall; time.mono = Number.MAX_SAFE_INTEGER;
  const api = controlled(), controller = createBrowserSessionController({ fetch: api.fetch });
  controller.revalidate(); api.calls.at(-1).resolve(response(metadata())); await flush();
  assert.equal(controller.getSession().kind, "unavailable"); controller.dispose();
}));

test("invalid live clock samples and backwards admission samples cannot create or retain ready", () => withClock(async time => {
  for (const change of [() => { time.wall = -1; }, () => { time.wall += 0.5; }, () => { time.mono = NaN; }, () => { time.mono = -1; }, () => { time.wall--; }, () => { time.mono--; }]) {
    time.wall = initialWall; time.mono = 100;
    const api = controlled(), controller = createBrowserSessionController({ fetch: api.fetch });
    try {
      controller.revalidate(); change(); api.calls.at(-1).resolve(response(metadata())); await flush();
      assert.equal(controller.getSession().kind, "unavailable");
    } finally { controller.dispose(); }
  }
}));

test("an owned expiry timer clears capability without a read, and disposal cancels owned timers", () => withClock(async () => {
  const set = globalThis.setTimeout, clear = globalThis.clearTimeout, timers = new Map(); let number = 0;
  globalThis.setTimeout = (callback, ms) => { const id = ++number; timers.set(id, { callback, ms }); return id; };
  globalThis.clearTimeout = id => { timers.delete(id); };
  const api = controlled(), controller = createBrowserSessionController({ fetch: api.fetch });
  try {
    await ready(controller, api); assert.equal(timers.size, 1);
    const timer = [...timers.values()][0]; assert.equal(timer.ms, 60000);
    timers.clear(); timer.callback(); assert.equal(controller.getSession().kind, "unavailable"); assert.equal(api.calls.length, 1);
    await ready(controller, api); controller.dispose(); assert.equal(timers.size, 0);
  } finally { controller.dispose(); globalThis.setTimeout = set; globalThis.clearTimeout = clear; }
}));

test("subscriber throws, asynchronous rejection and reentrant invalidation cannot break coherent epochs", () => withClock(async () => {
  const api = controlled(), controller = createBrowserSessionController({ fetch: api.fetch });
  try {
    controller.subscribe(() => { throw Error("private observer"); });
    controller.subscribe(async () => { throw Error("private async observer"); });
    const observed = [];
    let replace = true;
    controller.subscribe(value => { observed.push(value.kind); if (replace && value.kind === "ready") { replace = false; controller.revalidate(); } });
    controller.revalidate(); api.calls.at(-1).resolve(response(metadata())); await flush();
    assert.equal(api.calls.length, 2); assert.equal(controller.getSession().kind, "unavailable");
    api.calls.at(-1).resolve(response(metadata())); await flush(); assert.equal(controller.getSession().kind, "ready");
    assert.deepEqual(observed, ["unavailable", "unavailable", "ready", "unavailable", "ready"]);
  } finally { controller.dispose(); }
}));

test("reentrant clear observers supersede the old check before it dispatches", () => withClock(async () => {
  const api = controlled(), controller = createBrowserSessionController({ fetch: api.fetch });
  let replace = false;
  controller.subscribe(value => { if (replace && value.kind === "unavailable") { replace = false; controller.revalidate(); } });
  try {
    replace = true; controller.revalidate(); assert.equal(api.calls.length, 1);
    api.calls[0].resolve(response(metadata())); await flush(); assert.equal(controller.getSession().kind, "ready");
  } finally { controller.dispose(); }
}));

test("dispose aborts session/workspace work, removes observers and suppresses late results", () => withClock(async () => {
  const api = controlled(), controller = createBrowserSessionController({ fetch: api.fetch });
  const value = await ready(controller, api), operation = value.client.organizations(); await flush(); const pending = api.calls.at(-1);
  let calls = 0; const unsubscribe = controller.subscribe(() => { calls++; });
  const before = calls; controller.dispose(); controller.dispose(); unsubscribe();
  assert.equal(pending.signal.aborted, true); await assert.rejects(operation, error("aborted"));
  assert.equal(controller.getSession().kind, "unavailable"); assert.equal(calls, before);
  pending.resolve(response(orgs)); await flush(); assert.equal(controller.getSession().kind, "unavailable");
  const another = controlled(), other = createBrowserSessionController({ fetch: another.fetch });
  other.revalidate(); other.dispose(); assert.equal(another.calls[0].signal.aborted, true);
  another.calls[0].resolve(response(metadata())); await flush(); assert.equal(other.getSession().kind, "unavailable");
}));
