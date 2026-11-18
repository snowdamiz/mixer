import type { ApplicationSelection, CatalogPageRequest } from "../domain/build-catalog.js";
import { snapshotApplicationSelection, snapshotCatalogPageRequest } from "../domain/build-catalog.js";
import { parseBuildInputs, parseBuildReceipt, parseSubmissionJSON, snapshotBuildAttempt } from "../domain/build-submission.js";
import type { BuildInputPage, BuildAttempt, BuildReceipt } from "../domain/build-submission.js";
import { WorkspaceClientError, workspaceFailure } from "./workspace-transport.js";
import { buildSelectionQuery } from "./cookie-build-client.js";
import { catalogRecord } from "../domain/build-catalog.js";
import { parseBuildRead, snapshotBuildReadSelection } from "../domain/build-read.js";
import type { BuildReadSelection, BuildReadSnapshot } from "../domain/build-read.js";
import type { WorkspaceTransportOptions } from "./workspace-transport.js";

export type CancelBuild = (selection: BuildReadSelection, signal?: AbortSignal) => Promise<BuildReadSnapshot>;

export interface BuildSubmissionClient {
  inputs(scope: ApplicationSelection, page: CatalogPageRequest, signal?: AbortSignal): Promise<BuildInputPage>;
  submit(attempt: BuildAttempt, signal?: AbortSignal): Promise<BuildReceipt>;
}

/** Internal fixed-route adapter. The session owner alone supplies the private header closure. */
export function sessionBuildSubmission(options: WorkspaceTransportOptions, csrf: () => string): BuildSubmissionClient & { cancel: CancelBuild } {
  const fetchRequest = options.fetch ?? globalThis.fetch, timeoutMs = options.timeoutMs ?? 15_000;
  async function request<T>(path: string, write: BuildAttempt | "cancel" | undefined, decode: (value: unknown, status: number) => T, signal?: AbortSignal): Promise<T> {
    if (signal?.aborted) return workspaceFailure("aborted");
    const controller = new AbortController(); let finished = false, timedOut = false;
    let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
    const stop = () => controller.abort(); signal?.addEventListener("abort", stop, { once: true });
    const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
    let onAbort: (() => void) | undefined;
    const aborted = new Promise<never>((_, reject) => {
      onAbort = () => reject(new WorkspaceClientError(timedOut ? "unavailable" : "aborted"));
      controller.signal.addEventListener("abort", onAbort, { once: true });
    });
    const check = () => { if (finished || controller.signal.aborted) workspaceFailure(timedOut ? "unavailable" : "aborted"); };
    const perform = async () => {
      const headers: Record<string, string> = { accept: "application/json" };
      if (write) {
        const token = csrf();
        if (!/^[A-Za-z0-9_-]{43}$/u.test(token)) return workspaceFailure("invalid_request");
        headers["x-mixer-csrf"] = token;
        if (write !== "cancel") {
          headers["content-type"] = "application/json";
          headers["idempotency-key"] = write.key;
        }
      }
      check();
      const response = await fetchRequest(path, { method: write ? "POST" : "GET", headers,
        ...(write && write !== "cancel" ? { body: write.body } : {}), credentials: "same-origin", redirect: "error", cache: "no-store", referrerPolicy: "no-referrer", signal: controller.signal });
      if (finished || controller.signal.aborted) { void response.body?.cancel().catch(() => undefined); check(); }
      if (response.status !== 200 && !(write === "cancel" ? response.status === 202 : write && response.status === 201)) {
        void response.body?.cancel().catch(() => undefined);
        if (response.status === 401) return workspaceFailure("unauthenticated");
        if (response.status === 403) return workspaceFailure("permission_denied");
        if (response.status === 404) return workspaceFailure("not_found");
        if (response.status === 409 && write === "cancel") return workspaceFailure("conflict");
        if (response.status === 400 || response.status === 409) return workspaceFailure("invalid_request");
        return workspaceFailure("unavailable");
      }
      if (response.redirected || !/^application\/json(?:\s*;\s*charset=utf-8)?$/iu.test(response.headers.get("content-type") ?? "") ||
        response.headers.get("cache-control")?.toLowerCase() !== "no-store") { void response.body?.cancel().catch(() => undefined); return workspaceFailure("invalid_response"); }
      const length = response.headers.get("content-length");
      if (length !== null && (!/^(?:0|[1-9][0-9]*)$/u.test(length) || Number(length) > 32768)) { void response.body?.cancel().catch(() => undefined); return workspaceFailure("invalid_response"); }
      if (!response.body) return workspaceFailure("invalid_response");
      reader = response.body.getReader();
      const chunks: Uint8Array[] = []; let size = 0, reads = 0;
      while (true) {
        check(); if (++reads > 4096) return workspaceFailure("invalid_response");
        const item = await reader.read(); check(); if (item.done) break;
        size += item.value.byteLength; if (size > 32768) return workspaceFailure("invalid_response"); chunks.push(item.value.slice());
      }
      const bytes = new Uint8Array(size); let offset = 0;
      for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
      try { const result = decode(parseSubmissionJSON(new TextDecoder("utf-8", { fatal: true }).decode(bytes)), response.status); check(); return result; }
      catch (error) { if (error instanceof WorkspaceClientError) throw error; return workspaceFailure("invalid_response"); }
    };
    try { return await Promise.race([perform(), aborted]); }
    catch (error) { if (error instanceof WorkspaceClientError) throw new WorkspaceClientError(error.code); return workspaceFailure("unavailable"); }
    finally {
      finished = true; clearTimeout(timer); signal?.removeEventListener("abort", stop);
      if (onAbort) controller.signal.removeEventListener("abort", onAbort);
      try { void reader?.cancel().catch(() => undefined); } catch { /* Bounded best effort. */ }
      try { reader?.releaseLock(); } catch { /* Pending uncooperative read. */ }
    }
  }
  return Object.freeze({
    async inputs(input: ApplicationSelection, pageInput: CatalogPageRequest, signal?: AbortSignal) {
      const scope = snapshotApplicationSelection(input), page = snapshotCatalogPageRequest(pageInput);
      const query = new URLSearchParams({ organization_id: scope.organizationId, project_id: scope.projectId, application_id: scope.applicationId,
        ...(page.cursor === undefined ? {} : { cursor: page.cursor }) });
      return request("/console-api/v1/build-inputs?" + query, undefined, value => parseBuildInputs(value, scope), signal);
    },
    async cancel(input: BuildReadSelection, signal?: AbortSignal) {
      let selection: BuildReadSelection;
      try { selection = snapshotBuildReadSelection(input); } catch { return workspaceFailure("invalid_request"); }
      return request("/console-api/v1/builds/cancel?" + buildSelectionQuery(selection), "cancel", (wire, status) => {
        if (!catalogRecord(wire, ["outcome", "build"]) || (wire.outcome !== "applied" && wire.outcome !== "duplicate")) {
          return workspaceFailure("invalid_response");
        }
        const snapshot = parseBuildRead({ build: wire.build }, selection);
        if (snapshot.report.state !== (status === 202 ? "cancelling" : "cancelled") || snapshot.revision === 0) {
          return workspaceFailure("invalid_response");
        }
        return snapshot;
      }, signal);
    },
    async submit(value: BuildAttempt, signal?: AbortSignal) {
      let attempt: BuildAttempt;
      try { attempt = snapshotBuildAttempt(value); } catch { return workspaceFailure("invalid_request"); }
      return request("/console-api/v1/builds", attempt, (wire, status) => parseBuildReceipt(wire, attempt, status), signal);
    },
  });
}
