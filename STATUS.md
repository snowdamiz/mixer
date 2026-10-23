# Implementation status

Product status: **in development; no GA or dogfood gate passed**.

The repository began with only the product plan on October 22, 2026. It now has
an owned Swift SDK and native adapters, Rust interpreter, local release service,
native Swift signature verifier, CLI, and a separate FieldLog repository.
`work-graph.json` retains every W01–W18 package; all G01–G38 and D0–D8 gates remain
open. Implemented slices do not replace their complete acceptance requirements.

Observed implementation and evidence:

- Swift state/effects, generation-checked resources, bounded UI documents,
  reconciliation and native Apple controls pass host tests and iOS compilation.
  Raw UI decoding requires strict duplicate-key/Unicode/resource validation.
  An independently checked generated iOS consumer builds and runs in a dedicated
  simulator; this is not physical FieldLog D1 acceptance.
  The repository root now exports the same SDK products for revision-pinned Git
  consumption. A clean exported source package passes 23 tests. FieldLog now
  resolves public revision d8c6965 through SwiftPM and Xcode and uses MixerCore
  for its native task editor's state and save effects; see the consumer receipt below.
- The Android Swift/JNI/native widget adapter runs on a physical Pixel 8 Pro.
  Instrumentation and real input/touch paths verify text, task creation, toggles,
  stable IDs and stale-event rejection. Independent review fixed non-ASCII JSON
  escape acceptance and reran device tests. See `native/android/verification/receipt.json`.
  The CLI now generates an Android consumer whose shared Swift feature owns its
  draft/add/toggle state and whose native entry remains app-owned. The locked
  official toolchain builds an actual unsigned arm64 APK with inspected native
  dependency closure and DEX classes. Host checks cover the CLI, reusable runtime,
  existing checklist engine and generated app C ABI. Independent review reproduced
  staging symlink/hardlink writes outside the build directory; the repair rejects
  those paths before mutation and passes the original exploit replays. A fresh
  fixed consumer build and rebuild pass, with independent final APK inspection.
  These are local compilation/host results; the earlier physical checklist receipt
  does not qualify the new generator. Signing/installability, native resources and
  capabilities, published packages, FieldLog D2 and device/lifecycle/accessibility
  evidence remain open. See `verification/android-generator-integration-2026-10-22.json`.
- The dependency-free owned Wasm interpreter executes the bounded integer-v1
  profile. The opt-in numeric-v2 extension matches 29,794 floating-point reference
  cases on the physical Pixel and through the public C ABI in a signed iPhone
  app, plus 52 Android interpreter/numeric boundary tests and C ABI control checks. Integer-v1 acceptance is unchanged. Full Swift artifacts remain
  rejected. Opt-in table-memory-v3 now passes 2,996 Android reference cases and
  17 table/memory assertions on physical iPhone, with unchanged older profiles.
  Persistent native sessions now retain guest state through generation-checked
  handles, bounded copies and cancellation. Seven public session tests pass on
  physical iPhone; 12 session tests plus two existing ABI checks pass on Pixel.
  Independent review then reproduced a close/deallocation race in the 16-session
  ceiling. The fix retains the slot until actual deallocation completes; its host
  regression and 87 VM host tests pass, with new physical qualification pending.
  The typed Swift session wrapper passes seven host debug/release and iOS simulator
  tests, compiles for iOS/Android, and passes independent adversarial host review.
  Review also fixed a native-header check bypass under optimized Python. Bounded Swift/WASI
  imports, mobile SDK/lifecycle integration and corpus budgets remain open.
