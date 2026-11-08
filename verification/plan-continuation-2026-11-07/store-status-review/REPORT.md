**REQUEST CHANGES — one P2 finding; no verified P1 finding.**

This independent review covers the frozen, uncommitted W13 existing-build status
candidate at `/Users/andreyyurlov/.t3/worktrees/mixer/t3-b92773b5`, base
`25ac442c5213326b3601456a5fd62898f152111f`, tree
`1a08391fd1c317c88ccf6cbf8d9bed081ce37f38`. Parent review base is
`96f03ab65966a6374e958e780fa09a3eed814c0b`, tree
`6dacea5d2f5cd55d6934142cce556a4bd0fcd1c0`. Reviewed patch SHA-256:
`7bffa6b867dbed11a454c75f955ca7f234ec8f7ce520875ad4e7501a18fbeaf3`.

The intended customer behavior is to reconcile an already identified App Store
Connect build through `mixer submit status`, retain its processing observation,
and keep upload, testing readiness, review, and availability separate. The
binding references are product-plan Section 15 and the parent's
`store-next-integration/REPORT.md`. This is not approval of complete W13, D6, or GA.

**P2: a known credential in a prior observation survives persistence and is
emitted after the credential leaves the environment.**

Owning source: `cli/Sources/MixerBuild/StoreReconciliation.swift:88`, `:97-104`,
and `:177-178` in the frozen candidate. `reserve()` rewrites the prior observation
before credential-aware handling. The later `safeObservation` filter suppresses
only the current report. It neither sanitizes the durable observation nor prevents
a later credential-free invocation from returning it.

Executable reproduction is
`input/cli/Tests/MixerBuildTests/StoreIndependentReviewTests.swift:149-164`:

1. Query with dummy token A and a scripted valid provider response whose version
   is dummy token B. This creates the prior record through the production reader
   and commit path; the probe does not hand-edit that record.
2. Supply B as the new bearer token and return HTTP 401. The current report hides
   the observation, but the reservation has persisted B again.
3. Query the same identity with no token. The result correctly says
   `store.credential-required`, but its retained observation emits B in JSON.

Observed output:

```text
PROBE priorSecret currentOutputContains=false localRecordContains=true afterTokenRemovalOutputContains=true
```

Required behavior is that a value recognized as the current credential cannot
remain a reusable persisted observation and subsequently enter output. Apply
credential-aware sanitization or invalidation under the record lock before the
reservation rewrites it, preserve safe identity/progress, and test the subsequent
missing-token invocation. Do not retain a raw secret in a quarantine file or log.
The existing immediate-response suppression is a useful control but insufficient.

This is a synthetic reflection-boundary reproduction, not a claim that Apple has
returned a bearer token as a real build version, or that a live credential leaked.
It uses the reader's admitted value domain and the task's explicit prior-record
reflection requirement. That limits severity to P2, while the demonstrated durable
secret re-emission makes it a required correction rather than an untested
filesystem concern. The observational probe intentionally asserts the two bad
booleans; its passing test result is evidence of reproduction, not acceptance of
that behavior. The original suite does not exercise this transition.

**Execution and evidence.**

Only two compile/test attempts ran. Both used a new review-owned source snapshot
and Swift scratch, Apple Swift 6.3.3, Xcode 26.6 build 17F113, macOS SDK 26.5,
`-j 2`, the parent's existing `Commands` runner imported as `managedCommands`,
600 seconds per command, 1,200 seconds total, and 8 MiB aggregate output. The
wrapper removes `MIXER_ASC_BEARER_TOKEN` from the test process environment. All
provider responses and credentials were synthetic; no account was accessed.

The common executable and arguments were:

```text
/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift test --package-path /Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4/verification/plan-continuation-2026-11-07/store-status-review/input/cli --scratch-path /Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4/verification/plan-continuation-2026-11-07/store-status-review/scratch -j 2 --filter StoreSubmissionReconciliationTests
```

The second attempt changed only the filter to `StoreIndependentReviewTests` after
adding the separate review probe file. `run_review.py` retains the exact environment
and wrapper. Each attempt's `receipt.json` contains the argv, source hashes, tool
versions, log hashes, timestamps, and owned-process custody. The wrapper is now at
its two-attempt limit and scratch has been removed; it is not a third-run shortcut.

