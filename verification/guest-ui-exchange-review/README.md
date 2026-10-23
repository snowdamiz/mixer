# Independent guest UI exchange review

This lane owns only `verification/guest-ui-exchange-review/`. It read the accepted
design and frozen event contract, reviewed the four SDK production files, and
performed a related review of the sealed bridge composites, ownership pump,
construction cancellation, and typed native diagnostics. It changed no SDK,
bridge, activation, package manifest, contract, header, or status/gate source.
Root owns repairs, integration, commits, pushes, CI, and qualification.

Final scoped review passes against sealed SDK candidate 4. Eight independent
groups pass in optimized Release and ThreadSanitizer, including all three
terminal-result schedules. The Unicode substitution remains rejected. SDK owner
source hashes match at both ends, and all retained snapshot inputs remain
unchanged. `2026-10-23-fixed-4/receipt.json` SHA-256 is
`cfc1c714b81ac7e1e14c0c2f7a7565b8f5e34afea7492dbcc215e3cfc0ec9209`; the exact
owner receipt is `verification/guest-ui-sdk/2026-10-23-candidate-4/receipt.json`,
SHA-256 `f336e0a822579af8b8e24a08a62323583d4d633051321107430a177adbb60f5b`.
No SDK/bridge defect remains open from this review. Activation's presentation
retirement and complete signed execution remain separately owned evidence.

Two defects were identified and sent to root:

1. Candidate 1 accepted a native snapshot whose node/action identifiers had
   canonically equivalent but different UTF-8 bytes. Synthesized `UIDocument`
   equality uses Swift's canonical string equality. The accepted snapshot then
   supplied the changed identifiers to a guest event. Root replaced this with a
   comparator bounded by the claimed tree, with exact UTF-8 strings/keys/actions
   and exact numeric bit patterns. Candidate 2 independently rejects the
   substitution. The original statically linked failure executable and replay
   log are preserved in `2026-10-23-initial-unicode-finding/`; original object
   hashes were not captured before root rebuilt them. That limitation is
   explicit in its receipt.
2. Candidate 2 could lose an accepted event's terminal diagnostic. A result-free
   presentation claim was acquired; close then created a terminal event result;
   completing the older claim cleared that unseen result because stop was set.
   The independent eight-group replay against retained candidate-2 objects fails
   exactly this group in Release and ThreadSanitizer. Root repaired consumption
   to require exact result equality, preserving unseen results and stop-updated
   outcomes for a later claim. Candidate 4 independently passes queued,
   running, and already-claimed-delivered outcomes. The presentation model's
   final-stop claim/retirement remains separately qualified by its owner.

The first SDK repair was independently checked by linking small original Swift
probes to hash-sealed retained `MixerCore`, `MixerUI`, and `MixerGuest` products.
No new SwiftPM graph was created. `2026-10-23-fixed-2/receipt.json` pins owner SDK
candidate 2 (`5a2caded9bf8e480e125d3779ab812c35ee640c888c2d8319a1b247dc5edba02`)
and records matching source manifests before/after the checks. It contains
seven passing groups each in optimized Release and ThreadSanitizer, plus the
safe Unicode reproduction returning `snapshot_accepted=false`, closed input,
and no event bytes. Its receipt SHA-256 is
`27f6dce04e4ae45c46e70e5fdc57ce1a746541cb80e2956b12e2a699f87b4156`.

The expanded eight-group probe covers:

- 58 strict raw JSON rejections, five worst-escape/Unicode identifier roundtrips,
  positive UInt64 maxima, decoded duplicate keys, malformed Unicode/UTF-8, BOM,
  unknown fields, coercion, trailing bytes, and size limits.
- Exact issuer identity when numeric generations and serials are reused;
  foreign/stale/closed claims reject locally without stopping another owner.
- Whole-document mismatches including Unicode substitutions in node IDs,
  action IDs, and visible strings, plus negative-zero numeric bits.
- 513 produced frames, one claimed/one pending frame, latest-frame coalescing,
  display-lag rejection, and an earned receipt surviving newer revisions until
  the exact consume operation or stop.
- 32 accepted events retained through result consumption, event preference over
  ready wakes, exact sequence bytes, and control refresh without a new frame.
- 256 concurrent turn/input and intent/stop trials, both deterministic ordering
  directions, queued/running terminal-result retention schedules, and a claimed
  delivered outcome that stop changes before claim completion.
