# Candidate 5 Activity/worker timing correction

F06/F07 are corrected in a new host oracle and a frozen callback adaptation.
All 55 host tests pass. The same five exact independent-review fixtures which
passed the old oracle now reject. Native execution is **NOT RUN**; this packet
does not authorize dispatch. Root must independently accept this correction
before using its explicit native command.

The candidate 5 APK, its 179-member archive, 105-input source closure, geometry,
schedules, Java, DEX and production implementation remain unchanged. The new
packet references the immutable retained APK and archive in the prior packet;
it neither copies the archive nor rebuilds the APK.

## Oracle correction

The oracle validates every worker request against its sealed planned event,
checks its action interval and serial send order, and requires its history to be
empty. Only then does it index the validated worker by current sealed eventTime.
For each Activity entry/exit pair it additionally requires:

```text
matching.workerBefore <= entryUptime <= exitUptime <= matching.workerAfter
currentEvent.eventTime <= entryUptime
```

The comparisons are inclusive. A valid zero-duration interval whose event,
worker and Activity reads all share the same millisecond passes. Existing action
bounds, worker order, Activity order, endpoint, coordinates, pressure, state,
acknowledgement, export and identity checks remain in place.

An Activity event whose action is not MOVE must have empty history. Genuine
MOVE batching remains valid: the current MOVE matches its own worker, while its
historical MOVE samples may precede that worker interval. Historical samples
retain their sealed MOVE time, raw/local coordinate mapping, pressure and strict
cross-delivery ordering. Retaining the last MOVE while dropping intermediate
deliveries also remains valid.

These are source/parser corrections selected by
`verification/android-pointer-oracle-root-review/correction-selection.json`.
The five negative fixtures are synthetic observations, not observed Android
failures. The unchanged independent review records the official platform basis:
the synchronous Instrumentation send contract and zero history for non-MOVE
MotionEvents. This correction did not repeat online research or native tests.

## Frozen runner adaptation

The new `run.py` verifies the entire new host packet, prior producer packet,
independent review and all 1,121 root-selected bindings before entering the
reviewed runner. It loads the unchanged reviewed wrapper and its identical
concrete runner source. It overrides exactly two callback globals:

- `_pointer_validate_native`: the new corrected oracle.
- `_pointer_runtime_directory`: the new contained fresh-output policy.

The runtime receipt's `adaptation.timingCorrection` records the exact new
oracle/wrapper/policy/contract hashes, unchanged concrete runner and reviewed
wrapper hashes, and the selected correction receipt hash. Its wording explicitly
distinguishes the unchanged concrete runner source from the loaded new oracle.

The reviewed runner still checks all frozen source, APK, tool, archive, local
packaging, official alignment and certificate bindings before its first Android
tool command. Immediately before installation it repeats its already-qualified
source/APK, packaging, official alignment and certificate checks. The native
entry point was never called by these host controls. Official signature failure,
bounded output, owned process/extraction cleanup and runtime sealing code remain
byte-identical to the reviewed concrete source.

The new wrapper checks the output policy before loading the runner; the
overridden directory callback checks it again when the reviewed main requests an
output path. Only `verification/android-pointer-timing-correction/runtime/runtime-N`
is allowed, with a positive unpadded integer and a fresh attempt. The new host
seal excludes only that exact runtime subtree and its own exact root seal.
Nested receipts and nested seals remain bound. Symlinks reject throughout both
host and excluded runtime trees. The old runtime subtree is never selected.

## Executed host evidence

The exact collector command was run twice:

```text
python3 -B verification/android-pointer-timing-correction/collect_host.py --attempt host-1
python3 -B verification/android-pointer-timing-correction/collect_host.py --attempt host-2
```

`host-1` is a retained failure. The five new negative fixtures rejected and all
oracle controls passed, but two prior packet-policy tests patched a stale module
instance because the new support loader recreated reviewed modules. Caching
those unchanged reviewed modules fixed the harness isolation bug. No prior
packet file was changed. The first attempt's source bytes and reconstructed,
hash-verified exact contract are retained alongside its complete failing log.

`host-2` passed 42 prior tests against the corrected oracle and 13 additional
tests. The exact retained negative fixtures are referenced by their immutable
review paths and metadata/native hashes. New tests cover all four worker action
types rejecting history, non-MOVE Activity history, equal-millisecond boundaries,
earlier coalesced MOVE history, finite timestamps/coordinates, callback/source
identity, contract/tool drift, no-dispatch behavior, pre-entry packet failure,
fresh paths, nested seal/receipt binding and excluded-runtime symlink rejection.

The original 284-file host packet, 507-file predecessor and 42-file earlier
review, the 835-file independent review and all 1,121 root-selection bindings
passed before and after collection. All 179 archive members were independently
hashed; the unchanged 105 inputs and 88 live native/SDK inputs matched. Local
APK ZIP/ELF validation, official `zipalign -c -P 16 -v 4`, and official
`apksigner verify --verbose --print-certs` passed for the retained APK and exact
expected v3 certificate.

Commands, UTC times, Python/JDK/tool versions and binary hashes, source snapshots,
frozen source revision/tree/closure authority, complete logs, failures and owned
command group cleanup are retained in the attempts. Both scratch directories
were removed only after an empty `lsof` result, unchanged device/inode and no
symlinks. All recorded command groups ended empty. The collector made no Git,
ADB, emulator, simulator or physical-target command and no rebuild.

## Root dispatch handoff and limits

After independently accepting this separate packet, root can explicitly dispatch:

```text
python3 -B verification/android-pointer-timing-correction/run.py --build candidate-5 --attempt runtime-1 --execute-native
```

The current packet receipt states `nativeRuntime: NOT RUN` and
`nativeDispatchAuthorizedByThisPacket: false`. The wrapper's `--execute-native`
switch is necessary execution intent; the host packet is not root acceptance.
Physical phones remain disconnected and deferred. No IME, accessibility, broader
lifecycle, public V2, signed OTA, separately published FieldLog, store, customer,
operational or accountable GA gate is accepted by these finite host controls.
