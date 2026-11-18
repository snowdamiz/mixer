import { parseSubmissionJSON } from "../domain/build-submission.js";
import { isWorkspaceIdentifier, isWorkspaceCreateName } from "../domain/workspace-directory.js";
import { readWorkspaceJSON, workspaceFailure, WorkspaceClientError } from "./workspace-transport.js";
import type { WorkspaceTransportOptions, WorkspaceClientFailure } from "./workspace-transport.js";

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

function exactObject(value: unknown, keys: readonly string[]): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value) &&
    keys.length === Object.keys(value).length && keys.every(key => Object.hasOwn(value, key));
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

function refusal(status: number, value: unknown): WorkspaceClientFailure {
  if (!exactObject(value, ["error"]) || !exactObject(value.error, ["code", "message"]) ||
    value.error.message !== "Workspace request refused.") return "invalid_response";
  const code = value.error.code;
  if ((status === 400 || status === 413) && code === "invalid_request") return code;
  if (status === 401 && code === "unauthenticated") return code;
  if (status === 403 && code === "permission_denied") return code;
  if (status === 404 && code === "not_found") return code;
  if (status === 409 && (code === "quota_exceeded" || code === "conflict")) return code;
  if (status === 503 && code === "authorization_unavailable") return "unavailable";
  return "invalid_response";
}

/** The authenticated session owner supplies CSRF for this single fixed POST. */
export function sessionWorkspaceCreation(options: WorkspaceTransportOptions, csrf: () => string): WorkspaceCreateClient {
  const fetchRequest = options.fetch ?? globalThis.fetch;
  const timeoutMs = options.timeoutMs ?? 15_000;
  return Object.freeze({
    async submit(input: WorkspaceCreateInput, signal?: AbortSignal) {
      if (signal?.aborted) return workspaceFailure("aborted");
      const captured = Object.freeze({ ...input });
      if (!isWorkspaceCreateName(captured.displayName) || (captured.kind !== "organization" &&
        (captured.kind !== "project" || !isWorkspaceIdentifier(captured.organizationId)))) return workspaceFailure("invalid_request");
      const path = captured.kind === "organization" ? "/console-api/v1/orgs" : "/console-api/v1/projects";
      const body = JSON.stringify(captured.kind === "organization" ? { display_name: captured.displayName } :
        { organization_id: captured.organizationId, display_name: captured.displayName });
      const token = csrf();
      const controller = new AbortController();
      const stop = () => controller.abort();
      signal?.addEventListener("abort", stop, { once: true });
      const stopCode = () => signal?.aborted ? "aborted" : "unavailable";
      const timer = setTimeout(stop, timeoutMs);
      let onAbort: (() => void) | undefined;
      const stopped = new Promise<never>((_, reject) => {
        onAbort = () => reject(new WorkspaceClientError(stopCode()));
        controller.signal.addEventListener("abort", onAbort, { once: true });
      });
      const perform = async () => {
        const response = await fetchRequest(path, { method: "POST", body,
          headers: { accept: "application/json", "content-type": "application/json", "x-mixer-csrf": token },
          credentials: "same-origin", redirect: "error", cache: "no-store", referrerPolicy: "no-referrer", signal: controller.signal });
        if (controller.signal.aborted || response.headers.get("cache-control") !== "no-store" || response.headers.has("location")) {
          void response.body?.cancel().catch(() => undefined);
          return workspaceFailure(controller.signal.aborted ? stopCode() : "invalid_response");
        }
        const value = await readWorkspaceJSON(response, controller.signal, parseSubmissionJSON, 4096);
        if (response.status !== 201) return workspaceFailure(refusal(response.status, value));
        return receipt(value, captured);
      };
      try { return await Promise.race([perform(), stopped]); }
      catch (error) {
        if (controller.signal.aborted) return workspaceFailure(stopCode());
        if (error instanceof WorkspaceClientError) return workspaceFailure(error.code);
        return workspaceFailure("unavailable");
      } finally {
        clearTimeout(timer);
        if (onAbort) controller.signal.removeEventListener("abort", onAbort);
        signal?.removeEventListener("abort", stop);
      }
    },
  });
}
