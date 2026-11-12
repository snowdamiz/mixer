import { WorkspaceClientError } from "../api/workspace-client.js";
import { catalogRecord, parseApplicationPage, parseBuildPage, snapshotProjectSelection } from "../domain/build-catalog.js";
import type { ApplicationPage, BuildPage, ProjectSelection, CatalogPageRequest } from "../domain/build-catalog.js";
import { parseBuildRead, snapshotBuildReadSelection } from "../domain/build-read.js";
import type { BuildReadSelection, BuildReadSnapshot } from "../domain/build-read.js";
import { parseWorkspaceOrganizations, parseWorkspaceProjects } from "../domain/workspace-directory.js";
import type { WorkspaceDirectoryState } from "../domain/workspace-directory.js";
import type { ConsoleSession } from "./browser-session-controller.js";

type Failure = "permission_denied" | "not_found" | "request_failed" | "invalid_response";
type Pending = { readonly kind: "unselected" | "loading" | "unauthenticated" | "unavailable" } |
  { readonly kind: "error"; readonly reason: Failure };
export type CatalogLoad<T> = Pending | { readonly kind: "ready" | "empty"; readonly page: T };
export type DetailLoad = Pending | { readonly kind: "ready"; readonly selection: BuildReadSelection; readonly snapshot: BuildReadSnapshot };
export interface BuildSelectionState {
  readonly applications: CatalogLoad<ApplicationPage>;
  readonly builds: CatalogLoad<BuildPage>;
  readonly detail: DetailLoad;
  readonly selectedApplicationId?: string;
}
export interface BuildSelectionController {
  getState(): BuildSelectionState;
  subscribe(listener: (state: BuildSelectionState) => void): () => void;
  setSession(session: ConsoleSession): void;
  setWorkspace(workspace: WorkspaceDirectoryState): void;
  selectApplication(applicationId: string): void;
  selectBuild(key: Readonly<Pick<BuildReadSelection, "buildId" | "platform">>): void;
  firstApplications(): void;
  nextApplications(): void;
  firstBuilds(): void;
  nextBuilds(): void;
  refreshSelected(): void;
  dispose(): void;
}
type ReadySession = Extract<ConsoleSession, { kind: "ready" }>;
interface Request {
  readonly session: ReadySession;
  readonly clients: ReadySession["buildClients"];
  readonly catalog: ReadySession["buildClients"]["catalog"];
  readonly read: ReadySession["buildClients"]["read"];
  readonly project: ProjectSelection;
  readonly generation: number;
  readonly controller: AbortController;
}
interface Subscription { readonly listener: (state: BuildSelectionState) => void; revision: number }
const unselected = Object.freeze({ kind: "unselected" } satisfies Pending);
const first: CatalogPageRequest = Object.freeze({});
const initial = (applications: Pending = unselected): BuildSelectionState => Object.freeze({ applications, builds: unselected, detail: unselected });

