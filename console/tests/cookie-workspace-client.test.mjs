import assert from "node:assert/strict";
import { after, test } from "node:test";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const output = mkdtempSync(join(tmpdir(), "mixer-cookie-workspace-client-"));
after(() => rmSync(output, { recursive: true, force: true }));
try {
  execFileSync(process.execPath, [join(root, "node_modules/typescript/bin/tsc"),
    "src/api/cookie-workspace-client.ts", "--outDir", output, "--target", "ES2022", "--module", "ESNext",
    "--moduleResolution", "Bundler", "--strict", "--skipLibCheck", "--noUncheckedIndexedAccess",
    "--exactOptionalPropertyTypes"], { cwd: root, stdio: "pipe" });
} catch (error) { rmSync(output, { recursive: true, force: true }); throw error; }
writeFileSync(join(output, "package.json"), '{"type":"module"}\n');
const { createCookieWorkspaceClient } = await import(pathToFileURL(join(output, "api/cookie-workspace-client.js")).href);
const { WorkspaceClientError: ExistingClientError } = await import(pathToFileURL(join(output, "api/workspace-client.js")).href);
const { WorkspaceClientError } = await import(pathToFileURL(join(output, "api/workspace-transport.js")).href);
const page = { organizations: [{ id: "org", display_name: "FieldLog", organization_roles: ["owner"] }], next_cursor: null };
const response = (value = page) => new Response(JSON.stringify(value), { headers: { "content-type": "application/json" } });
const error = code => value => {
  assert.ok(value instanceof ExistingClientError);
  assert.equal(value.code, code);
  assert.equal(value.message, `Workspace request ${code}`);
  assert.deepEqual(Object.keys(value).sort(), ["code", "name"]);
  return true;
};

test("cookie requests use only fixed same-origin routes and expose no credentials", async () => {
  const seen = [];
  const api = createCookieWorkspaceClient({ fetch: async (...args) => { seen.push(args); return response(); } });
  assert.equal(seen.length, 0);
  assert.equal(WorkspaceClientError, ExistingClientError);
  const result = await api.organizations({ limit: 42, cursor: "opaque_09-A" });
  assert.deepEqual(result, page);
  assert.ok(Object.isFrozen(api)); assert.ok(Object.isFrozen(result.organizations[0].organization_roles));
  assert.deepEqual(Object.keys(api).sort(), ["organizations", "projects"]);
  const [url, init] = seen[0];
  assert.equal(url, "/console-api/v1/orgs?limit=42&cursor=opaque_09-A");
  assert.deepEqual(init.headers, { accept: "application/json" });
  for (const [key, value] of Object.entries({ method: "GET", credentials: "same-origin", redirect: "error", cache: "no-store", referrerPolicy: "no-referrer" })) assert.equal(init[key], value);
  assert.ok(init.signal instanceof AbortSignal);
  assert.equal(Object.hasOwn(init, "body"), false);
});

test("untrusted identifiers cannot change destination and round trip exactly once", async () => {
  for (const id of ["https://evil.invalid", "//evil.invalid", " /../+%2F北?&#=", " ", ".", "..", "é".repeat(64), "😀".repeat(32)]) {
    const api = createCookieWorkspaceClient({ fetch: async url => {
      assert.equal(url, `/console-api/v1/projects?organization_id=${encodeURIComponent(id)}`);
      const target = new URL(url, "https://console.mixer.invalid/workspace");
      assert.equal(target.origin, "https://console.mixer.invalid");
      assert.equal(target.pathname, "/console-api/v1/projects");
      assert.equal(target.searchParams.get("organization_id"), id);
      return response({ projects: [{ organization_id: id, id: "p", display_name: null, roles: ["viewer"] }], next_cursor: null });
    } });
    assert.equal((await api.projects(id)).projects[0].organization_id, id);
  }
});

test("cookie adapter rejects destination, bearer, cookie and header configuration", () => {
  for (const options of [null, [], { apiOrigin: "https://evil.invalid" }, { accessToken: () => "secret" },
    { headers: { authorization: "Bearer secret" } }, { credentials: "include" }, { cookie: "secret" },
    { timeoutMs: 0 }, { timeoutMs: 30_001 }, { timeoutMs: 1.5 }, { fetch: "not a function" }]) {
    assert.throws(() => createCookieWorkspaceClient(options), error("invalid_request"));
  }
});

test("invalid page and identifier values fail before network access", async () => {
  let calls = 0;
  const api = createCookieWorkspaceClient({ fetch: async () => { calls++; return response(); } });
  for (const value of [null, [], { limit: 0 }, { limit: 101 }, { limit: "3" }, { limit: undefined },
    { cursor: "" }, { cursor: "a=" }, { cursor: "a".repeat(1401) }, { cursor: undefined }, { after: 1 }]) {
    await assert.rejects(api.organizations(value), error("invalid_request"));
  }
  for (const id of [null, undefined, "", "*", "x".repeat(129), "a\n", "\ud800"]) {
    await assert.rejects(api.projects(id), error("invalid_request"));
  }
  assert.equal(calls, 0);
});

test("authentication and server failures remain fixed safe categories", async () => {
  for (const [status, code] of [[401, "unauthenticated"], [403, "permission_denied"], [404, "not_found"],
    [429, "unavailable"], [500, "unavailable"], [502, "unavailable"], [503, "unavailable"], [504, "unavailable"],
    [302, "invalid_response"], [201, "invalid_response"]]) {
    const api = createCookieWorkspaceClient({ fetch: async () => new Response("private provider error", { status }) });
    await assert.rejects(api.organizations(), error(code));
  }
  for (const cause of [new Error("https://private.invalid?token=secret"), Object.assign(new WorkspaceClientError("unavailable"), { message: "secret" })]) {
    await assert.rejects(createCookieWorkspaceClient({ fetch: async () => { throw cause; } }).organizations(), error("unavailable"));
  }
});

