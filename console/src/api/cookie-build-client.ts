import { parseBuildRead, snapshotBuildReadSelection } from "../domain/build-read.js";
import type { BuildReadSelection, BuildReadSnapshot } from "../domain/build-read.js";
import { createWorkspaceTransport, workspaceFailure } from "./workspace-transport.js";
import type { WorkspaceTransportOptions } from "./workspace-transport.js";

export type CookieBuildClientOptions = WorkspaceTransportOptions;
export interface CookieBuildClient {
  read(selection: BuildReadSelection, signal?: AbortSignal): Promise<BuildReadSnapshot>;
}

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
      const fields: readonly (readonly [string, string])[] = [
        ["organization_id", selection.organizationId], ["project_id", selection.projectId],
        ["application_id", selection.applicationId], ["build_id", selection.buildId], ["platform", selection.platform],
        ["source_sha256", selection.sourceSha256], ["toolchain_lock_sha256", selection.toolchainLockSha256],
        ["build_definition_sha256", selection.buildDefinitionSha256],
      ];
      const query = fields.map(([key, value]) => `${key}=${encodeURIComponent(value)}`).join("&");
      return request("/console-api/v1/builds?" + query, value => parseBuildRead(value, selection), signal);
    },
  });
}