- Typed HTTP/storage capability schemas generate Swift and Java adapters with
  strict cross-language codecs, grant intersection, bounded ownership and cancellation.
  Real app-private storage checks quotas on both mutation and reopen. Thirteen host
  tests and codec comparisons pass; official iOS/Android/WASI compilation is qualified
  separately. The opt-in native URLSession transport now adds streamed response
  bounds, ordinary system TLS, redirect rejection, cancellation and monotonic
  deadlines. Twenty-four capability tests, 23 SDK tests, eleven transport tests
  under Thread Sanitizer, actual local untrusted-TLS rejection and cross-builds
  pass. Root reviewed the source and matched the immutable receipt, including a
  negative deadline-regression mutation. Signed release-v2 grants pass 115
  cross-language cases and native-policy parity. Guest imports, Android networking
  packaging/trust behavior, physical behavior and FieldLog plugin adoption remain open.
  See `verification/http-transport-owner-review-2026-10-22.json`.
  Installed concrete HTTP/storage adapters now separately observe operation return
  and native cleanup before releasing capacity. Terminal delivery, cancellation
  and host deallocation cannot fabricate exit. Thirty-seven tests pass in debug
  and release, with 24 HTTP/exit tests under Thread Sanitizer and iOS/Android/WASI
  cross-builds. Six independent lifecycle/reentrancy probes pass in all three host
  configurations; arbitrary adapter substitution is rejected at compile time.
  Root matched 49 implementation inputs, 12 logs and 105 frozen review files.
  This proves the documented owned-adapter cleanup boundary, not process-wide
  quiescence, OS socket/RSS reclamation, rollback or guest integration. See
  `verification/capability-foundations-integration-2026-10-22.json`.
  The development guest transport contract now has a generated strict Swift value
  codec. All 90 byte fixtures pass in debug and release, including the 23 cases
  previously awaiting a wrapper implementation; ten independent public-API tests
  pass per mode. Review also reproduces deterministic first generation and matches
  unchanged legacy contracts/codecs. A separate review found that delayed watchdog
  scheduling could permit a late success. The repaired host captures an absolute
  deadline before work, checks it before dispatch and result selection, and preserves
  the installed native-exit join. The exact repair passes 45 debug/release tests,
  25 Thread Sanitizer tests and iOS/Android/WASI compilation. See
  `verification/guest-codec-deadline-integration-2026-10-23.json`. These are value
  codec and native host results; actual guest-to-I/O integration remains open.
  The observed installed-adapter API now also accepts a caller's existing absolute
  monotonic deadline. It narrows the host/operation cutoff, so mailbox or actor
  queue delay cannot renew the budget. Six concrete-storage regressions cover
  expired no-I/O admission, queue delay, earlier caps, unextended defaults and
  terminal/exit ownership. All 51 capability tests pass per host mode, 31 native
  HTTP/exit/deadline tests pass under Thread Sanitizer, and iOS/Android/WASI
  compilation passes. Root reviewed the source and matched 63 inputs and 15 logs;
  see `verification/carried-deadline-integration-2026-10-23.json`. This SDK
  prerequisite does not implement the guest bridge or qualify physical behavior.
  See `capabilities/verification/receipt.json` and
  `verification/independent-capabilities-2026-10-22.json`.
- The Go development service verifies canonical signed artifacts and separately
  signed rollout assignments, with scoped authorization, durable local state and
  retry/replay tests. It refuses production mode. Local HTTP → Swift verification
  → owned integer VM integration checks both iOS and Android metadata scopes.
  A local PostgreSQL17 implementation adds tenant transactions, forced row-level
  security, immutable audit/history/outbox and concurrent retry/sequence controls.
  Its isolated database checks include an actual local server crash. Independent
  review found and fixed unsafe schema/function ownership and unknown migration
  version acceptance. Root reviewed the committed changes and matched their
  evidence. Explicit v2 HTTP routes now compose typed signed grants with the same
  tenant transactions, audit, idempotency and sequence controls. A successful v2
  domain transaction atomically upgrades local storage; old service binaries reject
  that schema, and existing v1 bytes survive restart. The full Go race suite passes
  839 executions, CLI passes 15 tests, and isolated PostgreSQL passes 46 executions.
  Actual loopback HTTP reaches the public Swift verifier for both versions. Nine
  independent adversarial functions/36 cases pass, with source and log identities
  matched by root. Hosted identity, production operations and deployment remain
  open. See `verification/release-v2-owner-review-2026-10-22.json`.
