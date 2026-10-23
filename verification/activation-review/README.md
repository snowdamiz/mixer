# Independent activation/session integration review

Scope: read-only review of `activation/Sources/MixerActivation`, the additive `VMValidator`, and `ColdStartSelection`'s retained verified metadata, with original adversarial host tests. No production source is edited by this review. All test binaries link the fixed persistent-session VM at `64123c509e861ddd522631b293eadebdaca11341`; the observed static library SHA-256 is `5053e0d03513bfd43c09863c6da0f01b578f55acf7b6157cae68134281da52ff`.

The review found one timing-scope discrepancy, corrected by root before the final replay: the first activation charged selection/validation to its signed startup budget, while a healthy fallback reset its timing origin after fallback selection/validation. Root moved the fallback origin before `updater.reportFailure`. An original regression holds that recovery/selection commit for 1,100 ms against a healthy artifact's signed 1,000 ms budget; the fixed path returns `activation.deadline`, preserves the healthy pointer, and counts only the trapping candidate as a deterministic guest failure. This was a bounded timing-contract discrepancy, not an executable-validation or capability escape. No further confirmed blocker was found within this review's scope.

## Evidence and reproduction

Run against the immutable integrated activation commit identified by the final receipt:

```sh
python3 -B verification/activation-review/run.py --name UNIQUE_LABEL --revision dcca70f
```

The runner exports that commit's activation/runtime/updater packages, records the archive and a complete source manifest, adds only `IndependentReview.swift` to the private snapshot, builds a fresh fixed VM static library, and runs the root and independent suites separately. The working production tree is untouched. A fresh output label is required. Raw tool output, identities, source hashes, exit codes and durations are retained beneath `evidence/`; build artifacts/source exports remain in ignored `.build/`. Durations are development/tool execution observations, not mobile performance claims.

The immutable integrated source is `dcca70fe1d3c343a4b6168ae78e9a466216f729b`. The [frozen replay receipt](evidence/2026-10-22-frozen/receipt.json) is authoritative for its archive/source identities and command results.

The root suite has 10 Swift Testing functions and 11 parameter cases. The independent suite has 15 additional functions and 15 cases; internal loops cover further variants, without claiming a separate standards-case count. The runner records function and parameter-case totals separately from the console output. Initial 13-function working-snapshot evidence and the 15-function timing run are preserved separately from the immutable final replay. Earlier runner/Swift harness compilation errors are retained under ignored `.build/*/failed-evidence/`; they are not production defects or passing qualification.

Tool scope: macOS 27.0.1 arm64, Apple Swift 6.4/Xcode 27 toolchain for host tests, Rust 1.99.0 for the fixed static library, and pinned official `apple/swift-crypto` 5.0.3 (with its lockfile). Keys are freshly generated ephemeral test values and never persisted. Reviewer selection: `gpt-6.1-sol`, `xhigh`. The receipt pins actual tool output and hashes rather than treating these prose labels as authority.

## Original adversarial coverage

| Area | Observed result |
| --- | --- |
| Signed linear-memory rounding | 131,071 bytes permits one 64-KiB page; a two-page initial memory fails validation and growth cannot round the limit upward |
| Signed growth | 131,072 bytes permits exactly one growth from one to two pages; the next growth returns -1 |
| Complete executable validation | Unknown opcode in an uncalled function and unapproved import fail before staging |
| Explicit profile | Integer profile rejects f32; numeric-v2 executes the same valid floating-point module with bit-exact result |
| v2 authority | Empty signed grants preserve the same one-page growth limit; this grants no native capability |
| Cached payload mutation | Active instance retains independent state; after interruption recovery, the corrupt staged payload is rejected/quarantined at the next actual selection |
| Actor admission | A gated durable download operation prevents reentrant start; it cannot publish a guest while another idle operation is pending |
| Cancel during selection | No guest is published, no deterministic-trap count is earned, recovery records unknown interruption, and native slots remain reusable |
| Close during selection | Closed phase survives late completion; reopen records unknown interruption, without guest trap evidence |
| Initial startup deadline | Holding durable selection past the signed one-ms budget prevents activation and records unknown interruption |
| Fallback startup deadline | Holding trap recovery/fallback selection past the healthy budget rejects that fallback; only the candidate's actual unreachable trap counts |
| Native session capacity | Sixteen occupied VM slots cause `session_limit` and unknown interruption; releasing them permits a new cold-start retry |
| Completed startup ownership | Late cancellation/deadline callbacks cannot close the completed, returned session lease |
| Runtime trap | An actual provisional `unreachable` retires the guest lease, records one deterministic failure, and rejects further invocation |

The Wasm byte builder and signing harness were independently authored for this review. The tests call the real interpreter/C ABI, not an accepting executable-validator stub. Root's additional existing tests cover healthy offline reopen, signed v1/v2 metadata, candidate-to-healthy recovery, quarantine threshold, unrelated draft preservation, signed fuel, installed policy narrowing, payload integrity, argument-error classification and startup close/cancel races.

## Read-only reasoning and boundaries

The actor sets phase/admission guards before suspension. Startup checks closed/cancelled state before transferring the returned session into active ownership; a late result is closed. Idle download methods retain an operation guard across their updater await. Invocation has a separate busy guard, executes synchronous native work off the actor, and conservatively retires on error. Close can invalidate ownership while the native operation unwinds; this does not promise rollback of already executed instructions.

`StartupWork` publishes its session under a lock, captures cancellation before publication, closes cancelled sessions, and prevents late timer callbacks from cancelling completed ownership. Its lock is not held over guest invocation. A monotonic completion check rejects a result that exceeds the signed/native minimum even if the timer callback was delayed. Validation/instantiation are bounded by the existing profile but cannot be forcibly preempted by wall time. There is no exact scheduling, UI responsiveness or hard real-time claim.

The immutable verified token comes from the updater's same payload snapshot, and the installed policy checks runtime/capability binding, intersects signed fuel/memory with native ceilings, and dispatches to an explicit validator profile. The composition rejects guest capability maps/grants and unsupported imports. The installed fingerprint's generation/attestation is still an embedding/release responsibility; this local test fingerprint is not a published installed-build identity.

The deterministic-trap classifier requires native VM status 2 and a closed code allowlist. Native argument/capacity/cancellation/deadline errors do not become guest trap evidence. A runtime trap can terminate the process-local guest and select native fallback without switching live guest state. Durable quarantine of an already healthy artifact after later execution failure remains an explicitly open policy, not a claim made by this slice.

The underlying fixed registry reserves capacity during construction, close while operations are live, and actual payload destruction. The separate [session-lifetime regression](../../compiler/experiments/profile-budget/session-review/README.md) established the corrected destruction boundary. This activation review exercises aggregate slot exhaustion and retirement; it does not replace that allocator-gated regression or establish an aggregate process-byte budget.

No full Swift/WASI execution, guest UI/effect/capability protocol, real FieldLog activation, published package/runtime identity, physical device behavior, OS kill/power-loss durability, TSan/fuzzing/security audit, store approval, mobile lifecycle or performance gate is qualified. Phones were unavailable by user instruction; no device operation was attempted. Native fallback is an explicit result for the embedding to execute its actual compiled feature; these tests do not fabricate that feature or user-visible success.
