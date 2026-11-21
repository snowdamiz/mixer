import { createBrowserSessionClient } from "./browser-session-client.js";

export class BrowserLoginError extends Error {
  constructor() { super("Sign in is unavailable. Try again."); this.name = "BrowserLoginError"; }
}
const fail = (): never => { throw new BrowserLoginError(); };

/** Two scalar fields, with duplicate detection before JSON projection. */
function authorization(text: string): string {
  const match = /^\s*\{\s*"(authorization_url|expires_at)"\s*:\s*("(?:[^"\\\x00-\x1f]|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))*"|[1-9][0-9]*)\s*,\s*"(authorization_url|expires_at)"\s*:\s*("(?:[^"\\\x00-\x1f]|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))*"|[1-9][0-9]*)\s*\}\s*$/u.exec(text);
  if (!match || match[1] === match[3]) return fail();
  const value: unknown = JSON.parse(text);
  if (!value || typeof value !== "object" || !("authorization_url" in value) || !("expires_at" in value)) return fail();
  const url = value.authorization_url, expires = value.expires_at;
  if (typeof url !== "string" || new TextEncoder().encode(url).length > 8192 ||
    typeof expires !== "number" || !Number.isSafeInteger(expires) || expires <= Date.now() / 1000) return fail();
  const parsed = new URL(url);
  if (parsed.protocol !== "https:" || !parsed.hostname || parsed.username || parsed.password || parsed.hash ||
    url.includes("#") || /[\s\u0000-\u001f\u007f]/u.test(url)) return fail();
  return parsed.href;
}

/** The action alone owns fresh CSRF; the read-only session controller never sees it. */
export function createBrowserLoginClient(options: { readonly fetch?: typeof globalThis.fetch; readonly timeoutMs?: number } = {}) {
  const fetchRequest = options.fetch ?? globalThis.fetch;
  const timeoutMs = options.timeoutMs ?? 15000;
  if (typeof fetchRequest !== "function" || !Number.isInteger(timeoutMs) || timeoutMs < 1 || timeoutMs > 15000) return fail();
  return Object.freeze({ async begin(signal: AbortSignal): Promise<string> {
    const controller = new AbortController();
    const deadline = performance.now() + timeoutMs;
    const check = () => { if (signal.aborted || controller.signal.aborted || performance.now() >= deadline) return fail(); };
    const abort = () => controller.abort();
    signal.addEventListener("abort", abort, { once: true });
    let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
    let rejectAbort: (() => void) | undefined;
    const stopped = new Promise<never>((_, reject) => {
      rejectAbort = () => reject(new BrowserLoginError());
      controller.signal.addEventListener("abort", rejectAbort, { once: true });
    });
    const timer = setTimeout(abort, timeoutMs);
    const perform = async () => {
      check();
      const metadata = await createBrowserSessionClient({ fetch: fetchRequest, timeoutMs }).read(controller.signal);
      check();
      if (metadata.state !== "unauthenticated") return fail();
      const response = await fetchRequest("/auth/login", { method: "POST", credentials: "same-origin",
        headers: { accept: "application/json", "x-mixer-csrf": metadata.csrf_token },
        cache: "no-store", redirect: "error", referrerPolicy: "no-referrer", signal: controller.signal });
      if (controller.signal.aborted || signal.aborted) { void response.body?.cancel().catch(() => undefined); return fail(); }
      check();
      reader = response.body?.getReader();
      if (response.status !== 200 || response.redirected || response.headers.has("location") || !reader ||
        response.headers.get("content-type")?.toLowerCase() !== "application/json; charset=utf-8" ||
        response.headers.get("cache-control") !== "no-store" || response.headers.get("referrer-policy") !== "no-referrer") return fail();
      const length = response.headers.get("content-length");
      if (length !== null && (!/^(?:0|[1-9][0-9]*)$/u.test(length) || Number(length) > 16384)) return fail();
      const chunks: Uint8Array[] = [];
      let size = 0, reads = 0;
      while (true) {
        check();
        if (++reads > 4096) return fail();
        const item = await reader.read(); check();
        if (item.done) break;
        if (!(item.value instanceof Uint8Array)) return fail();
        size += item.value.byteLength;
        if (size > 16384) return fail();
        chunks.push(item.value.slice());
      }
      const bytes = new Uint8Array(size); let offset = 0;
      for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
      const result = authorization(new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(bytes));
      check(); return result;
    };
    try { return await Promise.race([perform(), stopped]); }
    catch { return fail(); }
    finally {
      clearTimeout(timer); controller.abort(); signal.removeEventListener("abort", abort);
      if (rejectAbort) controller.signal.removeEventListener("abort", rejectAbort);
      try { void reader?.cancel().catch(() => undefined); } catch { /* Bounded cleanup. */ }
      try { reader?.releaseLock(); } catch { /* A pending reader cannot extend the action. */ }
    }
  } });
}
