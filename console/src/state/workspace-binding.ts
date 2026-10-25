import { createEffect, createSignal, on, onCleanup } from "solid-js";
import type { Accessor } from "solid-js";
import { createWorkspaceController } from "./workspace-controller.js";
import type { WorkspaceController, WorkspaceSession } from "./workspace-controller.js";
import type { WorkspaceDirectoryState } from "../domain/workspace-directory.js";

export type WorkspaceActions = Pick<WorkspaceController, "selectOrganization" | "selectProject" |
  "nextOrganizations" | "nextProjects" | "retryOrganizations" | "retryProjects">;
export interface WorkspaceBinding {
  readonly state: Accessor<WorkspaceDirectoryState>;
  readonly controller: Readonly<WorkspaceActions>;
}

const pending = (kind: "loading" | "unauthenticated" | "unavailable"): WorkspaceDirectoryState =>
  Object.freeze({ organizations: Object.freeze({ kind }), projects: Object.freeze({ kind: "unselected" as const }) });
const loading = pending("loading");
const unauthenticated = pending("unauthenticated");
const unavailable = pending("unavailable");

/** Own inside a Solid root. Each immutable session value is one account/session epoch. */
export function createWorkspaceBinding(session: Accessor<WorkspaceSession | undefined>): WorkspaceBinding {
  const controller = createWorkspaceController();
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
  const current = () => !disposed && admitted() !== undefined && admitted()!.session === session();
  const state = (): WorkspaceDirectoryState => {
    const value = session();
    const data = snapshot();
    if (disposed) return unavailable;
    if (current()) return data;
    return value?.kind === "unauthenticated" ? unauthenticated : value?.kind === "ready" ? loading : unavailable;
  };
  const actions: WorkspaceActions = Object.freeze({
    selectOrganization(id: string) { if (current()) controller.selectOrganization(id); },
    selectProject(selection: { organizationId: string; projectId: string }) { if (current()) controller.selectProject(selection); },
    nextOrganizations(cursor: string) { if (current()) controller.nextOrganizations(cursor); },
    nextProjects(page: { organizationId: string; cursor: string }) { if (current()) controller.nextProjects(page); },
    retryOrganizations() { if (current()) controller.retryOrganizations(); },
    retryProjects(organizationId: string) { if (current()) controller.retryProjects(organizationId); },
  });
  onCleanup(() => {
    disposed = true;
    unsubscribe();
    controller.dispose();
    setAdmitted(undefined);
    setSnapshot(controller.getState());
  });
  return Object.freeze({ state, controller: actions });
}
