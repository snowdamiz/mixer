import { sessionSourceStarters } from "../api/cookie-source-starter-client.js";
import type { SourceStarterClient } from "../api/cookie-source-starter-client.js";
import { sessionApplicationRegistration } from "../api/cookie-application-registration-client.js";
import type { RegisterApplication } from "../api/cookie-application-registration-client.js";
import { sessionWorkspaceSupport } from "../api/cookie-workspace-support-client.js";
import type { SupportDraft, WorkspaceSupportClient } from "../api/cookie-workspace-support-client.js";
import { sessionWorkspaceAdmin } from "../api/cookie-workspace-admin-client.js";
import type { WorkspaceAdminClient, WorkspaceAdminInput } from "../api/cookie-workspace-admin-client.js";
import { sessionWorkspaceCreation } from "../api/cookie-workspace-create-client.js";
import type { WorkspaceCreateClient, WorkspaceCreateInput } from "../api/cookie-workspace-create-client.js";
import { sessionBuildSubmission } from "../api/build-submission.js";
import type { BuildSubmissionClient, CancelBuild } from "../api/build-submission.js";
import { BrowserSessionClientError, createBrowserSessionClient } from "../api/browser-session-client.js";
import type { BrowserSessionClientOptions, BrowserSessionMetadata } from "../api/browser-session-client.js";
import { createCookieWorkspaceClient } from "../api/cookie-workspace-client.js";
import { WorkspaceClientError } from "../api/workspace-client.js";
import type { WorkspaceClient, WorkspacePageRequest } from "../api/workspace-client.js";
import type { WorkspaceSession } from "./workspace-controller.js";
import { createCookieReleaseHeadClient } from "../api/cookie-release-head-client.js";
import type { ReleaseHeadClient } from "../api/cookie-release-head-client.js";
import type { PromotionPublication, ReleaseHeadTarget } from "../domain/release-head.js";
import { createCookieBuildClient } from "../api/cookie-build-client.js";
import type { CookieBuildClient } from "../api/cookie-build-client.js";
import { createCookieBuildCatalogClient } from "../api/cookie-build-catalog-client.js";
import type { BuildCatalogClient } from "../api/cookie-build-catalog-client.js";
import type { BuildLogTarget, BuildReadSelection } from "../domain/build-read.js";
import type { ProjectSelection, ApplicationSelection, CatalogPageRequest } from "../domain/build-catalog.js";

export type ConsoleSession = Exclude<WorkspaceSession, { readonly kind: "ready" }> |
  { readonly kind: "ready"; readonly client: WorkspaceClient;
    readonly workspaceCreate?: WorkspaceCreateClient;
    readonly workspaceAdmin?: WorkspaceAdminClient;
    readonly workspaceSupport?: WorkspaceSupportClient;
    readonly releaseHead: ReleaseHeadClient;
    readonly buildClients: Readonly<{ catalog: BuildCatalogClient; read: CookieBuildClient; create?: BuildSubmissionClient;
      cancel?: CancelBuild; registerApplication?: RegisterApplication; sourceStarters?: SourceStarterClient }> };

