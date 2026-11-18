import { parseSubmissionJSON } from "../domain/build-submission.js";
import { readWorkspaceJSON, workspaceFailure, WorkspaceClientError } from "./workspace-transport.js";
import type { WorkspaceTransportOptions, WorkspaceClientFailure } from "./workspace-transport.js";

export function exactObject(value: unknown, keys: readonly string[]): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value) &&
    keys.length === Object.keys(value).length && keys.every(key => Object.hasOwn(value, key));
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

export function createWorkspacePost(options: WorkspaceTransportOptions, csrf: () => string) {
  const fetchRequest = options.fetch ?? globalThis.fetch;
  const timeoutMs = options.timeoutMs ?? 15_000;
  return async (path: "/console-api/v1/orgs" | "/console-api/v1/projects" | "/console-api/v1/workspace-admin" | "/console-api/v1/support-requests" | "/console-api/v1/applications" | "/console-api/v1/source-starters",
    payload: object, status: 200 | 201, maximumBytes: number, signal?: AbortSignal): Promise<unknown> => {
    if (signal?.aborted) return workspaceFailure("aborted");
    const body = JSON.stringify(payload);
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
      const value = await readWorkspaceJSON(response, controller.signal, text => parseSubmissionJSON(text, maximumBytes === 4096 ? 25 : 4096), maximumBytes);
      if (response.status !== status) return workspaceFailure(refusal(response.status, value));
      return value;
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
  };
}