- The Swift verifier uses pinned standard cryptography and matches Go signature,
  canonical-CBOR and cohort vectors. The verifier executable runs on the physical
  Pixel and rejects replay. This is protocol evidence, not mobile OTA activation.
  Independent review fixed cross-verifier authority, strict pinned configuration
  decoding and bounded reads. Legacy JSON hardening now rejects alternate field
  spellings and noncanonical base64, while preserving dynamic map keys and original
  signatures. All closed Go models decode atomically into fresh receivers. The
  271 shared wire cases, 805 Go race executions, Swift debug/release and CLI checks
  pass; root matched 137 source files and 22 durably preserved evidence files. See
  `verification/protocol-wire-owner-review-2026-10-22.json`. The durable Swift updater now passes 28 test functions
  (40 parameter executions) on the Pixel and in a physical iPhone app sandbox:
  replay, resumed downloads, journal fault
  injection, monotonic health, quarantine and fallback. App lifecycle, physical
  power-loss and actual guest activation qualification remain open.
- `MixerActivation` now composes verified v1/v2 selection with the owned VM, enforcing
  installed and signed limits, retaining guest state and handling health and fallback.
  Its frozen source passes ten functions/11 cases in host release and the iOS simulator,
  plus 15 independent adversarial host tests; iOS and Android cross-builds pass.
  Review corrected the healthy fallback's startup timer to include selection and
  validation. Full Swift/UI/capability execution, compiled feature fallback integration,
  physical lifecycle and complete installed runtime identity remain open. See
  `verification/activation-2026-10-22/receipt.json`.
- Installed runtime identity now validates a closed build descriptor and derives
  exact compatibility, verifier policy and VM startup limits from its canonical
  fingerprint. Eight identity tests and thirteen activation functions/fourteen
  cases pass on the host; the activation cases also pass in the iOS simulator,
  with iOS and Android cross-builds. Independent review adds seven parser and
  three activation tests, 32 CLI hash-oracle cases and nine rejection cases. It
  reproduced and verified fixes for mixed verifier policy and a file-open race;
  the fixed file probe passes 80 attempts and all 53 update test cases pass.
  A bounded capture tool now copies declared inputs through pinned file descriptors,
  computes hashes from those exact bytes and verifies a content-addressed snapshot.
  Thirteen implementation tests and twenty independent checks pass in both normal
  and optimized Python modes; a real simulator VM archive also passes capture and
  verification after its original private copy changes. Review verified the fix for
  an oversized JSON integer that previously printed a traceback on rejection.
  Complete graph discovery, actual build consumption, signed binary embedding and
  provenance remain open. This is not a build attestation or physical-device
  qualification. A companion emitter now compiles the exact verified descriptor
  bytes and expected fingerprint into Swift source. The loader revalidates both
  before returning policy. Nineteen capture/embedding tests pass in both Python
  modes; the host release consumer runs after deleting its original snapshot and
  inputs, and the generated source compiles for iOS and Android arm64. Independent
  review passes eleven tests per mode, a strict Swift6 consumer with a maximum-size
  descriptor, and eight separately compiled corruption rejections. Root matched
  the frozen source and output hashes. A collector filename mismatch was corrected
  with a separate artifact-collection receipt; its original failure is retained.
  Automatic app build integration, linker-input consumption and signed provenance
  remain open. See `verification/runtime-identity-integration-2026-10-22.json`,
  `verification/input-capture-integration-2026-10-22.json` and
  `verification/runtime-embedding-integration-2026-10-22.json`.
- The CLI creates source-locked projects, builds/tests host packages, generates and
  runs iOS simulator apps, inventories migration concerns and exports source.
  Local update verification snapshots bounded inputs so signatures and executable
  validation examine identical bytes. Independent review made linked cryptography
  authoritative, enforced signed VM limits and fixed bounded reads/tool receipts.
  Publication remains unavailable.
