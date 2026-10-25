import { createMemo, createSignal } from "solid-js";
import { BuildOverview } from "../components/BuildOverview.js";
import type { BuildOverviewState } from "../components/BuildOverview.js";
import type { BuildOverviewInput, BuildState, ReportedPlatformBuild } from "../domain/build-overview.js";

/** Synthetic development examples. Only the DEV-only preview route may import this module. */
export function buildExample(scenario: string): BuildOverviewState {
  if (scenario === "loading" || scenario === "unavailable") return { kind: scenario };
  const scope = { organizationId: "sample-organization", projectId: "sample-fieldlog", applicationId: "sample-app" };
  const expected: BuildOverviewInput["expected"] = [
    { platform: "ios", buildId: "sample-ios-build-42", sourceSha256: "a".repeat(64),
      toolchainLockSha256: "b".repeat(64), buildDefinitionSha256: "c".repeat(64),
      source: { kind: "revision", reference: "sample/fieldlog@7c81d9a" } },
    { platform: "android", buildId: "sample-android-build-73", sourceSha256: "d".repeat(64),
      toolchainLockSha256: "e".repeat(64), buildDefinitionSha256: "f".repeat(64),
      source: { kind: "upload", reference: "sample-fieldlog-source.zip" } },
  ];
  const states: readonly BuildState[] = ["queued", "running", "cancelling", "reconciling", "succeeded", "failed", "cancelled", "timed_out"];
  const selected = states.includes(scenario as BuildState) ? scenario as BuildState : "succeeded";
  const reports: ReportedPlatformBuild[] = expected.map(({ source: _source, ...target }, index) => {
    const state = scenario === "mixed" ? index === 0 ? "running" : "failed" : selected;
    return { ...scope, ...target, state, attempt: 2, maxAttempts: 3,
      workerCompletionPending: ["running", "cancelling", "reconciling"].includes(state),
      ...(state === "failed" ? { failureCode: "compiler_error" as const } :
        state === "timed_out" ? { failureCode: "worker_timeout" as const } : {}),
    };
  });
  if (scenario === "missing") reports.pop();
  if (scenario === "empty") reports.length = 0;
  if (scenario === "invalid") reports[1] = { ...reports[1]!, sourceSha256: "0".repeat(64) };
  return { kind: "ready", input: { scope, expected, reports } satisfies BuildOverviewInput };
}

export default function BuildOverviewPreview() {
  const [scenario, setScenario] = createSignal("mixed");
  const state = createMemo(() => buildExample(scenario()));
  return <>
    <aside class="preview-banner" aria-label="Development preview">
      <div><strong>Local preview</strong><p>Synthetic build data. No connected project or build actions.</p></div>
      <label>Example state<select value={scenario()} onChange={event => setScenario(event.currentTarget.value)}>
        <option value="mixed">Running iOS, failed Android</option>
        <option value="queued">Queued</option><option value="running">Running</option>
        <option value="cancelling">Cancelling</option><option value="reconciling">Confirming outcome</option>
        <option value="succeeded">Succeeded</option><option value="failed">Failed</option>
        <option value="cancelled">Cancelled</option><option value="timed_out">Timed out</option>
        <option value="missing">Missing platform update</option><option value="empty">No updates yet</option>
        <option value="loading">Loading</option><option value="unavailable">Unavailable</option>
        <option value="invalid">Invalid data</option>
      </select></label>
    </aside>
    <BuildOverview state={state()} />
  </>;
}
