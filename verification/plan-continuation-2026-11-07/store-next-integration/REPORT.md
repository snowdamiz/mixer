# Add reconciliation for an existing App Store Connect build

Select one W13 slice: implement `mixer submit status` for a customer who already
has an App Store Connect build ID. The command reads that build's current
processing outcome and retains the last observation. It never uploads a binary.
This advances the Section 15 requirement to reconcile an uncertain upload rather
than submit the same version again. It is narrower than submission readiness.

## Observed source and gap

Audit base is `e7254f3703d5b8191aa72ec2fb11fa91b5ea99ba`, tree
`482fb5b41a203edfd517627b0e014d31eb7f02e2`. Git reports version `2.56.0`.
The working tree has concurrent root and Android changes. At final inspection,
`git diff --name-only -- cli hosted/lib/mixer_hosted/builds
hosted/lib/mixer_hosted_web/router.ex` returned no paths. Line references below
refer to the inspected owning files. Root tracking-file line numbers can move.

| Owning source | What exists and what it permits |
| --- | --- |
| `mixer-product-plan.md:574-580` | Customer-owned accounts and local signing are supported. Upload, processing, and ready-for-testing are distinct. Timeouts require reconciliation. |
| `mixer-product-plan.md:843`, Section 24 | W13 depends on W12 for the complete workflow. D6 needs actual readiness on both stores. Independent packages can advance through executable contracts. |
| `work-graph.json`, package `id == W13` | `state: ready`, empty evidence, full acceptance undemonstrated. This is scheduling state, not store qualification. |
| `cli/Sources/MixerCLI/main.swift:127-128` | Every `submit` invocation fails with `workflow.not-qualified`; there is no status subcommand or caller. |
| `cli/Sources/MixerCLI/main.swift:4-20,66-72` | Closed option parsing and per-command allowlists must both admit the new status options. |
| `cli/Sources/MixerBuild/Configuration.swift:11-56,81-86` | Existing application identity validation, duplicate-key JSON admission, and structured JSON output can support the command. |
| `cli/Sources/MixerBuild/Configuration.swift:92` | Source snapshots exclude `.mixer`; local reconciliation records belong there, not in exported source. |
| `hosted/lib/mixer_hosted/builds/lifecycle.ex:3-8,15-23` | Internal build decisions accept seven artifact reference kinds, including an unsigned native binary. They expressly do not prove signing or release eligibility. |
| `hosted/lib/mixer_hosted/builds/dispatch.ex:3-16`, `coordinator.ex:264-285` | Trusted worker dispatch has no default adapter; missing configuration returns `dispatch_unavailable`. This is not a store transport. |
| `hosted/lib/mixer_hosted_web/router.ex:12-23` | Customer workspace, artifact, and audit routes exist. There is no store or submission route. |
| `cli/Sources/MixerBuild/AppleProject.swift:43-51`, `AndroidProject.swift:180-189` | Current local builders produce unsigned development outputs. Neither supplies a signed-store submission handoff. |

The concrete customer gap is that a known provider build cannot be checked from
Mixer after an upload outcome becomes uncertain. Reusing the worker lifecycle or
calling an unsigned artifact a submission would not close this gap.

## Exact next task

Implement one read-only command, proposed spelling:

```text
mixer submit status --provider app-store-connect --build-id BUILD_ID --app-id ASC_APP_ID --directory PROJECT
```

Implement the production HTTP reader and the CLI caller in the same slice.
A state enum or an injected fake provider without that caller is insufficient.

1. Load the project's application identity. Require the explicit existing
   provider build and app IDs. Read build identity and processing status using
   the official App Store Connect API specification. Bind the returned identity
   to the requested build and app before updating the local record. Preserve
   provider version information. Do not claim a source or binary digest match
   that the provider response does not establish.
2. Accept a customer-supplied, short-lived bearer token through a secret input
   boundary, such as `MIXER_ASC_BEARER_TOKEN`. Implement no JWT signing, key
   storage, credential rotation, account connection, or account mutation here.
   Never place the token, authorization header, or unfiltered error body in JSON,
   logs, local records, or test receipts.
3. Issue bounded read requests to the fixed provider origin. Reject redirects
   and identity mismatches. Bound response bytes and request time. Treat numeric
   limits as explicit hypotheses for this development slice. Do not add a
   configurable provider URL or an upload/retry operation.
4. Retain a credential-free, identity-bound observation atomically under
   `.mixer/store/`. A timeout or malformed observation preserves the last valid
   observation and separately reports the latest query as unresolved. Reject
   concurrent overwrite of a newer observation. A timeout never schedules an
   upload or creates a replacement submission identity.
