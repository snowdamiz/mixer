import { catalogRecord } from "../domain/build-catalog.js";
import { parseSubmissionJSON } from "../domain/build-submission.js";
import { parseReleaseHead, releaseHeadQuery, snapshotReleaseHeadTarget } from "../domain/release-head.js";
import type { ReleaseHead, ReleaseHeadTarget } from "../domain/release-head.js";
import { createWorkspaceTransport, workspaceFailure } from "./workspace-transport.js";
import type { WorkspaceTransportOptions } from "./workspace-transport.js";

export interface ReleaseHeadClient {
  read(target: ReleaseHeadTarget, signal?: AbortSignal): Promise<ReleaseHead>;
}

export function createCookieReleaseHeadClient(options: WorkspaceTransportOptions = {}): ReleaseHeadClient {
  if (!catalogRecord(options, [], ["fetch", "timeoutMs"])) return workspaceFailure("invalid_request");
  const request = createWorkspaceTransport(options, "same-origin", () => ({ accept: "application/json" }),
    { parse: parseSubmissionJSON, maximumBytes: 16_384 });
  return Object.freeze({
    async read(input: ReleaseHeadTarget, signal?: AbortSignal) {
      let target: ReleaseHeadTarget;
      try { target = snapshotReleaseHeadTarget(input); }
      catch { return workspaceFailure("invalid_request"); }
      return request("/console-api/v1/release-head?" + releaseHeadQuery(target), value => parseReleaseHead(value, target), signal);
    },
  });
}
