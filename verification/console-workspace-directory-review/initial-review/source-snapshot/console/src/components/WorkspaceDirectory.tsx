import { createMemo, For, Match, Show, Switch } from "solid-js";
import { resolveWorkspaceDirectory, workspaceDisplayName } from "../domain/workspace-directory.js";
import type { WorkspaceDirectoryState, WorkspaceFailure, WorkspaceRole } from "../domain/workspace-directory.js";
import "./workspace-directory.css";

export interface WorkspaceDirectoryProps extends WorkspaceDirectoryState {
  readonly onSelectOrganization: (organizationId: string) => void;
  readonly onSelectProject: (selection: { readonly organizationId: string; readonly projectId: string }) => void;
  readonly onNextOrganizations?: (cursor: string) => void;
  readonly onNextProjects?: (page: { readonly organizationId: string; readonly cursor: string }) => void;
  readonly onRetryOrganizations?: () => void;
  readonly onRetryProjects?: (organizationId: string) => void;
}

const roleLabels: Record<WorkspaceRole, string> = {
  owner: "Owner", administrator: "Administrator", developer: "Developer",
  release_manager: "Release manager", billing_manager: "Billing manager", viewer: "Viewer",
};

function WorkspaceSymbol(props: { project?: boolean }) {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><Show when={props.project} fallback={<>
    <rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/>
    <rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>
  </>}><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Zm-8 4.5 8 4.5 8-4.5M12 12v9m-4-16 8 4.5"/></Show></svg>;
}

function Roles(props: { roles: readonly WorkspaceRole[]; project?: boolean }) {
  return <div class="workspace-roles"><Show when={props.roles.length > 0} fallback={<p>Project access</p>}>
    <p>{props.project ? "Project roles" : "Organization roles"}</p>
    <ul aria-label={props.project ? "Your project roles" : "Your organization roles"}>
      <For each={props.roles}>{role => <li>{roleLabels[role]}</li>}</For>
    </ul>
  </Show></div>;
}

type MessageState = { readonly kind: "loading" | "unauthenticated" | "unavailable" | "invalid" | "unselected" } |
  { readonly kind: "error"; readonly reason: WorkspaceFailure };

function DirectoryMessage(props: { state: MessageState; project?: boolean; onRetry: (() => void) | undefined }) {
  const copy = createMemo(() => {
    const noun = props.project ? "projects" : "organizations";
    const state = props.state;
    if (state.kind === "loading") return { title: `Loading ${noun}`, detail: `Your ${noun} will appear here shortly.` };
    if (state.kind === "unauthenticated") return { title: "Sign in to view your workspace", detail: "Your session has ended. Sign in to continue." };
    if (state.kind === "unavailable") return { title: "Workspace temporarily unavailable", detail: "Your workspace is unavailable right now. Try again shortly." };
    if (state.kind === "unselected") return { title: "Choose an organization", detail: "Select an organization to see the projects you can access." };
    if (state.kind === "error" && state.reason === "permission_denied") return {
      title: `You cannot view these ${noun}`, detail: "Your account does not have access. Contact your organization owner if you need help.",
    };
    if (state.kind === "error" && state.reason === "not_found") return {
      title: "Organization no longer available", detail: "Choose another organization or refresh your workspace.",
    };
    return { title: `Could not load ${noun}`, detail: "Refresh your workspace to try again." };
  });
  const alert = () => props.state.kind === "error" || props.state.kind === "invalid";
  const retry = () => props.onRetry && (props.state.kind === "error" || props.state.kind === "invalid" || props.state.kind === "unavailable");
  return <div class={`workspace-message${alert() ? " workspace-message-error" : ""}`} role={alert() ? "alert" : "status"}>
    <h3>{copy().title}</h3><p>{copy().detail}</p>
    <Show when={retry()}><button type="button" class="workspace-text-button" onClick={() => props.onRetry?.()}>Try again</button></Show>
  </div>;
}