- `../fieldlog` is a separate repository with native SwiftUI screens, durable
  offline drafts/outbox, projects/checklists, photos and report sharing. Baseline
  commit `1587d2d4f02ab2dad9914df97f878727dd622296` builds, installs and launches on
  the physical iPhone 12. At `a81e085`, isolated physical UI tests pass project/task
  editing, reorder, exact draft restoration, entry commit, report sharing and local
  pending changes; dark-mode controls were visually reviewed and corrected. Authentication,
  backend synchronization and real user adoption are not implemented or simulated.
  At d51adf5, the native task editor consumes the public MixerCore package pinned
  to d8c6965, with no engine-internal import or local Mixer dependency. Seventeen
  host tests and the unchanged end-to-end simulator workflow pass. Persisted
  models and native SwiftUI controls remain compatible. This is initial external
  package consumption, not full MixerUI/guest adoption or D1 acceptance; physical
  regression is pending. See `verification/fieldlog-public-sdk-2026-10-22.json`.
  The same task-feature source, models and public MixerCore dependency also compile
  to Android arm64 and Wasm objects with the official SDKs. These checks do not
  execute an Android app or Wasm guest; see
  `verification/fieldlog-shared-feature-cross-2026-10-22.json`.
- Actual FieldLog models at baseline `1587d2d` produce matching observations
  on macOS, the physical Pixel and the full Swift Wasm SDK in a development oracle:
  1,000 tasks, 50% progress, ordering, Unicode draft restoration, entry commit and
  report generation. The 60.5 MB Wasm module is rejected by the owned VM; neither
  full Swift execution nor production package-size budgets have passed.
  Eleven full-SDK optimization variants preserve those sampled observations. The
  smallest is 52,008,982 raw bytes / 18,852,048 gzip bytes, above the 3MiB budget.
  ICU accounts for 33,976,096 linked data bytes; removing it is not qualified by
  this corpus. Measured linear-memory page counts do not establish peak RSS.
  Separate bounded VM layout/session probes measured Rust heap allocations and
  process peak RSS. Applying measured layouts to the full corpus estimates at least
  341,333,936 bytes for eager decoding and initial memory; that is arithmetic,
  not an observed full-corpus execution or RSS measurement. Production memory
  architecture and ceilings remain unqualified. A new sequential body diagnostic
  inventories all 79,837 functions: 79,831 decode structurally and six exceed the
  unchanged control-depth ceiling. Source, diagnostic index and one decoded body
  peak at 55,910,263 directly requested bytes; diagnostic process peak RSS is
  60,276,736 bytes. These are diagnostic measurements, not full module validation
  or execution. A nondefault Rust streaming-validator experiment now completes
  validation under the existing profiles with separately bounded metadata, scratch
  and work. Its 104 feature checks and targeted independent review pass, including
  15,412 Node comparisons per build, allocation failures, cancellation and growth
  overlap. It retains immutable source spans and has no executable or public C
  route. Full Swift admission and production integration remain open. See
  `verification/function-diagnostics-owner-review-2026-10-22.json` and
  `verification/stream-validator-owner-review-2026-10-22.json`.

A nondefault Rust capability-mailbox experiment now snapshots bounded requests,
gates dispatch on successful turns, and separates terminal delivery from native
exit acknowledgement. Twenty new tests pass, with unchanged default profiles,
128 combined-feature tests per build mode and all nine explicit oracle functions.
Root matched 47 source inputs, 19 logs and 12 unchanged compatibility inputs.
Thirteen independent adversarial tests pass in both modes, including exhaustive
bounded lifecycle scripts, concurrent delivery/exit races and identity exhaustion.
Root matched the review sources and all 14 command logs. Payload allocation refusal is handled atomically;
the recorded macOS standard-library mutex allocation can still abort on OOM.
This has no guest imports, C route, strict payload/grant bridge, native I/O,
scheduler, counted registry retention or activation admission. See
`vm/verification/capability-mailbox/receipt.json` and
`verification/capability-foundations-integration-2026-10-22.json`.

The opt-in Rust capability guest now executes the six fixed imports through that
mailbox, with private admission, transactional memory/fuel accounting, disabled
startup, coalesced wake and terminal close. Default 91 and combined 162 tests pass
in both modes, plus nine explicit oracle functions and eight existing C smoke
runs. Ten independent actual-Wasm tests pass in each mode; root matches all 77
implementation inputs and 42 command logs at the frozen implementation. Legacy
profiles, entry points and C symbols remain unchanged. Native callers still must
retain their tickets through actual cleanup; there is no counted C registry or
native I/O bridge in this slice. Arc/mutex OOM abort and poisoned-mailbox ack
failure remain explicit. See `verification/capability-guest-integration-2026-10-23.json`.