- The original eight-test suite passed independently. The managed compile/test
  command took 30.585 seconds; the selected tests reported 0.178 seconds.
- Six independent probe groups completed in the second attempt. The managed
  command took 47.991 seconds; selected probes reported 32.126 seconds. Five groups
  verify controls and one records the P2 failure above.
- A URLProtocol that never responds reached the production caller's 30-second
  deadline in 30.005851459 seconds. It returned `store.timeout`, cancellation
  reached `stopLoading`, and the prior observation remained byte-identical after
  extracting and canonicalizing its JSON. No late observation was committed.
- A held local flock caused a bounded refusal in 2.005673208 seconds, with zero
  provider requests, the whole prior record unchanged, and no leftover atomic
  temporary files.
- Eight concurrent real CLI processes without a bearer token advanced the existing
  record from issued generation 1 to 9 without losing reservations or altering
  its observation. The original suite separately proves that an older successful
  request cannot replace a newer committed observation.
- Separate included-app mismatch, duplicate included app, relationship ID/type
  mismatch, empty included list, reflected raw state, and a control character in
  state all preserved the prior observation and reported unresolved.
- Record and lock symlinks, and generation-counter overflow, failed before any
  provider request and did not alter the outside control file.

The final verification receipt is `review-receipt.json`. Important SHA-256 values:

```text
AppStoreConnectBuildStatus.swift   21198f3f5a91f4666b66bb540ab9e14214381a142903b9c034e5cd30a260d8f5
StoreReconciliation.swift          5ff16e78f39beb1c1b81ce469b9c90ea486ed492f98d36022426e83bb1602ecc
MixerCLI/main.swift                d6b235f63e551f09db526103b6bdae2e311f8d50890bf62d79bf37aec0e52a42
StoreReconciliationTests.swift     1656b7d597e91ce569724ca34332c1f78bd4a1e207ce2d33e4a88d38393f713b
StoreIndependentReviewTests.swift  bacbcc4ce702de19856fa78a127935041aa3057cf7b1615d3c0ff0f407b1bae4
original snapshot content digest  aafb690f5df1bcee90b1648d070f0b7291c4c6d1b7be1860bc39f4277cd5d7a5
original snapshot manifest        6e7da583a8f812f21e3021cb7053b1feb37ac64e30d12f9d5e4933b4f069b956
parent managed Commands runner    c758c9685ef536968db06dfaf9f25450eac47db83fd2531a8caa2000cf793e1a
original suite stdout             8278461365cda46e588f74fb277667488bfbf4b2de721a54d9ac26e86c1cc71a
independent probes stdout         b9352aa223f40ca017a20d7d59de43a1bec37fadb5f3367d8fe05cae7d1d8f41
```

The snapshot digest is SHA-256 of compact sorted JSON mapping relative paths to
SHA-256 values. All 116 original snapshot files and the four candidate files were
rechecked unchanged after execution. The review probe is an additional file in
the evidence snapshot only. It does not modify candidate or parent product code.

**Verified controls and exact provider mapping.**

All seven retained official documentation files matched their recorded hashes
and byte counts. `official-contract-extract.json` retains the relevant schema
entries and source hashes. Primary web checks of Apple's HTML pages returned
JavaScript placeholders; the web tool could not fetch the documentation JSON.
The mapping below therefore relies on the inspected, retained official JSON,
not a claimed fresh API response.

