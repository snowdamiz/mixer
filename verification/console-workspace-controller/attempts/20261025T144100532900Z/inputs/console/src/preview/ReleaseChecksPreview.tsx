import { createMemo, createSignal } from "solid-js";
import { ReleaseChecks } from "../components/ReleaseChecks.js";
import type { ReleaseCheckInput, ReleaseCheckState } from "../components/ReleaseChecks.js";

/** Synthetic local development data. This module is excluded from production. */
export function example(scenario: string): ReleaseCheckState {
  if (scenario === "loading" || scenario === "unavailable") return { kind: scenario };
  const revision = "sample-current-7c81d9a";
  const expectedTargets = [{ id: "ios-26-build-42", platform: "ios" },
    { id: "android-build-42", platform: "android" }] as const;
  const requiredChecks = ["Compatibility", "Policy review", "Regression tests"];
  const reports: ReleaseCheckInput["reports"][number][] = expectedTargets.flatMap(target =>
    requiredChecks.map(checkId => ({ targetId: target.id, checkId, revision, state: "passed" as const })));
  const change = (index: number, updates: Partial<ReleaseCheckInput["reports"][number]>) => {
    reports[index] = { ...reports[index]!, ...updates };
  };
  if (scenario === "failed") { change(1, { state: "pending" }); change(5, { state: "failed" }); }
  if (scenario === "incomplete") {
    change(0, { revision: "sample-previous-391dbf0", state: "failed" });
    change(1, { state: "pending" }); change(4, { state: "not_run" }); reports.pop();
  }
  if (scenario === "invalid") reports.push({ ...reports[0]! });
  return { kind: "ready", input: { revision, expectedTargets, requiredChecks, reports } };
}

export default function ReleaseChecksPreview() {
  const [scenario, setScenario] = createSignal("failed");
  const state = createMemo(() => example(scenario()));
  return <>
    <aside class="preview-banner" aria-label="Development preview">
      <div><strong>Local preview</strong><p>Synthetic release data. No connected project or release actions.</p></div>
      <label>Example state<select value={scenario()} onChange={event => setScenario(event.currentTarget.value)}>
        <option value="failed">Platform failure</option><option value="incomplete">Incomplete and stale</option>
        <option value="passed">All checks passed</option><option value="loading">Loading</option>
        <option value="unavailable">Unavailable</option><option value="invalid">Invalid data</option>
      </select></label>
    </aside>
    <ReleaseChecks state={state()} />
  </>;
}
