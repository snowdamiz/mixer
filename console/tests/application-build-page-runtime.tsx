import { createSignal, onCleanup } from "solid-js";
import { render, clearDelegatedEvents, delegateEvents } from "solid-js/web";
import { MemoryRouter, createMemoryHistory } from "@solidjs/router";
import { ConsoleRoutes, ConsoleShell } from "../src/App.js";
import { WorkspaceProvider, useWorkspace } from "../src/state/workspace-context.js";
import { createBrowserSessionController } from "../src/state/browser-session-controller.js";
import type { BrowserSessionClientOptions } from "../src/api/browser-session-client.js";
import { SignInBoundary } from "../src/components/SignIn.js";
export { applyPromotionResume } from "../src/state/promotion-resume.js";
export function mount(
  container: HTMLElement,
  fetch: NonNullable<BrowserSessionClientOptions["fetch"]>,
  profile?: "workspace-manage" | "workspace-builds",
  initialPath = "/workspace",
  withSignIn = false,
) {
  // Earlier mounts clear document-level handlers when their fixture closes.
  if (profile) delegateEvents(["input", "submit"]);
  if (withSignIn) delegateEvents(["click"]);
  const controller = createBrowserSessionController({ fetch }, profile);
  const history = createMemoryHistory();
  history.set({ value: initialPath, replace: true, scroll: false });
  let workspace: ReturnType<typeof useWorkspace>;
  function Routes(props: { session: ReturnType<typeof controller.getSession> }) {
    workspace = useWorkspace();
    return <ConsoleRoutes session={props.session} onRetrySession={controller.revalidate} />;
  }
  const dispose = render(() => {
    const [session, setSession] = createSignal(controller.getSession());
    const unsubscribe = controller.subscribe(value => setSession(value));
    onCleanup(unsubscribe);
    const console = () => <WorkspaceProvider session={session()} onRetrySession={controller.revalidate}>
      <MemoryRouter history={history} preload={false} root={ConsoleShell}>
        <Routes session={session()} />
      </MemoryRouter>
    </WorkspaceProvider>;
    return withSignIn
      ? <SignInBoundary session={session} invalidate={controller.invalidate}>{console()}</SignInBoundary>
      : console();
  }, container);
  controller.revalidate();
  return { history, controller,
    selectProject(scope: Parameters<typeof workspace.controller.selectProject>[0]) { workspace.controller.selectProject(scope); },
    dispose() { dispose(); controller.dispose(); clearDelegatedEvents(); },
  };
}
