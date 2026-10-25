# Independent ordered Swift diagnostic design review

This review accepts the corrected bounded ordered-stream **design only**, with
no blocking findings within that written-proposal scope. It does not accept an
implemented Rust writer, analyzer, hook protocol, memory accounting or target driver. No
Rust implementation, target attempt, policy change or native runtime is selected
here. The remaining implementation gates below are mandatory.

The independent review identified seven concrete gaps. Their original statements
are preserved in
[findings.json](../verification/swift-ordered-retention-diagnostic-design-review/findings.json).
The final frozen proposal resolves them at the following explicit scope:

| Finding | Resolved design or finite-model scope |
| --- | --- |
| D1: file custody | Requires rechecking writer and reader descriptor/path identity, regular-file type and exact framed length; hash and copy through verified descriptors, recheck stability, then seal and reverify the captured evidence. Observed drift invalidates the supplement. Hashes do not authenticate an adversarial rewrite. |
| D2: close result | Removes the claim that `File::drop` exposes a close Result. Write results, observed custody, close-error observation and durable storage are distinct claims. |
| D3: invalidity latch | Requires keeping invalidity independently writable when `try_borrow` fails or a wrong thread has no active owner TLS. Inventory the latch, lifetime, owner state and all temporaries. |
| D4: failure context | Represents both attempted-pin failure and terminal harness failure. A terminal failure may have no active pin and an absent or independent cursor. It must not fabricate an operation or permit a later acquisition. |
| D5: finalization | Requires closing callback admission before a stable flag snapshot. Bound admission and finalization without spinning; a nonzero in-flight count cannot produce a valid footer or permit concurrent writer access. Require a separate enforced synchronous-dispatch/quiescence proof. |
| D6: capture disk | Bounds the original plus evidence-copy stream contribution, sidecar and copy attempts; inventory host copy buffers and descriptors separately. The per-file cap is not the total packet bound. |
| D7: cap reach | Rejects cap-only truncation when stored records are below the declared cap. Independently mutate the header cap and retain the initial fixture limitation. |

The [final audit receipt](../verification/swift-ordered-retention-diagnostic-design-review/attempts/2/result.json)
passes **25 producer methods** (19 wire/state and six finalization-model methods)
and **16 independent methods**. Counts overlap in purpose and are not product
executions. The producer seal is
`3d28dad80748a4b35ac0e49f9567a95bd5175997d57197c36ad6d85513d555c3`
with 34 members. Its corrected proposal is bound at SHA-256
`a9133fac08a4910d29834012257f7bcfa08134bc7fd83d4a9a13d1d72709b8ff`. The independent command is
`c80d55865bcf6fabf83a11fce8b6c95152c180665bb70b293bf10166555f6eb5`
and its result is
`17b5a52f1e9d403ba793fb23e0921b2c127159fcade2120ca57894b102aaeaf1`.

The review runner verifies every member of the producer's frozen seal and its
exact packet inventory before importing a frozen copy of the synthetic codec.
It reruns the producer methods and separately authored tests. The independent
byte encoder does not call the producer encoder. A second small resident/token
oracle compares valid traces with held pins across later acquisitions, releases
unrelated to the last operation, and two evictions within one acquisition. Every
eviction failure boundary retains only the actual completed effects: taking a
slot removes it even when the later drop/refund fails; it does not count a
completed eviction without its Commit.

The abstract finalization suite enumerates 140 orderings of two callback
enter/check/leave chains and End. Independent cases cover every End position in
a single wrong-thread chain and the model's finite 64-callback admission limit.
An in-flight callback keeps the footer absent even after its later leave. These
are finite atomic-transition checks; they assume linearizable transitions and
do not establish actual Rust memory ordering, lock freedom or source quiescence.

Independent controls also cover framing and reserved bytes, context and count
drift, tiny cap positions, sticky error classification before replay, corrupted
pin identity, nonzero original consuming-ledger fields, and terminal failures
outside a pin. A zero final consuming ledger leaves the separately reconstructed
resident and held pin intact; the analyzer cannot invent missing per-slot drain
events or silently zero that state.

This deliberately preserves the small model's remaining limits. It accepts some
unused payload/body-identity changes, phase changes, invalid PlanEnd outcomes
and missing scan transitions. These are executable observations of **missing full
schema/state validation**, not successful protocol qualification. Full plan
collision, immutable body identity, work intervals, original replacement
timestamps/ties, victim choice and lifecycle replay remain pending. Python lists
and dictionaries here are finite fixture storage, not the proposed writer or
bounded production-sized analyzer.

