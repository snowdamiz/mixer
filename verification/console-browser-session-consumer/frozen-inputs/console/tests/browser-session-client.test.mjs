import assert from "node:assert/strict";
import { after, test } from "node:test";
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { join } from "node:path";

const root = fileURLToPath(new URL("../", import.meta.url));
const cache = join(root, "node_modules/.cache");
mkdirSync(cache, { recursive: true });
const output = mkdtempSync(join(cache, "mixer-browser-session-client-"));
after(() => { rmSync(output, { recursive: true, force: true }); assert.equal(existsSync(output), false); });
try {
  execFileSync(process.execPath, [join(root, "node_modules/typescript/bin/tsc"), "src/api/browser-session-client.ts",
    "--target", "ES2022", "--module", "ESNext", "--moduleResolution", "Bundler", "--strict", "--skipLibCheck",
    "--noUncheckedIndexedAccess", "--exactOptionalPropertyTypes", "--outDir", output], { cwd: root, stdio: "pipe", timeout: 15000 });
} catch (error) {
  if (error.stdout) process.stderr.write(error.stdout);
  if (error.stderr) process.stderr.write(error.stderr);
  rmSync(output, { recursive: true, force: true }); throw error;
}
writeFileSync(join(output, "package.json"), '{"type":"module"}\n');
const { createBrowserSessionClient, BrowserSessionClientError } = await import(pathToFileURL(join(output, "browser-session-client.js")));
const csrf = "A".repeat(43), generation = "B".repeat(42) + "A";
const signedOut = { state: "unauthenticated", csrf_token: csrf };
const signedIn = { state: "authenticated", generation, expires_at: 2000000000, csrf_token: csrf };
const response = (text = JSON.stringify(signedIn), headers = {}) => new Response(text, {
  headers: { "content-type": "application/json", "cache-control": "no-store", ...headers },
});
const error = code => value => value instanceof BrowserSessionClientError && value.code === code && value.message === `Browser session ${code}` && !value.cause;
const read = value => createBrowserSessionClient({ fetch: async () => value }).read();
const flush = () => new Promise(resolve => setImmediate(resolve));
const deferred = () => { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };

test("only the two closed immutable scalar envelopes are admitted", async () => {
  for (const value of [signedIn, signedOut]) {
    const api = createBrowserSessionClient({ fetch: async () => response(JSON.stringify(value)) });
    assert.ok(Object.isFrozen(api)); assert.deepEqual(Reflect.ownKeys(api), ["read"]);
    const metadata = await api.read();
    assert.deepEqual(metadata, value); assert.ok(Object.isFrozen(metadata));
    assert.notEqual(metadata, value);
  }
  assert.deepEqual(await read(response(` \r\n{ "csrf_token" : "${csrf}",\t"expires_at":0,"generation":"${generation}","state":"authenticated" } `)), { ...signedIn, expires_at: 0 });
});

test("fixed request carries only the cookie transport policy and one owned abort signal", async () => {
  let called = 0;
  await createBrowserSessionClient({ fetch: async (url, init) => {
    called++; assert.equal(url, "/auth/session");
    assert.deepEqual(Object.keys(init).sort(), ["cache", "credentials", "headers", "method", "redirect", "referrerPolicy", "signal"]);
    assert.deepEqual({ ...init, signal: undefined }, { method: "GET", headers: { accept: "application/json" }, credentials: "same-origin",
      redirect: "error", cache: "no-store", referrerPolicy: "no-referrer", signal: undefined });
    assert.ok(init.signal instanceof AbortSignal);
    return response();
  } }).read();
  assert.equal(called, 1);
});

test("construction rejects all wider authority and invalid options with fixed text", () => {
  const values = [null, [], 1, "x", { token: csrf }, { fetch: undefined }, { timeoutMs: undefined }, { fetch: false },
    ...[0, -1, 30001, 1.5, NaN, Infinity, "10"].map(timeoutMs => ({ timeoutMs })), { [Symbol("private")]: 1 },
    Object.defineProperty({}, "session", { value: signedIn }), { get fetch() { throw Error(csrf); } }];
  for (const value of values) assert.throws(() => createBrowserSessionClient(value), error("invalid_request"));
});

