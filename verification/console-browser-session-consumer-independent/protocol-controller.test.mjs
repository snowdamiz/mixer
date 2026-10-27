// Independent host probes authored from frozen preaccess CL/CO oracles.
import assert from "node:assert/strict";
import { test, after } from "node:test";
import { moduleURL, wall0, csrf, generation, generation2, auth, unauth, orgs, projects, tick, deferred, json, api, code, ready, wire, clocked } from "./probe-helpers.mjs";
const { createBrowserSessionClient: client, BrowserSessionClientError: SessionError } = await import(moduleURL("api/browser-session-client"));
const { createBrowserSessionController: controller } = await import(moduleURL("state/browser-session-controller"));
const { WorkspaceClientError: WorkspaceError } = await import(moduleURL("api/workspace-client"));
const unhandled = [];
const rejection = error => unhandled.push(error);
process.on("unhandledRejection", rejection);
after(async () => { await tick(); process.off("unhandledRejection", rejection); assert.deepEqual(unhandled, []); });
console.log(JSON.stringify({ node: process.version, platform: process.platform, arch: process.arch, fixture_scope: "synthetic metadata, actual session and cookie workspace modules, no server/browser" }));
const read = (response, options = {}) => client({ fetch: async () => response, ...options }).read();
const invalid = response => assert.rejects(read(response), code(SessionError, "invalid_response"));

