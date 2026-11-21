import { catalogRecord } from "../domain/build-catalog.js";
import { parseSubmissionJSON } from "../domain/build-submission.js";
import { parsePromotionGroup, parseReleaseHeadDetails, promotionGroupQuery, releaseHeadQuery, snapshotReleaseHeadTarget } from "../domain/release-head.js";
import type { PromotionGroup, PromotionPublication, ReleaseHead, ReleaseHeadTarget } from "../domain/release-head.js";
import { createWorkspaceTransport, workspaceFailure } from "./workspace-transport.js";
import type { WorkspaceTransportOptions } from "./workspace-transport.js";

export interface ReleaseHeadClient {
  readPromotionGroup(publication: PromotionPublication, signal?: AbortSignal): Promise<PromotionGroup>;
  readDetails(target: ReleaseHeadTarget, signal?: AbortSignal): Promise<ReleaseHead>;
}

export function createCookieReleaseHeadClient(options: WorkspaceTransportOptions = {}): ReleaseHeadClient {
  if (!catalogRecord(options, [], ["fetch", "timeoutMs"])) return workspaceFailure("invalid_request");
  const request = createWorkspaceTransport(options, "same-origin", () => ({ accept: "application/json" }),
    { parse: parseSubmissionJSON, maximumBytes: 16_384 });
  return Object.freeze({
    async readPromotionGroup(input: PromotionPublication, signal?: AbortSignal) {
      let publication: PromotionPublication;
      let query: string;
      try {
        publication = { target: snapshotReleaseHeadTarget(input.target),
          sequence: input.sequence, manifestSha256: input.manifestSha256 };
        query = promotionGroupQuery(publication);
      } catch { return workspaceFailure("invalid_request"); }
      return request("/console-api/v1/release-head?" + query,
        value => parsePromotionGroup(value, publication), signal);
    },
    async readDetails(input: ReleaseHeadTarget, signal?: AbortSignal) {
      let target: ReleaseHeadTarget;
      try { target = snapshotReleaseHeadTarget(input); }
      catch { return workspaceFailure("invalid_request"); }
      return request("/console-api/v1/release-head?" + releaseHeadQuery(target) + "&view=details-v2",
        value => parseReleaseHeadDetails(value, target), signal);
    },
  });
}
