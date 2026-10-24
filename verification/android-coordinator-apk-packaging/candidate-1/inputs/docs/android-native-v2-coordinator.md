# Private ordinary Android V2 coordinator

`NativeCoordinatorV2` is a package-private, synchronous, main-Looper owner of one
ordinary JNI session and one concrete `NativeRenderer`. Its constructor receives
the actual Activity and root, creates its own renderer and session, and accepts
no app renderer, descriptor/support proof or captured environment. The public
`MixerActivity`, installed descriptor opt-in, signed transport and public bootstrap
remain outside this slice. The frozen seam is
`docs/android-native-v2-coordinator-contract.md` and
`verification/android-native-v2-coordinator/root-contract.json`.

`renderInitial()` prepares operation zero; `dispatchInput(byte[])` receives the
concrete renderer's synchronous callback and prepares operation one. Each captures
installed resources and the actual window, retains the opaque engine token before
requesting its defensive packet copy, and prepares the renderer from that exact
copy. A fresh check of the concrete capture after preparation can discard a known
unattached candidate. The coordinator sets `attachAttempted` before attachment.
Final attached validation immediately precedes scalar commit, and status zero
immediately enters the renderer's prepared finish. The retained packet is published
only after finish; there are no caller callbacks or fallible allocations between
successful engine commit and that finish.

Before commit, or after a known nonzero status in the private status range 1–7,
only abort status zero confirms a reusable session. The coordinator discards a
known unattached candidate or rolls back a returned attachment journal. A confirmed
initial rejection can be retried without publishing a presentation. Closed status
requires retirement even if another leaf reports a successful abort. Unexpected
statuses, failed/thrown abort, cleanup failure, JNI preparation without a returned
token, a throwing commit, and a post-commit finish failure retire both owners.
Unknown commit outcomes never attempt abort, rollback or restoration.

Any attachment exception aborts the retained engine token and retires both owners,
including a preflight exception before the renderer's consuming handler. No missing
journal is used to infer consumption. A failed native-input transaction performs
its known transaction cleanup, then retires even after a confirmed abort: native
text or switch input may already have changed. There is no synthetic IME restoration.
The concrete native callback contains an ordinary `RuntimeException` only after
retirement and records it in the confined `lastNativeInputFailure()` diagnostic,
so a routine rejected native edit does not escape its Android listener. Programmatic
`dispatchInput` still throws. `Error`/OOM, including nested cleanup Errors, propagates.
Unexpected native callback reentrancy retires immediately and propagates; it cannot
be mistaken for an ordinary contained edit rejection.

`refreshEnvironment()` uses the exact retained packet object, fresh concrete
captures, and prepare/attach/validate/finish without engine prepare, commit,
dispatch or document generation. Any failed refresh retires, with disposal of the
owned engine as part of retirement. Reentrancy and calls after retirement reject
before reaching either owner. `close()` also rejects repeated/reentrant calls;
confined state queries permit observing retirement during cleanup. Retirement
sets local closed state and clears its authoritative packet before independently
attempting native disposal and engine destruction, preserving cleanup failures.

The private renderer runtime floor stays API36. Java17 compilation against actual
SDK37 and D8 min28 establish source/platform linkage and DEX generation only.
`NativeCoordinatorV2HostTests` executes the same coordinator class bytes produced
by that real-source compilation with explicitly test-only Android/JNI/renderer
leaf substitutes. Its fault matrix establishes coordinator control flow, not
native view restoration, gating, draw, IME or JNI/Swift execution. Leaves are
isolated under `native/android/tests/NativeCoordinatorV2HostLeaves` and are never
included in production or future integration compilation.

Run the permitted headless checks with a fresh evidence directory:

```sh
python3 verification/android-native-v2-coordinator/verify.py --attempt candidate-1
```

Every attempt retains exact source snapshots, revision/tree digest, tool hashes
and versions, commands, complete outputs, executed coordinator class identity,
compiled classes, DEX and artifact hashes, including failed attempts.
`NativeCoordinatorV2IntegrationActivity` and
`NativeCoordinatorV2IntegrationInstrumentation` compile separately against actual
production sources and SDK; the accompanying future-only manifest is not packaged.
They require a private APK with actual JNI/Swift ordinary registry, installed
descriptor and native window, and remain **NOT RUN** under the user pause. The
future smoke test is not a complete native fault/IME/lifecycle or physical matrix.
No app, simulator, emulator, device, UI automation or capture is started or queried
by the headless verifier. Native transaction acceptance, physical final acceptance,
external immutable FieldLog qualification, public integration and GA remain pending.
