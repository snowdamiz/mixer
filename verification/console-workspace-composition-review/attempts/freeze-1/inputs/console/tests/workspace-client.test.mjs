import assert from "node:assert/strict";
import { after, test } from "node:test";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createServer } from "node:http";

const root = fileURLToPath(new URL("..", import.meta.url));
const output = mkdtempSync(join(tmpdir(), "mixer-workspace-client-"));
after(() => rmSync(output, { recursive: true, force: true }));
try {
  execFileSync(process.execPath, [join(root, "node_modules/typescript/bin/tsc"),
    "src/api/workspace-client.ts", "--outDir", output, "--target", "ES2022", "--module", "ESNext",
    "--moduleResolution", "Bundler", "--strict", "--skipLibCheck", "--noUncheckedIndexedAccess",
    "--exactOptionalPropertyTypes"], { cwd: root, stdio: "pipe" });
} catch (error) { rmSync(output, { recursive: true, force: true }); throw error; }
writeFileSync(join(output, "package.json"), '{"type":"module"}\n');
const { createWorkspaceClient, WorkspaceClientError } = await import(pathToFileURL(join(output, "api/workspace-client.js")).href);
const page = { organizations: [{ id: "org", display_name: "FieldLog", organization_roles: ["owner"] }], next_cursor: null };
const response = (value = page, init = {}) => new Response(JSON.stringify(value), {
  headers: { "content-type": "application/json; charset=utf-8" }, ...init,
});
function client(fetch, extra = {}) {
  return createWorkspaceClient({ apiOrigin: "https://api.mixer.invalid", accessToken: () => "synthetic.token", fetch, ...extra });
}
const error = code => value => {
  assert.ok(value instanceof WorkspaceClientError);
  assert.equal(value.code, code);
  assert.equal(value.message, `Workspace request ${code}`);
  assert.deepEqual(Object.keys(value).sort(), ["code", "name"]);
  return true;
};

test("request uses fixed HTTPS origin, private header transport and immutable strict pages", async () => {
  const seen = [];
  const api = client(async (...args) => { seen.push(args); return response(); });
  const result = await api.organizations({ limit: 42, cursor: "opaque_09-A" });
  assert.deepEqual(result, page);
  assert.ok(Object.isFrozen(api)); assert.ok(Object.isFrozen(result.organizations[0].organization_roles));
  const [url, init] = seen[0];
  assert.equal(url, "https://api.mixer.invalid/v3/orgs?limit=42&cursor=opaque_09-A");
  assert.equal(init.method, "GET");
  assert.deepEqual(init.headers, { accept: "application/json", authorization: "Bearer synthetic.token" });
  for (const [key, value] of Object.entries({ credentials: "omit", redirect: "error", cache: "no-store", referrerPolicy: "no-referrer" })) assert.equal(init[key], value);
  assert.ok(init.signal instanceof AbortSignal);
  assert.equal(Object.hasOwn(init, "body"), false);
});

test("projects encode full Scope IDs once in query and reject foreign rows", async () => {
  for (const id of [".", "..", " /../+%2F北?&#=", " ", "é".repeat(64), "😀".repeat(32)]) {
    const api = client(async url => {
      assert.equal(url, `https://api.mixer.invalid/v3/projects?organization_id=${encodeURIComponent(id)}`);
      assert.equal(new URL(url).searchParams.get("organization_id"), id);
      return response({ projects: [{ organization_id: id, id: "p", display_name: null, roles: ["viewer"] }], next_cursor: null });
    });
    assert.equal((await api.projects(id)).projects[0].organization_id, id);
  }
  await assert.rejects(client(async () => response({ projects: [{ organization_id: "other", id: "p", display_name: null, roles: ["viewer"] }], next_cursor: null })).projects("org"), error("invalid_response"));
});

