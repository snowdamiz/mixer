import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";
import { fileURLToPath } from "node:url";

export const own = fileURLToPath(new URL("./", import.meta.url));
export const root = fileURLToPath(new URL("../../", import.meta.url));
export const moduleURL = path => new URL(`./scratch/modules/${path}.js`, import.meta.url).href;
export const solidURL = pathToFileURL(root + "console/node_modules/solid-js/dist/solid.js").href;
export const wall0 = 1700000000000;
export const csrf = Buffer.alloc(32, 0x13).toString("base64url");
export const generation = Buffer.alloc(32, 0xa7).toString("base64url");
export const generation2 = Buffer.alloc(32, 0x51).toString("base64url");
export const auth = (change = {}) => ({ state: "authenticated", generation, expires_at: wall0 / 1000 + 90, csrf_token: csrf, ...change });
export const unauth = () => ({ state: "unauthenticated", csrf_token: csrf });
export const orgs = { organizations: [{ id: "org α", display_name: "Independent private studio", organization_roles: ["owner"] }], next_cursor: "NEXT" };
export const projects = { projects: [{ organization_id: "org α", id: "project β", display_name: "Independent private project", roles: ["viewer"] }], next_cursor: "MORE" };
export const tick = () => new Promise(resolve => setImmediate(resolve));
export const deferred = () => { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };
export const json = (value, headers = {}) => new Response(typeof value === "string" ? value : JSON.stringify(value), { headers: { "content-type": "application/json", "cache-control": "no-store", ...headers } });
export function api() { const calls = []; return { calls, fetch(path, init) { const value = { path, init, ...deferred() }; calls.push(value); return value.promise; } }; }
export function code(type, category) { return error => error instanceof type && error.code === category && error.message.endsWith(` ${category}`); }
export async function ready(controller, server, value = auth()) {
  controller.revalidate();
  assert.equal(controller.getSession().kind, "unavailable");
  assert.equal(server.calls.at(-1).path, "/auth/session");
  server.calls.at(-1).resolve(json(value));
  await tick();
  assert.equal(controller.getSession().kind, "ready");
  return controller.getSession();
}
export function wire({ text = JSON.stringify(unauth()), chunks, status = 200, redirected = false, headers = {}, read, cancel, release } = {}) {
  const state = { reads: 0, cancels: 0, releases: 0, bodyCancels: 0 };
  const data = chunks ?? [new TextEncoder().encode(text)];
  const reader = {
    read() { const index = state.reads++; return read ? read(index) : Promise.resolve(index < data.length ? { done: false, value: data[index] } : { done: true }); },
    cancel() { state.cancels++; return cancel ? cancel() : Promise.resolve(); },
    releaseLock() { state.releases++; if (release) release(); },
  };
  const fields = { "content-type": "application/json", "cache-control": "no-store", ...headers };
  return { state, response: { status, redirected, headers: { get: key => Object.hasOwn(fields, key) ? fields[key] : null }, body: {
    getReader() { return reader; }, cancel() { state.bodyCancels++; return cancel ? cancel() : Promise.resolve(); },
  } } };
}
export async function clocked(run) {
  const descriptor = Object.getOwnPropertyDescriptor(globalThis, "performance");
  const priorDate = Date.now, priorSet = globalThis.setTimeout, priorClear = globalThis.clearTimeout;
  const time = { wall: wall0, mono: 12.5 }, timers = new Set();
  Date.now = () => time.wall;
  Object.defineProperty(globalThis, "performance", { configurable: true, value: { now: () => time.mono } });
  globalThis.setTimeout = (callback, delay, ...args) => { let handle; handle = priorSet(() => { timers.delete(handle); callback(...args); }, delay); timers.add(handle); return handle; };
  globalThis.clearTimeout = handle => { timers.delete(handle); return priorClear(handle); };
  try { return await run(time, timers); }
  finally {
    const leaked = timers.size;
    for (const handle of timers) priorClear(handle);
    Date.now = priorDate; Object.defineProperty(globalThis, "performance", descriptor);
    globalThis.setTimeout = priorSet; globalThis.clearTimeout = priorClear;
    assert.equal(leaked, 0, "all owned timers cleaned before host globals restored");
  }
}
export class Target extends EventTarget {
  listeners = new Map();
  addEventListener(type, listener, options) { super.addEventListener(type, listener, options); if (!this.listeners.has(type)) this.listeners.set(type, new Set()); this.listeners.get(type).add(listener); }
  removeEventListener(type, listener, options) { super.removeEventListener(type, listener, options); this.listeners.get(type)?.delete(listener); }
  get count() { return [...this.listeners.values()].reduce((sum, items) => sum + items.size, 0); }
}
