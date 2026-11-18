import { createSignal, onCleanup, Show } from "solid-js";
import type { CancelBuild } from "../api/build-submission.js";
import type { BuildReadSelection } from "../domain/build-read.js";
import { WorkspaceClientError } from "../api/workspace-transport.js";

type Status = "idle" | "confirm" | "pending" | "denied" | "unknown";

export function CancelBuildForm(props: {
  readonly selection: BuildReadSelection;
  readonly cancel: CancelBuild;
  readonly refresh: () => void;
}) {
  const [status, setStatus] = createSignal<Status>("idle");
  const controller = new AbortController();
  onCleanup(() => controller.abort());

  async function cancel() {
    if (status() !== "confirm") return;
    setStatus("pending");
    try {
      await props.cancel(props.selection, controller.signal);
      if (!controller.signal.aborted) props.refresh();
    } catch (error) {
      if (controller.signal.aborted) return;
      const denied = error instanceof WorkspaceClientError &&
        ["permission_denied", "not_found", "conflict", "unauthenticated"].includes(error.code);
      setStatus(denied ? "denied" : "unknown");
    }
  }

  return <>
    <Show when={status() === "idle"}>
      <button type="button" class="workspace-page-button" onClick={() => setStatus("confirm")}>Cancel build</button>
    </Show>
    <Show when={status() === "confirm"}>
      <p>Cancel this platform build?</p>
      <button type="button" class="workspace-page-button" onClick={() => void cancel()}>Confirm cancellation</button>
      <button type="button" class="workspace-text-button" onClick={() => setStatus("idle")}>Keep build</button>
    </Show>
    <Show when={status() === "pending"}><p role="status">Requesting cancellation…</p></Show>
    <Show when={status() === "denied"}><p role="alert">This build could not be cancelled. Refresh the build to check its current status.</p></Show>
    <Show when={status() === "unknown"}><p role="alert">Cancellation could not be confirmed. Refresh the build to check its current status.</p></Show>
  </>;
}
