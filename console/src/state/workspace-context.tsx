import { createContext, useContext } from "solid-js";
import type { ParentProps } from "solid-js";
import { createWorkspaceBinding } from "./workspace-binding.js";
import { createWorkspaceCreation } from "./workspace-creation.js";
import type { WorkspaceCreationSession } from "./workspace-creation.js";

type WorkspaceContextValue = ReturnType<typeof createWorkspaceBinding> & {
  readonly creation: ReturnType<typeof createWorkspaceCreation>;
};
const WorkspaceContext = createContext<WorkspaceContextValue>();

export function WorkspaceProvider(props: ParentProps<{ readonly session: WorkspaceCreationSession | undefined; readonly onRetrySession?: () => void }>) {
  const binding = createWorkspaceBinding(() => props.session, { onRetrySession: () => props.onRetrySession?.() });
  const creation = createWorkspaceCreation(() => props.session, binding);
  return <WorkspaceContext.Provider value={{ ...binding, creation }}>{props.children}</WorkspaceContext.Provider>;
}

export function useWorkspace(): WorkspaceContextValue {
  const workspace = useContext(WorkspaceContext);
  if (!workspace) throw new Error("Missing workspace owner");
  return workspace;
}
