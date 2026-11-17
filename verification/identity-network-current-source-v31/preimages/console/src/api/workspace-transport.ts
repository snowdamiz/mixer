import { isWorkspaceIdentifier } from "../domain/workspace-directory.js";

export type WorkspaceClientFailure = "unauthenticated" | "permission_denied" | "not_found" |
  "unavailable" | "invalid_response" | "invalid_request" | "aborted";
const failureCodes: readonly string[] = ["unauthenticated", "permission_denied", "not_found", "unavailable", "invalid_response", "invalid_request", "aborted"];

/** Fixed public errors never include bearer tokens, response bodies, URLs or provider details. */
export class WorkspaceClientError extends Error {
  readonly code: WorkspaceClientFailure;
  constructor(code: WorkspaceClientFailure) {
    if (!failureCodes.includes(code)) code = "unavailable";
    super(`Workspace request ${code}`);
    this.name = "WorkspaceClientError";
    this.code = code;
  }
}

export interface WorkspacePageRequest { readonly limit?: number; readonly cursor?: string }
export interface WorkspaceTransportOptions {
  readonly fetch?: typeof globalThis.fetch;
  readonly timeoutMs?: number;
}

const maximumResponseBytes = 262_144;
export const workspaceFailure = (code: WorkspaceClientFailure): never => { throw new WorkspaceClientError(code); };
const failure = workspaceFailure;

export function workspaceQuery(page: WorkspacePageRequest, organizationId?: string): string {
  if (!page || typeof page !== "object" || Array.isArray(page) ||
    Object.keys(page).some(key => key !== "limit" && key !== "cursor")) return failure("invalid_request");
  const fields: [string, string][] = [];
  if (organizationId !== undefined) {
    if (!isWorkspaceIdentifier(organizationId)) return failure("invalid_request");
    fields.push(["organization_id", organizationId]);
  }
  if (Object.hasOwn(page, "limit")) {
    if (!Number.isInteger(page.limit) || page.limit! < 1 || page.limit! > 100) return failure("invalid_request");
    fields.push(["limit", String(page.limit)]);
  }
  if (Object.hasOwn(page, "cursor")) {
    if (typeof page.cursor !== "string" || page.cursor.length > 1400 || !/^[A-Za-z0-9_-]+$/u.test(page.cursor)) {
      return failure("invalid_request");
    }
    fields.push(["cursor", page.cursor]);
  }
  return fields.length ? `?${fields.map(([key, value]) => `${key}=${encodeURIComponent(value)}`).join("&")}` : "";
}

function cancelBody(response: Response): void {
  // Cancellation is best effort and must not extend the request deadline.
  void response.body?.cancel().catch(() => undefined);
}

async function json(response: Response, signal: AbortSignal): Promise<unknown> {
  if (response.redirected || !/^application\/json(?:\s*;\s*charset=utf-8)?$/iu.test(response.headers.get("content-type") ?? "")) {
    cancelBody(response); return failure("invalid_response");
  }
  const length = response.headers.get("content-length");
  if (length !== null && (!/^\d+$/u.test(length) || Number(length) > maximumResponseBytes)) {
    cancelBody(response); return failure("invalid_response");
  }
  if (!response.body) return failure("invalid_response");
  const reader = response.body.getReader();
  const cancel = () => { void reader.cancel().catch(() => undefined); };
  signal.addEventListener("abort", cancel, { once: true });
  const chunks: Uint8Array[] = [];
  let size = 0;
  let reads = 0;
  try {
    if (signal.aborted) return failure("aborted");
    while (true) {
      if (++reads > 4096) return failure("invalid_response");
      const item = await reader.read();
      if (signal.aborted) return failure("aborted");
      if (item.done) break;
      size += item.value.byteLength;
      if (size > maximumResponseBytes) return failure("invalid_response");
      chunks.push(item.value);
    }
    const bytes = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)) as unknown;
  } catch (error) {
    if (error instanceof WorkspaceClientError) throw error;
    return failure("invalid_response");
  } finally {
    signal.removeEventListener("abort", cancel);
    cancel();
    reader.releaseLock();
  }
}

/** Internal bounded reader shared by the bearer API and fixed browser-cookie adapter. */
export function createWorkspaceTransport(
  options: WorkspaceTransportOptions,
  credentials: "omit" | "same-origin",
  requestHeaders: () => HeadersInit | Promise<HeadersInit>,
) {
  const fetchRequest = options.fetch ?? globalThis.fetch;
  const timeoutMs = options.timeoutMs ?? 15_000;
  if (typeof fetchRequest !== "function" || !Number.isInteger(timeoutMs) || timeoutMs < 1 || timeoutMs > 30_000) {
    return failure("invalid_request");
  }

  async function request<T>(path: string, decode: (value: unknown) => T, signal?: AbortSignal): Promise<T> {
    if (signal?.aborted) return failure("aborted");
    const controller = new AbortController();
    let timedOut = false;
    const cancel = () => controller.abort();
    signal?.addEventListener("abort", cancel, { once: true });
    const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
    let abortListener: (() => void) | undefined;
    const stopped = new Promise<never>((_, reject) => {
      abortListener = () => reject(new WorkspaceClientError(timedOut ? "unavailable" : "aborted"));
      controller.signal.addEventListener("abort", abortListener, { once: true });
    });
    const perform = async (): Promise<T> => {
      const headers = await requestHeaders();
      if (controller.signal.aborted) return failure(timedOut ? "unavailable" : "aborted");
      const response = await fetchRequest(path, {
        method: "GET", headers,
        credentials, redirect: "error", cache: "no-store", referrerPolicy: "no-referrer", signal: controller.signal,
      });
      if (controller.signal.aborted) { cancelBody(response); return failure(timedOut ? "unavailable" : "aborted"); }
      if (response.status !== 200) {
        cancelBody(response);
        if (response.status === 401) return failure("unauthenticated");
        if (response.status === 403) return failure("permission_denied");
        if (response.status === 404) return failure("not_found");
        if ([429, 500, 502, 503, 504].includes(response.status)) return failure("unavailable");
        return failure("invalid_response");
      }
      const value = await json(response, controller.signal);
      try { return decode(value); } catch { return failure("invalid_response"); }
    };
    try { return await Promise.race([perform(), stopped]); }
    catch (error) {
      // A session provider may itself throw an Error with mutable private text.
      if (error instanceof WorkspaceClientError) throw new WorkspaceClientError(error.code);
      return failure(controller.signal.aborted ? (timedOut ? "unavailable" : "aborted") : "unavailable");
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener("abort", cancel);
      if (abortListener) controller.signal.removeEventListener("abort", abortListener);
    }
  }

  return request;
}
