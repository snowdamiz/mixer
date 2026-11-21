import { A } from "@solidjs/router";
import { For, Show } from "solid-js";
import type { Accessor } from "solid-js";
import type { PromotionReceipt, PublishedRelease } from "../domain/release-head.js";
import type { ReleaseHeadState } from "../state/release-head-binding.js";
import "./release-head-page.css";

const statusCopy = {
  missing: "Open a release link to view its published head.",
  invalid: "This release link does not specify a valid target.",
  unauthenticated: "Sign in to view this release.",
  "session-unavailable": "Console session unavailable.",
  "scope-mismatch": "This release target is outside your selected workspace.",
  loading: "Loading release head…",
  denied: "You cannot access this release target.",
  unavailable: "Release head unavailable.",
  empty: "No release has been published to this target.",
  published: "Published release",
} satisfies Record<ReleaseHeadState["kind"], string>;

const actionCopy = {
  publish: "Publish",
  promote: "Rollout expansion",
  stage_promote: "Environment promotion",
  rollback: "Rollback",
  halt: "Halt",
} satisfies Record<PublishedRelease["details"]["action"], string>;

function PromotionPublicationItem(props: { readonly receipt: PromotionReceipt }) {
  const receipt = () => props.receipt;
  const headStatus = () => {
    const head = receipt().head;
    return head.kind === "current" ? "Current head" : "Head advanced to " + head.sequence;
  };
  return <li>
    <strong>{receipt().target.platform === "ios" ? "iOS" : "Android"}</strong>
    <div>Sequence <code>{receipt().sequence}</code> · {headStatus()}</div>
    <div>Manifest <code>{receipt().manifestSha256}</code></div>
  </li>;
}

export function ReleaseHeadPage(props: {
  readonly state: Accessor<ReleaseHeadState>;
  readonly onRetrySession?: () => void;
}) {
  const kind = () => props.state().kind;
  const head = () => {
    const state = props.state();
    return state.kind === "empty" || state.kind === "published" ? state : undefined;
  };
  const published = () => {
    const state = head();
    return state?.kind === "published" ? state.release : undefined;
  };

  const group = () => {
    const state = head();
    return state?.kind === "published" ? state.promotionGroup : null;
  };

  const committedGroup = () => {
    const promotion = group();
    return promotion?.kind === "committed" ? promotion : undefined;
  };

  return <section aria-labelledby="release-head-heading">
    <header class="page-heading"><h1 id="release-head-heading">Releases</h1></header>
    <div class="empty-state">
      <div role="status"><h2>{statusCopy[kind()]}</h2></div>
      <Show when={kind() === "scope-mismatch"}>
        <p><A href="/workspace">Change workspace selection</A></p>
      </Show>
      <Show when={kind() === "session-unavailable" || kind() === "unauthenticated"}>
        <button type="button" class="workspace-text-button" onClick={() => props.onRetrySession?.()}>Check session</button>
      </Show>
      <Show when={head()?.target}>{target => <dl class="release-head-fields" aria-label="Release target">
        <div><dt>Organization ID</dt><dd><code>{target().organizationId}</code></dd></div>
        <div><dt>Project ID</dt><dd><code>{target().projectId}</code></dd></div>
        <div><dt>Application ID</dt><dd><code>{target().applicationId}</code></dd></div>
        <div><dt>Environment ID</dt><dd><code>{target().environmentId}</code></dd></div>
        <div><dt>Platform</dt><dd><code>{target().platform}</code></dd></div>
        <div><dt>Runtime fingerprint</dt><dd><code>{target().runtimeFingerprint}</code></dd></div>
        <div><dt>Channel</dt><dd><code>{target().channel}</code></dd></div>
      </dl>}</Show>
      <Show when={published()}>{release => <dl class="release-head-fields" aria-label="Published release details">
        <div><dt>Release ID</dt><dd><code>{release().releaseId}</code></dd></div>
        <div><dt>Sequence</dt><dd><code>{release().sequence}</code></dd></div>
        <div><dt>Rollout basis points</dt><dd>{release().rolloutBasisPoints}</dd></div>
        <div><dt>Manifest SHA-256</dt><dd><code>{release().manifestSha256}</code></dd></div>
        <div><dt>Payload SHA-256</dt><dd><code>{release().payloadSha256}</code></dd></div>
        <div><dt>Source commit</dt><dd><code>{release().details.sourceCommit}</code></dd></div>
        <div><dt>Payload size</dt><dd>{release().details.payloadBytes} bytes</dd></div>
        <div><dt>Artifact signing key ID</dt><dd><code>{release().details.artifactKeyId}</code></dd></div>
        <div><dt>Assignment signing key ID</dt><dd><code>{release().details.assignmentKeyId}</code></dd></div>
        <div><dt>Ledger action</dt><dd>{actionCopy[release().details.action]}</dd></div>
        <div><dt>Runtime admission</dt><dd>Compatibility checked when this head was committed.</dd></div>
        <div><dt>Manifest capabilities</dt><dd>
          <Show when={release().details.capabilities.length > 0} fallback="None declared">
            <ul class="release-head-capabilities">
              <For each={release().details.capabilities}>{capability => <li>
                <code>{capability.id}</code>
                <div>{capability.permissions === null ? "No grant entry" :
                  capability.permissions.length === 0 ? "No permissions declared" :
                    capability.permissions.map(permission => <code>{permission}</code>)}</div>
              </li>}</For>
            </ul>
          </Show>
        </dd></div>
      </dl>}</Show>
      <Show when={group()}>{promotion => <section class="release-head-promotion" aria-labelledby="promotion-group-heading">
        <h3 id="promotion-group-heading">Promotion group</h3>
        <Show when={committedGroup()} fallback={
          <p role="status">{promotion().kind === "loading" ? "Loading promotion group…" : "Unavailable"}</p>
        }>{committed => <ul class="release-head-capabilities">
          <PromotionPublicationItem receipt={committed().ios} />
          <PromotionPublicationItem receipt={committed().android} />
        </ul>}</Show>
      </section>}</Show>
    </div>
  </section>;
}
