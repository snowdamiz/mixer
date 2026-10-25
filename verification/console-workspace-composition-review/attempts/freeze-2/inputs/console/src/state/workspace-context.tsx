import { createContext, useContext } from "solid-js";
import type { ParentProps } from "solid-js";
import { createWorkspaceBinding } from "./workspace-binding.js";
import type { WorkspaceBinding } from "./workspace-binding.js";
import type { WorkspaceSession } from "./workspace-controller.js";

const WorkspaceContext = createContext<WorkspaceBinding>();

export function WorkspaceProvider(props: ParentProps<{ readonly session: WorkspaceSession | undefined }>) {
  const binding = createWorkspaceBinding(() => props.session);
  return <WorkspaceContext.Provider value={binding}>{props.children}</WorkspaceContext.Provider>;
}

export function useWorkspace(): WorkspaceBinding {
  const workspace = useContext(WorkspaceContext);
  if (!workspace) throw new Error("Missing workspace owner");
  return workspace;
}
