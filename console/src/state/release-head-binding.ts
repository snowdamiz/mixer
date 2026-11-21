import { createEffect, createMemo, createSignal, onCleanup } from "solid-js";
import type { Accessor } from "solid-js";
import type { ReleaseHeadClient } from "../api/cookie-release-head-client.js";
import { WorkspaceClientError } from "../api/workspace-transport.js";
import { parseReleaseHeadSearch } from "../domain/release-head.js";
import type { PromotionGroup, ReleaseHead, ReleaseHeadTarget } from "../domain/release-head.js";
import type { WorkspaceDirectoryState } from "../domain/workspace-directory.js";
import type { ConsoleSession } from "./browser-session-controller.js";

type Blocked = { readonly kind: "missing" | "invalid" | "unauthenticated" | "session-unavailable" | "scope-mismatch" };
type Read = { readonly kind: "loading"; readonly target: ReleaseHeadTarget; readonly client: ReleaseHeadClient };
type PromotionGroupState = PromotionGroup | { readonly kind: "loading" | "unavailable" };
type Outcome =
  | Exclude<ReleaseHead, { readonly kind: "published" }>
  | (Extract<ReleaseHead, { readonly kind: "published" }> & { readonly promotionGroup: PromotionGroupState | null })
  | { readonly kind: "denied" | "unavailable" };
export type ReleaseHeadState = Blocked | { readonly kind: "loading" } | Outcome;

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
    if (input.kind !== "target") return input;
    const active = session();
    if (active?.kind === "unauthenticated") return { kind: "unauthenticated" };
    if (active?.kind !== "ready") return { kind: "session-unavailable" };
    const organizationId = organization(), projectId = project();
    if ((organizationId !== undefined && organizationId !== input.target.organizationId) ||
        (projectId !== undefined && projectId !== input.target.projectId)) return { kind: "scope-mismatch" };
    return { kind: "loading", target: input.target, client: active.releaseHead };
  });

  const [outcome, setOutcome] = createSignal<{ readonly read: Read; readonly state: Outcome }>();
  createEffect(() => {
    const read = current();
    setOutcome(undefined);
    if (read.kind !== "loading") return;
    const controller = new AbortController();
    onCleanup(() => controller.abort());
    const commit = (state: Outcome) => {
      if (!controller.signal.aborted && current() === read) setOutcome({ read, state });
    };
    void read.client.readDetails(read.target, controller.signal).then(head => {
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
    if (read.kind !== "loading") return read;
    const result = outcome();
    return result?.read === read ? result.state : { kind: "loading" };
  };
}
