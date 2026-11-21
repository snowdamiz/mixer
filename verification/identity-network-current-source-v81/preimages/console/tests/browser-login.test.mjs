import assert from "node:assert/strict";
import { after, test } from "node:test";
import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { join } from "node:path";
const root = fileURLToPath(new URL("../", import.meta.url));
mkdirSync(join(root, "node_modules/.cache"), { recursive: true });
const output = mkdtempSync(join(root, "node_modules/.cache/signin-"));
after(() => rmSync(output, { recursive: true, force: true }));
execFileSync(process.execPath, [join(root, "node_modules/typescript/bin/tsc"), "src/api/browser-login-client.ts", "src/state/sign-in-action.ts",
  "--target", "ES2022", "--module", "ESNext", "--moduleResolution", "Bundler", "--strict", "--skipLibCheck",
  "--noUncheckedIndexedAccess", "--exactOptionalPropertyTypes", "--outDir", output], { cwd: root, timeout: 15000 });
writeFileSync(join(output, "package.json"), '{"type":"module"}');
const { createBrowserLoginClient, BrowserLoginError } = await import(pathToFileURL(join(output, "api/browser-login-client.js")));
const { createSignInAction } = await import(pathToFileURL(join(output, "state/sign-in-action.js")));
const csrf = "A".repeat(43);
const url = "https://issuer.fixture.invalid/authorize?state=private";
const wire = () => ({ authorization_url: url, expires_at: Math.floor(Date.now() / 1000) + 60 });
const response = (text = JSON.stringify(wire()), headers = {}) => new Response(text, { headers: {
  "content-type": "application/json; charset=utf-8", "cache-control": "no-store", "referrer-policy": "no-referrer", ...headers } });
const metadata = () => new Response(JSON.stringify({ state: "unauthenticated", csrf_token: csrf }), { headers: { "content-type": "application/json", "cache-control": "no-store" } });
const signal = () => new AbortController().signal;
const invalid = e => e instanceof BrowserLoginError && e.message === "Sign in is unavailable. Try again." && !e.cause;
const clientFor = reply => createBrowserLoginClient({ fetch: async path => path === "/auth/session" ? metadata() : reply });
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };

test("fresh metadata then fixed empty POST, trusted JSON URL and exact browser policy", async () => {
  const calls = [];
  const client = createBrowserLoginClient({ fetch: async (path, init) => {
    calls.push({ path, init }); return path === "/auth/session" ? metadata() : response();
  } });
  assert.equal(await client.begin(signal()), url);
  assert.deepEqual(calls.map(c => c.path), ["/auth/session", "/auth/login"]);
  const post = calls[1].init;
  assert.deepEqual({ ...post, signal: undefined }, { method: "POST", credentials: "same-origin", headers: { accept: "application/json", "x-mixer-csrf": csrf }, cache: "no-store", redirect: "error", referrerPolicy: "no-referrer", signal: undefined });
});

test("reject duplicate, unknown, escaped-key, missing, oversized, expired and unsafe URL envelopes", async () => {
  const valid = JSON.stringify(wire());
  for (const text of [valid.replace("}", ',"expires_at":2000000000}'), valid.replace("}", ',"unknown":1}'),
    valid.replace('"expires_at"', '"expires\\u005fat"'), "{}", "[]", valid + "x", valid.replace('"authorization_url"', '"return_to"'),
    JSON.stringify({ ...wire(), expires_at: -1 }), JSON.stringify({ ...wire(), expires_at: 1 }),
    JSON.stringify({ ...wire(), expires_at: 9007199254740992 }), JSON.stringify({ ...wire(), expires_at: "2000000000" }),
    ...["http://issuer.invalid", "javascript:alert(1)", "https://user:password@issuer.invalid", "https://issuer.invalid/#", "https://issuer.invalid/#x", "https://issuer.invalid/" + "x".repeat(8192)].map(authorization_url => JSON.stringify({ ...wire(), authorization_url })),
    " ".repeat(16385) + valid]) await assert.rejects(clientFor(response(text)).begin(signal()), invalid);
});

test("reject redirects, absent safety headers, location, invalid UTF8 and body overflow", async () => {
  for (const reply of [response(undefined, { "content-type": "text/html" }), response(undefined, { "cache-control": "public" }),
    response(undefined, { "referrer-policy": "origin" }), response(undefined, { location: url }), response(undefined, { "content-length": "16385" }),
    new Response(null, { status: 303 }), response(new Uint8Array([255]))]) await assert.rejects(clientFor(reply).begin(signal()), invalid);
});

test("one total deadline covers metadata, fetch and an uncooperative body; abort never POSTs", async () => {
  for (const phase of ["metadata", "post", "body"]) {
    const calls = [];
    const client = createBrowserLoginClient({ timeoutMs: 15, fetch: async path => {
      calls.push(path);
      if (phase === "metadata" || (phase === "post" && path === "/auth/login")) return new Promise(() => {});
      return path === "/auth/session" ? metadata() : response(new ReadableStream({ start() {} }));
    } });
    await assert.rejects(client.begin(signal()), invalid);
    assert.equal(calls.length, phase === "metadata" ? 1 : 2);
  }
  const abort = new AbortController(); abort.abort(); let count = 0;
  await assert.rejects(createBrowserLoginClient({ fetch: async () => { count++; return metadata(); } }).begin(abort.signal), invalid);
  assert.equal(count, 0);
});

test("authenticated metadata cannot create a login and all dependency errors remain fixed", async () => {
  let calls = 0;
  const client = createBrowserLoginClient({ fetch: async () => { calls++; throw Error("secret provider payload"); } });
  await assert.rejects(client.begin(signal()), invalid); assert.equal(calls, 1);
});

test("pending suppresses double click, failures retry fresh, cancellation and disposal fence stale navigation", async () => {
  for (const stop of ["cancel", "dispose", "hidden"]) {
    let foreground = true, requests = 0, invalidations = 0; const navigations = [], states = [], pending = deferred();
    const action = createSignInAction({ allowed: () => true, foreground: () => foreground, invalidate: () => invalidations++, navigate: value => navigations.push(value), changed: value => states.push(value), client: { begin: async () => { requests++; return pending.promise; } } });
    const work = action.start(); await action.start(); assert.equal(requests, 1); assert.equal(invalidations, 1); assert.equal(states.at(-1).kind, "starting");
    if (stop === "hidden") foreground = false; else action[stop]();
    pending.resolve(url); await work; assert.deepEqual(navigations, []);
  }
  let attempts = 0; const states = [], nav = [];
  const action = createSignInAction({ allowed: () => true, foreground: () => true, invalidate() {}, changed: state => states.push(state), navigate: value => nav.push(value), client: { begin: async () => { if (++attempts === 1) throw Error("private"); return url; } } });
  await action.start(); assert.equal(states.at(-1).kind, "unavailable"); await action.start(); assert.equal(attempts, 2); assert.deepEqual(nav, [url]);
});