- 65,536 coalesced hints, one issued consumer, final hint before finished,
  coordinator lifetime, and under ThreadSanitizer a rejected simultaneous
  waiter plus cancellation preserving the parked continuation.

`2026-10-23-terminal-loss-candidate-2/receipt.json` preserves the expanded probe's
expected failure against candidate 2. It uses copied retained candidate-2
products, not whichever products root later rebuilds. SHA-256 is
`e3d2f5ab8dd3a9dfa2920f8346a2b49f214ddc3a5bc39d5aa72c4d012609d4a0`.
`2026-10-23-original-1/` is superseded timing/debug evidence: root had already
rebuilt the SDK by its product-copy step, and the initial Unicode probe then
threw ordinary `closed` after correct rejection. It is not an original-failure
or final-pass receipt.

The separate original Wasm bridge probe uses only retained products and the
selected native archive. `2026-10-23-bridge-seams-1/receipt.json` pins the sealed
bridge owner receipt
`08035b9ea818c6ff60170848177aa38e45df0a3d10e9a73d676ca0e645e1d8e6`, unchanged
bridge sources/inputs, actual object/module/archive hashes, commands, compiler
version, and logs. Its SHA-256 is
`23d38097ca5b577bbc99c26f6d386ad85b8c09e2224fe89a0b21d611b6145755`.
The probe passed 25 negative header cases and exact adjacency; four invalid
required-export cases; native exact report tuple, unchanged generic typed
diagnostics, malformed report/module rejection; actual startup and event
memory-copy/invocation/harvest; unchanged UI revision; a non-invoked ready check
that releases its exact claim without turn charging; changed event-buffer and
malformed-document harvest failures; and out-of-memory-range reads retaining
the bridge status-3 domain. The Wasm fixture was independently authored in this
review directory; no owner fixture or third-party implementation was imported.

The final tiny bridge replay uses the newly qualified native-only archive and
SDK candidate 4. `2026-10-23-bridge-seams-native-2/receipt.json` SHA-256 is
`446ddb858a29390acab3ba1f1f2b56d402c5d8ea83acda93bdc7f7c40f711270`; all three
groups pass with unchanged bridge sources and inputs. Its sole selected native
archive is
`experimental-capability-runtime/build-verification/local/guest-ui-1adb25c-v2/host/lib/libmixer_vm_capability_experimental.a`,
SHA-256 `4d3b6dc36ea034d5604299752d560cbbc0615002b6b5ef4e5c25bbb3cb7c6120`,
and it imports the same stage's headers. The receipt pins the native package
qualification (`6e6c64ce24406fccc6842b3a9437557d4f045bbeaab3cb6e2f63dd18cd0a6eaa`)
and binding audit (`f20392c3f75c28e7961740713227d7efd4d5b7011fef41c9b73c525e0255621f`).
This preserves the earlier combined-archive result as historical evidence while
binding the final local seam result to the current package. It does not replace
the full bridge/activation suites' new-package receipts.

Static bridge inspection found no additional defect in the reviewed scope:
the same exchange arbitrates fixed guest turns and input; successful harvest
precedes later pending-call admission; two shared-guard effect checkpoints
protect submission; actual fixed operations alone serve UI sessions; the
required-export mapping consumes checked typed diagnostics; and the repaired
construction-cancellation handoff preserves the shared cancellation stop before
owner cleanup. Those are source observations plus the scoped native probe,
not exhaustive race or effect-rollback proofs.

Reproduce a new SDK review run after root seals a new owner receipt:

```sh
python3 verification/guest-ui-exchange-review/verify.py UNIQUE-RUN verification/guest-ui-sdk/OWNER-RUN/receipt.json
```

An optional final argument selects an already captured products root containing
`Debug/` and `Release/`, allowing exact old-product replays. Bridge probe command
is `python3 verification/guest-ui-exchange-review/verify_bridge.py`; its output
directory is deliberately one-shot. All logs, exit codes, versions, source and
input hashes, elapsed times, and executable hashes live with the receipts.

This review proves bounded logical SDK behavior and the stated native Mac seam
checks only. ThreadSanitizer does not instrument the Rust archive or all system
frameworks. It is not an exhaustive interleaving, allocator/RSS, hard-latency,
native first-screen, signed activation, operational I/O-admission, full Swift
guest, Android rendering, simulator/physical-device, immutable FieldLog package,
store/customer/production publication, or GA qualification receipt. Phones
remain disconnected; no device discovery, device command, or reconnect request
was attempted. Activation was not compiled by this lane.
