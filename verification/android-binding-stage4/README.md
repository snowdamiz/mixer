# Private Android host binding prerequisite

This directory verifies the actual private Swift/C engine using a fixed host
resource owner. It does not enable Android signed UI, install a normal factory,
construct a JNI/native witness, or qualify a device/profile/release. The two C
modules are supplied explicitly by this harness; ordinary portable Android
preparation still rejects without admitting these resources or a Task.

The canonical reviewed product source is the immutable export referenced by
`runs/release-repaired-2/receipt.json`. Its source manifest is
`e8a6d021c7eb99db60391ba516870b6722c8307f5f331ad3f8a76999cb862645`.
`evidence.json` and `acceptance-results.json` bind the final selected receipts,
all six owned Swift sources, unchanged C transport, binding headers, actual host
object, original contract/acceptance, and the separate root-owned join-admission
amendment. A verifier-specific snapshot may have a different overall manifest
because its harness changed; the evidence collector requires identical product
and fixed native fixture bytes for every selected final execution.

`build.py` freezes complete activation source and recompiles the real module,
C transport and host object in Debug, Release or TSan. It links the retained real
SDK/dependency objects identified by the prerequisite receipt; those dependencies
are not rebuilt or instrumented by TSan. The fixed host object owns actual bounded
heap tree/listener/weak-owner allocations and clears them only under a real C UI
lease. Its destructor verifies that actual C facade reclaim already happened.
The host uses one permanent UI pthread and two transport FDs. It is not an Android
Looper or Java weak-global implementation.

The ordinary suite has 39 selected scenarios plus ordinary and testable negative
clients. Transport probes hold actual forwarded operations and preserve original
arguments/results exactly once. The scheduler investigation is narrower: its
actual RETIRE-resumed job hold precedes the Swift terminal store and is not the
literal S4-01 proof. Separate LLDB receipts bind source, binary, driver, PCs and
original worker identities. The literal post-store and consumed-continuation
proofs use unchanged product bytes. Failure controls only cause actual failure;
they never supply successful cleanup, joined, retirement or native-return values.

The final obligation gate has 16 preclaimed cells containing only the existing
obligation/reservation chain. It keeps the real owner alive on uncertainty and
abandonment; no extra resource-owner reference is stored. The Swift facade
reservation remains occupied until `obligation.retire()` returns from the actual
resource destructor. Prepared/transferred/bound abandonment synchronously
quarantines and closes scalar state without launching a cleanup Task.

Run new receipts with a unique name (outputs are never reused):

```sh
python3 verification/android-binding-stage4/build.py --mode debug --name review-1
python3 verification/android-binding-stage4/build.py --mode release --probe --name review-1
python3 verification/android-binding-stage4/build.py --mode tsan --debugger --name review-1
python3 verification/android-binding-stage4/debuggers.py --reference verification/android-binding-stage4/runs/tsan-debugger-review-1/receipt.json --name tsan-review-1
python3 verification/android-binding-stage4/regressions.py --reference verification/android-binding-stage4/runs/debug-review-1/receipt.json --name debug-review-1
python3 verification/android-binding-stage4/symbols.py --reference verification/android-binding-stage4/runs/debug-review-1/receipt.json --name review-1
```

`cross.py` uses the official Swift 6.3.3 Android SDK and NDK r27d API30 to compile
complete real Swift modules and native objects, then strictly links with `-z defs`
against the immutable `3a1bb5a455973bde841a4b57993277fa2c054569` experimental
VM archive built by the repository's canonical builder. It hashes the actual
Swift Crypto dependency objects. The retained earlier Crypto module-only build
lacked `bcm.cc.o`; the cross verifier compiles that actual vendored translation
unit in its own immutable copy with its canonical SwiftPM flags. ELF artifacts
remain host-fixture compile/link evidence only.

Four supplemental cases execute the original C endpoint/entry exhaustion and
fallback/late-close boundaries in all three modes. Root's separate fresh-source
SwiftPM CI receipt binds rebuilt, locked SDK dependencies and the 39 ordinary
cases in each mode; it does not replace the literal debugger matrix.

The S4-29 private Swift lifetime-counter exhaustion executes in Debug and TSan.
Optimized Release debug metadata exposes the exact initialized private reference
but no usable field location, so its failure injection remains unexecuted. The
retained failed attempt is not a Release pass. S4-21 dynamic stale Android event,
probe and attachment delivery remains pending stage5 because this host slice
has no corresponding submission API. No numeric cleanup-serial input API exists;
actual exhaustion, immutable stale-evidence replay and source/type checks are
reported separately.

Failures and narrower historical receipts remain retained. A scenario count is
not a claim that all 32 matrix schedules, every optimization-specific debugger
observation, or any mobile gate passed. Consult the per-case results and root's
independent review. Positive visible-window tests remain explicitly skipped;
physical iOS/Android, JNI/Looper/widgets/draw/Choreographer, signed core/Prepared
integration, actual signed-attempt fallback, FieldLog publication and release
qualification are pending.