test("CL01 closed frozen success and exact request", async () => {
  for (const value of [unauth(), auth(), { csrf_token: csrf, expires_at: 0, generation, state: "authenticated" }]) {
    let request;
    const owner = client({ fetch: async (path, init) => { request = { path, init }; return json(value); } });
    assert.ok(Object.isFrozen(owner));
    const result = await owner.read();
    assert.deepEqual(result, value); assert.ok(Object.isFrozen(result)); assert.notEqual(result, value);
    const { signal, ...init } = request.init;
    assert.ok(signal instanceof AbortSignal);
    assert.deepEqual({ path: request.path, init }, { path: "/auth/session", init: { method: "GET", headers: { accept: "application/json" }, credentials: "same-origin", redirect: "error", cache: "no-store", referrerPolicy: "no-referrer" } });
  }
});
test("CL02 exact own options and bounded timeout", async () => {
  const hidden = Object.defineProperty({}, "session", { value: auth() });
  for (const options of [null, [], false, 1, "", { fetch: null }, { fetch: undefined }, { [Symbol()]: 1 }, hidden,
    ...[0, 30001, -1, 0.5, NaN, Infinity, undefined].map(timeoutMs => ({ timeoutMs }))]) {
    assert.throws(() => client(options), code(SessionError, "invalid_request"));
  }
  for (const timeoutMs of [1, 30000]) assert.deepEqual(await read(json(unauth()), { timeoutMs }), unauth());
});
test("CL03 all non200 unavailable and HTML200 invalid, no body projection", async () => {
  for (const status of [204, 301, 302, 307, 401, 403, 404, 429, 500, 501, 503, 599]) {
    const sample = wire({ status, text: "PRIVATE_PROVIDER_TEXT" });
    await assert.rejects(read(sample.response), code(SessionError, "unavailable"));
    assert.equal(sample.state.reads, 0); assert.equal(sample.state.bodyCancels, 1);
  }
  await invalid(new Response("<html>SPA fallback</html>", { headers: { "content-type": "text/html", "cache-control": "no-store" } }));
});
test("CL04 redirected and closed media type grammar", async () => {
  for (const value of [null, "text/json", "application/json; charset=utf-16", "application/json; x=1", "application/json, application/json", "application/json; charset=utf-8; charset=utf-8", "application/json; charset=\"utf-8\""]) {
    const sample = wire({ headers: { "content-type": value } }); await invalid(sample.response); assert.equal(sample.state.reads, 0);
  }
  await invalid(wire({ redirected: true }).response);
  for (const value of ["application/json", " APPLICATION/JSON \t", "application/json \t; \tChArSeT = UTF-8 \t"]) assert.deepEqual(await read(wire({ headers: { "content-type": value } }).response), unauth());
});
test("CL05 syntactically separate no-store and no header authority", async () => {
  for (const value of [null, "no-cache", "x=\"no-store\"", "x-no-store", "no-store-more", "no-store=1", "no-store,", ",no-store", "no-store garbage", "public,,no-store", "x=\"unterminated,no-store"]) await invalid(wire({ headers: { "cache-control": value } }).response);
  for (const value of ["no-store", "public, NO-STORE", "x=\"a,no-store\", private, no-store", "private=\"a\\\"b\", no-store"]) {
    assert.deepEqual(await read(wire({ headers: { "cache-control": value, Date: "future", "Set-Cookie": "session=private", "x-session": "ready" } }).response), unauth());
  }
});
test("CL06 canonical declared length and independently counted body", async () => {
  for (const value of ["00", "01", "+1", "-1", " 1", "1 ", "1,1", "1.0", "1e3", "9007199254740992", "8193"]) {
    const sample = wire({ headers: { "content-length": value } }); await invalid(sample.response); assert.equal(sample.state.reads, 0);
  }
  for (const value of [null, "0", "8192"]) assert.deepEqual(await read(wire({ headers: { "content-length": value } }).response), unauth());
});
test("CL07 complete success body 4096 boundary and immediate overflow", async () => {
  const text = JSON.stringify(unauth());
  assert.deepEqual(await read(wire({ text: text.padEnd(4096, " ") }).response), unauth());
  for (const chunks of [[new Uint8Array(4097)], [new TextEncoder().encode(text.padEnd(4096, " ")), new Uint8Array([32])]]) {
    const sample = wire({ chunks }); await invalid(sample.response);
    assert.equal(sample.state.reads, chunks.length); assert.equal(sample.state.cancels, 1); assert.equal(sample.state.releases, 1);
  }
});
test("CL08 read count includes empty chunks and final done", async () => {
  const text = new TextEncoder().encode(JSON.stringify(unauth()));
  const legal = wire({ read: index => Promise.resolve(index === 4095 ? { done: true } : { done: false, value: index === 0 ? text : new Uint8Array() }) });
  assert.deepEqual(await read(legal.response), unauth()); assert.equal(legal.state.reads, 4096);
  const excessive = wire({ read: index => Promise.resolve({ done: false, value: index === 0 ? text : new Uint8Array() }) });
  await invalid(excessive.response); assert.equal(excessive.state.reads, 4096); assert.equal(excessive.state.releases, 1);
});
test("CL09 required stream, fatal UTF8, BOM and trailing bytes", async () => {
  await invalid({ status: 200, headers: new Headers({ "content-type": "application/json", "cache-control": "no-store" }), body: null });
  for (const chunks of [[Uint8Array.from([0xef, 0xbb, 0xbf]), new TextEncoder().encode(JSON.stringify(unauth()))], [Uint8Array.from([0xc0, 0xaf])], [Uint8Array.from([0xe2]), Uint8Array.from([0x28, 0xa1])]]) await invalid(wire({ chunks }).response);
  for (const text of [JSON.stringify(unauth()) + "x", JSON.stringify(unauth()) + "\u00a0", JSON.stringify({ ...unauth(), state: "unauthenticatéd" })]) await invalid(wire({ text }).response);
  assert.deepEqual(await read(wire({ text: "\r\n\t " + JSON.stringify(unauth()) + " \r\n\t" }).response), unauth());
});
test("CL10 strict flat lexical JSON and aliases", async () => {
  const base = JSON.stringify(unauth());
  for (const text of ["null", "[]", "{}", base + base, base.replace("}", ',"state":"unauthenticated"}'), base.replace('"state"', '"sta\\u0074e"'), base.replace('"unauthenticated"', '"unauthentica\\u0074ed"'), base.replace('"state"', '"statex"'), base.replace('"unauthenticated"', '{}'), base.replace("}", ',"extra":1}'), base.replace("}", ",}"), base.replace('"csrf_token"', '"csrf_token"'), JSON.stringify({ state: "unauthenticated" })]) {
    if (text === base) continue;
    await invalid(wire({ text }).response);
  }
});
test("CL11 canonical43 independently re-encoded including trailing bits", async () => {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
  const last = alphabet.indexOf(csrf.at(-1)); assert.equal(last % 4, 0);
  for (const value of [csrf.slice(1), csrf + "A", csrf.slice(0, -1) + "=", "+" + csrf.slice(1), "/" + csrf.slice(1), csrf.slice(0, -1) + alphabet[last + 1], csrf.slice(0, -1) + " "]) {
    await invalid(json({ ...unauth(), csrf_token: value })); await invalid(json(auth({ generation: value })));
  }
  for (const value of [Buffer.alloc(32).toString("base64url"), Buffer.alloc(32, 255).toString("base64url")]) assert.deepEqual(await read(json(auth({ generation: value, csrf_token: value }))), auth({ generation: value, csrf_token: value }));
});
test("CL12 expires integer lexical forms and safe seconds", async () => {
  for (const token of ["-0", "+1", "-1", "01", "1.0", "1e3", '"1"', "NaN", "9007199254740992"]) await invalid(wire({ text: JSON.stringify(auth()).replace(String(auth().expires_at), token) }).response);
  for (const expires_at of [0, Number.MAX_SAFE_INTEGER]) assert.equal((await read(json(auth({ expires_at })))).expires_at, expires_at);
});
test("CL13 one deadline, noncooperative fetch/read/cancel and late rejection", async () => {
  for (const mode of ["caller-fetch", "deadline-fetch", "caller-read", "deadline-read"]) {
    const abort = new AbortController(), late = deferred(), sample = wire({ read: () => late.promise, cancel: () => new Promise(() => {}) });
    let usedSignal;
    const pending = client({ timeoutMs: 8, fetch: (path, init) => { usedSignal = init.signal; return mode.endsWith("fetch") ? late.promise : Promise.resolve(sample.response); } }).read(abort.signal);
    const checked = assert.rejects(pending, code(SessionError, mode.startsWith("caller") ? "aborted" : "unavailable"));
    await tick(); if (mode.startsWith("caller")) abort.abort(); await checked;
    assert.equal(usedSignal.aborted, true);
    if (mode.endsWith("fetch")) late.resolve(sample.response); else late.reject(Error("PRIVATE_LATE_READ"));
    await tick(); assert.ok(mode.endsWith("fetch") ? sample.state.bodyCancels > 0 : sample.state.cancels > 0);
    if (mode.endsWith("read")) assert.equal(sample.state.releases, 1);
  }
  const stopped = new AbortController(); stopped.abort(); let count = 0;
  await assert.rejects(client({ fetch: () => { count++; throw Error(); } }).read(stopped.signal), code(SessionError, "aborted")); assert.equal(count, 0);
  const late = deferred(), abort = new AbortController(); const promise = client({ fetch: () => late.promise }).read(abort.signal);
  const checked = assert.rejects(promise, code(SessionError, "aborted")); abort.abort(); await checked; late.reject(Error("PRIVATE_LATE_FETCH")); await tick();
});
test("CL14 private exceptions and hostile cleanup stay closed", async () => {
  const failure = async (promise, category) => assert.rejects(promise, error => code(SessionError, category)(error) && !`${error.message}\n${error.stack}`.includes("PRIVATE_"));
  await failure(client({ fetch: () => { throw Error("PRIVATE_FETCH"); } }).read(), "unavailable");
  const header = wire(); header.response.headers.get = () => { throw Error("PRIVATE_HEADER"); }; await failure(read(header.response), "invalid_response");
  const sample = wire({ read: () => Promise.reject(Error("PRIVATE_READ")), cancel: () => { throw Error("PRIVATE_CANCEL"); }, release: () => { throw Error("PRIVATE_RELEASE"); } });
  await failure(read(sample.response), "invalid_response"); assert.equal(sample.state.releases, 1);
  const noBody = wire({ status: 404, cancel: () => Promise.reject(Error("PRIVATE_BODY_CANCEL")) }); await failure(read(noBody.response), "unavailable"); await tick();
});
test("CL15 decode/publication cannot outlive absolute deadline or caller abort", () => clocked(async time => {
  const btoa0 = globalThis.btoa;
  try {
    globalThis.btoa = value => { time.mono = 100; return btoa0(value); };
    await assert.rejects(read(json(unauth()), { timeoutMs: 10 }), code(SessionError, "unavailable"));
    time.mono = 12.5;
    const signal = new AbortController(); globalThis.btoa = value => { signal.abort(); return btoa0(value); };
    await assert.rejects(client({ fetch: async () => json(unauth()) }).read(signal.signal), code(SessionError, "aborted"));
  } finally { globalThis.btoa = btoa0; }
}));