[Read build information](https://developer.apple.com/documentation/appstoreconnectapi/get-v1-builds-_id_)
permits GET `/v1/builds/{id}`, `fields[builds]` containing version, processingState
and app, `include=app`, and `fields[apps]=bundleId`.
[Build response](https://developer.apple.com/documentation/appstoreconnectapi/buildresponse),
[app linkage](https://developer.apple.com/documentation/appstoreconnectapi/build/relationships-data.dictionary/app-data.dictionary/data-data.dictionary),
and [app attributes](https://developer.apple.com/documentation/appstoreconnectapi/app/attributes-data.dictionary)
support the resource and bundle checks. Candidate reader lines 42-49 bind all five
identities: requested build, requested app, relationship app, included app, and
project bundle. Missing evidence fails closed. Requiring optional provider
attributes for this narrow observation is a documented admission restriction.

[Build attributes](https://developer.apple.com/documentation/appstoreconnectapi/build/attributes-data.dictionary)
list PROCESSING, FAILED, INVALID, and VALID. Candidate reconciliation lines 32-38
preserve raw state and version: pending, failed, and processing-succeeded are
separate outcomes; unknown values remain unresolved. All reports keep TestFlight
readiness, review approval, and availability unverified. The original repeated
invocation test covers each mapped state and an unknown state. Success does not
become a release or a new submission identity.

Reader lines 20-37 and 81-111 constrain the production request to the fixed HTTPS
Apple endpoint and GET, reject redirect callbacks and 3xx responses, enforce
streaming/declared byte bounds, and bound both URLSession and caller waiting. The
session is ephemeral with cookies, URL cache, and credential store removed.
Authentication challenges other than server trust are cancelled. Selected provider
fields reject current-token reflection; error bodies, headers, and underlying
transport diagnostic strings are not serialized. The original suite drives these
production methods through scripted URL loading, including wrong identity,
duplicate JSON keys, invalid JSON, byte limits, redirection, 401/403/404/429/500,
invalid credentials, and error-message reflection. It does not prove live TLS or
account behavior.

The CLI wiring at `main.swift:15`, `:73`, and `:130-133` preserves narrow option
admission and invokes the real reconciliation entry. Subprocess checks prove bare
submit/upload refusal, duplicate and unrelated option refusal, missing credentials,
repeated invocation, and help. Successful provider responses are tested through
the public reconciliation entry with the production reader; a successful network
query through an external CLI process is still unqualified. No provider URL,
upload operation, JWT signer, key persistence, or configuration bypass was added.

The local file code uses generation reservation before HTTP, per-identity flock,
file fsync, atomic rename, and directory fsync. Opened record/lock files must be
single-link regular files; descriptor-relative opens reject final symlinks. Normal
failure paths close descriptors and unlink owned temporary files. Source inspection
and the host controls support these statements, not a power-loss or adversarial
filesystem qualification.

**Limitations and integration conditions.**

The lack of an exhaustive provider account-action taxonomy is an honest limitation
for this slice. The retained [error schema](https://developer.apple.com/documentation/appstoreconnectapi/errorresponse/errors-data.dictionary)
describes machine-readable hierarchical codes but does not establish a complete
agreement/verification mapping. A 403 safely reports denied access and asks the
customer to inspect Apple's interface while retaining progress. It must not be
promoted to Section 15's complete awaiting-human-action workflow. Inventing a
particular missing agreement from a generic 403 would be incorrect.

The implementation's simulated-timeout limitation is partly reduced by this
review: the actual 30-second caller deadline and cancellation were exercised with
a silent scripted transport. Real DNS/TLS/socket/provider deadline behavior remains
unverified. No power-loss, fsync/rename failure injection, hostile concurrent
filesystem replacement, or lock-inode replacement campaign ran. New parent-directory
creation is not separately fsynced in the current implementation, so the ordinary
file/store-directory fsync path is not proof of power-loss durability for the
whole newly created hierarchy. These are explicit durability limits, not claimed
passes or additional reproduced customer failures.

The known-credential persistence issue is different: it has an executable
counterexample in the requested reflection boundary and must be fixed before
acceptance. No other speculative or cosmetic findings are promoted.

After a corrected candidate passes independent review, the parent must integrate
only the four owned files, retain its pair9 source/CI/signature corrections, and
rebind the canonical owning closure. Read-only `source_inputs(load_profile())`
inspection counted 101 current parent inputs; the two added CLI sources make 103.
`main.swift` changes an existing input. The test file is outside that roster.
Do not copy the candidate's pair8 policy or use its older closure receipts. Fresh
canonical consumers on the corrected integrated tree remain required.

Live App Store Connect/account validation; full account-action mapping; discovery
without a known build ID; upload and uncertain-upload recovery; signed W12 handoff;
Play distribution; test links/readiness; review and release; separate-repository
FieldLog consumption of immutable published packages; native and final physical
acceptance; D6; and GA remain pending. No gate is promoted by this review.

`cleanup.json` records positive terminal custody for every managed command and
removal of only this review's scratch and temporary directories. Aggregate managed
output was 13,197 bytes. Product files, parent tracking files, and candidate evidence
were not edited. No commit, push, child agent, account/token request, native/ADB/
simulator/UI/capture/cloud attempt, held process probe, or frozen-lane execution
occurred. All named historical custody/process holds remain untouched.
