import { createWorkspacePost, exactObject } from "./cookie-workspace-post.js";
import { isWorkspaceIdentifier, isWorkspaceCreateName } from "../domain/workspace-directory.js";
import { workspaceFailure } from "./workspace-transport.js";
import type { WorkspaceTransportOptions } from "./workspace-transport.js";

export type WorkspaceCreateInput =
  | { readonly kind: "organization"; readonly displayName: string }
  | { readonly kind: "project"; readonly organizationId: string; readonly displayName: string };

type CreatedOrganizationId = string & { readonly __brand: "CreatedOrganizationId" };
type CreatedProjectId = string & { readonly __brand: "CreatedProjectId" };
export type CreatedWorkspace =
  | { readonly kind: "organization"; readonly organizationId: CreatedOrganizationId }
  | { readonly kind: "project"; readonly organizationId: string; readonly projectId: CreatedProjectId };

export interface WorkspaceCreateClient {
  submit(input: WorkspaceCreateInput, signal?: AbortSignal): Promise<CreatedWorkspace>;
}

function organizationId(value: unknown): value is CreatedOrganizationId {
  return typeof value === "string" && value.length === 36 && /^org-[a-f0-9]{32}$/u.test(value);
}

function projectId(value: unknown): value is CreatedProjectId {
  return typeof value === "string" && value.length === 40 && /^project-[a-f0-9]{32}$/u.test(value);
}

function receipt(value: unknown, input: WorkspaceCreateInput): CreatedWorkspace {
  if (input.kind === "organization") {
    if (exactObject(value, ["id", "display_name", "organization_roles", "plan"]) &&
      organizationId(value.id) && value.display_name === input.displayName && value.plan === "free" &&
      Array.isArray(value.organization_roles) && value.organization_roles.length === 1 && value.organization_roles[0] === "owner") {
      return Object.freeze({ kind: "organization", organizationId: value.id });
    }
  } else if (exactObject(value, ["id", "organization_id", "display_name"]) &&
    projectId(value.id) && value.organization_id === input.organizationId && value.display_name === input.displayName) {
    return Object.freeze({ kind: "project", organizationId: input.organizationId, projectId: value.id });
  }
  return workspaceFailure("invalid_response");
}

export function sessionWorkspaceCreation(options: WorkspaceTransportOptions, csrf: () => string): WorkspaceCreateClient {
  const post = createWorkspacePost(options, csrf);
  return Object.freeze({
    async submit(input: WorkspaceCreateInput, signal?: AbortSignal) {
      if (signal?.aborted) return workspaceFailure("aborted");
      const captured = Object.freeze({ ...input });
      if (!isWorkspaceCreateName(captured.displayName) || (captured.kind !== "organization" &&
        (captured.kind !== "project" || !isWorkspaceIdentifier(captured.organizationId)))) return workspaceFailure("invalid_request");
      const path = captured.kind === "organization" ? "/console-api/v1/orgs" : "/console-api/v1/projects";
      const body = captured.kind === "organization" ? { display_name: captured.displayName } :
        { organization_id: captured.organizationId, display_name: captured.displayName };
      return receipt(await post(path, body, 201, 4096, signal), captured);
    },
  });
}