The opt-in native capability C layer now shares the existing sixteen-session
registry with legacy sessions. A fixed eight-ticket ledger retains native exit
obligations after close; quarantine and final destruction also retain capacity.
Complete pointer preflight rejects writable aliases without changing any output.
Default91 and combined185 tests pass per mode, plus9 explicit oracle functions
per mode and14 actual C smoke runs. Independent public C checks include48 take/close
and48 ack/close races in each mode. Root matched90 inputs,76 implementation logs,
2 archive-build logs,9 independent logs and14 unchanged legacy inputs. iOS/Android
arm64 archive/C layout/link checks pass without execution. Exact tested archives
are pinned; a differing repeated debug build is preserved without a bit-reproducibility
claim. The following Swift bridge checkpoint adds dispatch, scheduling and
actual host guest I/O; verified activation remains open. See `verification/capability-native-integration-2026-10-23.json` and
`docs/experimental-capability-native-implementation.md`.

The separate experimental archive builder now exports 81 immutable Git inputs,
uses isolated Cargo configuration and stages one distinctly named static archive
with matching headers. Its frozen implementation passes 22 boundary tests in
normal Python and 22 under optimization; an independent public CLI suite passes
13 functions in both modes. Root matched all source, artifact, tool and log hashes.
The actual macOS C consumers pass 27 smoke and 52 mixed legacy/capability registry
checks. iOS, simulator and Android layout compilation and C linking pass without
execution. Process cleanup failures quarantine the owned cache; installed tools
and coordinated cache use remain trusted. See
`verification/capability-builder-review/receipt.json` and
`experimental-capability-runtime/build-verification/RESULTS.md`.
The following Swift bridge checkpoint adds host guest-to-I/O composition. Signed
activation, distribution and physical-device qualification remain open. The first
hosted builder failures and subsequent repairs are retained below.

The separate experimental Swift bridge now connects real Wasm requests to the
strict codec and concrete HTTP/storage adapters. It reserves bounded construction
ownership before queuing, uses a serialized pump with rate/deadline limits, parks
idle timers, and retains native exits through cancellation, close and deinit.
Sixteen tests pass in each debug/release/Swift-TSan mode. Independent review passes
10 public and14 instrumented ordering tests in each mode, plus isolated metadata
and constructor faults:76 test executions. Review reproduced an ordinary close
race that reported failure after successful cleanup; four final regressions now
pass while malformed metadata and failed acknowledgements remain fatal. Root
matched55 implementation inputs,60 observation inputs,42 review files,131 evidence
files,163 independent bindings and all four linked consumers. Actual normal-trust
TLS rejection passes; iOS/simulator/Android links are not platform execution.
Eight overlapping real storage gets drain with eight acknowledgements. Debug
batches reach9.261–9.801ms, confirming the8ms budget is cooperative; sampled memory
includes probe/runtime/framework work and does not bound transient allocation/RSS.
See `verification/capability-bridge-integration-2026-10-23.json` and
`experimental-capability-runtime/verification/RESULTS.md`. Verified installed
material, signed capability activation, provisioned HTTPS success, full Swift/UI,
FieldLog, publication and physical-device qualification remain open.

Official Swift 6.3.3 Android/Wasm SDKs are installed and compiler probes have run
on a physical Pixel and in a development-only Node WASI oracle. Xcode 27.1 / Swift
6.4 builds Apple targets. Cross compilation uses Xcode 26.6's matching macOS SDK
through per-command `DEVELOPER_DIR`; no global Xcode selection was changed.

The critical next dependencies are actual FieldLog model/feature compiler closure,
the full owned Swift execution profile, signed capability/guest integration, broader
native UI/lifecycle behavior, and durable device update activation/recovery. Hosted
services, isolated builds/signing, stores, console/commercial features,
independent security/operational reviews, users and paid pilots remain mandatory.
There is no production deployment receipt or GA claim; remote CI status is recorded below.