export interface BrowserSessionController {
  getSession(): ConsoleSession;
  subscribe(listener: (session: ConsoleSession) => void): () => void;
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
interface Subscription { readonly listener: (session: ConsoleSession) => void; revision: number }
const unavailable: ConsoleSession = Object.freeze({ kind: "unavailable" });
const aborted = (): never => { throw new WorkspaceClientError("aborted"); };

function clock(): { wall: number; mono: number } | undefined {
  try {
    const wall = Date.now(), mono = performance.now();
    if (Number.isSafeInteger(wall) && wall >= 0 && Number.isFinite(mono) && mono >= 0 && mono <= Number.MAX_SAFE_INTEGER) return { wall, mono };
  } catch { /* Invalid runtime clocks conservatively deny the capability. */ }
  return undefined;
}

/** Owns a local capability epoch, never a login provider, token or writable session. */
export type BrowserConsoleProfile = "workspace-manage" | "workspace-builds";

export function createBrowserSessionController(options: BrowserSessionClientOptions = {}, profile?: BrowserConsoleProfile): BrowserSessionController {
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
    const rawReleaseHead = createCookieReleaseHeadClient(settings);
    const releaseHead: ReleaseHeadClient = Object.freeze({
      readPromotionGroup: (publication: PromotionPublication, signal?: AbortSignal) =>
        delegate(value, owned => rawReleaseHead.readPromotionGroup(publication, owned), signal),
      readDetails: (target: ReleaseHeadTarget, signal?: AbortSignal) =>
        delegate(value, owned => rawReleaseHead.readDetails(target, owned), signal),
    });
    const rawCatalog = createCookieBuildCatalogClient(settings);
    const rawRead = createCookieBuildClient(settings);
    const catalog: BuildCatalogClient = Object.freeze({
      applications: (scope: ProjectSelection, page: CatalogPageRequest, signal?: AbortSignal) =>
        delegate(value, owned => rawCatalog.applications(scope, page, owned), signal),
      builds: (scope: ApplicationSelection, page: CatalogPageRequest, signal?: AbortSignal) =>
        delegate(value, owned => rawCatalog.builds(scope, page, owned), signal),
    });
    const read: CookieBuildClient = Object.freeze({
      read: (selection: BuildReadSelection, signal?: AbortSignal) => delegate(value, owned => rawRead.read(selection, owned), signal),
      readLogs: (target: BuildLogTarget, signal?: AbortSignal) => delegate(value, owned => rawRead.readLogs(target, owned), signal),
    });
    const csrf = () => {
      if (!live(value)) return aborted();
      return metadata.csrf_token;
    };
    const reads = { catalog, read };
    const workspaceWriters = () => {
      if (profile === "workspace-manage" || profile === "workspace-builds") {
        const raw = sessionWorkspaceCreation(settings, csrf);
        const workspaceCreate: WorkspaceCreateClient = Object.freeze({
          submit: (input: WorkspaceCreateInput, signal?: AbortSignal) =>
            delegate(value, owned => raw.submit(input, owned), signal),
        });
        const rawAdmin = sessionWorkspaceAdmin(settings, csrf);
        const workspaceAdmin: WorkspaceAdminClient = Object.freeze({
          request: (input: WorkspaceAdminInput, signal?: AbortSignal) =>
            delegate(value, owned => rawAdmin.request(input, owned), signal),
        });
        const rawSupport = sessionWorkspaceSupport(settings, csrf);
        const workspaceSupport: WorkspaceSupportClient = Object.freeze({
          list: (organizationId: string, signal?: AbortSignal) =>
            delegate(value, owned => rawSupport.list(organizationId, owned), signal),
          submit: (organizationId: string, draft: SupportDraft, signal?: AbortSignal) =>
            delegate(value, owned => rawSupport.submit(organizationId, draft, owned), signal),
        });
        return { workspaceCreate, workspaceAdmin, workspaceSupport };
      }
      return {};
    };
    const buildWriters = () => {
      if (profile === "workspace-manage") return {};
      const rawCreate = sessionBuildSubmission(settings, csrf);
      const create: BuildSubmissionClient = Object.freeze({
        inputs: (scope: ApplicationSelection, page: CatalogPageRequest, signal?: AbortSignal) =>
          delegate(value, owned => rawCreate.inputs(scope, page, owned), signal),
        submit: (attempt: Parameters<BuildSubmissionClient["submit"]>[0], signal?: AbortSignal) =>
          delegate(value, owned => rawCreate.submit(attempt, owned), signal),
      });
      const cancel: CancelBuild = (selection, signal) => delegate(value, owned => rawCreate.cancel(selection, owned), signal);
      if (profile !== "workspace-builds") return { create };
      const register = sessionApplicationRegistration(settings, csrf);
      const registerApplication: RegisterApplication = (input, signal) =>
        delegate(value, owned => register(input, owned), signal);
      const rawStarters = sessionSourceStarters(settings, csrf);
      const sourceStarters: SourceStarterClient = {
        discover: (scope, signal) => delegate(value, owned => rawStarters.discover(scope, owned), signal),
        select: (input, signal) => delegate(value, owned => rawStarters.select(input, owned), signal),
      };
      return { create, cancel, registerApplication, sourceStarters: Object.freeze(sourceStarters) };
    };
    active = undefined;
    capability = value;
    // Each accepted check is a fresh local epoch, including equal server generation strings.
    // Server metadata and CSRF never enter the public session or workspace client.
    session = Object.freeze({ kind: "ready", client, releaseHead, ...workspaceWriters(), buildClients: Object.freeze({ ...reads, ...buildWriters() }) });
    deadlineTimer = setTimeout(() => { if (capability === value && epoch === value.epoch) clear(); },
      Math.max(0, Math.floor(monoDeadline - now.mono)));
    revision++; notify();
  }

  return Object.freeze({
    getSession(): ConsoleSession {
      if (capability) live(capability);
      return session;
    },
    subscribe(listener: (value: ConsoleSession) => void): () => void {
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
