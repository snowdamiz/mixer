import { WorkspaceSupport } from "./WorkspaceSupport.js";
import { WorkspaceAdministration } from "./WorkspaceAdministration.js";
import type { WorkspaceAdminClient } from "../api/cookie-workspace-admin-client.js";
import type { ConsoleSession } from "../state/browser-session-controller.js";
import { A } from "@solidjs/router";
import { createMemo, createSignal, Show } from "solid-js";
import { resolveWorkspaceDirectory, workspaceDisplayName } from "../domain/workspace-directory.js";
import { WorkspaceCreateForm } from "./WorkspaceCreateForm.js";
import { WorkspaceDirectory } from "./WorkspaceDirectory.js";
import { useWorkspace } from "../state/workspace-context.js";

/** Routed customer view; the application owns the session and request lifetime. */
export function WorkspacePage(props: { readonly session?: ConsoleSession | undefined }) {
  const workspace = useWorkspace();
  const { controller, creation } = workspace;
  const pending = () => creation.state()?.kind === "pending";
  const [deleted, setDeleted] = createSignal(false);
  const view = createMemo(() => resolveWorkspaceDirectory(workspace.state()));
  const adminOrganization = createMemo(() => {
    const organization = view().selectedOrganization;
    return organization?.organization_roles.length ? organization : undefined;
  }, undefined, {
    equals: (current, next) => current?.id === next?.id &&
      current?.organization_roles.join() === next?.organization_roles.join(),
  });
  const admin = () => props.session?.kind === "ready" ? props.session.workspaceAdmin : undefined;
  const [eligibility, setEligibility] = createSignal<{ client: WorkspaceAdminClient; organizationId: string }>();
  const projectOrganization = () => {
    const grant = eligibility();
    if (grant && grant.client === admin() && grant.organizationId === creation.ownedOrganization()?.id) {
      return grant.organizationId;
    }
  };
  const support = () => props.session?.kind === "ready" ? props.session.workspaceSupport : undefined;
  const supportOrganization = () => {
    const organization = view().selectedOrganization;
    return organization && organization.organization_roles.length > 0 ? organization.id : undefined;
  };
  return <><WorkspaceDirectory {...workspace.state()}
    organizationActions={<Show when={creation.canCreateOrganization()}>
      <WorkspaceCreateForm item="organization" pending={pending()}
        onCreate={displayName => creation.submit({ kind: "organization", displayName })} />
    </Show>}
    projectActions={<Show when={projectOrganization()} keyed>{organizationId =>
      <WorkspaceCreateForm item="project" pending={pending()}
        onCreate={async displayName => {
          if (projectOrganization() === organizationId) return creation.submit({ kind: "project", organizationId, displayName });
          return false;
        }} />
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
    <Show when={support()} keyed>{client =>
      <Show when={supportOrganization()} keyed>{organizationId =>
        <WorkspaceSupport client={client} organizationId={organizationId} />
      }</Show>
    }</Show>
    <Show when={deleted()}><p role="status">Organization deleted.</p></Show>
    <Show when={admin()} keyed>{client =>
      <Show when={adminOrganization()} keyed>{organization =>
        <WorkspaceAdministration client={client} organization={organization}
          project={view().selectedProject} usageRevision={workspace.usageRevision()} archiveProject={workspace.archiveProject}
          onEligibilityChange={eligible => {
            if (eligible && admin() === client && adminOrganization()?.id === organization.id) {
              setEligibility({ client, organizationId: organization.id });
            } else if (!eligible) {
              setEligibility(current => current?.client === client && current.organizationId === organization.id
                ? undefined : current);
            }
          }} onDeleteOrganization={() => { setDeleted(true); controller.refreshOrganizations(); }} />
      }</Show>
    }</Show>
  </>;
}
