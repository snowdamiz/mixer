import { WorkspaceClientError } from "../api/workspace-transport.js";
import type { WorkspaceAdminResult } from "../api/cookie-workspace-admin-client.js";
import type { CreatedWorkspace } from "../api/cookie-workspace-create-client.js";
import { createEffect, createSignal, on, onCleanup } from "solid-js";
import type { Accessor } from "solid-js";
import { createWorkspaceController } from "./workspace-controller.js";
import type { WorkspaceController, WorkspaceSession } from "./workspace-controller.js";
import type { WorkspaceDirectoryState } from "../domain/workspace-directory.js";

export type WorkspaceActions = Pick<WorkspaceController, "selectOrganization" | "selectProject" |
  "nextOrganizations" | "nextProjects" | "firstOrganizations" | "firstProjects" | "retryOrganizations" | "retryProjects" | "refreshOrganizations">;
export interface WorkspaceBinding {
  readonly state: Accessor<WorkspaceDirectoryState>;
  readonly controller: Readonly<WorkspaceActions>;
  readonly usageRevision: Accessor<number>;
  archiveProject(organizationId: string, projectId: string): Promise<WorkspaceAdminResult>;
  prepareCreatedRefresh(): (target: CreatedWorkspace) => Promise<boolean>;
}

const pending = (kind: "loading" | "unauthenticated" | "unavailable"): WorkspaceDirectoryState =>
  Object.freeze({ organizations: Object.freeze({ kind }), projects: Object.freeze({ kind: "unselected" as const }) });
const loading = pending("loading");
const unauthenticated = pending("unauthenticated");
const unavailable = pending("unavailable");

/** Own inside a Solid root. Each immutable session value is one account/session epoch. */
export function createWorkspaceBinding(
  session: Accessor<WorkspaceSession | undefined>,
  options: { readonly onRetrySession?: () => void } = {},
): WorkspaceBinding {
  const controller = createWorkspaceController();
  const [usageRevision, setUsageRevision] = createSignal(0);
  const [snapshot, setSnapshot] = createSignal(controller.getState());
  const [admitted, setAdmitted] = createSignal<{ readonly session: WorkspaceSession | undefined }>();
  let disposed = false;
  const unsubscribe = controller.subscribe(value => setSnapshot(value));
  // Pure consumers may run before this effect. Every public read and action below
  // compares the live session to its admitted epoch, independently of effect order.
  createEffect(on(session, value => {
    setAdmitted(undefined);
    controller.setSession(value ?? { kind: "unavailable" });
    setAdmitted({ session: value });
  }));
  const current = () => {
    const value = admitted();
    return !disposed && value !== undefined && value.session === session();
  };
  const state = (): WorkspaceDirectoryState => {
    const value = session();
    const data = snapshot();
    if (disposed) return unavailable;
    if (current()) return data;
    return value?.kind === "unauthenticated" ? unauthenticated : value?.kind === "ready" ? loading : unavailable;
  };
  let navigationVersion = 0;
  function navigate(action: () => void) {
    if (!current()) return;
    const before = controller.getState();
    action();
    if (before !== controller.getState()) navigationVersion++;
  }
  const actions: WorkspaceActions = Object.freeze({
    selectOrganization(id: string) { navigate(() => controller.selectOrganization(id)); },
    selectProject(selection: { organizationId: string; projectId: string }) { navigate(() => controller.selectProject(selection)); },
    nextOrganizations(cursor: string) { navigate(() => controller.nextOrganizations(cursor)); },
    nextProjects(page: { organizationId: string; cursor: string }) { navigate(() => controller.nextProjects(page)); },
    firstOrganizations() { navigate(() => controller.firstOrganizations()); },
    firstProjects(organizationId: string) { navigate(() => controller.firstProjects(organizationId)); },
    retryOrganizations() {
      if (!current()) return;
      if (session()?.kind === "unavailable") options.onRetrySession?.();
      else navigate(() => controller.retryOrganizations());
    },
    refreshOrganizations() { if (current()) controller.refreshOrganizations(); },
    retryProjects(organizationId: string) { navigate(() => controller.retryProjects(organizationId)); },
  });
  onCleanup(() => {
    disposed = true;
    unsubscribe();
    controller.dispose();
    setAdmitted(undefined);
    setSnapshot(controller.getState());
  });
  return Object.freeze({ state, controller: actions, usageRevision,
    async archiveProject(organizationId: string, projectId: string) {
      const owner = admitted();
      const value = owner?.session;
      if (!current() || value?.kind !== "ready" || !value.workspaceAdmin) throw new WorkspaceClientError("aborted");
      const reconcile = (confirmed: boolean) => {
        if (current() && admitted() === owner) {
          void controller.reconcileArchive(organizationId, projectId, confirmed).then(() => {
            if (current() && admitted() === owner) setUsageRevision(revision => revision + 1);
          });
        }
      };
      let result: WorkspaceAdminResult;
      try {
        result = await value.workspaceAdmin.request({ kind: "delete_project", organizationId, projectId });
        if (result.kind !== "delete_project") throw new WorkspaceClientError("invalid_response");
      } catch (error) {
        if (!(error instanceof WorkspaceClientError) || error.code === "unavailable" || error.code === "invalid_response") {
          reconcile(false);
        }
        throw error;
      }
      reconcile(true);
      return result;
    },
    prepareCreatedRefresh() {
      const owner = admitted();
      const version = navigationVersion;
      return async (target: CreatedWorkspace) => {
        if (!current() || admitted() !== owner) return false;
        const selected = navigationVersion === version && await controller.refreshCreated(target);
        if (current() && admitted() === owner) setUsageRevision(revision => revision + 1);
        return selected;
      };
    },
  });
}
