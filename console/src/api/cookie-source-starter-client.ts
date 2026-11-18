import { catalogRecord, isBuildCatalogId, snapshotApplicationSelection } from "../domain/build-catalog.js";
import type { ApplicationSelection } from "../domain/build-catalog.js";
import { parseBuildInput, parseSubmissionJSON } from "../domain/build-submission.js";
import type { BuildInput } from "../domain/build-submission.js";
import { createWorkspacePost } from "./cookie-workspace-post.js";
import { createWorkspaceTransport, workspaceFailure } from "./workspace-transport.js";
import type { WorkspaceTransportOptions } from "./workspace-transport.js";

type SourceStarter = Readonly<{ id: string }>;

export interface SourceStarterClient {
  discover(scope: ApplicationSelection, signal?: AbortSignal): Promise<SourceStarter | null>;
  select(input: Readonly<{ scope: ApplicationSelection; starterId: string }>, signal?: AbortSignal): Promise<BuildInput>;
}

const path = "/console-api/v1/source-starters";
const scopeKeys = ["organizationId", "projectId", "applicationId"];

function wireScope(scope: ApplicationSelection) {
  return { organization_id: scope.organizationId, project_id: scope.projectId, application_id: scope.applicationId };
}

function responseScope(value: unknown, scope: ApplicationSelection, keys: readonly string[]): value is Record<string, unknown> {
  return catalogRecord(value, [...scopeKeys, ...keys]) && value.organizationId === scope.organizationId &&
    value.projectId === scope.projectId && value.applicationId === scope.applicationId;
}

function requestScope(value: unknown): ApplicationSelection {
  try { return snapshotApplicationSelection(value); }
  catch { return workspaceFailure("invalid_request"); }
}

export function sessionSourceStarters(options: WorkspaceTransportOptions, csrf: () => string): SourceStarterClient {
  const get = createWorkspaceTransport(options, "same-origin", () => ({ accept: "application/json" }),
    { parse: parseSubmissionJSON, maximumBytes: 4096 });
  const post = createWorkspacePost(options, csrf);
  return {
    async discover(input, signal) {
      if (signal?.aborted) return workspaceFailure("aborted");
      const scope = requestScope(input);
      const query = new URLSearchParams(wireScope(scope));
      return get(path + "?" + query, value => {
        if (!responseScope(value, scope, ["starter"])) return workspaceFailure("invalid_response");
        if (value.starter === null) return null;
        if (!catalogRecord(value.starter, ["id"]) || !isBuildCatalogId(value.starter.id)) {
          return workspaceFailure("invalid_response");
        }
        return Object.freeze({ id: value.starter.id });
      }, signal);
    },
    async select(input, signal) {
      if (signal?.aborted) return workspaceFailure("aborted");
      if (!catalogRecord(input, ["scope", "starterId"]) || !isBuildCatalogId(input.starterId)) {
        return workspaceFailure("invalid_request");
      }
      const scope = requestScope(input.scope);
      const starterId = input.starterId;
      const value = await post(path, { ...wireScope(scope), starter_id: starterId }, 200, 4096, signal);
      if (!responseScope(value, scope, ["sourceInputId", "platform", "sourceSha256", "toolchainLockSha256", "buildDefinitionSha256"]) || value.sourceInputId !== starterId) {
        return workspaceFailure("invalid_response");
      }
      const { organizationId, projectId, applicationId, ...inputFields } = value;
      try { return parseBuildInput(inputFields); }
      catch { return workspaceFailure("invalid_response"); }
    },
  };
}
