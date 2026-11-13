import { A } from "@solidjs/router";
import { createMemo, For, Match, Show, Switch } from "solid-js";
import type { BuildCatalogRow } from "../domain/build-catalog.js";
import type { BuildOverviewInput, BuildState } from "../domain/build-overview.js";
import { resolveWorkspaceDirectory, workspaceDisplayName } from "../domain/workspace-directory.js";
import type { WorkspaceDirectoryState } from "../domain/workspace-directory.js";
import type { BuildSelectionBinding } from "../state/build-selection-binding.js";
import type { BuildSelectionState } from "../state/build-selection-controller.js";
import { BuildOverview } from "./BuildOverview.js";
import "./application-build-page.css";

const labels: Record<BuildState, string> = {
  queued: "Queued", running: "Running", cancelling: "Cancelling", reconciling: "Confirming outcome",
  failed: "Failed", cancelled: "Cancelled", timed_out: "Timed out", succeeded: "Succeeded",
};
type Load = BuildSelectionState["applications"] | BuildSelectionState["builds"] | BuildSelectionState["detail"];
function LoadMessage(props: { state: Load; noun: string; onRetrySession: (() => void) | undefined }) {
  const copy = createMemo(() => {
    const state = props.state;
    switch (state.kind) {
      case "loading": return { title: "Loading " + props.noun, detail: "Waiting for the latest information." };
      case "unauthenticated": return { title: "Sign in to continue", detail: "Your session has ended. Sign in, then check your session again." };
      case "unavailable": return { title: "Build data unavailable", detail: "Build information is unavailable right now. Check your session or return to your workspace." };
      case "unselected": return { title: "Choose " + props.noun, detail: "Select a row above to continue." };
      case "error":
        if (state.reason === "permission_denied") return { title: "Build access unavailable", detail: "Your account cannot view this selection. Contact your organization owner if you need help." };
        if (state.reason === "not_found") return { title: "Selection no longer available", detail: "Return to your workspace to choose an available project." };
        return { title: "Could not load " + props.noun, detail: "Return to your workspace and try again." };
      case "ready": case "empty": return { title: "", detail: "" };
    }
  });
  return <div class="workspace-message" role={props.state.kind === "error" ? "alert" : "status"} aria-live="polite">
    <h3>{copy().title}</h3><p>{copy().detail}</p>
    <Show when={props.onRetrySession && (props.state.kind === "unauthenticated" || props.state.kind === "unavailable")}>
      <button type="button" class="workspace-text-button" onClick={() => props.onRetrySession?.()}>Check session</button>
    </Show>
  </div>;
}

