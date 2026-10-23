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
The new step failed on641b844 andaca686b because pinned Xcode26.3 could not typecheck
the bridge's nested metrics expression. Both failed runs are preserved in
`verification/github-ci-641b844/` and `verification/github-ci-aca686b/`; their VM
and services jobs passed. A narrow expansion into typed loops preserves the same
lock and observation order. Local16 debug/release/TSan tests,10 public tests and
four platform links pass; root matched sources, logs and linked binaries in
`verification/capability-bridge-compiler-compat-review-2026-10-23.json`.
At99c9f5b the pinned compiler builds the repaired production bridge, then fails
on three long expressions in its test-only Wasm builder. The subsequent fixture
rewrite preserves byte-identical output for11 modes and passes all16 host tests
against frozen99c9f5b production, including normal-trust TLS rejection. See
`verification/bridge-fixture-compiler-review/` and the preserved failed run in
`verification/github-ci-99c9f5b/`. Run39916644922 at24a7437 now passes all three
hosted jobs, including16 bridge tests per debug/release/TSan and10 public-consumer
tests with pinned Xcode26.3. See `verification/github-ci-24a7437/receipt.json`.
This qualifies that revision, before the following additive implementation.


Four additive contracts now define capability execution through identity2,
release3 and guest ABI2 over the unchanged table-memory-v3 grammar. Root matched
241 static checks in normal and optimized Python,79 independent consistency
checks,35 implementation bindings and eight unchanged old contract files before
freezing the definitions for implementation. Static checks confer no execution
or release authority. See
`verification/capability-authority-contract-freeze-2026-10-23.json`.

Identity2 now has strict parsing, declared-input capture and embedded-source
generation. Root review found and repaired a caller-backed Data gap between the
strict scan and typed decode; both now consume one owned snapshot. The fixed
candidate passes19 Swift tests per debug/release,32 Python tests normally and
under optimization, and byte-identical old CLI outputs. Capture verifies declared
inputs, not completeness of the build graph or final linked adapter identity.
See `verification/runtime-identity-v2/README.md` and the final snapshot receipt.

Explicit release3 Go and Swift verifiers now share154 manifest and36 assignment
cases. Swift exposes opaque artifacts/grants tied to one verifier context;55 tests
per debug/release and15 scoped TSan tests pass, with public construction/decoding
rejected at compile time. Official iOS/Android checks compile modules/objects only.
Go passes the full services race suite and seven independent public-API test
functions, canonical-byte checks and fixture regeneration. Use the checked Go
decoders at document boundaries; raw stdlib decoding strips outer whitespace.
Root matched the frozen sources, logs and artifacts, passed89 independent Swift
public checks and19 combined identity tests, and verified identity2-to-release3
metadata binding with legacy rejection. Receipts are in
`verification/release-v3-root-review/`, `verification/release-v3-swift/`,
`verification/release-v3-go/` and `verification/release-v3-go-review/`.

These are parsing and signature primitives. Run39917971778 atc5bf3fe passes all
three hosted jobs, including55 update and19 identity tests with pinned Xcode26.3;
see `verification/github-ci-c5bf3fe/receipt.json`.

The next validator candidate adds two independent process-wide validation permits,
owned bounded module capture, cancellation that retains queued/running capacity,
and full native validation without instance, adapter or export execution. Matching
construction accepts exact zero pages. Checked native status/code/context now
produces typed diagnostics and preserves the first failure through cleanup. Owner
review found and repaired premature deinit release of a quarantined validation
permit; the negative reproduction remains preserved. All27 tests per mode,
nine derived ownership-probe executions, ten unchanged public tests and four
platform links pass. Root matched64 source inputs, logs and binaries, reviewed
lifetime/classification invariants and passed22 original public checks. See
`verification/capability-validation-review/receipt.json`. The full matrix uses
local Swift6.3.3. Run39919256699 at09c317c also passes all three hosted jobs,
including27 tests per bridge/validation debug/release/TSan mode,10 public bridge
tests and the generated simulator consumer with pinned Xcode26.3. See
`verification/github-ci-09c317c/receipt.json`.

Installed material now binds exact canonical policy/configuration/grant bytes and
raw roots to identity2 plus the linked known native/schema constants. Root found
and fixed unbounded role-ID hashing before admission. The final candidate passes
16 tests per debug/release/TSan mode, helper and public opacity checks, and official
iOS/Android module/object compilation. Root matched135 frozen inputs,21 command
results,8 cross artifacts and the final source/evidence manifests, then passed53
public shared origin/namespace cases. See
`verification/capability-installed-root-review/receipt.json`. The read-only helper
exports the exact2394-byte native digest preimage without a final LF.