test("strict parser rejects duplicates, escaped aliases, nested/extra values and noncanonical numbers", async () => {
  const valid = JSON.stringify(signedIn);
  const bodies = ["null", "[]", "{}", valid + " false", "\ufeff" + valid,
    valid.replace('"authenticated"', '"auth\\u0065nticated"'), valid.replace('"state"', '"st\\u0061te"'),
    valid.replace('"state":', '"state":"authenticated","state":'), valid.replace('"generation":', '"generation":"' + generation + '","generation":'),
    valid.replace('"csrf_token":', '"extra":null,"csrf_token":'), valid.replace('"csrf_token":', '"extra":{},"csrf_token":'),
    valid.replace('"csrf_token":', '"extra":[],"csrf_token":'), valid.replace('"expires_at":2000000000,', ''),
    JSON.stringify({ ...signedOut, generation }), JSON.stringify({ ...signedIn, identity: "private" }),
    ...["-0", "-1", "1.0", "1e3", "01", "9007199254740992", '"12"', "null", "false"].map(token => valid.replace("2000000000", token)),
    valid.replace(/}$/, ",}"), valid.replace(/}$/, ""), valid.replace('"state"', '"stâte"')];
  for (const body of bodies) await assert.rejects(read(response(body)), error("invalid_response"), body.slice(0, 80));
});

test("canonical43 rejects padding, wrong length, alphabet and unused trailing bits", async () => {
  for (const field of ["generation", "csrf_token"]) for (const token of ["A".repeat(42), "A".repeat(44), "A".repeat(42) + "B", "A".repeat(42) + "=", "+".repeat(43), "_".repeat(43), " ".repeat(43)]) {
    await assert.rejects(read(response(JSON.stringify({ ...signedIn, [field]: token }))), error("invalid_response"));
  }
  for (const tail of ["A", "E", "I", "M", "Q", "U", "Y", "c", "g", "k", "o", "s", "w", "0", "4", "8"]) {
    const value = { ...signedIn, csrf_token: "_".repeat(42) + tail };
    assert.deepEqual(await read(response(JSON.stringify(value))), value);
  }
});

test("non200 and a200HTML fallback never imply signed out or expose body text", async () => {
  for (const status of [204, 301, 401, 403, 404, 429, 500, 599]) {
    let cancelled = false;
    const body = status === 204 ? null : new ReadableStream({ cancel() { cancelled = true; return new Promise(() => {}); } });
    await assert.rejects(read(new Response(body, { status })), error("unavailable"));
    if (body) assert.equal(cancelled, true);
  }
  await assert.rejects(read(response("<html>static fallback private</html>", { "content-type": "text/html" })), error("invalid_response"));
  await assert.rejects(createBrowserSessionClient({ fetch: async () => { throw Error(csrf); } }).read(), error("unavailable"));
});

test("content type, response redirects and complete no-store directives fail closed", async () => {
  for (const headers of [
    { "content-type": "text/json" }, { "content-type": "application/json; charset=utf8" }, { "content-type": "application/json; charset=utf-8; x=y" },
    { "content-type": "application/json, text/html" }, { "content-type": "" },
    ...["", "no-cache", "x-no-store", 'private="no-store"', "no-store private", "no-store,", ",no-store", "no-store=yes", "no-store, bad=", 'no-store, private="unterminated', "no-store;private"].map(value => ({ "cache-control": value })),
  ]) await assert.rejects(read(response(undefined, headers)), error("invalid_response"));
  const redirected = response(); Object.defineProperty(redirected, "redirected", { value: true });
  await assert.rejects(read(redirected), error("invalid_response"));
  for (const value of ["no-store", "private, no-store", 'private="a,b", NO-STORE', "\t no-store \t, max-age=0", 'other="a\\\"b", no-store']) {
    assert.deepEqual(await read(response(undefined, { "cache-control": value, "content-type": "APPLICATION/JSON ; CHARSET = UTF-8 " })), signedIn);
  }
});

test("Content-Length is canonical bounded advisory text, independent of actual bytes", async () => {
  for (const length of ["01", "+1", "-1", "1.0", "1e3", "8193", "1, 2", "9007199254740992", ""]) {
    let pulled = 0;
    const item = response(undefined, { "content-length": length });
    Object.defineProperty(item, "body", { value: { cancel: async () => {}, getReader() { pulled++; throw Error("must not read"); } } });
    await assert.rejects(read(item), error("invalid_response")); assert.equal(pulled, 0);
  }
  assert.deepEqual(await read(response(undefined, { "content-length": "0" })), signedIn);
  assert.deepEqual(await read(response(undefined, { "content-length": "8192" })), signedIn);
  await assert.rejects(read(response(" ".repeat(4097), { "content-length": "0" })), error("invalid_response"));
});

