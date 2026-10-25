import assert from "node:assert/strict";
import { test } from "node:test";
import { createServer } from "node:http";
import { pathToFileURL } from "node:url";

const { createWorkspaceClient, WorkspaceClientError } = await import(pathToFileURL(process.env.MIXER_REVIEW_CLIENT_JS).href);
const tick = () => new Promise(resolve => setImmediate(resolve));
const response = (value, init = {}) => new Response(JSON.stringify(value), { headers: { "content-type": "application/json" }, ...init });
const organizations = { organizations: [{ id: "org", display_name: null, organization_roles: [] }], next_cursor: null };
const project = id => ({ projects: [{ organization_id: id, id: "p", display_name: "Stored Name", roles: ["billing_manager"] }], next_cursor: null });
const client = (fetch, extra = {}) => createWorkspaceClient({ apiOrigin: "https://api.example.invalid", accessToken: () => "synthetic.review.token", fetch, ...extra });
const error = code => value => {
  assert.ok(value instanceof WorkspaceClientError);
  assert.equal(value.code, code);
  assert.equal(value.message, `Workspace request ${code}`);
  assert.deepEqual(Object.keys(value).sort(), ["code", "name"]);
  assert.equal(Object.hasOwn(value, "cause"), false);
  return true;
};

async function until(check) {
  for (let count = 0; count < 50; count++) {
    if (check()) return;
    await tick();
  }
  assert.fail("bounded independent fixture did not become ready");
}

async function listen(server) {
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  return `http://127.0.0.1:${server.address().port}`;
}

async function close(server) {
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
  assert.equal(server.listening, false);
}

test("actual fetch rejects a cross-origin redirect without forwarding bearer to its sink", async () => {
  let originRequests = 0;
  let sinkRequests = 0;
  const sink = createServer((_, res) => { sinkRequests++; res.end("private sink"); });
  const sinkOrigin = await listen(sink);
  const origin = createServer((req, res) => {
    originRequests++;
    assert.equal(req.url, "/v3/orgs");
    assert.equal(req.headers.authorization, "Bearer synthetic.review.token");
    assert.equal(req.headers.cookie, undefined);
    assert.equal(req.headers.referer, undefined);
    res.writeHead(302, { location: sinkOrigin + "/capture" });
    res.end("private redirect body");
  });
  try {
    const apiOrigin = await listen(origin);
    const api = createWorkspaceClient({ apiOrigin, allowInsecureLoopback: true, accessToken: () => "synthetic.review.token", timeoutMs: 1000 });
    await assert.rejects(api.organizations(), error("unavailable"));
    await tick();
    assert.equal(originRequests, 1);
    assert.equal(sinkRequests, 0);
  } finally {
    if (origin.listening) await close(origin);
    await close(sink);
  }
});

test("timeout bounds a fetch that ignores abort and cancels its late unread response", async () => {
  let release;
  let cancelled = 0;
  const api = client(() => new Promise(resolve => { release = resolve; }), { timeoutMs: 15 });
  const pending = api.organizations();
  await until(() => release !== undefined);
  await assert.rejects(pending, error("unavailable"));
  const body = new ReadableStream({ cancel() { cancelled++; } });
  release(new Response(body, { headers: { "content-type": "application/json" } }));
  await tick();
  await tick();
  assert.equal(cancelled, 1);
  assert.equal(body.locked, false);
});

test("caller abort wins a non-cooperative fetch and its late rejection stays handled", async () => {
  let rejectFetch;
  const caller = new AbortController();
  const api = client(() => new Promise((_, reject) => { rejectFetch = reject; }), { timeoutMs: 1000 });
  const pending = api.organizations({}, caller.signal);
  await until(() => rejectFetch !== undefined);
  caller.abort();
  await assert.rejects(pending, error("aborted"));
  rejectFetch(new Error("private late network origin or bearer"));
  await tick();
  await tick();
});

test("abort of an active body does not await an underlying cancellation promise", async () => {
  let cancellations = 0;
  const caller = new AbortController();
  const stream = new ReadableStream({
    start(controller) { controller.enqueue(new TextEncoder().encode('{"organizations":[')); },
    cancel() { cancellations++; return new Promise(() => {}); },
  });
  const api = client(async () => new Response(stream, { headers: { "content-type": "application/json" } }), { timeoutMs: 1000 });
  const pending = api.organizations({}, caller.signal);
  await until(() => stream.locked);
  caller.abort();
  await assert.rejects(pending, error("aborted"));
  await tick();
  assert.equal(cancellations, 1);
  assert.equal(stream.locked, false);
});

