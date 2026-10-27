import { BrowserSessionClientError, createBrowserSessionClient } from "../api/browser-session-client.js";
import type { BrowserSessionClientOptions, BrowserSessionMetadata } from "../api/browser-session-client.js";
import { createCookieWorkspaceClient } from "../api/cookie-workspace-client.js";
import { WorkspaceClientError } from "../api/workspace-client.js";
import type { WorkspaceClient, WorkspacePageRequest } from "../api/workspace-client.js";
import type { WorkspaceSession } from "./workspace-controller.js";

export interface BrowserSessionController {
  getSession(): WorkspaceSession;
  subscribe(listener: (session: WorkspaceSession) => void): () => void;
  revalidate(): void;
  invalidate(): void;
  dispose(): void;
}
interface Check { readonly epoch: symbol; readonly controller: AbortController }
interface Capability {
  readonly epoch: symbol;
  readonly wallDeadline: number;
  readonly monoDeadline: number;
  lastWall: number;
  lastMono: number;
}
interface Subscription { readonly listener: (session: WorkspaceSession) => void; revision: number }
const unavailable: WorkspaceSession = Object.freeze({ kind: "unavailable" });
const aborted = (): never => { throw new WorkspaceClientError("aborted"); };

function clock(): { wall: number; mono: number } | undefined {
  try {
    const wall = Date.now(), mono = performance.now();
    if (Number.isSafeInteger(wall) && wall >= 0 && Number.isFinite(mono) && mono >= 0 && mono <= Number.MAX_SAFE_INTEGER) return { wall, mono };
  } catch { /* Invalid runtime clocks conservatively deny the capability. */ }
  return undefined;
}

