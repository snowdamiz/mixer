export type BrowserSessionFailure = "invalid_request" | "invalid_response" | "unavailable" | "aborted";
export type BrowserSessionMetadata =
  | Readonly<{ state: "unauthenticated"; csrf_token: string }>
  | Readonly<{ state: "authenticated"; generation: string; expires_at: number; csrf_token: string }>;
export interface BrowserSessionClientOptions {
  readonly fetch?: typeof globalThis.fetch;
  readonly timeoutMs?: number;
}

/** Closed public failures never inherit a dependency's text or cause. */
export class BrowserSessionClientError extends Error {
  readonly code: BrowserSessionFailure;
  constructor(code: BrowserSessionFailure) {
    if (!["invalid_request", "invalid_response", "unavailable", "aborted"].includes(code)) code = "unavailable";
    super(`Browser session ${code}`);
    this.name = "BrowserSessionClientError";
    this.code = code;
  }
}
const fail = (code: BrowserSessionFailure): never => { throw new BrowserSessionClientError(code); };

function canonical43(value: string): boolean {
  if (!/^[A-Za-z0-9_-]{43}$/u.test(value)) return false;
  const bytes = atob(value.replace(/-/gu, "+").replace(/_/gu, "/") + "=");
  return bytes.length === 32 && btoa(bytes).replace(/\+/gu, "-").replace(/\//gu, "_").replace(/=+$/u, "") === value;
}

/** Parse the deliberately small wire grammar without projecting away duplicate keys. */
function metadata(text: string): BrowserSessionMetadata {
  let position = 0;
  const whitespace = () => { while (/[ \t\r\n]/u.test(text[position] ?? "x")) position++; };
  const take = (character: string) => {
    whitespace();
    if (text[position++] !== character) fail("invalid_response");
  };
  const string = () => {
    take('"');
    const start = position;
    while (position < text.length && text[position] !== '"') {
      const code = text.charCodeAt(position++);
      if (code < 0x20 || code > 0x7e || code === 0x5c) fail("invalid_response");
    }
    if (position === text.length) return fail("invalid_response");
    const value = text.slice(start, position);
    position++;
    return value;
  };
  const fields = new Map<string, string | number>();
  take("{");
  while (true) {
    const key = string();
    if (!["state", "generation", "expires_at", "csrf_token"].includes(key) || fields.has(key)) return fail("invalid_response");
    take(":");
    if (key === "expires_at") {
      whitespace();
      const start = position;
      while (/[0-9]/u.test(text[position] ?? "x")) position++;
      const token = text.slice(start, position);
      if (!/^(?:0|[1-9][0-9]*)$/u.test(token)) return fail("invalid_response");
      const value = Number(token);
      if (!Number.isSafeInteger(value)) return fail("invalid_response");
      fields.set(key, value);
    } else fields.set(key, string());
    whitespace();
    if (text[position] === "}") { position++; break; }
    take(",");
  }
  whitespace();
  if (position !== text.length) return fail("invalid_response");
  const state = fields.get("state"), csrf = fields.get("csrf_token");
  if (typeof csrf !== "string" || !canonical43(csrf)) return fail("invalid_response");
  if (state === "unauthenticated" && fields.size === 2) return Object.freeze({ state, csrf_token: csrf });
  const generation = fields.get("generation"), expires = fields.get("expires_at");
  if (state === "authenticated" && fields.size === 4 && typeof generation === "string" && canonical43(generation) &&
    typeof expires === "number") return Object.freeze({ state, generation, expires_at: expires, csrf_token: csrf });
  return fail("invalid_response");
}

/** Require a complete directive list, rather than searching arbitrary header text. */
function noStore(text: string | null): boolean {
  if (!text || text.length > 8192) return false;
  let position = 0, found = false;
  const whitespace = () => { while (text[position] === " " || text[position] === "\t") position++; };
  const token = () => {
    const start = position;
    while (/[!#$%&'*+.^_`|~0-9A-Za-z-]/u.test(text[position] ?? " ")) position++;
    return text.slice(start, position);
  };
  while (position < text.length) {
    whitespace();
    const name = token().toLowerCase();
    if (!name) return false;
    whitespace();
    let argument = false;
    if (text[position] === "=") {
      argument = true; position++; whitespace();
      if (text[position] === '"') {
        position++;
        while (position < text.length && text[position] !== '"') {
          if (text[position] === "\\") position++;
          const code = text.charCodeAt(position++);
          if (!(code === 9 || (code >= 0x20 && code <= 0x7e))) return false;
        }
        if (text[position++] !== '"') return false;
      } else if (!token()) return false;
      whitespace();
    }
    if (name === "no-store") { if (argument) return false; found = true; }
    if (position === text.length) return found;
    if (text[position++] !== ",") return false;
    whitespace();
    if (position === text.length) return false;
  }
  return found;
}

function cancelBody(response: Response): void {
  try { void response.body?.cancel().catch(() => undefined); } catch { /* Best effort only. */ }
}

/** Read only the fixed same-origin session endpoint; this does not authenticate a user. */
export function createBrowserSessionClient(options: BrowserSessionClientOptions = {}) {
  let fetchRequest: typeof globalThis.fetch, timeoutMs: number;
  try {
    if (!options || typeof options !== "object" || Array.isArray(options) ||
      Reflect.ownKeys(options).some(key => key !== "fetch" && key !== "timeoutMs")) return fail("invalid_request");
    fetchRequest = Object.hasOwn(options, "fetch") ? options.fetch! : globalThis.fetch;
    timeoutMs = Object.hasOwn(options, "timeoutMs") ? options.timeoutMs! : 15_000;
    if (typeof fetchRequest !== "function" || !Number.isInteger(timeoutMs) || timeoutMs < 1 || timeoutMs > 30_000) return fail("invalid_request");
  } catch { return fail("invalid_request"); }

  return Object.freeze({
    async read(signal?: AbortSignal): Promise<BrowserSessionMetadata> {
      if (signal?.aborted) return fail("aborted");
      const controller = new AbortController();
      const deadline = performance.now() + timeoutMs;
      let timedOut = false, finished = false;
      let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
      const stopCode = () => signal?.aborted ? "aborted" as const : timedOut ? "unavailable" as const : "aborted" as const;
      const check = () => {
        if (!timedOut && performance.now() >= deadline) { timedOut = true; controller.abort(); }
        if (controller.signal.aborted || finished) fail(stopCode());
      };
      const cancel = () => controller.abort();
      signal?.addEventListener("abort", cancel, { once: true });
      let stopped: (() => void) | undefined;
      const cancelled = new Promise<never>((_, reject) => {
        stopped = () => reject(new BrowserSessionClientError(stopCode()));
        controller.signal.addEventListener("abort", stopped, { once: true });
      });
      const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
      const perform = async (): Promise<BrowserSessionMetadata> => {
        check();
        let response: Response;
        try {
          response = await fetchRequest("/auth/session", { method: "GET", headers: { accept: "application/json" },
            credentials: "same-origin", redirect: "error", cache: "no-store", referrerPolicy: "no-referrer", signal: controller.signal });
        } catch { check(); return fail("unavailable"); }
        if (finished || controller.signal.aborted) { cancelBody(response); return fail(stopCode()); }
        try {
          check();
          if (response.status !== 200) { cancelBody(response); return fail("unavailable"); }
          if (response.redirected || !/^[ \t]*application\/json[ \t]*(?:;[ \t]*charset[ \t]*=[ \t]*utf-8[ \t]*)?$/iu.test(response.headers.get("content-type") ?? "") ||
            !noStore(response.headers.get("cache-control"))) { cancelBody(response); return fail("invalid_response"); }
          const length = response.headers.get("content-length");
          if (length !== null && (!/^(?:0|[1-9][0-9]*)$/u.test(length) || !Number.isSafeInteger(Number(length)) || Number(length) > 8192)) {
            cancelBody(response); return fail("invalid_response");
          }
          if (!response.body) return fail("invalid_response");
          reader = response.body.getReader();
          const chunks: Uint8Array[] = [];
          let size = 0, reads = 0;
          while (true) {
            check();
            if (++reads > 4096) return fail("invalid_response");
            const item = await reader.read();
            check();
            if (item.done) break;
            if (!(item.value instanceof Uint8Array)) return fail("invalid_response");
            size += item.value.byteLength;
            if (size > 4096) return fail("invalid_response");
            chunks.push(item.value.slice());
          }
          const bytes = new Uint8Array(size);
          let offset = 0;
          for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
          const value = metadata(new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(bytes));
          check();
          return value;
        } catch (error) {
          check();
          if (error instanceof BrowserSessionClientError) return fail(error.code);
          return fail("invalid_response");
        }
      };
      try { return await Promise.race([perform(), cancelled]); }
      catch (error) {
        if (controller.signal.aborted) return fail(stopCode());
        if (error instanceof BrowserSessionClientError) return fail(error.code);
        return fail("unavailable");
      } finally {
        finished = true;
        clearTimeout(timer);
        signal?.removeEventListener("abort", cancel);
        if (stopped) controller.signal.removeEventListener("abort", stopped);
        // Neither an uncooperative cancel nor read may retain the public operation.
        try { void reader?.cancel().catch(() => undefined); } catch { /* Best effort only. */ }
        try { reader?.releaseLock(); } catch { /* A hostile stream cannot break cleanup. */ }
        reader = undefined;
      }
    },
  });
}