/** Displays only the existing owner's current admitted pages and captured selection. */
export function ApplicationBuildPage(props: {
  readonly binding: Readonly<BuildSelectionBinding>;
  readonly workspace: WorkspaceDirectoryState;
  readonly onRetrySession?: () => void;
}) {
  const directory = createMemo(() => resolveWorkspaceDirectory(props.workspace));
  const state = () => props.binding.state();
  const applications = () => { const value = state().applications; return value.kind === "ready" || value.kind === "empty" ? value.page : undefined; };
  const builds = () => { const value = state().builds; return value.kind === "ready" || value.kind === "empty" ? value.page : undefined; };
  const detail = () => { const value = state().detail; return value.kind === "ready" ? value : undefined; };
  const rowSnapshot = (row: BuildCatalogRow) => {
    const current = state().detail, selection = row.selection;
    const value = current.kind === "ready" ? current : "previous" in current ? current.previous : undefined;
    return value && value.selection.organizationId === selection.organizationId &&
      value.selection.projectId === selection.projectId && value.selection.applicationId === selection.applicationId &&
      value.selection.buildId === selection.buildId && value.selection.platform === selection.platform &&
      value.selection.sourceSha256 === selection.sourceSha256 && value.selection.toolchainLockSha256 === selection.toolchainLockSha256 &&
      value.selection.buildDefinitionSha256 === selection.buildDefinitionSha256 && value.snapshot.revision >= row.snapshot.revision
      ? value.snapshot : row.snapshot;
  };
  const overview = createMemo((): BuildOverviewInput | undefined => {
    const value = detail();
    if (!value) return undefined;
    const { selection, snapshot } = value;
    return {
      scope: { organizationId: selection.organizationId, projectId: selection.projectId, applicationId: selection.applicationId },
      expected: [{ platform: selection.platform, buildId: selection.buildId, sourceSha256: selection.sourceSha256,
        toolchainLockSha256: selection.toolchainLockSha256, buildDefinitionSha256: selection.buildDefinitionSha256 }],
      reports: [snapshot.report],
    };
  });
  return <section class="application-build-page" aria-labelledby="application-build-heading">
    <header class="page-heading"><p class="eyebrow">Your project</p><h1 id="application-build-heading">Application builds</h1>
      <p>Choose an application, then a platform build to view its latest outcome.</p></header>
    <nav class="application-build-context" aria-label="Build workspace">
      <A href="/workspace">Organizations &amp; projects</A>
      <Show when={directory().selectedOrganization}>{organization => <span><bdi>{workspaceDisplayName(organization())}</bdi></span>}</Show>
      <Show when={directory().selectedProject}>{project => <strong><bdi>{workspaceDisplayName(project())}</bdi></strong>}</Show>
    </nav>
    <Show when={directory().selectedProject} fallback={<div class="workspace-message" role="status">
      <h2>Choose a project</h2><p>Select an organization and project in your workspace to view applications and builds.</p>
      <A class="workspace-page-button" href="/workspace">Go to workspace</A>
      <Show when={state().applications.kind === "unavailable" || state().applications.kind === "unauthenticated"}>
        <LoadMessage state={state().applications} noun="applications" onRetrySession={props.onRetrySession} />
      </Show>
    </div>}>
      <div class="application-build-columns">
        <section class="workspace-directory-panel" aria-labelledby="application-list-heading" aria-busy={state().applications.kind === "loading"}>
          <header class="workspace-directory-heading"><div><h2 id="application-list-heading">Applications</h2><p>Application IDs in this project.</p></div></header>
          <Show when={applications()} fallback={<LoadMessage state={state().applications} noun="applications" onRetrySession={props.onRetrySession} />}>{page => <>
            <Show when={page().applications.length} fallback={<div class="workspace-message" role="status"><h3>No applications yet</h3><p>This project has no applications to display.</p></div>}>
              <ul class="workspace-directory-list" aria-label="Applications"><For each={page().applications}>{row => <li class="workspace-directory-row" classList={{ "workspace-row-selected": state().selectedApplicationId === row.applicationId }}>
                <button type="button" class="workspace-row-button" aria-current={state().selectedApplicationId === row.applicationId ? "true" : undefined}
                  onClick={() => props.binding.controller.selectApplication(row.applicationId)}>
                  <span class="workspace-row-identity"><span>Application ID</span><code><bdi>{row.applicationId}</bdi></code></span><span aria-hidden="true">→</span>
                </button>
              </li>}</For></ul>
            </Show>
            <div class="workspace-pagination"><button type="button" class="workspace-page-button" onClick={props.binding.controller.firstApplications}>First applications</button>
              <Show when={page().nextCursor !== null}><button type="button" class="workspace-page-button" onClick={props.binding.controller.nextApplications}>More applications</button></Show></div>
          </>}</Show>
        </section>
        <section class="workspace-directory-panel" aria-labelledby="platform-build-list-heading" aria-busy={state().builds.kind === "loading"}>
          <header class="workspace-directory-heading"><div><h2 id="platform-build-list-heading">Platform builds</h2><p><Show when={state().selectedApplicationId} fallback="Choose an application to see its builds.">{id => <>Application ID <code><bdi>{id()}</bdi></code></>}</Show></p></div></header>
          <Show when={builds()} fallback={<LoadMessage state={state().builds} noun="a platform build" onRetrySession={props.onRetrySession} />}>{page => <>
            <Show when={page().builds.length} fallback={<div class="workspace-message" role="status"><h3>No builds yet</h3><p>This application has no stored builds.</p></div>}>
              <ul class="workspace-directory-list" aria-label="Platform builds"><For each={page().builds}>{row => <li class="workspace-directory-row">
                <button type="button" class="workspace-row-button" aria-current={detail()?.selection.buildId === row.selection.buildId && detail()?.selection.platform === row.selection.platform ? "true" : undefined}
                  onClick={() => props.binding.controller.selectBuild({ buildId: row.selection.buildId, platform: row.selection.platform })}>
                  <span class="workspace-row-identity"><strong>{row.selection.platform === "ios" ? "iOS" : "Android"}</strong><code><bdi>{row.selection.buildId}</bdi></code>
                    <span>{labels[rowSnapshot(row).report.state]}</span><Show when={rowSnapshot(row).report.workerCompletionPending}><span>Waiting for the build worker to finish.</span></Show>
                  </span><span aria-hidden="true">→</span>
                </button>
              </li>}</For></ul>
            </Show>
            <div class="workspace-pagination"><button type="button" class="workspace-page-button" onClick={props.binding.controller.firstBuilds}>First builds</button>
              <Show when={page().nextCursor !== null}><button type="button" class="workspace-page-button" onClick={props.binding.controller.nextBuilds}>More builds</button></Show></div>
          </>}</Show>
        </section>
      </div>
      <section class="application-build-detail" aria-label="Selected build" aria-busy={state().detail.kind === "loading"}>
        <Show when={overview()} fallback={<LoadMessage state={state().detail} noun="a build" onRetrySession={props.onRetrySession} />}>{input => <>
          <div class="application-build-detail-actions"><h2>Selected platform build</h2><button type="button" class="workspace-page-button" onClick={props.binding.controller.refreshSelected}>Refresh build</button></div>
          <Show when={detail()?.snapshot.report.workerCompletionPending}><p class="workspace-message" role="status">Waiting for the build worker to finish. The outcome is still being confirmed.</p></Show>
          <BuildOverview state={{ kind: "ready", input: input() }} />
        </>}</Show>
      </section>
    </Show>
  </section>;
}
