import { WorkspaceDirectory } from "./WorkspaceDirectory.js";
import { useWorkspace } from "../state/workspace-context.js";

/** Routed customer view; the application owns the session and request lifetime. */
export function WorkspacePage() {
  const workspace = useWorkspace();
  const controller = workspace.controller;
  return <WorkspaceDirectory {...workspace.state()}
    onSelectOrganization={controller.selectOrganization}
    onSelectProject={controller.selectProject}
    onNextOrganizations={controller.nextOrganizations}
    onNextProjects={controller.nextProjects}
    onRetryOrganizations={controller.retryOrganizations}
    onRetryProjects={controller.retryProjects} />;
}