test("CO01 constructor idle, frozen initial state and closed surface", () => {
  const server = api(), owner = controller({ fetch: server.fetch });
  assert.equal(server.calls.length, 0); assert.ok(Object.isFrozen(owner)); assert.ok(Object.isFrozen(owner.getSession()));
  assert.deepEqual(Object.keys(owner), ["getSession", "subscribe", "revalidate", "invalidate", "dispose"]);
  let count = 0; const off = owner.subscribe(value => { assert.equal(value.kind, "unavailable"); count++; });
  assert.equal(count, 1); off(); owner.dispose(); owner.revalidate(); assert.equal(server.calls.length, 0);
});
test("CO02 supersession installs unavailable before synchronous abort reentry", () => clocked(async () => {
  const server = api(), owner = controller({ fetch: server.fetch });
  try {
    const prior = await ready(owner, server); const pending = prior.client.organizations(); const checked = assert.rejects(pending, code(WorkspaceError, "aborted")); await tick();
    let observed; server.calls.at(-1).init.signal.addEventListener("abort", () => { observed = owner.getSession().kind; }, { once: true });
    owner.revalidate(); assert.equal(observed, "unavailable"); assert.equal(owner.getSession().kind, "unavailable"); await checked;
    server.calls.at(-1).resolve(json(auth())); await tick(); assert.equal(owner.getSession().kind, "ready");
  } finally { owner.dispose(); }
}));
test("CO03 latest operation wins for equal and different generations", () => clocked(async () => {
  const server = api(), owner = controller({ fetch: server.fetch });
  try {
    owner.revalidate(); const a = server.calls.at(-1); owner.revalidate(); const b = server.calls.at(-1); owner.revalidate(); const c = server.calls.at(-1);
    b.resolve(json(auth())); a.resolve(json(auth({ generation: generation2 }))); c.resolve(json(auth())); await tick();
    const prior = owner.getSession(); assert.equal(prior.kind, "ready");
    const equal = await ready(owner, server); assert.notEqual(equal, prior); assert.notEqual(equal.client, prior.client);
    const changed = await ready(owner, server, auth({ generation: generation2 })); assert.notEqual(changed, equal);
    owner.revalidate(); const old = server.calls.at(-1); owner.revalidate(); server.calls.at(-1).resolve(json(auth())); await tick(); const current = owner.getSession();
    old.reject(Error("late failure")); await tick(); assert.equal(owner.getSession(), current);
  } finally { owner.dispose(); }
}));
test("CO04 all retained wrappers reject without dispatch after epoch removal", () => clocked(async time => {
  for (const kind of ["equal", "different", "unauthenticated", "invalidate", "expiry", "dispose"]) {
    time.wall = wall0; time.mono = 12.5; const server = api(), owner = controller({ fetch: server.fetch });
    try {
      const prior = await ready(owner, server);
      if (kind === "equal" || kind === "different") await ready(owner, server, auth(kind === "different" ? { generation: generation2 } : {}));
      else if (kind === "unauthenticated") { owner.revalidate(); server.calls.at(-1).resolve(json(unauth())); await tick(); }
      else if (kind === "expiry") time.mono += 90000;
      else owner[kind]();
      const count = server.calls.length;
      await assert.rejects(prior.client.organizations(), code(WorkspaceError, "aborted"));
      await assert.rejects(prior.client.projects("org α"), code(WorkspaceError, "aborted")); assert.equal(server.calls.length, count);
    } finally { owner.dispose(); }
  }
}));
test("CO05 captured wall/monotonic lifetime and 900 second cap", () => clocked(async time => {
  const server = api(), owner = controller({ fetch: server.fetch });
  try {
    owner.revalidate(); time.mono += 5000; time.wall += 5000; server.calls.at(-1).resolve(json(auth({ expires_at: wall0 / 1000 + 3 }))); await tick(); assert.equal(owner.getSession().kind, "unavailable");
    time.wall = wall0; time.mono = 12.5; await ready(owner, server, auth({ expires_at: wall0 / 1000 + 3600 }));
    time.mono = 900012.5; assert.equal(owner.getSession().kind, "unavailable");
    time.wall = wall0; time.mono = 12.5; owner.revalidate(); time.mono = 1012.5; time.wall += 1000; server.calls.at(-1).resolve(json(auth({ expires_at: wall0 / 1000 + 1 }))); await tick(); assert.equal(owner.getSession().kind, "unavailable");
  } finally { owner.dispose(); }
}));
test("CO06 invalid clocks and unsafe deadline arithmetic fail closed", () => clocked(async time => {
  for (const [field, invalidValue] of [["wall", -1], ["wall", 0.5], ["wall", NaN], ["wall", Infinity], ["wall", Number.MAX_SAFE_INTEGER + 1], ["mono", -1], ["mono", NaN], ["mono", Infinity], ["mono", Number.MAX_SAFE_INTEGER + 1]]) {
    const server = api(), owner = controller({ fetch: server.fetch }); time.wall = wall0; time.mono = 12.5; time[field] = invalidValue;
    try { owner.revalidate(); assert.equal(owner.getSession().kind, "unavailable"); assert.equal(server.calls.length, 0); } finally { owner.dispose(); }
  }
  for (const [mono, expires_at] of [[12.5, Number.MAX_SAFE_INTEGER], [Number.MAX_SAFE_INTEGER, wall0 / 1000 + 90]]) {
    time.wall = wall0; time.mono = mono; const server = api(), owner = controller({ fetch: server.fetch });
    try { owner.revalidate(); server.calls.at(-1).resolve(json(auth({ expires_at }))); await tick(); assert.equal(owner.getSession().kind, "unavailable"); } finally { owner.dispose(); }
  }
}));
test("CO07 synchronous expiry and rollback on read/delegate/result", () => clocked(async time => {
  for (const [field, change] of [["wall", 90000], ["mono", 90000], ["wall", -1], ["mono", -0.25]]) {
    time.wall = wall0; time.mono = 12.5; const server = api(), owner = controller({ fetch: server.fetch });
    try {
      const prior = await ready(owner, server); time[field] += change; assert.equal(owner.getSession().kind, "unavailable");
      const count = server.calls.length; await assert.rejects(prior.client.organizations(), code(WorkspaceError, "aborted")); assert.equal(server.calls.length, count);
    } finally { owner.dispose(); }
  }
}));
test("CO08 owned expiration timer removes ready without automatic retry", () => clocked(async (time, timers) => {
  const server = api(), owner = controller({ fetch: server.fetch });
  try {
    await ready(owner, server, auth({ expires_at: wall0 / 1000 + 1 })); assert.equal(timers.size, 1);
    const [timer] = timers; timer._onTimeout(); await tick();
    // Explicit invocation emulates throttled delivery; clearTimeout retires its handle.
    assert.equal(owner.getSession().kind, "unavailable"); assert.equal(server.calls.length, 1);
    await ready(owner, server); assert.equal(server.calls.length, 2);
  } finally { owner.dispose(); }
}));
test("CO09 actual cookie transport fixed routes, query, headers and parser", () => clocked(async () => {
  const server = api(), owner = controller({ fetch: server.fetch, timeoutMs: 1234 });
  try {
    const session = await ready(owner, server); assert.deepEqual(Object.keys(session).sort(), ["client", "kind"]); assert.ok(Object.isFrozen(session.client));
    const organizations = session.client.organizations({ limit: 3, cursor: "CURSOR" }); await tick(); const a = server.calls.at(-1);
    assert.equal(a.path, "/console-api/v1/orgs?limit=3&cursor=CURSOR"); assert.deepEqual(a.init.headers, { accept: "application/json" }); assert.equal(a.init.credentials, "same-origin"); a.resolve(json(orgs)); assert.deepEqual(await organizations, orgs);
    const request = session.client.projects("org α", { cursor: "NEXT" }); await tick(); const b = server.calls.at(-1);
    assert.equal(b.path, "/console-api/v1/projects?organization_id=org%20%CE%B1&cursor=NEXT"); b.resolve(json(projects)); assert.deepEqual(await request, projects);
    const invalidPage = session.client.organizations({ origin: "https://evil.invalid" }); await assert.rejects(invalidPage, code(WorkspaceError, "invalid_request"));
  } finally { owner.dispose(); }
}));
test("CO10 caller abort scoped; outer invalidate aborts all tracked requests", () => clocked(async () => {
  const server = api(), owner = controller({ fetch: server.fetch });
  try {
    const session = await ready(owner, server), caller = new AbortController();
    const a = session.client.organizations({}, caller.signal), b = session.client.projects("org α");
    const ca = assert.rejects(a, code(WorkspaceError, "aborted")), cb = assert.rejects(b, code(WorkspaceError, "aborted")); await tick();
    const calls = server.calls.slice(-2); caller.abort(); await ca; assert.equal(calls[0].init.signal.aborted, true); assert.equal(calls[1].init.signal.aborted, false);
    owner.invalidate(); assert.equal(calls[1].init.signal.aborted, true); await cb;
    const dead = new AbortController(); dead.abort(); const count = server.calls.length;
    await assert.rejects(session.client.organizations({}, dead.signal), code(WorkspaceError, "aborted")); assert.equal(server.calls.length, count);
  } finally { owner.dispose(); }
}));
test("CO11 actual current401 clears outer immediately; other errors scoped", () => clocked(async () => {
  for (const [status, category] of [[401, "unauthenticated"], [403, "permission_denied"], [404, "not_found"], [503, "unavailable"]]) {
    const server = api(), owner = controller({ fetch: server.fetch });
    try { const session = await ready(owner, server); const pending = session.client.organizations(); const checked = assert.rejects(pending, code(WorkspaceError, category)); await tick(); server.calls.at(-1).resolve(new Response(null, { status })); await checked; assert.equal(owner.getSession().kind, status === 401 ? "unavailable" : "ready"); assert.equal(server.calls.length, 2); } finally { owner.dispose(); }
  }
  const server = api(), owner = controller({ fetch: server.fetch });
  try { const session = await ready(owner, server); const pending = session.client.organizations(); const checked = assert.rejects(pending, code(WorkspaceError, "unavailable")); await tick(); server.calls.at(-1).reject({ name: "WorkspaceClientError", code: "unauthenticated" }); await checked; assert.equal(owner.getSession(), session); } finally { owner.dispose(); }
}));
test("CO12 postawait expiry and stale401 cannot alter current capability", () => clocked(async time => {
  for (const status of [200, 401, 503]) {
    time.wall = wall0; time.mono = 12.5; const server = api(), owner = controller({ fetch: server.fetch });
    try {
      const session = await ready(owner, server); const pending = session.client.organizations(); const checked = assert.rejects(pending, code(WorkspaceError, "aborted")); await tick(); const request = server.calls.at(-1);
      time.wall += 90000; request.resolve(status === 200 ? json(orgs) : new Response(null, { status })); await checked; assert.equal(owner.getSession().kind, "unavailable");
    } finally { owner.dispose(); }
  }
  time.wall = wall0; time.mono = 12.5; const server = api(), owner = controller({ fetch: server.fetch });
  try { const old = await ready(owner, server); const pending = old.client.organizations(); const checked = assert.rejects(pending, code(WorkspaceError, "aborted")); await tick(); const request = server.calls.at(-1); const fresh = await ready(owner, server); await checked; request.resolve(new Response(null, { status: 401 })); await tick(); assert.equal(owner.getSession(), fresh); } finally { owner.dispose(); }
}));
test("CO13 reentrant and throwing subscribers cannot publish stale ready", () => clocked(async () => {
  const server = api(), owner = controller({ fetch: server.fetch }), observed = [];
  let nested = false, unsubscribe;
  try {
    owner.subscribe(() => { throw Error("observer"); });
    owner.subscribe(value => { if (value.kind === "ready" && !nested) { nested = true; unsubscribe(); owner.revalidate(); } });
    unsubscribe = owner.subscribe(value => observed.push(value.kind));
    owner.revalidate(); server.calls.at(-1).resolve(json(auth())); await tick();
    assert.equal(owner.getSession().kind, "unavailable"); assert.equal(server.calls.length, 2); assert.deepEqual(observed, ["unavailable", "unavailable"]);
    let late = 0; owner.subscribe(value => { late++; assert.equal(value.kind, owner.getSession().kind); });
    server.calls.at(-1).resolve(json(auth())); await tick(); assert.equal(owner.getSession().kind, "ready"); assert.equal(late, 2);
  } finally { owner.dispose(); }
}));
test("CO14 nested abort revalidation remains current and disposal terminal", () => clocked(async () => {
  const server = api(), owner = controller({ fetch: server.fetch });
  try {
    owner.revalidate(); const old = server.calls.at(-1); let calls = 0;
    old.init.signal.addEventListener("abort", () => { assert.equal(owner.getSession().kind, "unavailable"); calls++; owner.revalidate(); }, { once: true });
    owner.revalidate(); assert.equal(calls, 1); assert.equal(server.calls.length, 2);
    server.calls.at(-1).resolve(json(auth())); await tick(); assert.equal(owner.getSession().kind, "ready");
    const session = owner.getSession(), pending = session.client.organizations(), checked = assert.rejects(pending, code(WorkspaceError, "aborted")); await tick();
    server.calls.at(-1).init.signal.addEventListener("abort", () => owner.dispose(), { once: true });
    owner.revalidate(); await checked; assert.equal(owner.getSession().kind, "unavailable"); const count = server.calls.length; owner.revalidate(); assert.equal(server.calls.length, count);
  } finally { owner.dispose(); }
}));
test("CO15 dispose pending work idempotently blocks all later publication", () => clocked(async () => {
  const server = api(), owner = controller({ fetch: server.fetch }); let notifications = 0;
  owner.subscribe(() => notifications++); owner.revalidate(); const pending = server.calls.at(-1); owner.dispose(); const count = notifications;
  pending.resolve(json(auth())); await tick(); owner.dispose(); owner.invalidate(); owner.revalidate(); owner.subscribe(() => { throw Error("after disposal"); });
  assert.equal(owner.getSession().kind, "unavailable"); assert.equal(server.calls.length, 1); assert.equal(notifications, count);
}));
