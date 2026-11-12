import { catalogRecord, parseApplicationPage, parseBuildPage, snapshotApplicationSelection,
  snapshotCatalogPageRequest, snapshotProjectSelection } from "../domain/build-catalog.js";
import type { ApplicationPage, ApplicationSelection, BuildPage, CatalogPageRequest, ProjectSelection } from "../domain/build-catalog.js";
import { createWorkspaceTransport, workspaceFailure } from "./workspace-transport.js";
import type { WorkspaceTransportOptions } from "./workspace-transport.js";

export type CookieBuildCatalogClientOptions = WorkspaceTransportOptions;
export interface BuildCatalogClient {
  applications(scope: ProjectSelection, page: CatalogPageRequest, signal?: AbortSignal): Promise<ApplicationPage>;
  builds(scope: ApplicationSelection, page: CatalogPageRequest, signal?: AbortSignal): Promise<BuildPage>;
}

function query(scope: ProjectSelection, page: CatalogPageRequest, applicationId?: string): string {
  const fields: [string, string][] = [["organization_id", scope.organizationId], ["project_id", scope.projectId]];
  if (applicationId !== undefined) fields.push(["application_id", applicationId]);
  const cursor = Object.hasOwn(page, "cursor") ? page.cursor : undefined;
  if (cursor !== undefined) fields.push(["cursor", cursor]);
  return "?" + fields.map(([key, value]) => `${key}=${encodeURIComponent(value)}`).join("&");
}

/** Fixed cookie discovery routes; pages and continuations confer no authority. */
export function createCookieBuildCatalogClient(options: CookieBuildCatalogClientOptions = {}): BuildCatalogClient {
  if (!catalogRecord(options, [], ["fetch", "timeoutMs"])) return workspaceFailure("invalid_request");
  const captured = Object.freeze({ ...options });
  const request = createWorkspaceTransport(captured, "same-origin", () => ({ accept: "application/json" }));
  return Object.freeze({
    async applications(input: ProjectSelection, pageInput: CatalogPageRequest, signal?: AbortSignal) {
      let scope: ProjectSelection;
      let page: CatalogPageRequest;
      try { scope = snapshotProjectSelection(input); page = snapshotCatalogPageRequest(pageInput); }
      catch { return workspaceFailure("invalid_request"); }
      return request("/console-api/v1/applications" + query(scope, page), value => parseApplicationPage(value, scope), signal);
    },
    async builds(input: ApplicationSelection, pageInput: CatalogPageRequest, signal?: AbortSignal) {
      let scope: ApplicationSelection;
      let page: CatalogPageRequest;
      try { scope = snapshotApplicationSelection(input); page = snapshotCatalogPageRequest(pageInput); }
      catch { return workspaceFailure("invalid_request"); }
      return request("/console-api/v1/build-catalog" + query(scope, page, scope.applicationId), value => parseBuildPage(value, scope), signal);
    },
  });
}
