import { isWorkspaceIdentifier, parseWorkspaceOrganizations, parseWorkspaceProjects } from "../domain/workspace-directory.js";
import type { WorkspaceOrganizationPage, WorkspaceProjectPage } from "../domain/workspace-directory.js";

import { createWorkspaceTransport, workspaceFailure as failure, workspaceQuery as query } from "./workspace-transport.js";
import type { WorkspacePageRequest } from "./workspace-transport.js";
export { WorkspaceClientError } from "./workspace-transport.js";
export type { WorkspaceClientFailure, WorkspacePageRequest } from "./workspace-transport.js";

export interface WorkspaceClientOptions {
  /** Trusted application configuration, never derived from response data or workspace IDs. */
  readonly apiOrigin: string;
  /** Resolve the current in-memory session for every request; no token is cached by this client. */
  readonly accessToken: () => string | null | Promise<string | null>;
  readonly fetch?: typeof globalThis.fetch;
  readonly timeoutMs?: number;
  readonly allowInsecureLoopback?: boolean;
}
export interface WorkspaceClient {
  organizations(page?: WorkspacePageRequest, signal?: AbortSignal): Promise<WorkspaceOrganizationPage>;
  projects(organizationId: string, page?: WorkspacePageRequest, signal?: AbortSignal): Promise<WorkspaceProjectPage>;
}

function origin(options: WorkspaceClientOptions): string {
  try {
    const value = new URL(options.apiOrigin);
    const loopback = ["localhost", "127.0.0.1", "[::1]"].includes(value.hostname);
    if (value.username || value.password || value.pathname !== "/" || value.search || value.hash ||
      !(value.protocol === "https:" || (options.allowInsecureLoopback === true && loopback && value.protocol === "http:"))) {
      return failure("invalid_request");
    }
    return value.origin;
  } catch { return failure("invalid_request"); }
}

function token(value: unknown): value is string {
  return typeof value === "string" && value.length <= 4089 && /^[A-Za-z0-9._~+/-]+=*$/u.test(value);
}

/** Read-only customer workspace transport. Login and selection state belong to its caller. */
export function createWorkspaceClient(options: WorkspaceClientOptions): WorkspaceClient {
  const base = origin(options);
  if (typeof options.accessToken !== "function") return failure("invalid_request");
  const accessToken = options.accessToken;
  const request = createWorkspaceTransport(options, "omit", async () => {
    const bearer = await accessToken();
    if (!token(bearer)) return failure("unauthenticated");
    return { accept: "application/json", authorization: `Bearer ${bearer}` };
  });

  return Object.freeze({
    async organizations(page: WorkspacePageRequest = {}, signal?: AbortSignal) {
      return request(base + "/v3/orgs" + query(page), parseWorkspaceOrganizations, signal);
    },
    async projects(organizationId: string, page: WorkspacePageRequest = {}, signal?: AbortSignal) {
      // undefined cannot silently select an unscoped project endpoint at runtime.
      if (!isWorkspaceIdentifier(organizationId)) return failure("invalid_request");
      return request(base + "/v3/projects" + query(page, organizationId), value => parseWorkspaceProjects(value, organizationId), signal);
    },
  });
}