test("origin configuration is closed and insecure HTTP requires explicit loopback opt in", () => {
  for (const apiOrigin of ["", "/relative", "javascript:alert(1)", "http://api.mixer.invalid", "https://user:secret@api.mixer.invalid", "https://api.mixer.invalid/path", "https://api.mixer.invalid/?token=x", "https://api.mixer.invalid/#hash", "http://127.0.0.1", "http://localhost"]) {
    assert.throws(() => client(async () => response(), { apiOrigin }), error("invalid_request"));
  }
  for (const apiOrigin of ["http://127.0.0.1:8200", "http://localhost:8200", "http://[::1]:8200"]) {
    assert.ok(client(async () => response(), { apiOrigin, allowInsecureLoopback: true }));
  }
  assert.throws(() => client(async () => response(), { apiOrigin: "http://localhost.evil.invalid", allowInsecureLoopback: true }), error("invalid_request"));
  for (const timeoutMs of [0, -1, 30001, Infinity, 1.5]) assert.throws(() => client(async () => response(), { timeoutMs }), error("invalid_request"));
});

test("invalid request pages and identifiers stop before requesting a token or network", async () => {
  let calls = 0;
  const api = client(async () => { calls++; return response(); }, { accessToken: () => { calls++; return "token"; } });
  for (const value of [null, [], { limit: 0 }, { limit: 101 }, { limit: "3" }, { limit: undefined }, { cursor: "" }, { cursor: "a=" }, { cursor: "a".repeat(1401) }, { cursor: undefined }, { after: 1 }]) {
    await assert.rejects(api.organizations(value), error("invalid_request"));
  }
  for (const id of [null, undefined, "", "*", "x".repeat(129), "a\n", "\ud800"]) await assert.rejects(api.projects(id), error("invalid_request"));
  assert.equal(calls, 0);
});

test("every call resolves current session and invalid bearer material never reaches fetch", async () => {
  const tokens = [];
  let current = "first.token";
  const api = client(async (_, init) => { tokens.push(init.headers.authorization); return response(); }, { accessToken: () => current });
  await api.organizations(); current = "second.token"; await api.organizations();
  assert.deepEqual(tokens, ["Bearer first.token", "Bearer second.token"]);
  for (current of [null, "", "x".repeat(4090), "a b", "a\r\n", "é", "=a", "a=b", undefined]) await assert.rejects(api.organizations(), error("unauthenticated"));
  assert.equal(tokens.length, 2);
  current = "a".repeat(4089); await api.organizations(); assert.equal(tokens.length, 3);
});

test("HTTP errors and thrown provider/transport errors expose only fixed categories", async () => {
  for (const [status, code] of [[401, "unauthenticated"], [403, "permission_denied"], [404, "not_found"], [429, "unavailable"], [500, "unavailable"], [502, "unavailable"], [503, "unavailable"], [504, "unavailable"], [302, "invalid_response"], [201, "invalid_response"]]) {
    await assert.rejects(client(async () => new Response("private body secret", { status })).organizations(), error(code));
  }
  await assert.rejects(client(async () => { throw new Error("secret network URL"); }).organizations(), error("unavailable"));
  await assert.rejects(client(async () => response(), { accessToken: () => { throw new Error("private provider response"); } }).organizations(), error("unavailable"));
  for (const code of ["unavailable", "private-token-value"]) {
    const providerError = new WorkspaceClientError(code); providerError.message = "private provider response";
    await assert.rejects(client(async () => response(), { accessToken: () => { throw providerError; } }).organizations(), error("unavailable"));
  }
});

test("malformed media, UTF8, JSON, shape, overflow and redirect responses fail closed", async () => {
  for (const make of [
    () => new Response(JSON.stringify(page)),
    () => response(page, { headers: { "content-type": "application/json, text/html" } }),
    () => new Response(new Uint8Array([0xff]), { headers: { "content-type": "application/json" } }),
    () => new Response("{", { headers: { "content-type": "application/json" } }),
    () => response({ ...page, extra: "secret" }),
    () => response(page, { headers: { "content-type": "application/json", "content-length": "262145" } }),
    () => response(page, { headers: { "content-type": "application/json", "content-length": "invalid" } }),
    () => new Response(" ".repeat(262145), { headers: { "content-type": "application/json" } }),
    () => { const value = response(); Object.defineProperty(value, "redirected", { value: true }); return value; },
  ]) await assert.rejects(client(async () => make()).organizations(), error("invalid_response"));
});

