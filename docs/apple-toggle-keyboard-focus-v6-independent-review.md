# V6 Settings diagnostic: independent source and host review

**Disposition: no actionable findings within the selected host ordering repair.**
The reviewed preparation seal is
`5b2743fd61dbabc95abc6e50468347efe406953fb1314785b17013922b6438fd`
(184 bound files); root repair selection is
`a687f64d09bc04df73842b3a45a4014551497a452cdf5092cd24ee60cbb9a3d7`.
All bound files match before and after the review. The sealed V5 independent
review and its original 45-file stale witness also remain unchanged. This review
stops for root selection; it does not select native execution.

`review.json` contains the disposition; `attempt-3.json` contains independently
executed commands, Python/Swift versions, source hashes, complete output and
outcomes. `review-seal.json` inventories this review's immutable evidence.
Historical source revision context is
`9a9c0e000234b07a92c4484979d3587f7f24df48`, copied from the sealed V5 binary
receipt. No current Git revision is asserted or queried.

The independently recomputed actual V5-to-V6 diff exactly matches the producer's
saved production delta. The only Settings verifier behavior change retains the
accepted route tap's exact `finishedUptime`, verifies its route index and preceding
tap sequence, and requires `finishedUptime <= captureStartedUptime` before appending
opened-route credit or allocating its uploads. Existing capture bounds continue
to bind both the old-selector snapshot and separate destination snapshot. Opened
summary bindings expose the same route's tap sequence, completion and capture
start. Offline replay calls the identical real Session verifier.

The fresh `test_fresh.py` emitter imports the sealed real runtime, Bridge,
Session and replay; it does not import producer fixtures or test helpers. Its
AX, PNG, clock and input markers are explicitly synthetic host data. Its ten
methods pass. Fifteen independent contexts cover all three routes with capture
start before tap start, during the tap, the representable instant immediately
before completion, exact completion, and the representable instant immediately
after completion. The first three reject; equality and the following instant
accept. Accepted summaries retain the exact current route's tap/search sequences
and completion, and replay agrees. The recorded matrix is
`fresh-boundary-matrix.json`.

Fresh negative probes additionally reject another route's tap, a stale search
sequence, invalid tap timing, capture times that follow an older route's tap but
precede the current route's tap, internal wrong-route/nonpreceding-sequence
faults, and stale captures sent over the actual HTTP endpoint. Each semantic
rejection preserves the complete accepted Session state, journal and payload
files, records the Bridge failure and leaves destination/setup credit absent.
The HTTP endpoint returns bounded status 400 with the specific ordering reason.
Injected selected-record persistence failure preserves the accepted route,
completion, cursor, clocks and upload allocation; the same valid record can be
accepted after persistence recovers. The injection fails before writing that
selected record and does not claim arbitrary partial-I/O recovery. Mutating each
route's opened capture in a complete fresh durable journal causes actual offline
replay rejection.

Valid initial-off and initial-on flows continue to satisfy only the setup
observation. The unchanged anchored three-second switch observation, request,
event, upload, payload, diagnostic and session bounds, first-error transport,
cleanup/export semantics and strict qualification boundary are covered by the
reproduced existing controls. The runtime summary remains `DIAGNOSTIC_ONLY`;
all six application cases are unrun, with keyboard/carrier/GA acceptance false.

All 269 producer Python methods were independently rerun: 8 + 26 + 18 + 17 + 44
on V6, plus exact historical V4 39 + 44, V3 44 and V2 29. These are independently
executed existing assertions, distinct from the ten fresh probes and from the
producer's earlier evidence. The isolation wrapper redirects only scratch and
historical witness output into this review lane, preserves test-method ASTs and
loads runtime sources unchanged. Of the independent V5 suite's 26 test methods,
25 retain identical ASTs. The sole CONTRACT adaptation expects immediate stale
capture rejection and retains its false-setup assertion; the fresh emitter
independently verifies that behavior.

The original V5 suite still reports exactly its one CONTRACT failure, with the
same positive stale destination/setup credit. The historical V3 suite retains
its same three failing methods/five failure records. The exact frozen V5 stale
journal still credits all three destinations on V5 and is rejected by V6 at its
first stale capture; all 45 files remain unchanged. Frozen V4 runtime replay and
analysis checks also pass, preserving agreement with that failed native result.
These historical failures remain failures, not successful qualification.

All 102 paths in the exact-copy reuse map were independently compared to their
originals. App source closure remains
`f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46`,
app archive `b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393`.
Strict V2 oracle and V5 native runner/transport sources, products and archives
remain byte-identical. Runner source identity in its original V5 path context is
`acda99b1fb3b2c4252e346bf57f592a0048cba6a4c291aa08208488c69274af1`;
product identity is
`b4b793cf270527e47df3fc73bab3ea30f67c77a413508f5a880dbd4cc9268f84`;
archive identity is
`40365412907c311d421ce94d63e147b67a55b0543d5b6ba6f56211497dbea479`.
The exact existing Foundation host transport executables passed 16 + 35 checks.
No compilation or rebuild occurred or is required by this unchanged runner.
Their official compilation provenance is reused historical evidence, not a new
compiler or iOS-runtime receipt.

Two review-harness failures are retained transparently. The first fresh attempt
compared deliberately fault-injected in-memory bindings against an unmodified
durable journal before restoring the injected state. Its source/output is saved;
the corrected probe restores state before replay comparison. The first full-suite
isolation attempt let `unittest.main` inspect the wrapper module and therefore
discovered zero direct-module tests (exit 5); `attempt-2.json` and its source/output
are retained. The corrected wrapper registers the executed module as `__main__`;
`attempt-3.json` confirms every required outcome and all 269 methods. Neither
review-harness issue is a product finding.

Only this review lane and this document were written. All owned temporary host
scratch is removed. No Git, product edit, native build, simulator/emulator/device
query, launch, UI, capture, settings change, publication or tracker operation
occurred. No native instance was created or required cleanup. Physical phones
remain disconnected and deferred; a future selected native diagnostic and final
physical-device matrix retain their actual pending status. This source/host
review accepts no keyboard, carrier or GA gate.

Reproduce the host review with:

```sh
python3 -B verification/apple-toggle-keyboard-focus-v6-independent-review/run_review.py
```

The recorder writes a new numbered attempt; a new run requires resealing this
review packet before any downstream use of the new evidence.
