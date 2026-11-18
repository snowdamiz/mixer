import { isWorkspaceIdentifier } from "../domain/workspace-directory.js";
import { createWorkspacePost, exactObject } from "./cookie-workspace-post.js";
import { workspaceFailure } from "./workspace-transport.js";
import type { WorkspaceTransportOptions } from "./workspace-transport.js";

const requestId = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/u;

export interface SupportRequest {
  readonly id: string;
  readonly subject: string;
  readonly message: string;
  readonly submitted_at: number;
}

export interface SupportDraft {
  readonly id: string;
  readonly subject: string;
  readonly message: string;
}

export interface WorkspaceSupportClient {
  list(organizationId: string, signal?: AbortSignal): Promise<readonly SupportRequest[]>;
  submit(organizationId: string, draft: SupportDraft, signal?: AbortSignal): Promise<SupportRequest>;
}

function isSupportRequest(value: unknown): value is SupportRequest {
  return exactObject(value, ["id", "subject", "message", "submitted_at"]) &&
    typeof value.id === "string" && value.id.length === 36 && requestId.test(value.id) &&
    typeof value.subject === "string" && typeof value.message === "string" &&
    validSupportText(value.subject, value.message) &&
    typeof value.submitted_at === "number" && Number.isSafeInteger(value.submitted_at) &&
    value.submitted_at > 0 && value.submitted_at <= 8_640_000_000_000;
}

export function validSupportText(subject: string, message: string): boolean {
  const encoder = new TextEncoder();
  return subject.trim().length > 0 && encoder.encode(subject).length <= 120 &&
    !/[\u0000-\u001f\u007f-\u009f]/u.test(subject) &&
    message.trim().length > 0 && encoder.encode(message).length <= 1800 &&
    !/[\u0000-\u0008\u000b-\u001f\u007f-\u009f]/u.test(message);
}

export function sessionWorkspaceSupport(
  options: WorkspaceTransportOptions, csrf: () => string,
): WorkspaceSupportClient {
  const post = createWorkspacePost(options, csrf);
  const path = "/console-api/v1/support-requests";

  return {
    async list(organizationId, signal) {
      if (!isWorkspaceIdentifier(organizationId)) return workspaceFailure("invalid_request");
      const value = await post(path, { operation: "list", organization_id: organizationId }, 200, 128 * 1024, signal);
      if (!exactObject(value, ["organization_id", "requests"]) || value.organization_id !== organizationId ||
        !Array.isArray(value.requests) || value.requests.length > 20 || !value.requests.every(isSupportRequest)) {
        return workspaceFailure("invalid_response");
      }
      return value.requests;
    },
    async submit(organizationId, draft, signal) {
      const { id, subject, message } = draft;
      if (!isWorkspaceIdentifier(organizationId) || id.length !== 36 || !requestId.test(id) ||
        !validSupportText(subject, message)) return workspaceFailure("invalid_request");

      const value = await post(path, {
        operation: "submit", organization_id: organizationId, request_id: id, subject, message,
      }, 201, 16 * 1024, signal);
      if (!exactObject(value, ["organization_id", "request"]) || value.organization_id !== organizationId ||
        !isSupportRequest(value.request) || value.request.id !== id ||
        value.request.subject !== subject || value.request.message !== message) {
        return workspaceFailure("invalid_response");
      }
      return value.request;
    },
  };
}