test("fatal UTF8, BOM, missing stream, 4KiB total and 4096 read ceiling are enforced", async () => {
  for (const bytes of [Uint8Array.of(0xff), Uint8Array.of(0xc0, 0xaf), Uint8Array.of(0xef, 0xbb, 0xbf, 0x7b, 0x7d)]) {
    await assert.rejects(read(response(bytes)), error("invalid_response"));
  }
  await assert.rejects(read(response(null)), error("invalid_response"));
  const text = JSON.stringify(signedIn);
  assert.deepEqual(await read(response(text + " ".repeat(4096 - Buffer.byteLength(text)))), signedIn);
  await assert.rejects(read(response(text + " ".repeat(4097 - Buffer.byteLength(text)))), error("invalid_response"));
  let reads = 0, cancelled = 0, released = 0;
  const item = response();
  Object.defineProperty(item, "body", { value: { getReader() { return {
    read: async () => { reads++; return { done: false, value: new Uint8Array() }; },
    cancel: async () => { cancelled++; }, releaseLock: () => { released++; },
  }; } } });
  await assert.rejects(read(item), error("invalid_response"));
  assert.equal(reads, 4096); assert.equal(cancelled, 1); assert.equal(released, 1);
});

test("stream chunks are copied and a split strict UTF8 body cannot widen the grammar", async () => {
  const bytes = new TextEncoder().encode(JSON.stringify(signedIn));
  let position = 0;
  const stream = new ReadableStream({ pull(controller) { if (position < bytes.length) controller.enqueue(bytes.slice(position, ++position)); else controller.close(); } });
  assert.deepEqual(await read(response(stream)), signedIn);
});

test("noncooperative fetch cancellation and deadline finish and cancel a late response", async () => {
  for (const mode of ["abort", "timeout"]) {
    const pending = deferred(), caller = new AbortController(); let signal, cancelled = 0;
    const api = createBrowserSessionClient({ timeoutMs: 12, fetch: (_path, init) => { signal = init.signal; return pending.promise; } });
    const operation = api.read(caller.signal);
    if (mode === "abort") caller.abort();
    await assert.rejects(operation, error(mode === "abort" ? "aborted" : "unavailable"));
    assert.equal(signal.aborted, true);
    pending.resolve(response(new ReadableStream({ cancel() { cancelled++; return new Promise(() => {}); } })));
    await flush(); assert.equal(cancelled, 1);
  }
  let calls = 0; const controller = new AbortController(); controller.abort();
  await assert.rejects(createBrowserSessionClient({ fetch: async () => { calls++; return response(); } }).read(controller.signal), error("aborted"));
  assert.equal(calls, 0);
});

test("noncooperative read and cancel do not retain the operation or reader lock", async () => {
  for (const mode of ["abort", "timeout"]) {
    const pending = deferred(), caller = new AbortController(); let released = 0, cancelled = 0;
    const item = response();
    Object.defineProperty(item, "body", { value: { getReader() { return {
      read: () => pending.promise, cancel: () => { cancelled++; return new Promise(() => {}); }, releaseLock: () => { released++; },
    }; } } });
    const operation = createBrowserSessionClient({ timeoutMs: 12, fetch: async () => item }).read(caller.signal);
    await flush(); if (mode === "abort") caller.abort();
    await assert.rejects(operation, error(mode === "abort" ? "aborted" : "unavailable"));
    assert.equal(cancelled, 1); assert.equal(released, 1);
    pending.reject(Error("private late stream rejection")); await flush();
  }
});

test("one absolute deadline spans fetch, body and synchronous decode publication", async () => {
  const descriptor = Object.getOwnPropertyDescriptor(globalThis, "performance");
  let now = 0;
  Object.defineProperty(globalThis, "performance", { configurable: true, value: { now: () => now } });
  try {
    const item = response(); const original = item.body.getReader.bind(item.body);
    Object.defineProperty(item.body, "getReader", { value() {
      const reader = original();
      return { read: async () => { now = 16; return reader.read(); }, cancel: () => reader.cancel(), releaseLock: () => reader.releaseLock() };
    } });
    await assert.rejects(createBrowserSessionClient({ timeoutMs: 15, fetch: async () => { now = 8; return item; } }).read(), error("unavailable"));
  } finally { Object.defineProperty(globalThis, "performance", descriptor); }
});

test("timers and caller listeners are released after success and malformed response", async () => {
  for (const result of [response(), response("private malformed")]) {
    const caller = new AbortController(); let added = 0, removed = 0;
    const add = caller.signal.addEventListener.bind(caller.signal), remove = caller.signal.removeEventListener.bind(caller.signal);
    caller.signal.addEventListener = (...args) => { added++; return add(...args); };
    caller.signal.removeEventListener = (...args) => { removed++; return remove(...args); };
    await createBrowserSessionClient({ fetch: async () => result }).read(caller.signal).catch(() => {});
    assert.equal(added, 1); assert.equal(removed, 1);
  }
});
