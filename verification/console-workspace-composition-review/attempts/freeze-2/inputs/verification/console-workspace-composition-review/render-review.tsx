import { renderToString } from "solid-js/web";
import { StaticRouter } from "@solidjs/router";
import { ConsoleRoutes, ConsoleShell } from "../../console/src/App.js";
import { WorkspaceProvider, useWorkspace } from "../../console/src/state/workspace-context.js";
import type { WorkspaceSession } from "../../console/src/state/workspace-controller.js";

export function renderReviewRoute(url: string, session?: WorkspaceSession) {
  return renderToString(() => <WorkspaceProvider session={session}>
    <StaticRouter url={url} root={ConsoleShell}><ConsoleRoutes /></StaticRouter>
  </WorkspaceProvider>);
}

export function renderMissingProvider() {
  const Consumer = () => { useWorkspace(); return <p>Should not render</p>; };
  return renderToString(() => <Consumer />);
}
