import { createEffect, createResource, createSignal, on, onCleanup, Show } from "solid-js";
import { isMemberRole } from "../api/cookie-workspace-admin-client.js";
import type { WorkspaceAdminClient, WorkspaceAdminInput, WorkspaceAdminResult } from "../api/cookie-workspace-admin-client.js";
import { WorkspaceClientError } from "../api/workspace-transport.js";
import { isWorkspaceIdentifier, workspaceDisplayName } from "../domain/workspace-directory.js";
import type { WorkspaceOrganization, WorkspaceProject } from "../domain/workspace-directory.js";

function refusal(error: unknown): string {
  switch (error instanceof WorkspaceClientError ? error.code : undefined) {
    case "permission_denied": return "Your role cannot perform this action.";
    case "not_found": return "The requested workspace record is unavailable.";
    case "conflict": return "The current workspace state prevents this action.";
    case "quota_exceeded": return "The workspace has reached its quota.";
    default: return "The workspace request failed. Refresh before trying again.";
  }
}

type Action =
  | { readonly kind: "pending" | "success" | "error"; readonly message: string }
  | undefined;

export function WorkspaceAdministration(props: {
  readonly client: WorkspaceAdminClient;
  readonly organization: WorkspaceOrganization;
  readonly project: WorkspaceProject | null;
  readonly usageRevision: number;
  readonly onEligibilityChange: (eligible: boolean) => void;
  readonly archiveProject: (organizationId: string, projectId: string) => Promise<WorkspaceAdminResult>;
  readonly onDeleteOrganization: () => void;
}) {
  const organizationId = props.organization.id;
  const abort = new AbortController();
  onCleanup(() => abort.abort());
  const [action, setAction] = createSignal<Action>();
  const [confirmOrganization, setConfirmOrganization] = createSignal(false);
  const [confirmation, setConfirmation] = createSignal("");
  const [archiveTarget, setArchiveTarget] = createSignal<WorkspaceProject>();
  createEffect(on(() => props.project?.id, () => setArchiveTarget(undefined), { defer: true }));
  const [usage, { refetch }] = createResource(() => props.usageRevision, async () => {
    try {
      const result = await props.client.request({ kind: "usage", organizationId }, abort.signal);
      if (result.kind === "usage") return { kind: "ready", counts: result.usage, canAdminister: result.canAdminister } as const;
      return { kind: "error", message: "Usage is unavailable." } as const;
    } catch (error) {
      if (error instanceof WorkspaceClientError && error.code === "not_found") return { kind: "hidden" } as const;
      return { kind: "error", message: refusal(error) } as const;
    }
  });
  const usageCounts = () => {
    const value = usage();
    return value?.kind === "ready" ? value.counts : undefined;
  };

  async function submit(input: WorkspaceAdminInput, pending: string,
    complete: (result: WorkspaceAdminResult) => string) {
    if (action()?.kind === "pending") return;
    setAction({ kind: "pending", message: pending });
    try {
      const result = input.kind === "delete_project"
        ? await props.archiveProject(input.organizationId, input.projectId)
        : await props.client.request(input, abort.signal);
      if (!abort.signal.aborted) setAction({ kind: "success", message: complete(result) });
    } catch (error) {
      if (!abort.signal.aborted) setAction({ kind: "error", message: refusal(error) });
    }
  }

  function download(result: WorkspaceAdminResult) {
    if (result.kind !== "export") throw new WorkspaceClientError("invalid_response");
    const url = URL.createObjectURL(new Blob([JSON.stringify(result.data, null, 2) + "\n"], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `${organizationId}-export.json`;
    try { link.click(); }
    finally { setTimeout(() => URL.revokeObjectURL(url), 0); }
    return "Workspace export prepared.";
  }

  const usageError = () => {
    const value = usage();
    return value?.kind === "error" ? value.message : undefined;
  };
  const selectedArchiveTarget = () => {
    const target = archiveTarget();
    return target?.id === props.project?.id ? target : undefined;
  };

  const canAdminister = () => {
    const value = usage();
    return value?.kind === "ready" && value.canAdminister;
  };

  createEffect(() => props.onEligibilityChange(canAdminister()));
  onCleanup(() => props.onEligibilityChange(false));

  return <Show when={usage()?.kind !== "hidden"}><section class="workspace-current-selection" aria-label="Workspace administration">
    <h2>Workspace administration</h2>
    <h3>Free plan usage</h3>
    <Show when={usageCounts()}>{counts =>
      <dl>
        <dt>Active projects</dt><dd>{counts().active_projects} of {counts().project_limit}</dd>
        <dt>Concurrent build capacity</dt><dd>{counts().held_builds} of {counts().build_limit} reserved</dd>
        <dt>Build records</dt><dd>{counts().builds}</dd>
      </dl>
    }</Show>
    <Show when={usage.loading}><p role="status">Loading usage…</p></Show>
    <Show when={usageError()}>{message =>
      <p role="alert">{message()}</p>
    }</Show>
    <button class="workspace-page-button" type="button" disabled={usage.loading} onClick={() => void refetch()}>Refresh usage</button>

    <Show when={canAdminister()}>
      <h3>Membership</h3>
      <form class="workspace-create-form" onSubmit={event => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        const principalId = data.get("principal");
        const role = data.get("role");
        if (!isWorkspaceIdentifier(principalId) || !isMemberRole(role)) {
          setAction({ kind: "error", message: "Enter a registered principal ID and choose a role." });
          return;
        }
        void submit({ kind: "set_member", organizationId, principalId, role }, "Saving role…", () => "Membership role saved.");
      }}>
        <label>Registered principal ID <input name="principal" required maxLength={128} disabled={action()?.kind === "pending"} /></label>
        <label>Organization role <select name="role" disabled={action()?.kind === "pending"}>
          <option value="viewer">Viewer</option>
          <option value="developer">Developer</option>
          <option value="administrator">Administrator</option>
        </select></label>
        <button class="workspace-page-button" type="submit" disabled={action()?.kind === "pending"}>Save role</button>
      </form>

      <h3>Export and deletion</h3>
      <p>The JSON export contains organization, project, and membership records.</p>
      <button class="workspace-page-button" type="button" disabled={action()?.kind === "pending"}
        onClick={() => void submit({ kind: "export", organizationId }, "Preparing export…", download)}>Download workspace export</button>
      <Show when={props.project}>{project =>
        <button class="workspace-page-button" type="button" disabled={action()?.kind === "pending"}
          onClick={() => setArchiveTarget(project())}>Archive selected project</button>
      }</Show>
      <Show when={selectedArchiveTarget()} keyed>{target =>
        <div role="group" aria-label="Confirm project archival">
          <p>Archive <strong><bdi>{workspaceDisplayName(target)}</bdi></strong>? It will disappear from the project directory. Its archived record remains in the export.</p>
          <button class="workspace-page-button" type="button" disabled={action()?.kind === "pending"} onClick={() => {
            void submit({ kind: "delete_project", organizationId, projectId: target.id }, "Archiving project…", () => {
              setArchiveTarget(undefined);
              return "Project archived.";
            });
          }}>Confirm archive</button>
          <button class="workspace-page-button" type="button" disabled={action()?.kind === "pending"}
            onClick={() => setArchiveTarget(undefined)}>Cancel</button>
        </div>
      }</Show>
      <button class="workspace-page-button" type="button" disabled={action()?.kind === "pending"}
        onClick={() => { setConfirmation(""); setConfirmOrganization(true); }}>Delete organization</button>
      <Show when={confirmOrganization()}>
        <form class="workspace-create-form" aria-label="Confirm organization deletion" onSubmit={event => {
          event.preventDefault();
          void submit({ kind: "delete_organization", organizationId, confirmation: confirmation() },
            "Deleting organization…", result => {
              if (result.kind !== "delete_organization") throw new WorkspaceClientError("invalid_response");
              props.onDeleteOrganization();
              return "Organization deleted.";
            });
        }}>
          <p>Deleting <strong><bdi>{workspaceDisplayName(props.organization)}</bdi></strong> removes access for all members.
            Download the export first. Records are retained. Settle any queued builds or unresolved workers before deleting.</p>
          <p>Enter the organization ID <code>{organizationId}</code> to confirm.</p>
          <label>Organization ID <input value={confirmation()} required maxLength={128}
            disabled={action()?.kind === "pending"} onInput={event => setConfirmation(event.currentTarget.value)} /></label>
          <button class="workspace-page-button" type="submit"
            disabled={confirmation() !== organizationId || action()?.kind === "pending"}>Confirm deletion</button>
          <button class="workspace-page-button" type="button" disabled={action()?.kind === "pending"}
            onClick={() => setConfirmOrganization(false)}>Cancel</button>
        </form>
      </Show>
    </Show>
    <Show when={action()}>{status =>
      <p role={status().kind === "error" ? "alert" : "status"}>{status().message}</p>
    }</Show>
  </section></Show>;
}
