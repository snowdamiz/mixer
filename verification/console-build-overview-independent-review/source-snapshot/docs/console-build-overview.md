# Mixer console Builds view

This is a read-only SolidJS display slice for product-plan sections 13, 14, and
17. It uses the shared console shell, website assets, and website palette and
typography. The production `/builds` route remains genuinely unavailable while
there is no connected build API. The root-owned `/preview/builds` route imports
synthetic examples only in development.

Each selected platform has its own build identity, outcome, source label, and
attempt count. The view has no aggregate success state. It renders all eight
accepted lifecycle states; `reconciling` is labeled **Confirming outcome**.
Cancelling says it is waiting for the build to stop, and confirming outcome says
it is still confirming whether the build has stopped. Neither claims terminal
completion. Failed and timed-out attempts show plain-language explanations for
the accepted failure code. The view offers no cancellation, retry, signing,
download, publishing, billing, queue-position, or ETA controls or conclusions.

Source reference or upload reference is shown only when supplied in the selected
platform metadata. The source-content, toolchain-lock, and build-definition
SHA-256 digests are available under **Immutable build inputs**. The source
content digest is not labeled as a Git commit. A single footer explains that
build status is separate from signing and distribution.

## Internal display contract

`console/src/domain/build-overview.ts` defines the internal TypeScript view
model. It is not a public API JSON contract and is not a Phoenix adapter.

```ts
interface BuildOverviewInput {
  scope: { organizationId: string; projectId: string; applicationId: string };
  expected: readonly ExpectedPlatformBuild[];
  reports: readonly ReportedPlatformBuild[];
}
```

The selected `expected` array has one or two entries, with unique platforms
(`ios` or `android`). Each contains `platform`, `buildId`, `sourceSha256`,
`toolchainLockSha256`, and `buildDefinitionSha256`, and optionally
`source: { kind: "revision" | "upload", reference: string }`. These build IDs
and digests may differ between the platforms. Every report includes the common
scope, that platform's complete immutable identity, `state`, `attempt`,
`maxAttempts`, and `workerCompletionPending`. Failed and timed-out reports also
require an allowlisted `failureCode`; other states reject that field.

The future adapter must obtain the selection and immutable identity from an
authorized `Lifecycle.Build.spec` and join its `customer_status` projection
under the exact organization/project/application/build/platform scope:

| Lifecycle value | Internal display field |
| --- | --- |
| Spec organization/project/application IDs | `scope` and matching report scope |
| Spec `build_id`, `platform` | `buildId`, `platform` |
| Spec `source.sha256` | `sourceSha256` |
| Selected Spec source kind/reference, when supplied | Optional expected `source` metadata |
| Spec `toolchain_lock_sha256`, `build_definition_sha256` | Corresponding immutable identity digests |
| Status `state`, `attempt`, `max_attempts` | `state`, `attempt`, `maxAttempts` |
| Status `worker_completion_pending` | `workerCompletionPending` |
| Status `failure.code` on failed/timed-out attempt | `failureCode` |

Status alone lacks the immutable source/toolchain identity and tenant scope.
Joining it to a selection by platform alone is insufficient. The view does not
consume or reinterpret artifact references, retry eligibility, backoff, worker
references, or fences. Authentication, authorization, durable state, worker
observation trust, artifact content checks, and release eligibility remain the
future adapter's responsibilities.

`summarizeBuildOverview(unknown)` validates closed JSON-like input shapes, bounded
text and arrays, lowercase SHA-256 digests, exact selected identities, supported
states, attempts in `1..maxAttempts` with a maximum of five, and the accepted
worker uncertainty mapping. Only running, cancelling, and reconciling have
`workerCompletionPending: true`. Duplicate, unexpected, malformed, or mixed
identity reports fail closed. The component renders an alert without outcomes
when validation fails. Returned scope, rows, selected metadata, observations,
and arrays are copied and frozen.

Text follows the accepted backend contract: scope and build IDs contain
1..128 UTF-8 bytes, source references 1..1024 UTF-8 bytes. Unicode must be valid
and satisfy the local Elixir 1.20.4 `String.printable?` ranges. These include
U+0007..000D, U+001B, U+0020..007F, U+00A0..D7FF, U+E000..FFFD, and
U+10000..10FFFF. Lone UTF-16 surrogates are rejected. Whitespace is preserved
without trimming or normalization. A bounded cross-language probe compares
original representative vectors with the actual `Lifecycle.new` constructor;
it does not infer backend acceptance from a second copy of the frontend check.

The caller supplies expectations independently of reports. A missing report
remains an explicit **Not reported** platform card. Zero reports says **No build
updates yet** and retains every expected identity. Loading and unavailable states
show no previous outcomes. Components should receive a new reactive state when
the selected input changes.

## Validation and remaining work

Nine domain tests cover all 64 pairs of platform lifecycle states, expected
ordering, missing results, independent platform identities, immutable snapshots,
bounded failure codes, text boundaries, and malformed or inconsistent input. Six compiled Solid
view tests cover the actual rendered component, every state, failure visibility,
uncertainty wording, missing data, optional labels, disclosure markup, and
escaped untrusted text. The complete console suite, strict application
typecheck, and production build are captured by:

```sh
python3 verification/console-build-overview/verify.py
```

The [producer receipt](../verification/console-build-overview/receipt.json)
records commands, tool versions, inherited base revision, current source
digests, output hashes, limitations, and temporary-output cleanup. Initial checks
before the final wording/layout refinement are marked superseded.

Root owns browser verification and integration acceptance separately. This
producer receipt does not establish browser layout, interactive disclosure or
selector behavior, full accessibility, authenticated API integration, deployment,
real builds, physical devices, FieldLog dogfood qualification, or any GA gate.
No server, browser, simulator, emulator, phone, or production operation is used
by this lane.
