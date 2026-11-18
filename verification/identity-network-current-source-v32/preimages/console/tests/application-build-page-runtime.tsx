import { createSignal, onCleanup } from "solid-js";
import { render, clearDelegatedEvents } from "solid-js/web";
import { MemoryRouter, createMemoryHistory } from "@solidjs/router";
import { ConsoleRoutes, ConsoleShell } from "../src/App.js";
import { WorkspaceProvider } from "../src/state/workspace-context.js";
import { createBrowserSessionController } from "../src/state/browser-session-controller.js";
import type { BrowserSessionClientOptions } from "../src/api/browser-session-client.js";
export function mount(container: HTMLElement, fetch: NonNullable<BrowserSessionClientOptions["fetch"]>) {
  const controller = createBrowserSessionController({ fetch });
  const history = createMemoryHistory();
  history.set({ value: "/workspace", replace: true, scroll: false });
  const dispose = render(() => {
    const [session, setSession] = createSignal(controller.getSession());
    const unsubscribe = controller.subscribe(value => setSession(value));
    onCleanup(unsubscribe);
    return <WorkspaceProvider session={session()} onRetrySession={controller.revalidate}>
      <MemoryRouter history={history} preload={false} root={ConsoleShell}>
        <ConsoleRoutes session={session()} onRetrySession={controller.revalidate} />
      </MemoryRouter>
    </WorkspaceProvider>;
  }, container);
  controller.revalidate();
  return { history, controller, dispose() { dispose(); controller.dispose(); clearDelegatedEvents(); } };
}