5. Preserve the raw provider processing state alongside the interpreted outcome.
   A processing success cannot report TestFlight readiness, review approval, or
   availability. Those require additional provider evidence outside this slice.
   Unknown provider states remain unresolved. Report authentication failure and
   explicit provider-required human action without erasing progress.
6. Admit only the `submit status` subcommand. Bare `submit` and upload requests
   retain the existing refusal. Return structured pending/failure outcomes that
   a later hosted submission consumer can use without confusing them with D6.

No provider specification was fetched in this audit. Exact endpoint, relationship,
field, and error mappings are deliberately unverified. The implementer must read
the official specification before coding them. Do not guess a readiness mapping
from a processing field. This is a proposed contract, not an existing one.

## Ownership and executable acceptance

Reserve only these implementation paths for one fresh ordinary worker:

- New `cli/Sources/MixerBuild/AppStoreConnectBuildStatus.swift` for the real HTTP
  reader and provider response boundary.
- New `cli/Sources/MixerBuild/StoreReconciliation.swift` for the command entry,
  identity checks, local observation persistence, and structured outcomes.
- New `cli/Tests/MixerBuildTests/StoreReconciliationTests.swift` for a named
  `StoreSubmissionReconciliationTests` suite.
- A narrow coordinated edit of `cli/Sources/MixerCLI/main.swift` for parser,
  help, and caller wiring. The parent reserves and integrates this shared file.

Existing Foundation and package dependencies suffice. Leave `ProjectGenerator`,
Android product and tests, source-pair files, hosted sources, CI, and root
tracking files to their current owners. The parent updates tracking after an
accepted implementation. Use a new evidence directory distinct from this audit.

The host command for the proposed suite is:

```sh
swift test --package-path cli --scratch-path "$MIXER_STORE_SCRATCH" --filter StoreSubmissionReconciliationTests
```

`MIXER_STORE_SCRATCH` must be a fresh, explicitly owned absolute path. The suite
uses an injected scripted URL loading transport and a non-secret dummy token.
It exercises the production request builder, response reader, command entry,
and actual temporary record files. No real account or network is needed.
Required cases are processing pending, provider validation failure, processing
success with readiness still unverified, timeout after a valid prior observation,
wrong app or build, duplicate or malformed JSON, unknown status, response bounds,
redirect refusal, authentication rejection, stale concurrent write, and token
redaction. Assert the entire request trace contains only the permitted reads and
zero upload calls. Exercise repeated invocations against the same local record.
Also verify the CLI's new argument dispatch and retained bare-submit refusal.

Stop after this one passing host integration and independent review. Do not turn
it into a complete store connection, signer, uploader, or generic workflow rewrite.
Capture compiler/tool versions, source digest, command, output, and owned scratch
cleanup when the parent authorizes execution. This audit runs no such command.

## Frozen dependencies and remaining gates

`PLAN.md:986-990` explicitly freezes the hosted catalog-inspector and
authority-driver lanes and the rejected outbound Worker transport V2 lane.
`docs/hosted-build-coordinator.md:128-144` keeps production worker transport and
signing pending and states that its coordinator uses no frozen catalog or
authority code. Neither internal worker status nor the customer OTA artifact API
is a signed-store handoff. A complete W12-to-W13 submission join remains pending.

This selected status command depends on the customer's already existing ASC build
identity, which is compatible with the Section 15 customer-owned account and
local-signing path. It does not read, import, configure, or execute the frozen
lanes. Therefore no specific frozen dependency blocks this slice, and no W15
fallback is selected. If no provider build ID exists after an upload timeout,
discovery by account, app, and version remains a separate unimplemented problem.

Implementation and host acceptance can occur entirely without publishing,
credentials, real submissions, native execution, UI, capture, phones, or historical
process probes. Actual provider validation still needs separately authorized
read-only account access. Uploads, full submission reconciliation, test links,
Play support, signed W12 handoff, FieldLog immutable-package qualification, D6,
physical acceptance, and GA remain pending.

Audit commands were bounded `rg`, `sed`, `nl`, `cat`, and read-only Git inspection,
including `git status --short`, `git rev-parse HEAD 'HEAD^{tree}'`, `git --version`,
and the scoped `git diff --name-only` above. Read the plan Sections 15, 23, and 24,
W13 and W15, owning CLI/build/router sources, and public hold descriptions.
No compiler, test, build, delegated agent, provider request, device/process probe,
commit, push, or frozen implementation was run or opened. The only written
artifact is this report. No gate is promoted.