Current execution constraints: physical phones are disconnected until the user
says otherwise. New device checks remain pending; development continues with host,
cross-compiler and simulator evidence. Periodic source/evidence commits and pushes
to `snowdamiz/mixer` are authorized and recorded in PLAN.md. The initial GitHub
run passed Rust and Go checks and the 23 Swift SDK tests, then rejected the CLI
because the runner supplied Swift 6.1 while the package requires 6.2. CI now selects
and verifies Xcode26.3/Swift6.2 explicitly, with updater tests added. Hosted run
39877689050 at commit17134eb and 39879453401 at b492da3 passed all three jobs, including the generated iOS
simulator consumer. This covers the listed host CI suite, not physical devices,
PostgreSQL integration or full release gates. The expanded run39880996716 at
d8c6965 also passed all three jobs, including the public SDK, capabilities, native
VM wrapper, activation and generated simulator consumer. See
`verification/github-ci-d8c6965.json`. Run39881858217 at c99ed79 also passed
all three jobs; see `verification/github-ci-c99ed79.json`.

The independent FieldLog public-consumer review passed ten adversarial host test
functions/twelve cases, including save failures, retry, observer ownership, close
and durable-state preservation. The stale README introduction was corrected in
FieldLog commit8219234. This review confirms the scoped MixerCore adoption; D1,
Android app behavior and full plugin/guest adoption remain open. See
`verification/fieldlog-consumer-review-resolution-2026-10-22.json`.

GitHub run39883597203 at37c1253 passed all three jobs, including the expanded Swift
and generated simulator-consumer workflow. See `verification/github-ci-37c1253.json`.

GitHub run39887102131 at80268f7 passed all three jobs, including runtime identity
and signed activation checks. See `verification/github-ci-80268f7.json`.

GitHub run39890316915 at2fda7ab passed Swift and services but failed the newly
enabled Linux numeric reference test: f32.ceil returned a signaling NaN without
quieting it. Commit16727d canonicalizes arithmetic NaNs while preserving exact-bit
operations and integer conversion traps. The default91 and experimental108 host
tests pass in both modes, along with all nine explicit Node oracle functions per
mode. GitHub run39891654598 at8ab3b7f then passed all three jobs, including both
Linux float reference modes and the generated simulator consumer. See
`verification/github-ci-2fda7ab/receipt.json`.

The numeric fix source and local evidence review is recorded in
`verification/numeric-portability-owner-review-2026-10-22.json`.

Successful repaired CI evidence: `verification/github-ci-8ab3b7f/receipt.json`.

GitHub run39894771420 at8e76cfd passed all three jobs, including Linux default and
combined stream/mailbox checks and numeric reference oracles in both modes,
Android runtime host tests and build-staging regressions, and the generated iOS
simulator build. This run predates the installed native exit change and does not
build an Android APK on CI. See `verification/github-ci-8e76cfd/receipt.json`.

GitHub run39896049407 at5d25a2b passed all three jobs, including installed native
exit behavior in macOS tests, Linux stream/mailbox/numeric checks and the generated
iOS simulator consumer. This predates the new guest value codec and deadline
repair. See `verification/github-ci-5d25a2b/receipt.json`. The next workflow adds
Thread Sanitizer coverage for native HTTP, exit ownership and host deadlines.

GitHub run39899331225 at3b1903a passed all three jobs, including 45 capability
tests, 25 native HTTP/exit/deadline tests under Thread Sanitizer and the generated
iOS simulator consumer. See `verification/github-ci-3b1903a/receipt.json`. This
run predates the Rust guest composition and the new full raw-fixture CI step.

GitHub run39901133183 at3e118a9 passed all three jobs. It includes the opt-in
Rust guest tests and all 90 raw transport fixtures in each Swift build mode,
plus the existing 45 capability and 25 native Thread Sanitizer tests. See
`verification/github-ci-3e118a9/receipt.json`. The carried deadline overload and
experimental native C session implementation are later work, outside that run.

GitHub run39902113915 atbec5731 passed all three jobs, including51 capability
tests and31 native HTTP/exit/deadline tests under Thread Sanitizer, both raw90
fixture modes and the generated simulator consumer. See
`verification/github-ci-bec5731/receipt.json`. This predates the native C layer
and its expanded Linux public-client checks.

