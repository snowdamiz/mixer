import { isWorkspaceIdentifier, parseWorkspaceOrganizations, parseWorkspaceProjects } from "../domain/workspace-directory.js";
import type { WorkspaceClient, WorkspacePageRequest } from "./workspace-client.js";
import { createWorkspaceTransport, workspaceFailure, workspaceQuery } from "./workspace-transport.js";

export interface CookieWorkspaceClientOptions {
  readonly fetch?: typeof globalThis.fetch;
  readonly timeoutMs?: number;
}

/**
 * Browser adapter for the confidential same-origin session boundary. The browser
 * supplies its HttpOnly cookie; no access token or configurable destination is accepted.
 * Creating this client does not authenticate a session or install it in the app.
 */
export function createCookieWorkspaceClient(options: CookieWorkspaceClientOptions = {}): WorkspaceClient {
  if (!options || typeof options !== "object" || Array.isArray(options) ||
    Object.keys(options).some(key => key !== "fetch" && key !== "timeoutMs")) {
    return workspaceFailure("invalid_request");
  }
  const request = createWorkspaceTransport(options, "same-origin", () => ({ accept: "application/json" }));

  return Object.freeze({
    async organizations(page: WorkspacePageRequest = {}, signal?: AbortSignal) {
      return request("/console-api/v1/orgs" + workspaceQuery(page), parseWorkspaceOrganizations, signal);
    },
    async projects(organizationId: string, page: WorkspacePageRequest = {}, signal?: AbortSignal) {
      if (!isWorkspaceIdentifier(organizationId)) return workspaceFailure("invalid_request");
      return request("/console-api/v1/projects" + workspaceQuery(page, organizationId),
        value => parseWorkspaceProjects(value, organizationId), signal);
    },
  });
}