This material value creates no adapter, session, task or filesystem state. It does
not attest arbitrary descriptor build hashes or the complete linked graph. Hosted
material CI at61f34bf now passes all three jobs, including16 material tests and the
preimage helper with pinned Xcode26.3. See `verification/github-ci-61f34bf/receipt.json`.

The explicit v3 development service now accepts only registered protocol3/ABI2
hosts through closed bounded transport envelopes, preserves old protocol routes
and advances local state to schema3 without later downgrade. PostgreSQL migration
001 and protocol primitives are byte-identical. Full Go races (25 protocol,22
release,9 updater test functions), vet, isolated PostgreSQL17.11 fault/RLS/restart
tests and old-binary schema rejection pass. Four independent public Go race tests
and12 original TCP assertions pass; the public Swift verifier accepts delivered
signed metadata before/after reopen and rejects replay/retargeting/tampering. Root
matched53 source inputs and owner/review/subreceipt logs. See
`verification/release-v3-service-root-review/receipt.json`. Synthetic service
payloads are metadata fixtures; production mode remains disabled.

The reviewed durable-updater design now requires a separate immediate terminal
failure latch because exact cleanup drain may never arrive. It also reserves a
process-wide owner before any adapters and retains it through actual cleanup.
The metadata-only recovery SPI now passes69 debug/release tests,14 TSan tests,
public opacity checks and official iOS/simulator/Android module builds. Root
matched71 inputs,31 command logs,87 evidence files and12 retained artifacts, then
passed204 independent external checks including the shared malformed-input corpus.
Current-time verification stays strict. Retained metadata skips only signing-root
time windows; it cannot establish committed-health provenance or execution authority.
See `verification/release-v3-durable-spi-root-review/receipt.json`.

Private durable I/O now bounds reads, chunks, state and prune inventory, pins its
directory fd and preserves legacy I/O bytes. All23 tests pass in debug/release/TSan,
29 independent checks pass, and iOS/Android modules and objects compile. Root
matched139 frozen inputs,5 live new source files, both matrices and independent
review; see `verification/capability-durable-io/final-receipt.json`. This synchronous
primitive is not yet product actor/lifecycle integration. Hosted run39923420515 at
a81f54c passes all three jobs before these additions; see
`verification/github-ci-a81f54c/receipt.json`.

The concrete adapter lifecycle SPI now joins constructor return, exact native
drain and actual host/KV close before its separate retirement callback. The first
checked terminal failure is delivered before cleanup. All32 owner tests pass in
debug/release/TSan,15 derived race probes pass, ten old public tests pass, and eight
ordinary/SPI consumers link across host/iOS/simulator/Android. Independent review
adds17 public checks per host mode, four opacity rejections, eight internal gate
checks and six forced private close-failure checks. Root matched71 source inputs
and the full evidence seals; see
`verification/capability-bridge-lifecycle-root-review/receipt.json`. Exclusive
adapter transfer and fixed acyclic sinks remain trusted caller requirements.

Pure internal execution policy now revalidates enclosing signed evidence, narrows
native limits including zero-page memory and intersects each grant dimension.
It creates no adapter/session or execution authority. Seven new tests plus23
existing material/I/O tests pass in debug/release; official iOS/Android modules
compile and external public access is rejected. Independent source review found
no actionable issue; see `verification/capability-execution-policy/final-receipt.json`.
Hosted run39925395453 at3bdf5cd passes all three jobs, including69 update and23
material/I/O tests, before these lifecycle/policy additions.

Private counted recovery storage now passes41 debug/release tests,18 new TSan
tests and24 independent probes. Both reviewed capacity races are fixed: concurrent
owner destruction and live ingress snapshots now retain their outer reservation
until their logical tails return. Exact signed download records preserve replay
high-water and use real bounded native validation before staging. Root audited113
frozen inputs,16 command logs, retained artifacts and both evidence seals; see
`verification/capability-durable-store-root-review/receipt.json`. This foundation
does not yet select startup candidates or commit effects/health. Its qualification
uses frozen3bdf5cd dependencies; composition with later lifecycle/policy code is
still pending. Hosted run39928599118 at4a413b4 passes all three jobs for the prior
lifecycle/policy checkpoint; see `verification/github-ci-4a413b4/receipt.json`.

Owned enable now carries its original uptime cutoff through the guest queue and
rejects expiry before native enable with ordinary cleanup. All35 bridge tests
pass in debug/release/TSan. After correcting only a new consumer's missing Wasm
ABI elements, eight consumers link across four targets and two host consumers
run. Independent review adds14 public and28 derived checks per debug/release mode,
including zero native enable calls after queued expiry and complete permit reuse.
See `verification/capability-enable-deadline/receipt.json`. This remains a sampled
cooperative check, not a hard real-time guarantee.

