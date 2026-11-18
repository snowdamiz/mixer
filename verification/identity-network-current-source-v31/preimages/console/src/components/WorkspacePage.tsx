import { A } from "@solidjs/router";
import { createMemo, Show } from "solid-js";
import { resolveWorkspaceDirectory, workspaceDisplayName } from "../domain/workspace-directory.js";
import { WorkspaceDirectory } from "./WorkspaceDirectory.js";
import { useWorkspace } from "../state/workspace-context.js";

/** Routed customer view; the application owns the session and request lifetime. */
export function WorkspacePage() {
  const workspace = useWorkspace();
  const controller = workspace.controller;
  const view = createMemo(() => resolveWorkspaceDirectory(workspace.state()));
  return <><WorkspaceDirectory {...workspace.state()}
    onSelectOrganization={controller.selectOrganization}
    onSelectProject={controller.selectProject}
    onNextOrganizations={controller.nextOrganizations}
    onNextProjects={controller.nextProjects}
    onFirstOrganizations={controller.firstOrganizations}
    onFirstProjects={controller.firstProjects}
    onRetryOrganizations={controller.retryOrganizations}
    onRetryProjects={controller.retryProjects} />
    <Show when={view().selectedProject}>{project => <div class="workspace-current-selection">
      <p>Continue with <strong><bdi>{workspaceDisplayName(project())}</bdi></strong>.</p>
      <A class="workspace-page-button" href="/builds">View builds</A>
    </div>}</Show>
  </>;
}