test("the actual UTF8 byte bound accepts its boundary and rejects one extra byte", async () => {
  const maximum = 262144;
  const json = JSON.stringify({ organizations: [{ id: "北", display_name: "é", organization_roles: [] }], next_cursor: null });
  const bytes = new TextEncoder().encode(json).byteLength;
  for (const extra of [0, 1]) {
    const body = json + " ".repeat(maximum - bytes + extra);
    const api = client(async () => new Response(body, { headers: { "content-type": "application/json" } }));
    if (extra === 0) assert.equal((await api.organizations()).organizations[0].id, "北");
    else await assert.rejects(api.organizations(), error("invalid_response"));
  }
});

test("rejected status and media cancel without consuming private bodies or leaking cancellation errors", async () => {
  for (const [status, contentType, expected] of [[403, "text/private", "permission_denied"], [200, "text/html", "invalid_response"]]) {
    let cancelled = false;
    const stream = new ReadableStream({ cancel() { cancelled = true; throw new Error("private cancellation payload"); } });
    const api = client(async () => new Response(stream, { status, headers: { "content-type": contentType } }));
    await assert.rejects(api.organizations(), error(expected));
    await tick();
    assert.equal(cancelled, true);
    assert.equal(stream.locked, false);
  }
});

test("concurrent requests independently resolve tokens and preserve full IDs without ambient credentials", async () => {
  const resolvers = [];
  const seen = [];
  const api = client(async (url, init) => {
    const id = new URL(url).searchParams.get("organization_id");
    seen.push({ id, url, init });
    return response(project(id));
  }, { accessToken: () => new Promise(resolve => resolvers.push(resolve)) });
  const firstId = "../org+%2F/北?&#=";
  const secondId = " . ";
  const first = api.projects(firstId, { limit: 100 });
  const second = api.projects(secondId);
  assert.equal(resolvers.length, 2);
  resolvers[1]("second.review.token");
  resolvers[0]("first.review.token");
  assert.equal((await first).projects[0].organization_id, firstId);
  assert.equal((await second).projects[0].organization_id, secondId);
  assert.deepEqual(seen.map(value => [value.id, value.init.headers.authorization]), [[secondId, "Bearer second.review.token"], [firstId, "Bearer first.review.token"]]);
  for (const value of seen) {
    assert.ok(value.url.startsWith("https://api.example.invalid/v3/projects?organization_id="));
    assert.equal(value.url.includes("review.token"), false);
    assert.equal(value.init.credentials, "omit");
    assert.equal(value.init.redirect, "error");
    assert.equal(value.init.cache, "no-store");
    assert.equal(value.init.referrerPolicy, "no-referrer");
    assert.equal(Object.hasOwn(value.init, "body"), false);
  }
});

test("response validation rejects scope roles names and extra fields and returns deeply frozen copies", async () => {
  const good = project("org");
  const row = good.projects[0];
  const bad = [
    { ...good, extra: "private" },
    { projects: [{ ...row, organization_id: "other" }], next_cursor: null },
    { projects: [{ ...row, roles: [] }], next_cursor: null },
    { projects: [{ ...row, roles: ["viewer", "owner"] }], next_cursor: null },
    { projects: [{ ...row, display_name: "private\nname" }], next_cursor: null },
    { projects: [{ ...row, id: "*" }], next_cursor: null },
    { projects: [], next_cursor: "opaque_cursor" },
  ];
  for (const value of bad) await assert.rejects(client(async () => response(value)).projects("org"), error("invalid_response"));
  const result = await client(async () => response(good)).projects("org");
  for (const value of [result, result.projects, result.projects[0], result.projects[0].roles]) assert.ok(Object.isFrozen(value));
  assert.throws(() => { result.projects[0].display_name = "mutated"; }, TypeError);
});

test("session-provider failure and late token do not leak metadata or trigger a hidden retry", async () => {
  let fetches = 0;
  let releases;
  const api = client(async () => { fetches++; return response(organizations); }, {
    timeoutMs: 15,
    accessToken: () => new Promise(resolve => { releases = resolve; }),
  });
  const pending = api.organizations();
  await assert.rejects(pending, error("unavailable"));
  releases("late.private.review.token");
  await tick();
  assert.equal(fetches, 0);
  const privateError = new WorkspaceClientError("unavailable");
  privateError.message = "private provider token";
  privateError.code = "private unknown error";
  await assert.rejects(client(async () => response(organizations), { accessToken: () => { throw privateError; } }).organizations(), error("unavailable"));
});
