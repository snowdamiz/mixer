import { renderToString } from "solid-js/web";
import { WorkspaceDirectory } from "../src/components/WorkspaceDirectory.js";
import type { WorkspaceDirectoryProps } from "../src/components/WorkspaceDirectory.js";

export function renderWorkspaceDirectory(props: WorkspaceDirectoryProps): string {
  return renderToString(() => <WorkspaceDirectory {...props} />);
}
