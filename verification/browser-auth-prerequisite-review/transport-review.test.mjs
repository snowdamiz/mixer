import assert from "node:assert/strict";
import { test } from "node:test";
import { pathToFileURL } from "node:url";
import { join } from "node:path";

const output = process.env.MIXER_REVIEW_COMPILED_JS;
assert.ok(output, "isolated runner must supply selected compilation output");
const { createCookieWorkspaceClient } = await import(pathToFileURL(join(output, "api/cookie-workspace-client.js")));
const { createWorkspaceClient, WorkspaceClientError } = await import(pathToFileURL(join(output, "api/workspace-client.js")));
const { WorkspaceClientError: SharedError } = await import(pathToFileURL(join(output, "api/workspace-transport.js")));
const organizations = { organizations: [], next_cursor: null };
const projects = id => ({ projects: [{ organization_id: id, id: "same-project", display_name: null, roles: ["viewer"] }], next_cursor: null });
const response = value => new Response(JSON.stringify(value), { headers: { "content-type": "application/json" } });
const safe = code => error => {
  assert.ok(error instanceof WorkspaceClientError);
  assert.equal(error.constructor, SharedError);
  assert.equal(error.code, code);
  assert.equal(String(error), `WorkspaceClientError: Workspace request ${code}`);
  assert.deepEqual(Object.keys(error).sort(), ["code", "name"]);
  return true;
};
const tick = () => new Promise(resolve => setImmediate(resolve));

test("mixed adversarial IDs cannot introduce an origin, path, fragment or second query field", async () => {
  let calls = 0;
  const api = createCookieWorkspaceClient({ fetch: async (path, init) => {
    calls++;
    const parsed = new URL(path, "https://console.example.invalid/nested/route");
    assert.equal(parsed.origin, "https://console.example.invalid");
    assert.equal(parsed.pathname, "/console-api/v1/projects");
    assert.equal(parsed.hash, "");
    assert.equal([...parsed.searchParams].length, 1);
    assert.equal(init.credentials, "same-origin");
    assert.deepEqual(init.headers, { accept: "application/json" });
    return response(projects(parsed.searchParams.get("organization_id")));
  } });
  const ids = ["//attacker.invalid/a?x=1#fragment", "\\\\attacker.invalid", "%252f%252f", "x&organization_id=other", "x?limit=1", "x#p", "x=other", "'\"<svg>", "北+é/../%2F"];
  for (const id of ids) assert.equal((await api.projects(id)).projects[0].organization_id, id);
  assert.equal(calls, ids.length);
});

test("destination and credential configuration reject before evaluating their values", () => {
  let reads = 0;
  for (const name of ["apiOrigin", "baseURL", "accessToken", "headers", "credentials", "cookie", "authorization"]) {
    const options = Object.defineProperty({}, name, { enumerable: true, get() { reads++; throw Error("private credential"); } });
    assert.throws(() => createCookieWorkspaceClient(options), safe("invalid_request"));
  }
  assert.equal(reads, 0);
});

test("client captures trusted fetch and timeout so subsequent option mutation cannot retarget it", async () => {
  let original = 0;
  const options = { fetch: async () => { original++; return response(organizations); }, timeoutMs: 100 };
  const api = createCookieWorkspaceClient(options);
  options.fetch = async () => { throw Error("unexpected destination"); };
  options.timeoutMs = 0;
  assert.deepEqual(await api.organizations(), organizations);
  assert.equal(original, 1);
});

test("concurrent tenant requests decode only their own scope even when responses arrive in reverse order", async () => {
  const releases = new Map();
  const api = createCookieWorkspaceClient({ fetch: path => new Promise(resolve => releases.set(new URL(path, "https://console.invalid").searchParams.get("organization_id"), resolve)) });
  const first = api.projects("first"); const second = api.projects("second");
  await tick(); releases.get("second")(response(projects("second")));
  assert.equal((await second).projects[0].organization_id, "second");
  releases.get("first")(response(projects("second")));
  await assert.rejects(first, safe("invalid_response"));
});

test("one aborted request does not cancel or poison concurrent and later requests", async () => {
  const pending = [];
  const api = createCookieWorkspaceClient({ fetch: (_, init) => new Promise(resolve => pending.push({ resolve, signal: init.signal })) });
  const controller = new AbortController();
  const canceled = api.organizations({}, controller.signal); const live = api.organizations();
  await tick(); controller.abort(); await assert.rejects(canceled, safe("aborted"));
  assert.equal(pending[0].signal.aborted, true); assert.equal(pending[1].signal.aborted, false);
  pending[0].resolve(response(organizations)); pending[1].resolve(response(organizations));
  assert.deepEqual(await live, organizations);
  const later = api.organizations(); await tick(); pending[2].resolve(response(organizations));
  assert.deepEqual(await later, organizations);
});

test("reentrant caller abort inside fetch rejects the completed response and cancels its unread body", async () => {
  const controller = new AbortController(); let canceled = false;
  const stream = new ReadableStream({ cancel() { canceled = true; } });
  const api = createCookieWorkspaceClient({ fetch: async () => { controller.abort(); return new Response(stream, { headers: { "content-type": "application/json" } }); } });
  await assert.rejects(api.organizations({}, controller.signal), safe("aborted"));
  await tick(); assert.equal(canceled, true); assert.equal(stream.locked, false);
});