test("unrelated tenant rows, invalid media, redirects and oversized responses fail closed", async () => {
  const foreign = { projects: [{ organization_id: "other", id: "p", display_name: null, roles: ["viewer"] }], next_cursor: null };
  for (const make of [
    () => response(foreign),
    () => new Response(JSON.stringify({ projects: [], next_cursor: null })),
    () => new Response(new Uint8Array([0xff]), { headers: { "content-type": "application/json" } }),
    () => new Response("{", { headers: { "content-type": "application/json" } }),
    () => new Response(" ".repeat(262145), { headers: { "content-type": "application/json" } }),
    () => new Response("{}", { headers: { "content-type": "application/json", "content-length": "262145" } }),
    () => { const value = response({ projects: [], next_cursor: null }); Object.defineProperty(value, "redirected", { value: true }); return value; },
  ]) await assert.rejects(createCookieWorkspaceClient({ fetch: async () => make() }).projects("org"), error("invalid_response"));
});

test("stream limits release readers even when cancellation never resolves", async () => {
  for (const kind of ["bytes", "empty-chunks"]) {
    let reads = 0; let cancelled = false;
    const stream = new ReadableStream({
      pull(controller) { reads++; controller.enqueue(new Uint8Array(kind === "bytes" ? 65536 : 0)); },
      cancel() { cancelled = true; return new Promise(() => {}); },
    });
    const api = createCookieWorkspaceClient({ fetch: async () => new Response(stream, { headers: { "content-type": "application/json" } }) });
    await assert.rejects(api.organizations(), error("invalid_response"));
    assert.equal(cancelled, true); assert.equal(stream.locked, false);
    assert.ok(reads <= (kind === "bytes" ? 6 : 4097));
  }
});

test("pre-aborted requests do not invoke fetch", async () => {
  let calls = 0;
  const controller = new AbortController(); controller.abort();
  await assert.rejects(createCookieWorkspaceClient({ fetch: async () => { calls++; return response(); } }).organizations({}, controller.signal), error("aborted"));
  assert.equal(calls, 0);
});

test("abort and deadline settle noncooperative fetch and cancel its late body", async () => {
  for (const kind of ["abort", "deadline"]) {
    const controller = new AbortController(); let release; let cancelled = false;
    const api = createCookieWorkspaceClient({ timeoutMs: kind === "deadline" ? 15 : 1000,
      fetch: () => new Promise(resolve => { release = resolve; }) });
    const pending = api.organizations({}, controller.signal);
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(typeof release, "function");
    if (kind === "abort") controller.abort();
    await assert.rejects(pending, error(kind === "abort" ? "aborted" : "unavailable"));
    release(new Response(new ReadableStream({ cancel() { cancelled = true; } }), { headers: { "content-type": "application/json" } }));
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(cancelled, true);
  }
});

test("body deadline cancels a stuck reader and releases the stream", async () => {
  let cancelled = false;
  const stream = new ReadableStream({ cancel() { cancelled = true; } });
  const api = createCookieWorkspaceClient({ timeoutMs: 15,
    fetch: async () => new Response(stream, { headers: { "content-type": "application/json" } }) });
  await assert.rejects(api.organizations(), error("unavailable"));
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(cancelled, true); assert.equal(stream.locked, false);
});

test("each request reaches the session boundary afresh and never caches old account data", async () => {
  let current = page;
  const api = createCookieWorkspaceClient({ fetch: async () => current ? response(current) : new Response(null, { status: 401 }) });
  const old = await api.organizations();
  current = null;
  await assert.rejects(api.organizations(), error("unauthenticated"));
  current = { organizations: [{ id: "new", display_name: null, organization_roles: ["viewer"] }], next_cursor: null };
  assert.equal((await api.organizations()).organizations[0].id, "new");
  assert.equal(old.organizations[0].id, "org");
});

test("real host HTTP round trip preserves routes, scoped query and safe error mapping", async () => {
  const requests = [];
  const organization = " /../+%2F北?&#=";
  const server = createServer((request, reply) => {
    requests.push({ method: request.method, url: request.url, authorization: request.headers.authorization, accept: request.headers.accept });
    const url = new URL(request.url, "http://localhost");
    reply.setHeader("content-type", "application/json");
    if (url.pathname === "/console-api/v1/orgs") return reply.end(JSON.stringify(page));
    if (url.searchParams.get("cursor") === "expired") { reply.statusCode = 401; return reply.end('private session failure'); }
    assert.equal(url.searchParams.get("organization_id"), organization);
    reply.end(JSON.stringify({ projects: [{ organization_id: organization, id: "p", display_name: null, roles: ["viewer"] }], next_cursor: null }));
  });
  try {
    await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
    const base = `http://127.0.0.1:${server.address().port}`;
    const api = createCookieWorkspaceClient({ fetch: (path, init) => {
      assert.equal(init.credentials, "same-origin");
      return globalThis.fetch(new URL(path, base), init);
    } });
    assert.deepEqual(await api.organizations({ limit: 1 }), page);
    assert.equal((await api.projects(organization)).projects[0].id, "p");
    await assert.rejects(api.projects(organization, { cursor: "expired" }), error("unauthenticated"));
    assert.equal(requests.length, 3);
    assert.equal(requests[0].url, "/console-api/v1/orgs?limit=1");
    for (const request of requests) {
      assert.equal(request.method, "GET"); assert.equal(request.authorization, undefined); assert.equal(request.accept, "application/json");
    }
  } finally {
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
  }
});
