import { createEffect, createSignal, getOwner, on, onCleanup } from "solid-js";
import type { Accessor } from "solid-js";
import type { ConsoleSession } from "./browser-session-controller.js";
import { createBuildSelectionController } from "./build-selection-controller.js";
import type { BuildSelectionController, BuildSelectionState } from "./build-selection-controller.js";
import type { WorkspaceDirectoryState } from "../domain/workspace-directory.js";

export type BuildSelectionActions = Pick<BuildSelectionController, "selectApplication" | "selectBuild" |
  "firstApplications" | "nextApplications" | "firstBuilds" | "nextBuilds" | "refreshSelected">;
export interface BuildSelectionBinding {
  readonly state: Accessor<BuildSelectionState>;
  readonly controller: Readonly<BuildSelectionActions>;
}
const pending = (kind: "loading" | "unauthenticated" | "unavailable"): BuildSelectionState => Object.freeze({
  applications: Object.freeze({ kind }), builds: Object.freeze({ kind: "unselected" }), detail: Object.freeze({ kind: "unselected" }),
});
export function createBuildSelectionBinding(
  session: Accessor<ConsoleSession | undefined>, workspace: Accessor<WorkspaceDirectoryState>,
): BuildSelectionBinding {
  if (!getOwner()) throw new Error("Missing build selection owner");
  const controller = createBuildSelectionController();
  const [snapshot, setSnapshot] = createSignal(controller.getState());
  const [admitted, setAdmitted] = createSignal<{ session: ConsoleSession | undefined; workspace: WorkspaceDirectoryState }>();
  let disposed = false, ownedSession: ConsoleSession | undefined;
  const unsubscribe = controller.subscribe(value => setSnapshot(value));
  createEffect(on(() => [session(), workspace()] as const, ([value, directory]) => {
    setAdmitted(undefined);
    if (ownedSession !== value) { ownedSession = value; controller.setSession(value ?? { kind: "unavailable" }); }
    controller.setWorkspace(directory);
    if (!disposed) setAdmitted({ session: value, workspace: directory });
  }));
  const current = () => {
    const value = admitted();
    return !disposed && value !== undefined && value.session === session() && value.workspace === workspace();
  };
  const actions: BuildSelectionActions = Object.freeze({
    selectApplication(id: string) { if (current()) controller.selectApplication(id); },
    selectBuild(key: Parameters<BuildSelectionController["selectBuild"]>[0]) { if (current()) controller.selectBuild(key); },
    firstApplications() { if (current()) controller.firstApplications(); },
    nextApplications() { if (current()) controller.nextApplications(); },
    firstBuilds() { if (current()) controller.firstBuilds(); },
    nextBuilds() { if (current()) controller.nextBuilds(); },
    refreshSelected() { if (current()) controller.refreshSelected(); },
  });
  onCleanup(() => { disposed = true; unsubscribe(); controller.dispose(); setAdmitted(undefined); setSnapshot(controller.getState()); });
  return Object.freeze({
    state() {
      const value = session(), data = snapshot(); workspace();
      if (current()) return data;
      return pending(disposed || !value || value.kind === "unavailable" ? "unavailable" : value.kind === "unauthenticated" ? "unauthenticated" : "loading");
    }, controller: actions,
  });
}
