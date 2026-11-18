import { For, Show } from "solid-js";
import type { BuildSelectionActions } from "../state/build-selection-binding.js";
import type { SubmissionState } from "../state/build-selection-controller.js";

export function BuildCreation(props: { state: SubmissionState | undefined; actions: Readonly<BuildSelectionActions> }) {
  const page = () => { const s = props.state; return s?.kind === "ready" || s?.kind === "submitting" || s?.kind === "unknown" ? s.page : undefined; };
  const selected = () => { const s = props.state; return s?.kind === "ready" ? s.input : s?.kind === "submitting" || s?.kind === "unknown" ? s.attempt.input : undefined; };
  const platforms = () => [...new Set(page()?.inputs.map(row => row.platform) ?? [])];
  const submitting = () => props.state?.kind === "submitting";
  const error = () => { const s = props.state; return s?.kind === "error" ? s.reason : undefined; };
  return <section class="workspace-directory-panel" aria-label="Create a build" aria-busy={submitting() || props.state?.kind === "loading"}>
    <h2>Create a build</h2>
    <p>Choose an admitted source input for this application. Submission checks your current permission again.</p>
    <Show when={!props.state || props.state.kind === "error" || props.state.kind === "committed"}>
      <button type="button" class="workspace-page-button" onClick={props.actions.beginCreate}>New build</button>
    </Show>
    <Show when={props.state?.kind === "loading"}><p role="status">Loading admitted inputs…</p></Show>
    <Show when={error()}>{reason => <p role="alert">{reason() === "permission_denied"
      ? "Build creation is read-only for this session. You can still view available builds."
      : reason() === "not_found" ? "This application is no longer available for creation."
      : reason() === "invalid_request" ? "The server refused this submission. Refresh admitted inputs before starting a new build."
      : "Admitted inputs are unavailable. Try loading them again."}</p>}</Show>
    <Show when={page()}>{current => <>
      <Show when={current().inputs.length > 0} fallback={<p role="status">No admitted source inputs. Build creation is unavailable for this application.</p>}>
        <For each={platforms()}>{platform => <fieldset disabled={submitting()}>
          <legend>{platform === "ios" ? "iOS" : "Android"}</legend>
          <For each={current().inputs.filter(row => row.platform === platform)}>{row => <div>
            <button type="button" class="workspace-row-button" aria-pressed={selected()?.platform === row.platform && selected()?.sourceInputId === row.sourceInputId}
              disabled={submitting()} onClick={() => props.actions.selectInput(row.platform, row.sourceInputId)}>
              <span>Input <code><bdi>{row.sourceInputId}</bdi></code> · Source <code title={row.sourceSha256}>{row.sourceSha256.slice(0, 12)}</code></span>
            </button>
            <details><summary>Full input digests for <bdi>{row.sourceInputId}</bdi></summary>
              <dl><dt>Source SHA-256</dt><dd><code>{row.sourceSha256}</code></dd>
                <dt>Toolchain lock SHA-256</dt><dd><code>{row.toolchainLockSha256}</code></dd>
                <dt>Build definition SHA-256</dt><dd><code>{row.buildDefinitionSha256}</code></dd></dl>
            </details>
          </div>}</For>
        </fieldset>}</For>
      </Show>
      <Show when={props.state?.kind === "ready"}>
        <button type="button" class="workspace-page-button" disabled={!selected()} onClick={props.actions.submitBuild}>Create build</button>
        <Show when={current().nextCursor !== null}><button type="button" class="workspace-page-button" onClick={props.actions.nextInputs}>More admitted inputs</button></Show>
        <button type="button" class="workspace-text-button" onClick={props.actions.beginCreate}>Refresh admitted inputs</button>
      </Show>
    </>}</Show>
    <Show when={submitting()}><p role="status">Submitting build…</p><button type="button" onClick={props.actions.cancelSubmit}>Stop waiting</button></Show>
    <Show when={props.state?.kind === "unknown"}>
      <p role="alert">Submission outcome unknown. The server may have committed the build. Retry this same submission to check; stopping did not roll it back.</p>
      <button type="button" class="workspace-page-button" onClick={props.actions.retrySubmit}>Retry same submission</button>
    </Show>
    <Show when={props.state?.kind === "committed" ? props.state.receipt : undefined}>{receipt => <p role="status">
      Submission confirmed for build <code><bdi>{receipt().selection.buildId}</bdi></code>.
    </p>}</Show>
  </section>;
}