GitHub run39903653915 at b25e3b7 passed all three jobs. The expanded Linux job
executes both public native C clients: 27 smoke checks and 4,589 independent
assertions, including 48 take/close and 48 acknowledgement/close races. Default
and combined experimental VM checks, explicit reference tests, 51 Swift capability
tests, 31 native Thread Sanitizer tests and the generated simulator consumer also
pass. See `verification/github-ci-b25e3b7/receipt.json`. This qualifies the listed
host CI execution; the Swift guest-to-I/O bridge and new physical-device checks
remain pending.


GitHub run39905251612 at 3dd90c2 passed all three existing jobs after the native
C documentation/evidence checkpoint. See `verification/github-ci-3dd90c2/receipt.json`.
This revision predates the separate archive builder and Swift bridge implementation.


GitHub run39907419542 at eb5dd05 passed the Linux VM and service jobs. The macOS
job passed its earlier SDK/runtime/activation steps, then failed one builder
boundary test: a 250 ms fixture deadline expired before the expected output flood.
The optimized suite, actual archive stage, C consumers and generated consumer were
not reached in that run. The builder itself is unchanged while the fixture gains
a bounded child-readiness barrier. See `verification/github-ci-eb5dd05/receipt.json`.

The fixture-only repair now passes all 22 boundary functions in both normal and
optimized Python, including a deliberately delayed child startup. It preserves
exact timeout/overflow/exit assertions and checks that descendant writes stop.
Root reviewed the new fixture and matched both logs and source snapshots; the
production builder remains byte-identical. See
`verification/capability-builder-review/ci-fixture-fix.json`. The following hosted
runs pass both repaired boundary suites.


GitHub run39908555619 at bd24e7c passes both 22-function builder suites and builds
an archive from the same 81 frozen native inputs. It then fails C smoke compilation
because the CI command used an unqualified compiler without an explicit macOS SDK.
The workflow now selects clang and SDK with xcrun and passes `-isysroot`; both
corrected C recipes compile and execute locally (27 smoke/52 mixed checks).
See `verification/github-ci-bd24e7c/receipt.json` and
`verification/capability-builder-review/ci-apple-sdk-fix.json`. The following hosted
run passes the corrected recipes.


GitHub run39909473019 at 1ab4d4e passes all Swift and service steps, including
the archive builder, 27 C smoke and 52 shared-registry checks. The Linux VM job
then aborts in its release mailbox allocator fixture on a 148-byte allocation;
remaining release suites, explicit oracles and public Linux C clients do not run.
A deterministic foreign-thread regression reproduces that abort with the old
process-wide fault injector. The fixture now scopes refusal and requested-byte
counters to the thread running the synchronous mailbox operation, preserving
all payload refusal/cleanup assertions and passing host debug/release. These are
caller-thread observations, not total heap or cross-thread ownership accounting.
Independent source review found no blocking defect; the production VM is unchanged.
See `verification/github-ci-1ab4d4e/receipt.json` and
`verification/capability-allocation-fixture-review/receipt.json`. The next checkpoint confirms the Linux rerun.


GitHub run39911306920 at2f6b393 passes all three jobs, including the repaired
caller-thread allocation fixture in Linux debug/release, the remaining VM/reference
suites and public C clients, archive builder, Swift integration and generated
simulator consumer. See `verification/github-ci-2f6b393/receipt.json`. This run
precedes641b844 and its new Swift bridge debug/release/TSan/public-consumer CI step.


Four additive contracts now define capability execution through identity2,
release3 and guest ABI2 over the unchanged table-memory-v3 grammar. Root matched
241 static checks in normal and optimized Python,79 independent consistency
checks,35 implementation bindings and eight unchanged old contract files before
freezing the definitions for implementation. Static checks confer no execution
or release authority. Schema2 capture/embedding, protocol3 verification, bounded
complete validation/typed failures, concrete material binding and separate signed
activation remain implementation work. See
`verification/capability-authority-contract-freeze-2026-10-23.json`.