The historical sizing arithmetic is independently recomputed from the accepted
baseline counts: H=537,576, M=61,628, A=599,204 and E=61,564. With three eviction
stages and both pin-return and terminal failures,
`4A+5M+3E+8 = 2,889,656` records or 369,875,968 ordinary bytes. The 4,194,304-record
cap permits 536,870,912 ordinary bytes and 536,871,936 bytes with framing. This
is headroom for that historical prefix, not evidence of future coverage. Two
stream files plus the 8,192-byte sidecar contribute at most 1,073,752,064 bytes;
original stdout/stderr, raw results and other driver evidence still require their
own explicit bounds before any target preparation. No 512-MiB file is allocated
by these checks.

The proposal correctly separates diagnostic overhead from production CacheWork,
reservation tickets and guest results. The 16-KiB external logical inventory,
128-KiB host-copy inventory, 8-MiB analyzer arena, 64-KiB analyzer transient bound,
authored step ceilings and report cap are unimplemented hard acceptance gates. They are not measured Rust
layouts, allocator behavior, physical stack/RSS, CPU cost or performance
qualification. Every complete usage snapshot, copied helper argument/return,
error Result, atomic/guard, file metadata owner and copy buffer must appear in
the appropriate measured inventory. A prior observer is not silently added to
this one. No production limits or timestamps are retuned to fund observation.

Before a future finite Rust slice is accepted, independently verify the closed
event-specific field/sentinel/footer/sidecar schemas; exact baseline reversal
and unchanged cargo/control/limits; all selected original Swift and generic
tests; hook on/off and Frozen-mode parity; partial work/cancellation/publication/
release/eviction failures; original token nonce versus its successor; all-pinned
and held-instruction safety; bounded short-write/Interrupted/WriteZero and error
paths; allocation ordinals; measured complete layout/allocation accounting;
finalization and lifecycle/reset guards; and authoritative final consuming
ledgers. A syscall-count bound does not bound kernel latency.

A separately selected target driver must bound stdout/stderr draining **before**
execution, preserve the original raw result before supplemental classification,
bind source/input/tool/binary/schema/selection identities, and retain actual
failure and cleanup evidence even if diagnostics are invalid or unavailable.
Synchronous observation can shorten the unchanged wall deadline and change the
observed failure. Truncation, I/O failure or changed progress cannot authorize a
larger cap, repeated target attempt, new policy or inferred later phase. An
accepted stream would describe only its actual baseline prefix; it cannot prove
counterfactual work or target benefit.

The first frozen audit's 18 producer and 13 independent passes are retained in
[attempt 1](../verification/swift-ordered-retention-diagnostic-design-review/attempts/1/).
Its tiny-prefix fixture accidentally declared cap=32 while retaining fewer rows
and setting cap-only truncation. That exposed D7; it did not establish actual cap
reach. The exact earlier reviewer sources and frozen inputs are preserved under
[history/attempt-1](../verification/swift-ordered-retention-diagnostic-design-review/history/attempt-1/).
The final fixture sets the header cap to the actual tiny cap and adds an explicit
premature-cap rejection test. No failed run or superseded binding is erased.

All 132 named VM files match the original
`16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd`
manifest before and after the final tests. The final receipt confirms both
children exited successfully and the selected inputs remained stable. Exact argv, selected environment, Python 3.14.8 executable/version/hash,
Darwin 27.0.0 arm64 and source revision context
`eec94804ba89cb1b68746b764a1495d54e7ddedb` are retained per attempt.
Root metadata is historical context rather than a requirement that other lanes
remain frozen. The captured finite command was:

```sh
python3 -B verification/swift-ordered-retention-diagnostic-design-review/audit.py
```

For read-only verification of the sealed packet and frozen finite suites, use
`python3 -B verification/swift-ordered-retention-diagnostic-design-review/verify.py`.
The receipt producer above creates a new attempt and would require resealing.

Only standard-library host Python tests ran. Both synchronous children exited;
`-B` suppressed bytecode. There was no VM edit, source restoration, Rust/compiler
build, target selection, native/UI/capture run, process discovery, signal or
cleanup deletion. Retained review files are evidence; no scratch source/build
products or disposable native instances were created. The native pause remains
in force. Complete workload, separately published-package FieldLog, signing,
store/provider/customer/operational and accountable GA acceptance remain pending.