test("streamed overflow and excessive empty chunks cancel bounded response readers", async () => {
  for (const body of ["overflow", "empty-chunks"]) {
    let reads = 0; let cancelled = false;
    const stream = new ReadableStream({
      pull(controller) { reads++; controller.enqueue(body === "overflow" ? new Uint8Array(65536).fill(32) : new Uint8Array()); },
      cancel() { cancelled = true; },
    });
    await assert.rejects(client(async () => new Response(stream, { headers: { "content-type": "application/json" } })).organizations(), error("invalid_response"));
    assert.equal(cancelled, true); assert.ok(reads <= (body === "overflow" ? 6 : 4097));
    assert.equal(stream.locked, false);
  }
});

test("timeout includes a stuck session provider and ignores its late token", async () => {
  let release; let fetches = 0;
  const api = client(async () => { fetches++; return response(); }, { timeoutMs: 15, accessToken: () => new Promise(resolve => { release = resolve; }) });
  await assert.rejects(api.organizations(), error("unavailable"));
  release("late.token"); await new Promise(resolve => setImmediate(resolve));
  assert.equal(fetches, 0);
});

test("deadline cancels a stalled body reader and returns no partial page", async () => {
  let cancelled = false;
  const stream = new ReadableStream({ start(controller) { controller.enqueue(new TextEncoder().encode('{"organizations":[')); }, cancel() { cancelled = true; } });
  await assert.rejects(client(async () => new Response(stream, { headers: { "content-type": "application/json" } }), { timeoutMs: 15 }).organizations(), error("unavailable"));
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(cancelled, true); assert.equal(stream.locked, false);
});

test("caller abort before and during request cancels old session work", async () => {
  const controller = new AbortController(); controller.abort(); let calls = 0;
  const api = client(async () => { calls++; return response(); });
  await assert.rejects(api.organizations({}, controller.signal), error("aborted")); assert.equal(calls, 0);
  const pending = new AbortController(); let release;
  const waiting = client(async () => { calls++; return response(); }, { accessToken: () => new Promise(resolve => { release = resolve; }) });
  const promise = waiting.organizations({}, pending.signal); pending.abort();
  await assert.rejects(promise, error("aborted")); release("old.token");
  await new Promise(resolve => setImmediate(resolve)); assert.equal(calls, 0);
});

test("actual loopback HTTP preserves encoded ID, bearer, page and cleanup", async () => {
  const seen = [];
  const server = createServer((req, res) => {
    seen.push({ url: req.url, authorization: req.headers.authorization, cookie: req.headers.cookie });
    const id = new URL(req.url, "http://localhost").searchParams.get("organization_id");
    res.writeHead(200, { "content-type": "application/json", "cache-control": "no-store" });
    res.end(JSON.stringify({ projects: [{ organization_id: id, id: "p", display_name: "FieldLog", roles: ["viewer"] }], next_cursor: null }));
  });
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  try {
    const api = createWorkspaceClient({ apiOrigin: `http://127.0.0.1:${server.address().port}`, allowInsecureLoopback: true, accessToken: () => "fixture.token" });
    const id = "../ north+%2F/北"; const result = await api.projects(id, { limit: 2 });
    assert.equal(result.projects[0].organization_id, id);
    assert.deepEqual(seen, [{ url: `/v3/projects?organization_id=${encodeURIComponent(id)}&limit=2`, authorization: "Bearer fixture.token", cookie: undefined }]);
  } finally {
    server.closeAllConnections(); await new Promise(resolve => server.close(resolve));
  }
  assert.equal(server.listening, false);
});