test("deadline settles a never-resolving response and cancels a late body without parsing it", async () => {
  let release; let canceled = false;
  const api = createCookieWorkspaceClient({ timeoutMs: 10, fetch: () => new Promise(resolve => { release = resolve; }) });
  await assert.rejects(api.organizations(), safe("unavailable"));
  release(new Response(new ReadableStream({ cancel() { canceled = true; return new Promise(() => {}); } }), { headers: { "content-type": "application/json" } }));
  await tick(); assert.equal(canceled, true);
});

test("body deadline and caller cancellation return no partial page and release the locked reader", async () => {
  for (const kind of ["deadline", "abort"]) {
    let canceled = false; const controller = new AbortController();
    const stream = new ReadableStream({ start(c) { c.enqueue(new TextEncoder().encode('{"organizations":[')); }, cancel() { canceled = true; return new Promise(() => {}); } });
    const api = createCookieWorkspaceClient({ timeoutMs: kind === "deadline" ? 10 : 1000, fetch: async () => new Response(stream, { headers: { "content-type": "application/json" } }) });
    const pending = api.organizations({}, controller.signal); await tick();
    if (kind === "abort") controller.abort();
    await assert.rejects(pending, safe(kind === "deadline" ? "unavailable" : "aborted"));
    await tick(); assert.equal(canceled, true); assert.equal(stream.locked, false);
  }
});

test("non-200 statuses cancel unread bodies and never decode private errors", async () => {
  for (const [status, code] of [[204, "invalid_response"], [206, "invalid_response"], [301, "invalid_response"], [400, "invalid_response"], [401, "unauthenticated"], [403, "permission_denied"], [404, "not_found"], [408, "invalid_response"], [429, "unavailable"], [500, "unavailable"], [501, "invalid_response"], [503, "unavailable"]]) {
    let canceled = false;
    const body = status === 204 ? null : new ReadableStream({ cancel() { canceled = true; } });
    await assert.rejects(createCookieWorkspaceClient({ fetch: async () => new Response(body, { status }) }).organizations(), safe(code));
    if (body) { await tick(); assert.equal(canceled, true); }
  }
});

test("response length metadata cannot bypass streaming byte bounds or UTF8 validation", async () => {
  for (const [body, length] of [["x".repeat(262145), "1"], [new Uint8Array([0xc0, 0xaf]), "2"], ["{}", "-1"], ["{}", "1.0"], ["{}", "1e1"], ["{}", "262145"], ["{}", "99999999999999999999999999"]]) {
    await assert.rejects(createCookieWorkspaceClient({ fetch: async () => new Response(body, { headers: { "content-type": "application/json", "content-length": length } }) }).organizations(), safe("invalid_response"));
  }
});

test("malformed body errors and unknown shared error categories never expose thrown text", async () => {
  const badBody = new ReadableStream({ pull(controller) { controller.error(new Error("secret body payload")); } });
  await assert.rejects(createCookieWorkspaceClient({ fetch: async () => new Response(badBody, { headers: { "content-type": "application/json" } }) }).organizations(), safe("invalid_response"));
  const thrown = new SharedError("not_found"); thrown.code = "secret category"; thrown.message = "secret token";
  await assert.rejects(createCookieWorkspaceClient({ fetch: async () => { throw thrown; } }).organizations(), safe("unavailable"));
});

test("read limits account for empty chunks independently of byte limits", async () => {
  let pulls = 0; let canceled = false;
  const stream = new ReadableStream({ pull(c) { pulls++; c.enqueue(new Uint8Array()); }, cancel() { canceled = true; } });
  await assert.rejects(createCookieWorkspaceClient({ fetch: async () => new Response(stream, { headers: { "content-type": "application/json" } }) }).organizations(), safe("invalid_response"));
  assert.ok(pulls <= 4097); assert.equal(canceled, true); assert.equal(stream.locked, false);
});

test("mixed foreign and duplicate tenant project pages reject the entire result", async () => {
  for (const rows of [[...projects("mine").projects, ...projects("foreign").projects], [...projects("mine").projects, ...projects("mine").projects]]) {
    await assert.rejects(createCookieWorkspaceClient({ fetch: async () => response({ projects: rows, next_cursor: null }) }).projects("mine"), safe("invalid_response"));
  }
});

test("shared bearer adapter still resolves current token per request and omits browser credentials", async () => {
  let current = "first.synthetic"; const seen = [];
  const api = createWorkspaceClient({ apiOrigin: "https://api.example.invalid", accessToken: () => current, fetch: async (path, init) => {
    seen.push([path, init.credentials, init.headers.authorization]); return response(organizations);
  } });
  await api.organizations(); current = "second.synthetic"; await api.organizations();
  assert.deepEqual(seen, [["https://api.example.invalid/v3/orgs", "omit", "Bearer first.synthetic"], ["https://api.example.invalid/v3/orgs", "omit", "Bearer second.synthetic"]]);
});

test("late bearer resolution after cancellation cannot send private credential material", async () => {
  let release; let calls = 0; const controller = new AbortController();
  const api = createWorkspaceClient({ apiOrigin: "https://api.example.invalid", accessToken: () => new Promise(resolve => { release = resolve; }), fetch: async () => { calls++; return response(organizations); } });
  const pending = api.organizations({}, controller.signal); controller.abort();
  await assert.rejects(pending, safe("aborted")); release("late.synthetic"); await tick();
  assert.equal(calls, 0);
});