/** Controlled directory: the caller owns authorization, requests, pagination and selection. */
export function WorkspaceDirectory(props: WorkspaceDirectoryProps) {
  const view = createMemo(() => resolveWorkspaceDirectory(props));
  const organizations = () => {
    const state = view().organizations;
    return state.kind === "ready" ? state.page : undefined;
  };
  const projects = () => {
    const state = view().projects;
    return state.kind === "ready" ? state.page : undefined;
  };

  return <section class="workspace-directory" aria-labelledby="workspace-directory-heading">
    <header class="page-heading"><p class="eyebrow">Your workspace</p>
      <h1 id="workspace-directory-heading">Organizations &amp; projects</h1>
      <p>Choose an organization and project to continue.</p>
    </header>
    <div class="workspace-directory-columns">
      <section class="workspace-directory-panel" aria-labelledby="workspace-organizations-heading">
        <header class="workspace-directory-heading"><span class="workspace-directory-symbol"><WorkspaceSymbol /></span>
          <div><h2 id="workspace-organizations-heading">Organizations</h2><p>The organizations you can access.</p></div>
        </header>
        <Switch>
          <Match when={organizations()}><Show when={organizations()}>{page => <>
            <Show when={page().organizations.length > 0} fallback={<div class="workspace-message" role="status">
              <h3>No organizations yet</h3><p>You do not have access to an organization yet.</p>
            </div>}>
              <ul class="workspace-directory-list" aria-label="Organizations">
                <For each={page().organizations}>{organization => <li class="workspace-directory-row"
                  classList={{ "workspace-row-selected": view().selectedOrganization?.id === organization.id }}>
                  <button type="button" class="workspace-row-button"
                    aria-pressed={view().selectedOrganization?.id === organization.id}
                    onClick={() => props.onSelectOrganization(organization.id)}>
                    <span class="workspace-row-identity"><span class="workspace-row-name"><bdi>{workspaceDisplayName(organization)}</bdi></span>
                      <Show when={organization.display_name !== null}><code><bdi>{organization.id}</bdi></code></Show></span>
                    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 5 7 7-7 7"/></svg>
                  </button>
                  <Roles roles={organization.organization_roles} />
                </li>}</For>
              </ul>
            </Show>
            <Show when={page().next_cursor}>{cursor => <div class="workspace-pagination">
              <p>More organizations are available.</p><button type="button" class="workspace-page-button"
                disabled={!props.onNextOrganizations} onClick={() => props.onNextOrganizations?.(cursor())}>Next organizations</button>
            </div>}</Show>
          </>}</Show></Match>
          <Match when={view().organizations.kind !== "ready"}>
            <DirectoryMessage state={view().organizations as MessageState} onRetry={props.onRetryOrganizations} />
          </Match>
        </Switch>
      </section>
      <section class="workspace-directory-panel" aria-labelledby="workspace-projects-heading">
        <header class="workspace-directory-heading"><span class="workspace-directory-symbol"><WorkspaceSymbol project /></span>
          <div><h2 id="workspace-projects-heading">Projects</h2><p><Show when={view().selectedOrganization}
            fallback="Select an organization to get started.">{organization => <bdi>{workspaceDisplayName(organization())}</bdi>}</Show></p></div>
        </header>
        <Switch>
          <Match when={projects()}><Show when={projects()}>{page => <>
            <Show when={page().projects.length > 0} fallback={<div class="workspace-message" role="status">
              <h3>No accessible projects</h3><p>There are no projects available to your account in this organization.</p>
            </div>}>
              <ul class="workspace-directory-list" aria-label="Projects">
                <For each={page().projects}>{project => <li class="workspace-directory-row"
                  classList={{ "workspace-row-selected": view().selectedProject?.id === project.id }}>
                  <button type="button" class="workspace-row-button"
                    aria-pressed={view().selectedProject?.id === project.id}
                    onClick={() => props.onSelectProject({ organizationId: project.organization_id, projectId: project.id })}>
                    <span class="workspace-row-identity"><span class="workspace-row-name"><bdi>{workspaceDisplayName(project)}</bdi></span>
                      <Show when={project.display_name !== null}><code><bdi>{project.id}</bdi></code></Show></span>
                    <span class="workspace-selection-mark" aria-hidden="true"><Show when={view().selectedProject?.id === project.id}
                      fallback={<svg viewBox="0 0 24 24"><path d="m9 5 7 7-7 7"/></svg>}><svg viewBox="0 0 24 24"><path d="m5 12 4 4L19 6"/></svg></Show></span>
                  </button>
                  <Roles roles={project.roles} project />
                </li>}</For>
              </ul>
            </Show>
            <Show when={page().next_cursor}>{cursor => <div class="workspace-pagination">
              <p>More projects are available.</p><button type="button" class="workspace-page-button"
                disabled={!props.onNextProjects} onClick={() => {
                  const organization = view().selectedOrganization;
                  if (organization) props.onNextProjects?.({ organizationId: organization.id, cursor: cursor() });
                }}>Next projects</button>
            </div>}</Show>
          </>}</Show></Match>
          <Match when={view().projects.kind !== "ready"}>
            <DirectoryMessage state={view().projects as MessageState} project onRetry={props.onRetryProjects ? () => {
              const organization = view().selectedOrganization;
              if (organization) props.onRetryProjects?.(organization.id);
            } : undefined} />
          </Match>
        </Switch>
      </section>
    </div>
    <Show when={view().selectedProject}>{project => <p class="workspace-current-selection" role="status" aria-live="polite" aria-atomic="true">
      <span class="status status-passed"><span class="status-dot" aria-hidden="true"/>Selected project</span>
      <strong><bdi>{workspaceDisplayName(project())}</bdi></strong>
    </p>}</Show>
  </section>;
}