function checkedSnapshot(input: unknown, selection: BuildReadSelection): BuildReadSnapshot {
  if (!catalogRecord(input, ["revision", "report"]) || !catalogRecord(input.report,
    ["organizationId", "projectId", "applicationId", "buildId", "platform", "sourceSha256", "toolchainLockSha256",
      "buildDefinitionSha256", "state", "attempt", "maxAttempts", "workerCompletionPending"], ["failureCode"])) throw new TypeError();
  const r = input.report;
  return parseBuildRead({ build: { organizationId: r.organizationId, projectId: r.projectId,
    applicationId: r.applicationId, buildId: r.buildId, platform: r.platform, sourceSha256: r.sourceSha256,
    toolchainLockSha256: r.toolchainLockSha256, buildDefinitionSha256: r.buildDefinitionSha256,
    revision: input.revision, state: r.state, attempt: r.attempt, maxAttempts: r.maxAttempts,
    failureCode: r.failureCode ?? null, workerCompletionPending: r.workerCompletionPending } }, selection);
}
function checkedBuildPage(input: unknown, scope: Parameters<typeof parseBuildPage>[1]): BuildPage {
  if (!catalogRecord(input, ["organizationId", "projectId", "applicationId", "builds", "nextCursor"]) ||
    !Array.isArray(input.builds) || input.builds.length > 25) throw new TypeError();
  const builds = input.builds.map(row => {
    if (!catalogRecord(row, ["selection", "snapshot"])) throw new TypeError();
    const selection = snapshotBuildReadSelection(row.selection);
    const snapshot = checkedSnapshot(row.snapshot, selection), r = snapshot.report;
    return { organizationId: r.organizationId, projectId: r.projectId, applicationId: r.applicationId,
      buildId: r.buildId, platform: r.platform, sourceSha256: r.sourceSha256, toolchainLockSha256: r.toolchainLockSha256,
      buildDefinitionSha256: r.buildDefinitionSha256, revision: snapshot.revision, state: r.state, attempt: r.attempt,
      maxAttempts: r.maxAttempts, failureCode: r.failureCode ?? null, workerCompletionPending: r.workerCompletionPending };
  });
  return parseBuildPage({ organizationId: input.organizationId, projectId: input.projectId,
    applicationId: input.applicationId, builds, nextCursor: input.nextCursor }, scope);
}
function failure(error: unknown): Pending {
  try {
    if (error instanceof WorkspaceClientError) {
      switch (error.code) {
        case "unauthenticated": case "unavailable": return Object.freeze({ kind: error.code });
        case "permission_denied": case "not_found": case "invalid_response": return Object.freeze({ kind: "error", reason: error.code });
      }
    }
    if (error instanceof TypeError) return Object.freeze({ kind: "error", reason: "invalid_response" });
  } catch { /* Closed fallback. */ }
  return Object.freeze({ kind: "error", reason: "request_failed" });
}

