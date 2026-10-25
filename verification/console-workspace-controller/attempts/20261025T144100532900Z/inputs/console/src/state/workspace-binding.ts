import { createEffect, createSignal, on, onCleanup } from "solid-js";
import type { Accessor } from "solid-js";
import { createWorkspaceController } from "./workspace-controller.js";
import type { WorkspaceController, WorkspaceSession } from "./workspace-controller.js";
import type { WorkspaceDirectoryState } from "../domain/workspace-directory.js";

export interface WorkspaceBinding {
  readonly state: Accessor<WorkspaceDirectoryState>;
  readonly controller: WorkspaceController;
}

/** One owner per console: route changes retain selection, session changes erase it. */
export function createWorkspaceBinding(session: Accessor<WorkspaceSession | undefined>): WorkspaceBinding {
  const controller = createWorkspaceController();
  const [state, setState] = createSignal(controller.getState());
  const unsubscribe = controller.subscribe(value => setState(value));
  // Effects do not fetch while server rendering. The static shell stays unavailable
  // until its client-side session adapter supplies ordinary customer authorization.
  createEffect(on(session, value => controller.setSession(value ?? { kind: "unavailable" })));
  onCleanup(() => {
    unsubscribe();
    controller.dispose();
    setState(controller.getState());
  });
  return Object.freeze({ state, controller });
}
