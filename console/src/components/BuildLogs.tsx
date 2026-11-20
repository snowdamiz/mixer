import { createSignal, For, Match, onCleanup, Show, Switch } from "solid-js";
import type { CookieBuildClient } from "../api/cookie-build-client.js";
import type { BuildLogEvents, BuildLogTarget } from "../domain/build-read.js";

type LogView = { readonly kind: "idle" | "loading" | "unavailable" } |
  { readonly kind: "ready"; readonly events: BuildLogEvents };

export function BuildLogs(props: {
  readonly target: BuildLogTarget;
  readonly readLogs: CookieBuildClient["readLogs"];
}) {
  const [view, setView] = createSignal<LogView>({ kind: "idle" });
  const lifetime = new AbortController();
  onCleanup(() => lifetime.abort());
  const events = () => {
    const value = view();
    return value.kind === "ready" ? value.events : undefined;
  };

  async function load(): Promise<void> {
    const current = view().kind;
    if (lifetime.signal.aborted || (current !== "idle" && current !== "unavailable")) return;
    setView({ kind: "loading" });
    try {
      const result = await props.readLogs(props.target, lifetime.signal);
      if (!lifetime.signal.aborted) setView({ kind: "ready", events: result });
    } catch {
      if (!lifetime.signal.aborted) setView({ kind: "unavailable" });
    }
  }

  return <section class="workspace-message" aria-labelledby="build-logs-heading">
    <h3 id="build-logs-heading">Build logs</h3>
    <Switch>
      <Match when={view().kind === "loading"}>
        <p role="status">Loading build logs</p>
      </Match>
      <Match when={view().kind === "idle" || view().kind === "unavailable"}>
        <Show when={view().kind === "unavailable"}><p role="status">Build logs are unavailable.</p></Show>
        <button type="button" class="workspace-page-button" onClick={load}>
          {view().kind === "unavailable" ? "Retry build logs" : "View build logs"}
        </button>
      </Match>
      <Match when={events()}>{items =>
        <ol aria-label={`Build events for attempt ${props.target.attempt}`}>
          <For each={items()}>{event => event.event !== "build_command_finished" ?
            <li>
              {event.event === "compiler_finished" ? "Compiler" : "Android build driver"} finished (exit code {event.exitCode}).
              <div>{event.stdoutBytes} bytes on stdout and {event.stderrBytes} bytes on stderr.</div>
              <Show when={event.phases.length}><div>Recorded phases were {event.phases.join(", ")}.</div></Show>
              <Show when={event.tailTruncated}><div>The output tail was truncated.</div></Show>
            </li> :
            <li>Build command finished (exit code {event.exitCode}).</li>
          }</For>
        </ol>
      }</Match>
    </Switch>
  </section>;
}
