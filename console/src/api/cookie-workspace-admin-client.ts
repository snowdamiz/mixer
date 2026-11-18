import { isWorkspaceDisplayName, isWorkspaceIdentifier } from "../domain/workspace-directory.js";
import { createWorkspacePost, exactObject } from "./cookie-workspace-post.js";
import { workspaceFailure } from "./workspace-transport.js";
import type { WorkspaceTransportOptions } from "./workspace-transport.js";

export type MemberRole = "administrator" | "developer" | "viewer";
export type WorkspaceAdminInput = { readonly organizationId: string } & (
  | { readonly kind: "usage" | "export" }
  | { readonly kind: "set_member"; readonly principalId: string; readonly role: MemberRole }
  | { readonly kind: "delete_organization"; readonly confirmation: string }
  | { readonly kind: "delete_project"; readonly projectId: string }
);
type Usage = {
  readonly active_projects: number; readonly project_limit: number;
  readonly held_builds: number; readonly build_limit: number; readonly builds: number;
};
type Member = { readonly principal_id: string; readonly role: string; readonly active: boolean };
type WorkspaceExport = {
  readonly organization: { readonly id: string; readonly display_name: string | null };
  readonly projects: readonly { readonly id: string; readonly display_name: string | null; readonly active: boolean }[];
  readonly memberships: readonly Member[];
};
export type WorkspaceAdminResult =
  | { readonly kind: "usage"; readonly usage: Usage; readonly canAdminister: boolean }
  | { readonly kind: "export"; readonly data: WorkspaceExport }
  | { readonly kind: "set_member" | "delete_project" | "delete_organization" };
export interface WorkspaceAdminClient {
  request(input: WorkspaceAdminInput, signal?: AbortSignal): Promise<WorkspaceAdminResult>;
}

export function isMemberRole(value: unknown): value is MemberRole {
  return value === "administrator" || value === "developer" || value === "viewer";
}

function count(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
}

function exported(value: unknown, organizationId: string): WorkspaceExport {
  if (!exactObject(value, ["organization", "projects", "memberships"]) ||
    !exactObject(value.organization, ["id", "display_name"]) || value.organization.id !== organizationId ||
    !isWorkspaceDisplayName(value.organization.display_name) || !Array.isArray(value.projects) || !Array.isArray(value.memberships)) {
    return workspaceFailure("invalid_response");
  }
  const projects = value.projects.map((row: unknown) => {
    if (!exactObject(row, ["id", "display_name", "active"]) || !isWorkspaceIdentifier(row.id) ||
      !isWorkspaceDisplayName(row.display_name) || typeof row.active !== "boolean") return workspaceFailure("invalid_response");
    return { id: row.id, display_name: row.display_name, active: row.active };
  });
  const memberships = value.memberships.map((row: unknown) => {
    // The snapshot also includes project-specific memberships and inactive historical rows.
    if (!exactObject(row, ["principal_id", "role", "active"]) || !isWorkspaceIdentifier(row.principal_id) ||
      typeof row.role !== "string" || typeof row.active !== "boolean") return workspaceFailure("invalid_response");
    return { principal_id: row.principal_id, role: row.role, active: row.active };
  });
  return { organization: { id: organizationId, display_name: value.organization.display_name }, projects, memberships };
}

export function sessionWorkspaceAdmin(options: WorkspaceTransportOptions, csrf: () => string): WorkspaceAdminClient {
  const post = createWorkspacePost(options, csrf);
  return Object.freeze({
    async request(input: WorkspaceAdminInput, signal?: AbortSignal): Promise<WorkspaceAdminResult> {
      const captured = { ...input };
      if (!isWorkspaceIdentifier(captured.organizationId)) return workspaceFailure("invalid_request");
      const scope = { operation: captured.kind, organization_id: captured.organizationId };
      const send = (payload: object, limit = 4096) => post("/console-api/v1/workspace-admin", payload, 200, limit, signal);
      switch (captured.kind) {
        case "usage": {
          const row = await send(scope);
          if (!exactObject(row, ["organization_id", "plan", "active_projects", "project_limit", "held_builds", "build_limit", "builds", "can_administer"]) ||
            row.organization_id !== captured.organizationId || row.plan !== "free" ||
            typeof row.can_administer !== "boolean" || !count(row.active_projects) || !count(row.project_limit) || !count(row.held_builds) ||
            !count(row.build_limit) || !count(row.builds)) return workspaceFailure("invalid_response");
          const { active_projects, project_limit, held_builds, build_limit, builds } = row;
          return { kind: "usage", canAdminister: row.can_administer, usage: { active_projects, project_limit, held_builds, build_limit, builds } };
        }
        case "export":
          return { kind: "export", data: exported(await send(scope, 262_144), captured.organizationId) };
        case "set_member": {
          if (!isWorkspaceIdentifier(captured.principalId) || !isMemberRole(captured.role)) {
            return workspaceFailure("invalid_request");
          }
          const row = await send({ ...scope, principal_id: captured.principalId, role: captured.role });
          if (!exactObject(row, ["organization_id", "principal_id", "role", "id"]) ||
            row.organization_id !== captured.organizationId || row.principal_id !== captured.principalId ||
            row.role !== captured.role || !isWorkspaceIdentifier(row.id)) return workspaceFailure("invalid_response");
          return { kind: "set_member" };
        }
        case "delete_organization": {
          if (captured.confirmation !== captured.organizationId) return workspaceFailure("invalid_request");
          const row = await send({ ...scope, confirm: captured.confirmation });
          if (!exactObject(row, ["organization_id", "deleted", "retention"]) ||
            row.organization_id !== captured.organizationId || row.deleted !== true ||
            row.retention !== "tombstone") return workspaceFailure("invalid_response");
          return { kind: "delete_organization" };
        }
        case "delete_project": {
          if (!isWorkspaceIdentifier(captured.projectId)) return workspaceFailure("invalid_request");
          const row = await send({ ...scope, project_id: captured.projectId });
          if (!exactObject(row, ["organization_id", "id", "deleted", "retention"]) ||
            row.organization_id !== captured.organizationId || row.id !== captured.projectId ||
            row.deleted !== true || row.retention !== "tombstone") return workspaceFailure("invalid_response");
          return { kind: "delete_project" };
        }
      }
    },
  });
}
