import { renderToString } from "solid-js/web";
import { StaticRouter } from "@solidjs/router";
import { ConsoleRoutes, ConsoleShell } from "../src/App.js";
import { WorkspaceProvider } from "../src/state/workspace-context.js";
import type { WorkspaceSession } from "../src/state/workspace-controller.js";

export function renderWorkspaceApp(url: string, session?: WorkspaceSession) {
  return renderToString(() => <WorkspaceProvider session={session}>
    <StaticRouter url={url} root={ConsoleShell}><ConsoleRoutes /></StaticRouter>
  </WorkspaceProvider>);
}
