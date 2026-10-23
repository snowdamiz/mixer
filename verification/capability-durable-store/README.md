# Private capability recovery foundation

Owner: gpt-6.1-sol / xhigh. Candidate2 passed scoped owner qualification and independent review. This
slice adds only three internal production files and two original test files in
capability-activation. No public updater, selection, attempt/health commit API,
adapter, native session, effects dispatch or device claim is added.

The single process-wide outer pool admits16 complete owners. A reservation issues
at most one store admission and one adapter-group obligation at a time. Reference
copies share one-shot latches. Closing denies new claims. Claimed obligations
require explicit retirement; abandonment quarantines/pins capacity. Moved store
and adapter owners have separate bounded retirement flags, so simultaneous
retirement cannot release capacity while either destructor is still executing.
Strong owner destruction occurs outside locks; a second adapter cannot be claimed
under a retiring group. The pool has no reset or alternate production instance.

The private store facade admits one ordinary operation and one coalesced zero-
payload cancellation path before taking owned copies or hopping to its private
actor. It schedules no Task/Task.detached. All filesystem work is actor-isolated.
A claimed store obligation holds that actor before any I/O. Explicit close joins
actual fd closure, validator return and logical operation-tail retirement before
releasing its obligation. Begin/append snapshots live in inner async helpers that
return before the outer tail retires. This counts logical owned frames; it does
not claim destruction of caller Tasks/runtime allocations. An accidentally dropped
open facade quarantines without I/O or cleanup Tasks; its counted actor/actual
open directory remain retained. The future coordinator must own one coalesced
explicit cleanup path. Closing publishes bounded diagnostics then clears the
worker's unique in-memory state, leaving persisted records/high-water unchanged.

State is closed schema3/kind mixer-capability-cold-start-v1, with complete identity,
InstalledRuntime/channel/installation matching, <=4candidate records+one pending,
1MiB metadata and256-entry histories. CandidateID hashes the exact two raw signed
snapshots, assignment sequence and canonical artifact identity with deterministic
CBOR under `mixer.capability.candidate.v1\0`. Payloads use content hashes; partials
use candidate IDs. A greater sequence and exact offered headers are durably
reserved before accepting chunks. A replacement assignment never overwrites an
older signed record. Resume checks actual private regular-file length. Existing
payload reuse requires rehashing; corrupt referenced destinations are not replaced.

Finish uses the same captured ReleaseVerifierV3 context and actual concrete native
Void validator under exact signed/installed limits, including downward0-page
memory. No injected success validator exists. It rechecks cancellation, generation,
current pending record, monotonic deadline/backwards clock and current signing
authority after awaits. Cancellation before commit entry prevents mutations;
after synchronous commit entry it cannot roll back fsync/rename. Ambiguous I/O
poisons the owner and requires reopen, without lowering replay high-water. Health/
attempt models are closed storage scaffolding only; this slice creates no healthy
record, retained selection or authority from those fields.

## Frozen qualification

```sh
python3 verification/capability-durable-store/run.py --label fresh-review-label
```

The driver exports dependency package/source/test blobs from Git
`3bdf5cd4dc32842f3a9b876d473320c54f36731f`, then overlays only the five owned files.
Root's mutable policy/lifecycle/attempt-signals sources are excluded. This is a
self-contained package source export using the unchanged pinned Crypto lockfile;
no mutable SDK checkout is used by the actual qualification builds.

- Candidate2: `2026-10-23-candidate-2/receipt.json`, SHA256
  `5aa8a0f4e533c7d42bd5e81fce5abaa84b3c1fe2f68f7ec9308f593e68d36c36`.
-113-input manifest:
  `8e75b805bb82b0c31174a2ffee992b24be207fd6c60c4ee316b9af5c46198376`.
- Pool: `886d6c44984cfa40135c6aa865a594edb63185f818e5596332118faa13a83ef0`.
- Models: `8a628723bc59e505f5d63e54135e36d91bb2fdc1b75f3cb4456f02ccfeffe4cb`.
- Store: `fe6073f8d463ee27b6f62a343093fe0948391096fdde9a6d9e2646ed041248f3`.
-41XCTest functions pass in debug and release (23unchanged+18new);18new functions
  pass under owned Swift/C-shim TSan. No skipped test is counted as a pass.
- Original independently written Wasm fixtures validate through actual native
  code: valid modules, a malformed uncalled body, exact0-page limits versus1-page
  memory, and an exact4MiB module. The suite also covers all10I/O fault points,
  replay/resume/uncertain commit, externally backed snapshots, cache corruption,
  cancelled/late validation, clock/authority expiry, same-artifact assignments,
  max4records, abandoned owners,32concurrent admission claims and both lifetime
  regressions. Structured stores never accept a syntax-only validator substitute.
- Unchanged material-only public consumer links/runs; three intentional compile
  negatives confirm store/pool/state are internal. Official iOS and Android
  module/object builds pass; neither is an app link or platform/device run.
- One exact experimental Rust archive is reused from the reviewed builder stage,
  source `b25e3b7de2391a80d12e7fd75e60903495bec120`, archive SHA
  `a015ff65980422dd0b9c5cad2e28741d1e5ba478e0f657dcaedf75477d553b72`.
  Header/stage receipt hashes and commands are recorded. No default Rust archive
  is co-linked and no Cargo dynamic-library directory is exposed.

Debug and Release products/modules/maps were copied before TSan and188retained
files are hashed in the receipt for independent direct linking. The ignored work
root is capability-activation/.build/store-qualified-2026-10-23-candidate-2.
Its retained-debug library SHA is
`701be4c304b333a37932326a29ae57568050fc919de756476a8771f5f6843d99`;
retained-release is
`7b20320be3418ce6514927d3c8f0614a8972129eed65189274d3b2a7b445a3bc`.
Exact source exports, binaries and module/object outputs remain at the recorded
paths; these are artifact identity claims, not bit-reproducible-build claims.

Independent review: verification/capability-durable-store-review/final-receipt.json,
SHA256 `a3642344f8c3dde11ab33c4040e863b6632a2c5b0001ab4b495ce5cf84d1047b`.
All24 original probe executions passed across debug/release/TSan against this exact
candidate. The reviewer checked113sources,188retained files,7artifacts,16commands
and294review product bindings, replayed both pre-fix failures, and reported no
open actionable finding. This is a scoped independent review, not a broad security,
standards-fuzz, device or complete product qualification.

## Preserved findings and limits

The independent reviewer reproduced two pre-fix lifetime defects under
verification/capability-durable-store-review: concurrent moved-owner destruction
could free the outer slot, and actor-only close could free it before an owned
begin/append ingress frame returned. Original pre-fix library/source copies and
our development logs remain retained. Candidate1 is the fully passing intermediate
fix before candidate2 additionally clears closed-state metadata; it is not silently
rewritten. Initial test-harness compile diagnostics (async XCTest autoclosures and
weak-variable warning) are also retained, with corrected tests in the final pin.

The private input/owner caps are not totalRSS or recoverable-OOM promises. Production
allocation/runtime/platform failures may still terminate a process. TSan does not
instrument Rust or system framework internals. Intentional negative abandonment
cases pin slots/descriptors until test-process exit; no reset is used to pass.
Full coordinator, fresh/retained one-shot selection, health/effects/recovery,
published FieldLog packaging, physical lifecycle/performance, signing/store/hosted
and GA qualification remain outside this foundation. Phones remain unused.
