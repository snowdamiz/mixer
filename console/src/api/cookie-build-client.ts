import { buildSelectionQuery, parseBuildLogs, parseBuildRead, snapshotBuildLogTarget, snapshotBuildReadSelection } from "../domain/build-read.js";
import type { BuildLogEvents, BuildLogTarget, BuildReadSelection, BuildReadSnapshot } from "../domain/build-read.js";
import { createWorkspaceTransport, workspaceFailure } from "./workspace-transport.js";
import type { WorkspaceTransportOptions } from "./workspace-transport.js";

export type CookieBuildClientOptions = WorkspaceTransportOptions;
export interface CookieBuildClient {
  read(selection: BuildReadSelection, signal?: AbortSignal): Promise<BuildReadSnapshot>;
  readLogs(target: BuildLogTarget, signal?: AbortSignal): Promise<BuildLogEvents>;
}

export { buildSelectionQuery };

/** Fixed browser-cookie read adapter. Session authentication belongs to the server. */
export function createCookieBuildClient(options: CookieBuildClientOptions = {}): CookieBuildClient {
  if (!options || typeof options !== "object" || Array.isArray(options) ||
    Reflect.ownKeys(options).some(key => key !== "fetch" && key !== "timeoutMs")) {
    return workspaceFailure("invalid_request");
  }
  const request = createWorkspaceTransport(options, "same-origin", () => ({ accept: "application/json" }));
  return Object.freeze({
    async read(input: BuildReadSelection, signal?: AbortSignal) {
      let selection: BuildReadSelection;
      try { selection = snapshotBuildReadSelection(input); }
      catch { return workspaceFailure("invalid_request"); }
      return request("/console-api/v1/builds?" + buildSelectionQuery(selection), value => parseBuildRead(value, selection), signal);
    },
    async readLogs(input: BuildLogTarget, signal?: AbortSignal) {
      let target: BuildLogTarget;
      try { target = snapshotBuildLogTarget(input); }
      catch { return workspaceFailure("invalid_request"); }
      return request("/console-api/v1/build-logs?" + buildSelectionQuery(target.selection),
        value => parseBuildLogs(value, target), signal);
    },
  });
}