/** Selection is data from current validated pages; only the existing session owner grants transport access. */
export function createBuildSelectionController(): BuildSelectionController {
  let state = initial({ kind: "unavailable" }), session: ConsoleSession = { kind: "unavailable" };
  let workspace: WorkspaceDirectoryState | undefined, project: ProjectSelection | undefined;
  let active: Request | undefined, selected: { selection: BuildReadSelection; revision: number } | undefined;
  let generation = 0, workspaceGeneration = 0, revision = 0, disposed = false, notifying = false;
  let applicationAttempt: CatalogPageRequest = first, buildAttempt: CatalogPageRequest = first;
  const subscriptions = new Set<Subscription>();
  function notify(): void {
    if (notifying || disposed) return;
    notifying = true;
    try {
      while (!disposed) {
        const version = revision, value = state;
        const pending = [...subscriptions].filter(item => item.revision !== version);
        if (!pending.length) break;
        for (const item of pending) {
          if (disposed || revision !== version) break;
          if (!subscriptions.has(item) || item.revision === version) continue;
          item.revision = version;
          try { void Promise.resolve(item.listener(value)).catch(() => undefined); } catch { /* Isolated listener. */ }
        }
      }
    } finally { notifying = false; }
  }
  function update(next: BuildSelectionState, cancelled?: Request): void {
    state = Object.freeze(next); revision++;
    cancelled?.controller.abort();
    notify();
  }
  function current(value: Request): boolean {
    return !disposed && session.kind === "ready" && active === value && generation === value.generation && session === value.session &&
      project === value.project && session.buildClients === value.clients &&
      session.buildClients.catalog === value.catalog && session.buildClients.read === value.read && !value.controller.signal.aborted;
  }
  function request(): Request | undefined {
    if (disposed || session.kind !== "ready" || !project) return undefined;
    return { session, clients: session.buildClients, catalog: session.buildClients.catalog, read: session.buildClients.read, project, generation: ++generation, controller: new AbortController() };
  }
  function fail(value: Request, error: unknown, stage: "applications" | "builds" | "detail"): void {
    if (!current(value)) return;
    const reason = failure(error);
    if (!current(value)) return;
    active = undefined;
    if (stage !== "detail" || reason.kind !== "error" ||
      (reason.reason !== "invalid_response" && reason.reason !== "request_failed")) selected = undefined;
    if (reason.kind === "unauthenticated" || reason.kind === "unavailable" ||
      (reason.kind === "error" && (reason.reason === "permission_denied" || reason.reason === "not_found"))) {
      update(initial(reason));
    } else if (stage === "applications") update(initial(reason));
    else if (stage === "builds") update({ applications: state.applications, builds: reason, detail: unselected,
      ...(state.selectedApplicationId === undefined ? {} : { selectedApplicationId: state.selectedApplicationId }) });
    else update({ ...state, detail: reason });
  }
  function loadApplications(page: CatalogPageRequest): void {
    const value = request(); if (!value) return;
    const cancelled = active; active = value; selected = undefined; applicationAttempt = page; buildAttempt = first;
    update(initial({ kind: "loading" }), cancelled);
    void (async () => {
      if (!current(value)) return;
      try {
        const input = await value.session.buildClients.catalog.applications(value.project, page, value.controller.signal);
        if (!current(value)) return;
        const parsed = parseApplicationPage(input, value.project);
        if (!current(value)) return;
        active = undefined;
        update({ applications: Object.freeze({ kind: parsed.applications.length ? "ready" : "empty", page: parsed }), builds: unselected, detail: unselected });
      } catch (error) { fail(value, error, "applications"); }
    })();
  }
  function loadBuilds(applicationId: string, page: CatalogPageRequest): void {
    const value = request(); if (!value) return;
    const scope = Object.freeze({ ...value.project, applicationId });
    const cancelled = active; active = value; selected = undefined; buildAttempt = page;
    update({ applications: state.applications, selectedApplicationId: applicationId, builds: { kind: "loading" }, detail: unselected }, cancelled);
    void (async () => {
      if (!current(value)) return;
      try {
        const input = await value.session.buildClients.catalog.builds(scope, page, value.controller.signal);
        if (!current(value)) return;
        const parsed = checkedBuildPage(input, scope);
        if (!current(value)) return;
        active = undefined;
        update({ applications: state.applications, selectedApplicationId: applicationId,
          builds: Object.freeze({ kind: parsed.builds.length ? "ready" : "empty", page: parsed }), detail: unselected });
      } catch (error) { fail(value, error, "builds"); }
    })();
  }
  function loadDetail(row: { readonly selection: BuildReadSelection; readonly revision: number }): void {
    const value = request(); if (!value) return;
    const selection = snapshotBuildReadSelection(row.selection), floor = row.revision;
    const cancelled = active; active = value; selected = { selection, revision: floor };
    update({ ...state, detail: { kind: "loading" } }, cancelled);
    void (async () => {
      if (!current(value)) return;
      try {
        const input = await value.session.buildClients.read.read(selection, value.controller.signal);
        if (!current(value)) return;
        const snapshot = checkedSnapshot(input, selection);
        if (!current(value)) return;
        if (snapshot.revision < floor) throw new TypeError();
        active = undefined; selected = { selection, revision: snapshot.revision };
        update({ ...state, detail: Object.freeze({ kind: "ready", selection, snapshot }) });
      } catch (error) { fail(value, error, "detail"); }
    })();
  }
  function setSession(next: ConsoleSession): void {
    if (disposed || next === session) return;
    const cancelled = active; active = undefined; generation++; workspaceGeneration++;
    session = next; workspace = undefined; project = undefined; selected = undefined;
    applicationAttempt = first; buildAttempt = first;
    update(initial({ kind: next.kind === "ready" ? "unselected" : next.kind }), cancelled);
  }
  function setWorkspace(next: WorkspaceDirectoryState): void {
    if (disposed || workspace === next) return;
    const version = ++workspaceGeneration;
    let scope: ProjectSelection | undefined;
    try {
      if (next.organizations.kind === "ready" && next.projects.kind === "ready" &&
        next.selectedOrganizationId === next.projects.organizationId) {
        const orgs = parseWorkspaceOrganizations(next.organizations.input);
        const projects = parseWorkspaceProjects(next.projects.input, next.projects.organizationId);
        if (orgs.organizations.some(row => row.id === next.selectedOrganizationId) &&
          projects.projects.some(row => row.id === next.selectedProjectId)) {
          scope = snapshotProjectSelection({ organizationId: next.selectedOrganizationId, projectId: next.selectedProjectId });
        }
      }
    } catch { /* Invalid workspace never selects a project. */ }
    if (disposed || workspaceGeneration !== version) return;
    const samePages = workspace?.organizations === next.organizations && workspace?.projects === next.projects &&
      project?.organizationId === scope?.organizationId && project?.projectId === scope?.projectId;
    workspace = next;
    if (samePages) return;
    const cancelled = active; active = undefined; generation++; project = scope; selected = undefined;
    applicationAttempt = first; buildAttempt = first;
    update(initial(session.kind === "ready" ? unselected : { kind: session.kind }), cancelled);
    if (!disposed && workspaceGeneration === version && project === scope && scope) loadApplications(first);
  }
  return Object.freeze({
    getState: () => state,
    subscribe(listener: (state: BuildSelectionState) => void): () => void {
      if (disposed) return () => undefined;
      const item: Subscription = { listener, revision: -1 }; subscriptions.add(item); notify();
      return () => { subscriptions.delete(item); };
    },
    setSession, setWorkspace,
    selectApplication(applicationId: string): void {
      if (disposed || state.applications.kind !== "ready" || state.selectedApplicationId === applicationId ||
        !state.applications.page.applications.some(row => row.applicationId === applicationId)) return;
      loadBuilds(applicationId, first);
    },
    selectBuild(key: Readonly<Pick<BuildReadSelection, "buildId" | "platform">>): void {
      if (disposed || state.builds.kind !== "ready") return;
      let row;
      try {
        if (!catalogRecord(key, ["buildId", "platform"])) return;
        row = state.builds.page.builds.find(row => row.selection.buildId === key.buildId && row.selection.platform === key.platform);
      } catch { return; }
      if (disposed || !row || state.builds.kind !== "ready" || !state.builds.page.builds.includes(row)) return;
      const previous = selected;
      loadDetail({ selection: row.selection, revision: previous && Object.keys(row.selection).every(key => Reflect.get(previous.selection, key) === Reflect.get(row.selection, key)) ? previous.revision : row.snapshot.revision });
    },
    firstApplications(): void { if (!disposed && applicationAttempt.cursor !== undefined) loadApplications(first); },
    nextApplications(): void {
      const value = state.applications;
      if (!disposed && (value.kind === "ready" || value.kind === "empty") && value.page.nextCursor !== null)
        loadApplications(Object.freeze({ cursor: value.page.nextCursor }));
    },
    firstBuilds(): void { if (!disposed && buildAttempt.cursor !== undefined && state.selectedApplicationId !== undefined) loadBuilds(state.selectedApplicationId, first); },
    nextBuilds(): void {
      const value = state.builds;
      if (!disposed && (value.kind === "ready" || value.kind === "empty") && value.page.nextCursor !== null && state.selectedApplicationId !== undefined)
        loadBuilds(state.selectedApplicationId, Object.freeze({ cursor: value.page.nextCursor }));
    },
    refreshSelected(): void { if (!disposed && selected) loadDetail(selected); },
    dispose(): void {
      if (disposed) return;
      disposed = true; generation++; workspaceGeneration++; session = { kind: "unavailable" };
      project = undefined; workspace = undefined; selected = undefined;
      const cancelled = active; active = undefined; subscriptions.clear(); update(initial({ kind: "unavailable" }), cancelled);
    },
  });
}
