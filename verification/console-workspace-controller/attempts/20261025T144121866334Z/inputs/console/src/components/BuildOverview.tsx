import { createMemo, For, Match, Show, Switch } from "solid-js";
import { summarizeBuildOverview } from "../domain/build-overview.js";
import type { BuildFailureCode, BuildState } from "../domain/build-overview.js";
import "./build-overview.css";

export type BuildOverviewState =
  | { readonly kind: "loading" }
  | { readonly kind: "unavailable" }
  | { readonly kind: "ready"; readonly input: unknown };

const stateCopy: Record<BuildState | "not_reported", { label: string; detail: string; tone: string }> = {
  queued: { label: "Queued", detail: "Waiting to start.", tone: "pending" },
  running: { label: "Running", detail: "Build in progress.", tone: "pending" },
  cancelling: { label: "Cancelling", detail: "Cancellation requested. Waiting for the build to stop.", tone: "pending" },
  reconciling: { label: "Confirming outcome", detail: "The deadline has passed. Confirming whether the build has stopped.", tone: "pending" },
  succeeded: { label: "Succeeded", detail: "This platform build completed successfully.", tone: "passed" },
  failed: { label: "Failed", detail: "This platform build failed. Review the reported cause below.", tone: "failed" },
  cancelled: { label: "Cancelled", detail: "This platform build was cancelled.", tone: "neutral" },
  timed_out: { label: "Timed out", detail: "This attempt exceeded its deadline.", tone: "failed" },
  not_reported: { label: "Not reported", detail: "No update received for this exact platform build and source content.", tone: "neutral" },
};

const failureCopy: Record<BuildFailureCode, string> = {
  worker_unavailable: "A build worker was unavailable. Review the build diagnostics for the infrastructure failure.",
  worker_lost: "The build worker was lost. Review the build diagnostics before requesting another attempt.",
  dependency_transport: "A dependency could not be transferred. Review dependency access and the build diagnostics.",
  artifact_transport: "Build output could not be transferred. Review the build diagnostics for the transfer failure.",
  worker_timeout: "The worker exceeded the build deadline. Review the build diagnostics and configured timeout.",
  compiler_error: "Compilation failed. Review the compiler diagnostics and correct the source before building again.",
  test_failure: "Tests failed. Review the test diagnostics and correct the failing tests before building again.",
  policy_rejection: "A build policy check rejected this attempt. Review the policy diagnostics before building again.",
  invalid_input: "The build input was rejected. Review the input diagnostics and build configuration.",
  unknown_failure: "The failure could not be classified. Review the build diagnostics to identify the cause.",
};

function Status(props: { state: BuildState | "not_reported" }) {
  return <span class={`status status-${stateCopy[props.state].tone}`}>
    <span class="status-dot" aria-hidden="true" />{stateCopy[props.state].label}
  </span>;
}

/** Read-only status display. Reports never define the selected platforms or build identity. */
export function BuildOverview(props: { state: BuildOverviewState }) {
  const result = createMemo(() => {
    try {
      const state = props.state;
      if (state?.kind === "loading" || state?.kind === "unavailable") return { kind: state.kind } as const;
      if (state?.kind !== "ready") return { kind: "invalid" } as const;
      return { kind: "ready", summary: summarizeBuildOverview(state.input) } as const;
    } catch {
      return { kind: "invalid" } as const;
    }
  });
  const summary = () => {
    const value = result();
    return value.kind === "ready" ? value.summary : undefined;
  };

  return <section aria-labelledby="build-overview-heading" class="build-overview">
    <header class="page-heading"><p class="eyebrow">Build workspace</p>
      <h1 id="build-overview-heading">Builds</h1>
      <p>Follow each platform build, from its first attempt to its reported outcome.</p>
    </header>
    <Switch>
      <Match when={result().kind === "loading"}>
        <div class="empty-state" role="status"><h2>Loading builds</h2>
          <p>Waiting for the selected builds and their platform updates.</p></div>
      </Match>
      <Match when={result().kind === "unavailable"}>
        <div class="empty-state" role="status"><h2>Build data unavailable</h2>
          <p>No build data source is connected to this console yet.</p>
          <p>Platform updates will appear here when build data is available.</p></div>
      </Match>
      <Match when={result().kind === "invalid"}>
        <div class="empty-state invalid-state" role="alert"><h2>Build updates could not be displayed</h2>
          <p>The data does not match the selected builds or contains an unsupported status. No build overview is available.</p></div>
      </Match>
      <Match when={summary()}><Show when={summary()}>{value => <>
        <div class="build-coverage" role="status" aria-live="polite" aria-atomic="true">
          <div><p class="eyebrow">Platform updates</p>
            <h2>{value().reportedCount === 0 ? "No build updates yet" :
              `${value().reportedCount} of ${value().builds.length} platforms reported`}</h2>
            <p>{value().reportedCount < value().builds.length ?
              "The selected platform builds remain below, including updates that have not arrived." :
              "Review the status of each selected platform below."}</p></div>
          <span class="build-coverage-count" aria-label={`${value().reportedCount} of ${value().builds.length} platform updates received`}>
            {value().reportedCount}<span aria-hidden="true"> / {value().builds.length}</span>
          </span>
        </div>
        <div class="target-list build-list">
          <For each={value().builds}>{row => <section class={`target-card build-card build-${row.observation?.state ?? "not_reported"}`}
            aria-label={`${row.target.platform === "ios" ? "iOS" : "Android"} build ${row.target.buildId}`}>
            <header class="target-heading">
              <div class="target-identity"><span class="platform-symbol" aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="6" y="2" width="12" height="20" rx={row.target.platform === "ios" ? "3" : "1.5"}/><path d="M10 5h4m-3 14h2"/></svg></span>
                <div><h2>{row.target.platform === "ios" ? "iOS" : "Android"}</h2><p class="target-id">{row.target.buildId}</p></div></div>
              <Status state={row.observation?.state ?? "not_reported"} />
            </header>
            <div class="build-content">
              <p class="build-state-detail">{stateCopy[row.observation?.state ?? "not_reported"].detail}</p>
              <Show when={row.observation?.failureCode}>{code => <p class="build-failure">{failureCopy[code()]}</p>}</Show>
              <dl class="build-context">
                <div><dt>Attempt</dt><dd>{row.observation ? `${row.observation.attempt} of ${row.observation.maxAttempts}` : "Not reported"}</dd></div>
                <Show when={row.target.source}>{source => <div><dt>{source().kind === "revision" ? "Source reference" : "Upload reference"}</dt><dd><code>{source().reference}</code></dd></div>}</Show>
              </dl>
              <details class="build-identity"><summary>Immutable build inputs</summary>
                <dl><div class="build-source-digest"><dt>Source content SHA-256</dt><dd><code>{row.target.sourceSha256}</code></dd></div>
                  <div><dt>Toolchain lock SHA-256</dt><dd><code>{row.target.toolchainLockSha256}</code></dd></div>
                  <div><dt>Build definition SHA-256</dt><dd><code>{row.target.buildDefinitionSha256}</code></dd></div></dl>
              </details>
            </div>
          </section>}</For>
        </div>
        <p class="page-note">Build status is separate from signing and distribution.</p>
      </>}</Show></Match>
    </Switch>
  </section>;
}