/** Owns a local capability epoch, never a login provider, token or writable session. */
export function createBrowserSessionController(options: BrowserSessionClientOptions = {}): BrowserSessionController {
  // Snapshot trusted construction settings so later caller mutation cannot retarget a client.
  let settings: BrowserSessionClientOptions;
  try {
    if (!options || typeof options !== "object" || Array.isArray(options) ||
      Reflect.ownKeys(options).some(key => key !== "fetch" && key !== "timeoutMs")) throw new Error();
    settings = Object.freeze({ ...(Object.hasOwn(options, "fetch") ? { fetch: options.fetch! } : {}),
      ...(Object.hasOwn(options, "timeoutMs") ? { timeoutMs: options.timeoutMs! } : {}) });
  } catch { throw new BrowserSessionClientError("invalid_request"); }
  const sessionClient = createBrowserSessionClient(settings);
  let session = unavailable, epoch = Symbol(), disposed = false;
  let active: Check | undefined, capability: Capability | undefined;
  let deadlineTimer: ReturnType<typeof setTimeout> | undefined;
  let revision = 0, notifying = false;
  const work = new Set<AbortController>();
  const subscriptions = new Set<Subscription>();

  function notify(): void {
    if (notifying || disposed) return;
    notifying = true;
    try {
      while (!disposed) {
        const currentRevision = revision, currentSession = session;
        const pending = [...subscriptions].filter(item => item.revision !== currentRevision);
        if (!pending.length) break;
        for (const item of pending) {
          if (disposed || revision !== currentRevision) break;
          if (!subscriptions.has(item) || item.revision === currentRevision) continue;
          item.revision = currentRevision;
          try { void Promise.resolve(item.listener(currentSession)).catch(() => undefined); } catch { /* Isolated observer. */ }
        }
      }
    } finally { notifying = false; }
  }

  function clear(next?: Check): void {
    const previous = active, cancelled = [...work];
    epoch = next?.epoch ?? Symbol();
    active = next;
    capability = undefined;
    session = unavailable;
    revision++;
    if (deadlineTimer !== undefined) clearTimeout(deadlineTimer);
    deadlineTimer = undefined;
    work.clear();
    // Install every ownership slot before invoking abort handlers or subscribers.
    previous?.controller.abort();
    for (const item of cancelled) item.abort();
    notify();
  }

  function current(check: Check): boolean {
    return !disposed && active === check && epoch === check.epoch && !check.controller.signal.aborted;
  }
  function live(value: Capability): boolean {
    if (disposed || capability !== value || epoch !== value.epoch || session.kind !== "ready") return false;
    const now = clock();
    if (!now || now.wall < value.lastWall || now.mono < value.lastMono ||
      now.wall >= value.wallDeadline || now.mono >= value.monoDeadline) {
      clear();
      return false;
    }
    value.lastWall = now.wall; value.lastMono = now.mono;
    return true;
  }

  async function delegate<T>(value: Capability, call: (signal: AbortSignal) => Promise<T>, signal?: AbortSignal): Promise<T> {
    if (!live(value) || signal?.aborted) return aborted();
    const controller = new AbortController();
    const cancel = () => controller.abort();
    signal?.addEventListener("abort", cancel, { once: true });
    work.add(controller);
    try {
      if (!live(value) || signal?.aborted) return aborted();
      const result = await call(controller.signal);
      if (!live(value) || controller.signal.aborted || signal?.aborted) return aborted();
      return result;
    } catch (error) {
      if (!live(value) || controller.signal.aborted || signal?.aborted) return aborted();
      if (error instanceof WorkspaceClientError && error.code === "unauthenticated") clear();
      throw error;
    } finally {
      work.delete(controller);
      signal?.removeEventListener("abort", cancel);
    }
  }

  function admit(check: Check, start: { wall: number; mono: number }, metadata: BrowserSessionMetadata): void {
    if (!current(check)) return;
    if (metadata.state === "unauthenticated") {
      active = undefined;
      session = Object.freeze({ kind: "unauthenticated" });
      revision++; notify(); return;
    }
    const now = clock(), wallDeadline = metadata.expires_at * 1000;
    const monoDeadline = start.mono + Math.min(900_000, wallDeadline - start.wall);
    if (!now || !Number.isSafeInteger(wallDeadline) || !Number.isFinite(monoDeadline) || monoDeadline < 0 ||
      monoDeadline > Number.MAX_SAFE_INTEGER || now.wall < start.wall || now.mono < start.mono ||
      wallDeadline <= now.wall || monoDeadline <= now.mono) { clear(); return; }
    const value: Capability = { epoch: check.epoch, wallDeadline, monoDeadline, lastWall: now.wall, lastMono: now.mono };
    const cookieClient = createCookieWorkspaceClient(settings);
    const client: WorkspaceClient = Object.freeze({
      organizations: (page?: WorkspacePageRequest, signal?: AbortSignal) => delegate(value, owned => cookieClient.organizations(page, owned), signal),
      projects: (organizationId: string, page?: WorkspacePageRequest, signal?: AbortSignal) => delegate(value, owned => cookieClient.projects(organizationId, page, owned), signal),
    });
    active = undefined;
    capability = value;
    // Each accepted check is a fresh local epoch, including equal server generation strings.
    // Server metadata and CSRF never enter the public session or workspace client.
    session = Object.freeze({ kind: "ready", client });
    deadlineTimer = setTimeout(() => { if (capability === value && epoch === value.epoch) clear(); },
      Math.max(0, Math.floor(monoDeadline - now.mono)));
    revision++; notify();
  }

  return Object.freeze({
    getSession(): WorkspaceSession {
      if (capability) live(capability);
      return session;
    },
    subscribe(listener: (value: WorkspaceSession) => void): () => void {
      if (disposed) return () => undefined;
      const item: Subscription = { listener, revision: -1 };
      subscriptions.add(item); notify();
      return () => { subscriptions.delete(item); };
    },
    revalidate(): void {
      if (disposed) return;
      const check: Check = { epoch: Symbol(), controller: new AbortController() };
      clear(check);
      if (!current(check)) return;
      const start = clock();
      if (!start) { clear(); return; }
      void sessionClient.read(check.controller.signal).then(metadata => {
        if (current(check)) admit(check, start, metadata);
      }).catch(() => { if (current(check)) clear(); });
    },
    invalidate(): void { if (!disposed) clear(); },
    dispose(): void {
      if (disposed) return;
      disposed = true;
      subscriptions.clear();
      clear();
    },
  });
}
