import { catalogRecord, snapshotApplicationSelection } from "../domain/build-catalog.js";
import type { ApplicationSelection } from "../domain/build-catalog.js";
import { createWorkspacePost } from "./cookie-workspace-post.js";
import { workspaceFailure } from "./workspace-transport.js";
import type { WorkspaceTransportOptions } from "./workspace-transport.js";

export type RegisterApplication = (input: ApplicationSelection, signal?: AbortSignal) => Promise<void>;

export function sessionApplicationRegistration(options: WorkspaceTransportOptions, csrf: () => string): RegisterApplication {
  const post = createWorkspacePost(options, csrf);
  return async (input, signal) => {
    if (signal?.aborted) return workspaceFailure("aborted");
    let selection: ApplicationSelection;
    try { selection = snapshotApplicationSelection(input); }
    catch { return workspaceFailure("invalid_request"); }

    const payload = {
      organization_id: selection.organizationId,
      project_id: selection.projectId,
      application_id: selection.applicationId,
    };
    const receipt = await post("/console-api/v1/applications", payload, 201, 4096, signal);
    if (!catalogRecord(receipt, ["organization_id", "project_id", "application_id"]) ||
      receipt.organization_id !== payload.organization_id || receipt.project_id !== payload.project_id ||
      receipt.application_id !== payload.application_id) return workspaceFailure("invalid_response");
  };
}
