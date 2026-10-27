// Host-only Solid client reactivity with synthetic EventTargets. No browser, UI,
// screenshot, native runtime or real cookie/session acceptance is exercised.
import assert from "node:assert/strict";
import test from "node:test";
import { createComputed, createRoot, createSignal } from "solid-js";
import { readFileSync } from "node:fs";
const { createBrowserSessionBinding } = await import(process.env.MIXER_BROWSER_SESSION_BINDING_MODULE);
const { createWorkspaceBinding } = await import(process.env.MIXER_BROWSER_WORKSPACE_BINDING_MODULE);
const csrf = "A".repeat(43), generation = "B".repeat(42) + "A", initialWall = 1700000000000;
const metadata = (changes = {}) => ({ state: "authenticated", generation, csrf_token: csrf, expires_at: initialWall / 1000 + 60, ...changes });
const orgs = { organizations: [{ id: "a", display_name: "Private studio", organization_roles: ["owner"] }], next_cursor: "NEXT" };
const projects = { projects: [{ organization_id: "a", id: "p", display_name: "Private FieldLog", roles: ["viewer"] }], next_cursor: "MORE" };
const response = value => new Response(JSON.stringify(value), { headers: { "content-type": "application/json", "cache-control": "no-store" } });
const flush = () => new Promise(resolve => setImmediate(resolve));
const deferred = () => { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };
class Target extends EventTarget {
  listeners = new Map();
  addEventListener(type, listener, options) { super.addEventListener(type, listener, options); if (!this.listeners.has(type)) this.listeners.set(type, new Set()); this.listeners.get(type).add(listener); }
  removeEventListener(type, listener, options) { super.removeEventListener(type, listener, options); this.listeners.get(type)?.delete(listener); }
  get count() { return [...this.listeners.values()].reduce((count, items) => count + items.size, 0); }
}
function environment({ visibility = "visible", broadcast = true, fetch } = {}) {
  const keys = ["document", "window", "fetch", "BroadcastChannel", "performance", "localStorage", "sessionStorage"];
  const prior = new Map(keys.map(key => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  const document = new Target(), window = new Target(), channels = [], calls = [], time = { wall: initialWall, mono: 100 };
  const date = Date.now; Date.now = () => time.wall;
  document.visibilityState = visibility;
  class Channel extends Target {
    sent = []; closed = false;
    constructor(name) { super(); this.name = name; channels.push(this); }
    postMessage(value) { this.sent.push(value); }
    close() { this.closed = true; }
    receive(value) { this.dispatchEvent(new MessageEvent("message", { data: value })); }
  }
  const values = { document, window, fetch: (path, init) => {
    const pending = deferred(); const call = { path, ...init, ...pending }; calls.push(call);
    return fetch ? fetch(call) : pending.promise;
  }, BroadcastChannel: broadcast ? Channel : undefined, performance: { now: () => time.mono } };
  for (const [key, value] of Object.entries(values)) Object.defineProperty(globalThis, key, { configurable: true, value });
  for (const key of ["localStorage", "sessionStorage"]) Object.defineProperty(globalThis, key, { configurable: true, get() { throw Error("Persistent credential storage is forbidden"); } });
  return { document, window, channels, calls, time,
    visibility(value, dispatch = true) { document.visibilityState = value; if (dispatch) document.dispatchEvent(new Event("visibilitychange")); },
    event(type) { window.dispatchEvent(new Event(type)); },
    cleanup() { Date.now = date; for (const [key, descriptor] of prior) if (descriptor) Object.defineProperty(globalThis, key, descriptor); else delete globalThis[key]; },
  };
}
function owner({ workspace = false, before } = {}) {
  let binding, directory, dispose, poke;
  createRoot(stop => {
    dispose = stop;
    const [trigger, setTrigger] = createSignal(0); poke = () => setTrigger(value => value + 1);
    if (before) createComputed(() => { trigger(); if (binding) before(binding, directory); });
    binding = createBrowserSessionBinding();
    if (workspace) directory = createWorkspaceBinding(binding.workspaceSession);
  });
  return { binding, directory, dispose, poke };
}
async function ready(app, env, value = metadata()) {
  await flush(); assert.equal(env.calls.at(-1).path, "/auth/session");
  env.calls.at(-1).resolve(response(value)); await flush(); assert.equal(app.binding.workspaceSession().kind, "ready");
}

test("visible startup subscribes first, makes one check and coalesces one-turn foreground notifications", async () => {
  const env = environment(), app = owner();
  try {
    assert.ok(Object.isFrozen(app.binding)); assert.equal(app.binding.workspaceSession().kind, "unavailable");
    env.event("focus"); env.event("pageshow"); env.document.dispatchEvent(new Event("visibilitychange"));
    await ready(app, env); assert.equal(env.calls.length, 1);
    env.event("focus"); env.event("pageshow"); await flush(); assert.equal(env.calls.length, 2);
    assert.equal(app.binding.workspaceSession().kind, "unavailable");
    env.calls.at(-1).resolve(response(metadata())); await flush(); assert.equal(app.binding.workspaceSession().kind, "ready");
  } finally { app.dispose(); assert.equal(env.document.count, 0); assert.equal(env.window.count, 0); assert.ok(env.channels.every(channel => channel.closed && channel.count === 0)); env.cleanup(); }
});

test("initially hidden mount waits; hidden result is withheld before a visibility handler runs", async () => {
  const env = environment({ visibility: "hidden" }), app = owner();
  try {
    await flush(); assert.equal(env.calls.length, 0); assert.equal(app.binding.workspaceSession().kind, "unavailable");
    env.visibility("visible"); await flush(); assert.equal(env.calls.length, 1);
    env.visibility("hidden", false); env.calls[0].resolve(response(metadata())); await flush();
    assert.equal(app.binding.workspaceSession().kind, "unavailable");
    env.visibility("visible"); await ready(app, env); assert.equal(env.calls.length, 2);
  } finally { app.dispose(); env.cleanup(); }
});

test("hidden reads and pagehide synchronously erase ready and abort workspace before Solid effects", async () => {
  const env = environment(), observations = [];
  const app = owner({ workspace: true, before(binding, directory) {
    observations.push([binding.workspaceSession().kind, directory.state()]);
    directory.controller.selectOrganization("a"); directory.controller.nextOrganizations("NEXT");
  } });
  try {
    await ready(app, env); assert.equal(env.calls.at(-1).path, "/console-api/v1/orgs");
    env.calls.at(-1).resolve(response(orgs)); await flush();
    app.directory.controller.selectOrganization("a"); await flush(); const pendingProject = env.calls.at(-1);
    env.visibility("hidden", false); const count = env.calls.length; app.poke();
    assert.equal(pendingProject.signal.aborted, true); assert.equal(env.calls.length, count);
    assert.equal(observations.at(-1)[0], "unavailable");
    assert.doesNotMatch(JSON.stringify(observations.at(-1)), /Private|FieldLog/);
    pendingProject.resolve(response(projects)); await flush();
    env.visibility("visible"); await ready(app, env); const orgCall = env.calls.at(-1);
    env.event("pagehide"); assert.equal(app.binding.workspaceSession().kind, "unavailable"); assert.equal(orgCall.signal.aborted, true);
    env.event("pageshow"); await ready(app, env); assert.equal(app.binding.workspaceSession().kind, "ready");
  } finally { app.dispose(); env.cleanup(); }
});

test("actual cookie client and workspace binding discard rows, selection and cursor for every accepted epoch", async () => {
  const env = environment(), app = owner({ workspace: true });
  try {
    await ready(app, env);
    for (const value of [metadata(), metadata({ generation: "C".repeat(42) + "A" })]) {
      env.calls.at(-1).resolve(response(orgs)); await flush();
      app.directory.controller.selectOrganization("a"); await flush();
      assert.equal(env.calls.at(-1).path, "/console-api/v1/projects?organization_id=a");
      env.calls.at(-1).resolve(response(projects)); await flush();
      app.directory.controller.selectProject({ organizationId: "a", projectId: "p" });
      assert.equal(app.directory.state().selectedProjectId, "p");
      app.directory.controller.nextProjects({ organizationId: "a", cursor: "MORE" }); await flush();
      env.calls.at(-1).resolve(response({ ...projects, next_cursor: null })); await flush();
      assert.equal(app.directory.state().canReturnToFirstProjects, true);
      const prior = app.binding.workspaceSession(); app.binding.revalidate();
      assert.equal(app.binding.workspaceSession().kind, "unavailable");
      assert.equal(app.directory.state().organizations.kind, "unavailable");
      assert.equal(app.directory.state().selectedOrganizationId, undefined); assert.equal(app.directory.state().canReturnToFirstProjects, undefined);
      env.calls.at(-1).resolve(response(value)); await flush();
      assert.notEqual(app.binding.workspaceSession(), prior);
      assert.equal(env.calls.at(-1).path, "/console-api/v1/orgs");
      assert.deepEqual(env.calls.at(-1).headers, { accept: "application/json" }); assert.equal(env.calls.at(-1).credentials, "same-origin");
    }
    env.calls.at(-1).resolve(response(orgs)); await flush();
    app.directory.controller.selectOrganization("a"); await flush(); env.calls.at(-1).resolve(new Response(null, { status: 401 })); await flush();
    assert.equal(app.binding.workspaceSession().kind, "unavailable"); assert.equal(app.directory.state().organizations.kind, "unavailable");
    assert.doesNotMatch(JSON.stringify(app.directory.state()), /Private|FieldLog|NEXT|MORE/);
  } finally { app.dispose(); env.cleanup(); }
});

test("pure read/action fences reject wall and monotonic expiry without event or timer delivery", async () => {
  for (const kind of ["wall", "mono", "rollback"]) {
    const env = environment(), observed = [];
    const app = owner({ workspace: true, before(binding, directory) {
      observed.push(directory.state()); directory.controller.nextOrganizations("NEXT"); directory.controller.selectOrganization("a");
      assert.equal(binding.workspaceSession().kind, "unavailable");
    } });
    try {
      await ready(app, env); env.calls.at(-1).resolve(response(orgs)); await flush();
      if (kind === "wall") env.time.wall += 60000; else if (kind === "mono") env.time.mono += 60000; else env.time.wall--;
      const count = env.calls.length; app.poke(); assert.equal(env.calls.length, count);
      assert.equal(observed.at(-1).organizations.kind, "unavailable"); assert.equal(observed.at(-1).selectedOrganizationId, undefined);
      assert.doesNotMatch(JSON.stringify(observed), /Private studio/);
    } finally { app.dispose(); env.cleanup(); }
  }
});

test("cross-tab accepts only exact plain invalidation, rechecks when visible and never rebroadcasts inbound data", async () => {
  const env = environment(), app = owner();
  try {
    await ready(app, env); const channel = env.channels[0]; assert.equal(channel.name, "mixer.browser-session.v1");
    const before = env.calls.length;
    for (const data of [null, [], "invalidate", { type: "ready" }, { type: "invalidate", generation }, { type: "invalidate", csrf_token: csrf },
      Object.create({ type: "invalidate" }), Object.assign(Object.create(null), { type: "invalidate" }),
      Object.defineProperty({}, "type", { get() { throw Error("untrusted getter"); } }), { type: "invalidate", [Symbol()]: 1 }]) channel.receive(data);
    await flush(); assert.equal(env.calls.length, before); assert.equal(app.binding.workspaceSession().kind, "ready");
    channel.receive({ type: "invalidate" }); assert.equal(app.binding.workspaceSession().kind, "unavailable");
    channel.receive({ type: "invalidate" }); await flush(); assert.equal(env.calls.length, before + 1); assert.equal(channel.sent.length, 0);
    env.calls.at(-1).resolve(response(metadata())); await flush();
    app.binding.invalidate(); assert.equal(app.binding.workspaceSession().kind, "unavailable");
    assert.deepEqual(channel.sent, [{ type: "invalidate" }]); await flush(); assert.equal(env.calls.length, before + 1);
    env.visibility("hidden"); channel.receive({ type: "invalidate" }); await flush(); assert.equal(env.calls.length, before + 1);
  } finally { app.dispose(); env.cleanup(); }
});

test("missing BroadcastChannel preserves foreground checks; missing browser globals remain unavailable", async () => {
  const env = environment({ broadcast: false }), app = owner();
  try { await ready(app, env); assert.equal(env.channels.length, 0); app.binding.invalidate(); env.event("focus"); await ready(app, env); }
  finally { app.dispose(); env.cleanup(); }
  assert.throws(() => createBrowserSessionBinding(), /Missing browser session owner/);
  let binding; createRoot(dispose => { binding = createBrowserSessionBinding(); assert.equal(binding.workspaceSession().kind, "unavailable"); dispose(); });
  assert.equal(binding.workspaceSession().kind, "unavailable");
});

test("missing canonical session endpoint and HTML SPA fallback make zero workspace requests", async () => {
  for (const value of [new Response(null, { status: 404 }), new Response("<html>static fallback</html>", { headers: { "content-type": "text/html" } })]) {
    const env = environment(), app = owner({ workspace: true });
    try {
      await flush(); env.calls.at(-1).resolve(value); await flush();
      assert.equal(app.binding.workspaceSession().kind, "unavailable"); assert.equal(app.directory.state().organizations.kind, "unavailable");
      assert.deepEqual(env.calls.map(call => call.path), ["/auth/session"]);
    } finally { app.dispose(); env.cleanup(); }
  }
});

test("cleanup cancels queued checks, session and workspace requests, owned listeners and channels", async () => {
  const env = environment(), app = owner();
  app.dispose(); await flush(); assert.equal(env.calls.length, 0); assert.equal(env.document.count, 0); assert.equal(env.window.count, 0);
  assert.ok(env.channels.every(channel => channel.closed && channel.count === 0)); env.cleanup();
  const next = environment(), active = owner({ workspace: true });
  try {
    await ready(active, next); const call = next.calls.at(-1);
    active.dispose(); assert.equal(call.signal.aborted, true);
    call.resolve(response(orgs)); await flush(); assert.equal(active.binding.workspaceSession().kind, "unavailable");
    active.binding.revalidate(); active.binding.invalidate(); next.event("focus"); next.channels[0].receive({ type: "invalidate" }); await flush();
    assert.equal(next.calls.length, 2); assert.equal(next.document.count, 0); assert.equal(next.window.count, 0);
    assert.equal(next.channels[0].closed, true); assert.equal(next.channels[0].count, 0);
  } finally { active.dispose(); next.cleanup(); }
  const last = environment(), pending = owner();
  try {
    await flush(); pending.dispose(); assert.equal(last.calls[0].signal.aborted, true);
    last.calls[0].reject(Error("private late metadata")); await flush(); assert.equal(pending.binding.workspaceSession().kind, "unavailable");
  } finally { pending.dispose(); last.cleanup(); }
});

test("production main constructs one owner and passes a reactive App prop; no fake readiness or login UI", () => {
  const main = readFileSync(new URL("../src/main.tsx", import.meta.url), "utf8");
  assert.match(main, /function ConsoleRoot\(\)/); assert.match(main, /const binding = createBrowserSessionBinding\(\)/);
  assert.match(main, /<App workspaceSession=\{binding\.workspaceSession\(\)\} \/>/); assert.match(main, /render\(\(\) => <ConsoleRoot \/>, container\)/);
  assert.doesNotMatch(main, /kind:|csrf|generation|accessToken|login|localStorage|sessionStorage/);
});
