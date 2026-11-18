import { A } from "@solidjs/router";
import { createMemo, Show } from "solid-js";
import { resolveWorkspaceDirectory, workspaceDisplayName } from "../domain/workspace-directory.js";
import { WorkspaceCreateForm } from "./WorkspaceCreateForm.js";
import { WorkspaceDirectory } from "./WorkspaceDirectory.js";
import { useWorkspace } from "../state/workspace-context.js";

/** Routed customer view; the application owns the session and request lifetime. */
export function WorkspacePage() {
  const workspace = useWorkspace();
  const { controller, creation } = workspace;
  const pending = () => creation.state()?.kind === "pending";
  const view = createMemo(() => resolveWorkspaceDirectory(workspace.state()));
  return <><WorkspaceDirectory {...workspace.state()}
    organizationActions={<Show when={creation.canCreateOrganization()}>
      <WorkspaceCreateForm item="organization" pending={pending()}
        onCreate={displayName => creation.submit({ kind: "organization", displayName })} />
    </Show>}
    projectActions={<Show when={creation.ownedOrganization()?.id} keyed>{organizationId =>
      <WorkspaceCreateForm item="project" pending={pending()}
        onCreate={displayName => creation.submit({ kind: "project", organizationId, displayName })} />
    }</Show>}
    onSelectOrganization={controller.selectOrganization}
    onSelectProject={controller.selectProject}
    onNextOrganizations={controller.nextOrganizations}
    onNextProjects={controller.nextProjects}
    onFirstOrganizations={controller.firstOrganizations}
    onFirstProjects={controller.firstProjects}
    onRetryOrganizations={controller.retryOrganizations}
    onRetryProjects={controller.retryProjects} />
    <Show when={creation.state()} keyed>{submission => {
      const noun = submission.input.kind === "organization" ? "Organization" : "Project";
      return <div class="workspace-current-selection">
        {submission.kind === "pending" && <p role="status">Creating {noun.toLowerCase()}…</p>}
        {submission.kind === "committed" && <p role="status">{noun} created.{!submission.selected && " Check the directory to select it."}</p>}
        {submission.kind === "error" && <p role="alert">{submission.message}</p>}
      </div>;
    }}</Show>
    <Show when={view().selectedProject}>{project => <div class="workspace-current-selection">
      <p>Continue with <strong><bdi>{workspaceDisplayName(project())}</bdi></strong>.</p>
      <A class="workspace-page-button" href="/builds">View builds</A>
    </div>}</Show>
  </>;
}
