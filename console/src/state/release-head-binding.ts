import { createEffect, createMemo, createSignal, onCleanup } from "solid-js";
import type { Accessor } from "solid-js";
import type { ReleaseHeadClient } from "../api/cookie-release-head-client.js";
import { WorkspaceClientError } from "../api/workspace-transport.js";
import { parseReleaseHeadSearch } from "../domain/release-head.js";
import type { PromotionGroup, ReleaseHead, ReleaseHeadLocation, ReleaseHeadTarget } from "../domain/release-head.js";
import type { WorkspaceDirectoryState } from "../domain/workspace-directory.js";
import type { ConsoleSession } from "./browser-session-controller.js";

type Blocked = { readonly kind: "missing" | "invalid" | "unauthenticated" | "session-unavailable" | "scope-mismatch" };
type Selection = Extract<ReleaseHeadLocation, { readonly kind: "target" | "promotion" }>;
type Read = { readonly kind: "read"; readonly selection: Selection; readonly client: ReleaseHeadClient };
type PromotionGroupState = PromotionGroup | { readonly kind: "loading" | "unavailable" };
type Outcome =
  | Exclude<ReleaseHead, { readonly kind: "published" }>
  | (Extract<ReleaseHead, { readonly kind: "published" }> & { readonly promotionGroup: PromotionGroupState | null })
  | { readonly kind: "historical-promotion"; readonly target: ReleaseHeadTarget; readonly promotionGroup: PromotionGroup }
  | { readonly kind: "promotion-unavailable" }
  | { readonly kind: "denied" | "unavailable" };
export type ReleaseHeadState = Blocked | { readonly kind: "loading" | "promotion-loading" } | Outcome;

export function createReleaseHeadBinding(
  search: Accessor<string>,
  session: Accessor<ConsoleSession | undefined>,
  workspace: Accessor<WorkspaceDirectoryState>,
): Accessor<ReleaseHeadState> {
  const location = createMemo(() => parseReleaseHeadSearch(search()));
  const organization = createMemo(() => workspace().selectedOrganizationId);
  const project = createMemo(() => workspace().selectedProjectId);
  const current = createMemo((): Blocked | Read => {
    const input = location();
    if (input.kind !== "target" && input.kind !== "promotion") return input;
    const active = session();
    if (active?.kind === "unauthenticated") return { kind: "unauthenticated" };
    if (active?.kind !== "ready") return { kind: "session-unavailable" };
    const organizationId = organization(), projectId = project();
    const target = input.kind === "promotion" ? input.publication.target : input.target;
    if ((organizationId !== undefined && organizationId !== target.organizationId) ||
        (projectId !== undefined && projectId !== target.projectId)) return { kind: "scope-mismatch" };
    return { kind: "read", selection: input, client: active.releaseHead };
  });

  const [outcome, setOutcome] = createSignal<{ readonly read: Read; readonly state: Outcome }>();
  createEffect(() => {
    const read = current();
    setOutcome(undefined);
    if (read.kind !== "read") return;
    const controller = new AbortController();
    onCleanup(() => controller.abort());
    const commit = (state: Outcome) => {
      if (!controller.signal.aborted && current() === read) setOutcome({ read, state });
    };
    const selection = read.selection;
    if (selection.kind === "promotion") {
      const { publication } = selection;
      void read.client.readPromotionGroup(publication, controller.signal).then(
        promotionGroup => commit({ kind: "historical-promotion",
          target: promotionGroup[publication.target.platform].target, promotionGroup }),
        () => commit({ kind: "promotion-unavailable" }),
      );
      return;
    }
    void read.client.readDetails(selection.target, controller.signal).then(head => {
      if (head.kind === "empty") return commit(head);
      if (head.release.details.action !== "stage_promote") return commit({ ...head, promotionGroup: null });
      if (controller.signal.aborted || current() !== read) return;
      commit({ ...head, promotionGroup: { kind: "loading" } });
      const { sequence, manifestSha256 } = head.release;
      void read.client.readPromotionGroup({ target: head.target, sequence, manifestSha256 }, controller.signal).then(
        promotionGroup => commit({ ...head, promotionGroup }),
        () => commit({ ...head, promotionGroup: { kind: "unavailable" } }),
      );
    }, (error: unknown) => {
      if (error instanceof WorkspaceClientError && (error.code === "permission_denied" || error.code === "not_found")) {
        commit({ kind: "denied" });
      } else {
        commit({ kind: "unavailable" });
      }
    });
  });

  return () => {
    const read = current();
    if (read.kind !== "read") return read;
    const result = outcome();
    if (result?.read === read) return result.state;
    return { kind: read.selection.kind === "promotion" ? "promotion-loading" : "loading" };
  };
}