The fixed private attempt latch passes six cases per debug/release/TSan mode,
including128 stop/commit races and128 concurrent terminal reports. Its XCTest
branch typechecks and independent source review has no actionable finding; see
`verification/capability-attempt-signals/final-receipt.json`. Counted consumer
ownership and durable transitions remain future composition requirements.

Hosted run39930585800 at08e5c2d passed VM/services but failed to type-check a long
store-test fixture expression on pinned Xcode26.3. Splitting it preserves all512
generated Wasm variants byte for byte. Hosted run39932658048 atbf5021e now passes
all three jobs, including54 capability-activation tests on the pinned compiler.
See `verification/capability-store-ci-fixture-fix/receipt.json` and
`verification/github-ci-bf5021e/receipt.json`. Durable selection,
effects/health and coordinator integration remain under implementation; their
unfinished files are excluded from this checkpoint.
Concrete signed execution, health/recovery and full FieldLog remain in progress.
Physical checks remain pending while the phones are disconnected; no product or
GA gate is closed by this checkpoint.

The private signal latch now accepts generation-bound control wakes from one
coordinator-owned observation timer or an ordinary-operation completion. These
hints share its bounded stream and never consume the first terminal notification.
Eight cases pass in debug/release/TSan and the XCTest branch typechecks; see
`verification/capability-attempt-signals/2026-10-23-control-wake-1/receipt.json`.
The source-only independent review above applies to the earlier six-case latch.
Actual timer, consumer and signed coordinator composition remain under development.

Private durable startup selection, effects intent, observed health, exact typed
failure counting and bounded retained fallback now pass79 functions in debug and
release,25 transition functions under TSan, a public material-only consumer,
three public privacy negatives and iOS/Android module/object builds. These use
the immutable bf5021e dependency baseline. Root audited122 frozen inputs,116 Git
inputs,16 command logs,295 retained files and nine cross/client artifacts.
Review reproduced three cold-restart defects in the preliminary candidate;
failed/interrupted fresh-stage pointers now clear while actual health, candidate
records, accepted sequence and deny history remain durable. The same probes pass
in debug/release/TSan against the final candidate. A new closing-only option
persists failure without starting retained validation; synchronous stop remains
separate from actual descriptor close. See
`verification/capability-recovery-transitions-root-review/receipt.json`.
This is controlled persisted close/reopen, not physical crash or real UI health
qualification. Concrete attempt lifecycle and the public coordinator remain under
integration. All three hosted jobs at7365b85 pass for the preceding control-wake
checkpoint; see `verification/github-ci-7365b85/receipt.json`.

The private concrete attempt owner now reserves its adapter obligation before
I/O, constructs only derived concrete adapters off UI, and joins setup return,
active-method return and actual bridge retirement before releasing capacity.
Six tests pass in each host mode, including real signed selection, native
startup/enable, Wasm storage and persisted KV bytes. Nine derived checks hold
setup/method frames across real bridge retirement and verify partial KV cleanup.
Independent probes pass in all three host modes, covering join/cancel races and
eight actual signed/native last-owner-drop cycles per mode with the outer pool
filled. Root reviewed the source and verified both evidence seals,127 baseline
inputs,131 derived inputs,49 owner logs and19 artifacts; see
`verification/capability-concrete-attempt-root-review/receipt.json`.
This host qualification uses frozen transition candidate2 and does not include
the new coordinator or its combined cross builds. All three hosted jobs atf5d99d1
pass for the preceding durable-transition checkpoint; see
`verification/github-ci-f5d99d1/receipt.json`.

The additive signed cold-start coordinator composes that ownership with the
current durable store and signal control wakes. Its combined suite passes all
95 functions in each of Debug, Release and TSan. Thirteen functions per mode
exercise derived scheduling/retirement cases; only five are additional to the
eight coordinator tests. Two ordinary public consumers and six privacy-negative
compiles pass, as do official iOS/Android module/object builds. Root audited 133
frozen inputs, 47 command logs, 29 artifacts and 354 retained dependency bindings;
see `verification/capability-cold-start-runtime-root-review/receipt.json`.

