import { createSignal, Match, onCleanup, onMount, Switch } from "solid-js";
import type { SourceStarterClient } from "../api/cookie-source-starter-client.js";
import type { ApplicationSelection } from "../domain/build-catalog.js";

type State =
  | { kind: "checking" }
  | { kind: "absent" }
  | { kind: "available"; starterId: string }
  | { kind: "selecting" }
  | { kind: "check_failed" }
  | { kind: "selection_failed" };

export function SelectSourceStarter(props: {
  readonly scope: ApplicationSelection;
  readonly client: SourceStarterClient;
  readonly isCurrent: () => boolean;
  readonly refreshInputs: () => void;
  readonly onSelecting: (selecting: boolean) => void;
}) {
  const [state, setState] = createSignal<State>({ kind: "checking" });
  const lifetime = new AbortController();
  onCleanup(() => {
    lifetime.abort();
    if (state().kind === "selecting") props.onSelecting(false);
  });
  const current = () => !lifetime.signal.aborted && props.isCurrent();

  async function discover() {
    if (!current()) return;
    setState({ kind: "checking" });
    try {
      const starter = await props.client.discover(props.scope, lifetime.signal);
      if (current()) setState(starter ? { kind: "available", starterId: starter.id } : { kind: "absent" });
    } catch {
      if (current()) setState({ kind: "check_failed" });
    }
  }
  onMount(() => { void discover(); });

  async function select() {
    const available = state();
    if (!current() || available.kind !== "available") return;
    setState({ kind: "selecting" });
    props.onSelecting(true);
    try {
      await props.client.select({ scope: props.scope, starterId: available.starterId }, lifetime.signal);
      if (current()) {
        props.onSelecting(false);
        props.refreshInputs();
      }
    } catch {
      if (current()) {
        setState({ kind: "selection_failed" });
        props.onSelecting(false);
      }
    }
  }

  return <Switch>
    <Match when={state().kind === "checking"}><p role="status">Checking for a local starter…</p></Match>
    <Match when={state().kind === "available"}>
      <button type="button" class="workspace-page-button" onClick={() => void select()}>Select local starter</button>
    </Match>
    <Match when={state().kind === "selecting"}><p role="status">Selecting local starter…</p></Match>
    <Match when={state().kind === "check_failed"}>
      <p role="alert">Could not check for a local starter.</p>
      <button type="button" class="workspace-text-button" onClick={() => {
        if (state().kind === "check_failed") void discover();
      }}>Retry local starter check</button>
    </Match>
    <Match when={state().kind === "selection_failed"}>
      <p role="alert">Starter selection could not be confirmed. Refresh admitted inputs before trying again.</p>
    </Match>
  </Switch>;
}
