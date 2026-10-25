import { createMemo, For, Match, Show, Switch } from "solid-js";
import { summarizeReleaseChecks } from "../domain/release-check-summary.js";
import type {
  DisplayState, ReleaseTarget, ReportedCheck, SummaryState,
} from "../domain/release-check-summary.js";

export interface ReleaseCheckInput {
  readonly revision: string;
  readonly expectedTargets: readonly ReleaseTarget[];
  readonly requiredChecks: readonly string[];
  readonly reports: readonly ReportedCheck[];
}

export type ReleaseCheckState =
  | { readonly kind: "loading" }
  | { readonly kind: "unavailable" }
  | { readonly kind: "ready"; readonly input: ReleaseCheckInput };

const stateLabels: Record<DisplayState | "incomplete", string> = {
  passed: "Passed", failed: "Failed", pending: "Pending", not_run: "Not run",
  stale: "Previous revision", incomplete: "Incomplete",
};
const summaryCopy: Record<SummaryState, { title: string; detail: string }> = {
  failed: {
    title: "Checks failed",
    detail: "A required check failed for this revision. Review the affected target below.",
  },
  incomplete: {
    title: "Checks incomplete",
    detail: "Some required results are pending, missing, or from a previous revision.",
  },
  passed: {
    title: "Checks passed",
    detail: "Every required check reports a pass for this revision. Release approval is evaluated separately.",
  },
};

function Status(props: { state: DisplayState | "incomplete" }) {
  return <span class={`status status-${props.state}`}>
    <span class="status-dot" aria-hidden="true" />{stateLabels[props.state]}
  </span>;
}

/** Read-only display. Expected requirements come from the caller, never reports. */
export function ReleaseChecks(props: { state: ReleaseCheckState }) {
  const result = createMemo(() => {
    try {
      const state = props.state;
      if (state?.kind === "loading" || state?.kind === "unavailable") return { kind: state.kind } as const;
      if (state?.kind !== "ready") return { kind: "invalid" } as const;
      const input = state.input;
      return { kind: "ready", summary: summarizeReleaseChecks(input.revision,
        input.expectedTargets, input.requiredChecks, input.reports) } as const;
    } catch {
      return { kind: "invalid" } as const;
    }
  });
  const summary = () => {
    const value = result();
    return value.kind === "ready" ? value.summary : undefined;
  };

  return <section aria-labelledby="release-checks-heading" class="release-checks">
    <header class="page-heading">
      <p class="eyebrow">Release review</p>
      <h1 id="release-checks-heading">Release checks</h1>
      <p>Compatibility, policy, and test results for every target binary.</p>
    </header>
    <Switch>
      <Match when={result().kind === "loading"}>
        <div class="empty-state" role="status"><h2>Loading release checks</h2>
          <p>Waiting for the selected release and its required checks.</p></div>
      </Match>
      <Match when={result().kind === "unavailable"}>
        <div class="empty-state" role="status"><h2>Release data unavailable</h2>
          <p>No release data source is connected to this console yet.</p>
          <p>Checks will appear here when a release is available.</p></div>
      </Match>
      <Match when={result().kind === "invalid"}>
        <div class="empty-state invalid-state" role="alert"><h2>Check results could not be displayed</h2>
          <p>The release data is incomplete or inconsistent. No check summary is available.</p></div>
      </Match>
      <Match when={summary()}>
        <Show when={summary()}>{value => <>
          <div class={`summary-banner summary-${value().state}`} role="status" aria-live="polite" aria-atomic="true">
            <div><p class="eyebrow">Required checks</p>
              <h2>{summaryCopy[value().state].title}</h2>
              <p>{summaryCopy[value().state].detail}</p></div>
            <Status state={value().state} />
          </div>
          <dl class="release-context">
            <div><dt>Selected source revision</dt><dd><code>{value().revision}</code></dd></div>
            <div><dt>Target binaries</dt><dd>{value().targets.length}</dd></div>
            <div><dt>Required results</dt><dd>{value().targets.reduce((total, target) => total + target.checks.length, 0)}</dd></div>
          </dl>
          <div class="target-list">
            <For each={value().targets}>{target => <section class="target-card" aria-label={`${target.platform === "ios" ? "iOS" : "Android"} target ${target.id}`}>
              <header class="target-heading">
                <div class="target-identity"><span class="platform-symbol" aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="6" y="2" width="12" height="20" rx={target.platform === "ios" ? "3" : "1.5"}/><path d="M10 5h4m-3 14h2"/></svg></span>
                  <div><h2>{target.platform === "ios" ? "iOS" : "Android"}</h2><p class="target-id">{target.id}</p></div></div>
                <Status state={target.state} />
              </header>
              <table>
                <caption class="sr-only">Required checks for {target.id}</caption>
                <thead><tr><th scope="col">Check</th><th scope="col">Result</th><th scope="col">Reported evidence</th></tr></thead>
                <tbody><For each={target.checks}>{check => <tr class={`check-${check.state}`}>
                  <th scope="row">{check.checkId}</th>
                  <td><Status state={check.state} /></td>
                  <td class="evidence-cell">
                    <Show when={check.reportedRevision !== null} fallback={<span>No result received</span>}>
                      <Switch>
                        <Match when={check.state === "stale"}><p>Previously {check.reportedState === null ? "unreported" : stateLabels[check.reportedState].toLowerCase()}. Does not cover the selected revision.</p></Match>
                        <Match when={check.state === "pending"}><p>Waiting for completion.</p></Match>
                        <Match when={check.state === "not_run"}><p>Reported as not run.</p></Match>
                      </Switch>
                      <code>{check.reportedRevision}</code>
                    </Show>
                  </td>
                </tr>}</For></tbody>
              </table>
            </section>}</For>
          </div>
          <p class="page-note">Results apply to the source revision shown. Missing and previous-revision results do not count as a pass.</p>
        </>}</Show>
      </Match>
    </Switch>
  </section>;
}