Root's four original flows pass unchanged in all three host modes: early
milestones commit health later without another report, actually committed health
restarts after root-key expiry, the seventeenth owner opens no directory, and 32
cancelled opens per mode return capacity after actual cleanup. Independent review
found no actionable defect; two held health-write/close races pass in each host
mode, including 144 concurrent close calls. Both committed health and uncertain
state survive conservative reopen recovery. The owner-only
derived invoke driver is absent from production. Synthetic milestones and public
native-fallback smoke do not qualify guest event delivery, real UI health,
FieldLog or physical devices. All GA and dogfood gates remain open.

Hosted run 39939500626 at36c5579 passes VM/services but fails Swift 6.2.4
typechecking on three long test-fixture byte-array expressions. The test-only
repair produces exactly the same bytes for both valid and invalid-data variants
and passes all six affected XCTest functions locally. Original CI logs and the
fixture parser's stderr-count correction are preserved; no production bytes
changed. See `verification/github-ci-36c5579/receipt.json` and
`verification/capability-concrete-ci-fixture-fix/receipt.json`. The hosted result
below confirms the repair with the pinned compiler.

Hosted run 39941366514 at ac2d2b6 now passes all three jobs, including all 95
capability-activation functions under the pinned Swift 6.2.4 compiler. This
confirms the fixture repair and committed coordinator composition; see
`verification/github-ci-ac2d2b6/receipt.json`.

The full-Swift compiler investigation preserves every original model observation
while tracing nine actual WASI imports and 2,531 calls. Most random requests in
the sampled stacks come from UUID/outbox operations. The VM's host-call meter
resets per invocation; this single large corpus does not measure ordinary user
turns. ICU has no final byte differences, which does not establish immutability,
interim writes or peak/RSS savings. Official static reactor linkage works for a
scalar Swift export, but the owned VM still rejects its size/resource/import
requirements. Root reviewed the diagnostic source and verified 37 retained path
bindings; see `verification/swift-guest-next-root-review.json`. The unchanged
FieldLog model now also passes native/command/reactor parity for all 11 typed
observations across two calls after one initialization. The first run failed
because the second print remained buffered; an explicit flush in the test
boundary repairs output delivery while preserving every corpus-body byte. Root
matched 99 retained path bindings across 21 commands and sealed 131 evidence
files; see `verification/fieldlog-reactor-root-review.json`. The full reactor is
53,777,114 raw / 18,976,211 gzip bytes and still fails the unchanged owned VM
module limit. Nesting, persistent feature state and peak/RSS are unmeasured.
The separate decoded-function cache now has exact fallible entry allocations,
flat branch targets, checked opaque pins, bounded LRU eviction, cancellation and
lifetime work accounting behind a nondefault feature. Default tests pass 91
functions per debug/release; cache-feature tests pass 122 per mode and all nine
explicit development oracles pass. Independent probes pass 133 work boundaries,
three replacement allocation failures with a pinned neighbor, allocation-free
cleanup and concurrent owner identities. Review tightened drop-before-reservation
release on an unpublished cancellation path. Root combined cache/native checks
pass 199 tests per mode and audit 87 owner inputs, 88 review inputs and 76
unchanged baseline files; see `verification/span-function-cache-root-review/receipt.json`.
The largest observed cache requested heap peak is 8,001,136 bytes against an
8,011,216-byte reservation. This is not RSS or aggregate session admission; the
executor bridge, actual full Swift, native archive and physical qualification
remain open. CI now includes the cache in its combined experimental matrix.
Complete compressed artifact size, including required runtime code, remains the
3 MiB metric; delta/base reuse grants no size-budget or launch-gate credit.

The first signed guest UI integration now has a reviewed, frozen additive
contract/header and exact SDK/bridge ownership design. Fifty-five independent
static checks and C11/C++17 declaration/layout checks pass; see
`verification/guest-ui-contract-freeze-2026-10-23.json`. It reserves an explicit
installed identity mode, fixed startup/event exports, one accepted event and
bounded document delivery. One joined presentation consumer and private visible
native display receipt govern UI retirement and health. Existing contract and
header bytes remain unchanged. The validator, exchange, bridge and signed native
screen implementations are next; no UI execution or health gate is passed.

The additive native guest-UI validator now passes 79 combined native tests,
six focused tests, 49 default regressions and 16 public C checks per host mode.
An independent retained-Release public C probe passes 135 checks; root source
and evidence review is recorded in `verification/guest-ui-native-root-review.json`.
The installed-mode gate passes 12 scoped functions in Debug, Release and TSan,
including capability-only rejection before a full reservation pool or filesystem
access. Its receipt uses frozen pre-UI dependencies. The bounded exchange,
fixed bridge composites, signed facade and native presentation remain in progress.
All three hosted jobs passed for b02b76f and 51aafe8; receipts are retained.
No physical-device or UI health qualification is inferred from these checks.
