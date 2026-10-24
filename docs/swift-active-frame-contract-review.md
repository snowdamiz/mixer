# Independent review of the private Swift active-frame contract

Decision: recommend root freeze of the amended private ownership contract and
its positive declaration budget. No actionable contract finding remains in this
scope. This is not acceptance of product implementation, literal accounting
coverage of future implementation bindings, executable frames, a native target,
OTA publication or a GA gate.

The review owns only this document and
`verification/swift-active-frame-contract-review/`. It used original source,
host compiler checks and metadata executables. Computer use, captures, native
apps, simulators, emulators and phones remain paused. No product, producer,
tracker or gate source, commit or push was changed by this review.

## Exact reviewed closure

The amended producer seal is
`verification/swift-active-frame-contract/seal.json`, SHA-256
`fad763b5f7afa20f7d2c33b5bdd71c731a8e093db82bb41373380007c8825ac2`.
All 1,395 bound files were checked independently. The contract document is
SHA-256 `749df12243df774aa6615675d2cc0546d2694410095a963df938b21a708a5f26`.
The producer receipt is
`verification/swift-active-frame-contract/results/20261024T040915177519Z/receipt.json`,
SHA-256 `6ac8675278e6dfbf5a58b3f4e91876f2dde1d64a1c98358edc5bedf1173ca21b`.

The archived accepted baseline is the complete 117-file VM closure, tree
SHA-256 `5d1da3fedb28804ed8ddc271ce78461b58b06b8475b5cc8eb411226626bc199f`.
It predates only root's separately reviewed test-observer concurrency repair.
The isolated amended declaration candidate is tree SHA-256
`fb1d69887a04880781018cc240c18b773925eb2b61ff152d040c6daa387fc182`.
The review binds source bytes rather than assuming the later live HEAD is that
archived tree.

The independent receipt is
`verification/swift-active-frame-contract-review/results/20261024T041334790896Z/receipt.json`,
SHA-256 `db2fa703869810363548b64485a024d62eb0db5f31afd67561a7a428b02528b2`.
It records exact argv, cwd, tool versions, source manifests/digests, output hashes
and executable hashes. `review.json` and `review-seal.json` bind the final
recommendation and review artifacts. Raw duplicate binaries are ignored; the
independent receipt resolves the identical qualifying bytes from the sealed
producer portable archive, without Cargo targets.

## Independent observations

The independent checker verifies all 81 producer command records, eight complete
source variants, sixteen metadata layouts, four downstream privacy rejections,
all baseline/candidate C export comparisons, and all 24 portable artifacts.
There are sixteen metadata executables and eight ABI libraries; their bytes,
hashes and build/source associations match the qualifying records. Expected
negative compiler checks are not described as successful product execution.

Fresh independent minimal-Swift Debug and all-feature Release library checks
passed against the exact candidate archive, using separate targets and checking
every source byte before and after. All sixteen metadata executables were
extracted from the portable archive and replayed. Their complete AF records match
exactly. Unit runs select only the named metadata test, with no guest/frame
execution. Six tool/environment observations plus those two checks and sixteen
replays form the 24 successful independent command records. Rust/Cargo are 1.99.0
on the recorded aarch64 Apple host.

The candidate source comparison is literal and narrow. Original frozen source
is unchanged except for the appended crate-private function-Control constructor.
Original Swift execution source changes only for the inline cleanup field,
constructor initialization, positive permanent addition and private declaration
module. The isolated unit fixture gains only that empty field initialization.
The original value source changes only the visibility of the existing constant;
its initializer and algorithms are literal. Original control.rs is literal plus
exactly this read-only leaf:

```rust
impl ReservationTicket {
    pub(crate) fn matches_layout(&self, category: SwiftReservationCategory, bytes: usize) -> bool {
        self.category == category && self.bytes == bytes
    }
}
```

The original owner check remains mandatory before the leaf. The compiled witness
calls it first and invokes the bool comparison only on Ok. The leaf supplies no
authority, mutation, admission, checkpoint, transfer or refund. The new downstream
privacy check rejects external access.

## Ownership and completion reasoning

Rejected pin release preserves authority in SwiftReleaseFailure. Actual cache
release performs every fallible check before pin-record/slot mutation, including
its ActivePins debit removal. The proposal extracts a rejected pin and restores
the same moved frame at the same index. No fabricated token or second release
algorithm is used.

For the descending drain, `[0,unvisited)` remains the untouched original prefix;
the suffix contains only already-attempted rejected frames. Decrementing before
remove selects the deepest unvisited frame. Success shifts only the retained
suffix; rejection reinserts the same actual frame at that index. The next prefix
is unchanged in either case. Several rejected pins can therefore survive while
all other frames are attempted once. The guard is separately attempted first,
and an already-attempted guard/finish frame is marked processed for that pass.
An explicit later cleanup-only resume starts a new retry pass.

Those retained frames are terminal pin storage. Their scalar offsets may be
stale after global arena cleanup and cannot be interpreted by finish, value,
control, numeric, entry or fetch operations. One positively reserved State guard
retains the unpublished pin and acquired debit obligations. Occupied guard and
non-Active state reject another entry before pin acquisition.

PinAttempt explicitly carries a real acquired pin alongside nested completion
failure. Empty cache return slots end before phase completion. The pin and exact
nested-bound obligation move to State before any failure propagates. The first
failure stays sticky; real WASI survives through cleanup and supplies the actual
same-owner observation. Later cleanup observations are recorded separately.

The sticky live_unreconciled flag prevents malformed undercount from passing
completion merely because clearing actual arenas leaves both length and counter
at zero. Both consuming owner cleanup and value preparation must gain the full
State/bound/guard/marker/live barrier before any active-frame product route exists.
Direct cache teardown remains unreachable while external frame/guard authority
or unresolved obligations exist. These barriers are contract requirements; the
current zero-frame product code is not claimed to enforce them already.

The last amendment closes a concrete accounting gap. Actual pre-entry values and
controls lengths are distinct synchronous snapshots, with separate positive
source/local/rollback-argument/callee/caller positions and distinct borrow edges.
They are not parameter bases, frame metadata, current cleanup lengths or ledger
derivations. Rollback ends before enter returns; EntryGuard and State do not
persist these offsets. Resume clears actual global arenas and never retries a
stale snapshot or repairs unresolved counts by inference.

## Positive declaration inventory

All 1,061 fields are compiled actual types: 337 permanent and 724 active fields.
For each configuration, the independent checker associates every schema row with
its compiler-reported offset, complete size and alignment, rejects overlap, and
checks containment in its actual struct. All fields reserve simultaneously;
there is no inferred credit from padding, old aliases or mutually exclusive
windows.

| Host observation | Bytes |
| --- | ---: |
| Additional permanent positions, production | 175,144 |
| Additional permanent positions, unit | 175,336 |
| New frame active positions | 240,776 |
| Fresh full nested value component | 119,576 |
| New frame-operation envelope | 360,352 |
| Added inline State cleanup field | 112 |
| Original frozen fixed formula | 2,912 |

The checked new frame formula adds the full value component again, positively,
beyond every new frame edge/guard/pin/result/WASI position. The old reservation
supplies no credit. The component's actual source and sealed binding map are
hashed; compiler measurements retain its original 119,576-byte meaning. Only one
synchronous primitive call may occupy it at a time, after all cache phases/views
end. Frame completion cannot call zero-frame complete_values. Existing owner size
propagation is observed separately and is not credited against new fields.

The moved scalar locals, optional owner/guard/pin/type borrows, exact FunctionView
and SignatureView Try branches, return/failure wrappers, rollback snapshots and
new ticket-layout edges have distinct fields. This establishes the chosen
positive declaration shapes and compiler feasibility. The six frame methods
remain unimplemented. No declaration table, uncalled witness or index-only model
proves completeness of absent implementation bindings or runtime semantics.

## Boundaries remaining pending

All 22 original-owner frame runtime cases remain unexecuted. Implementation must
match the frozen positions or obtain another positive amendment, then prove real
nested/recursive pins, exact admission/work prefixes, local/control/frame effects,
pin-plus-completion failure, normal/failed return, mixed/repeated release rejection,
WASI/first-failure preservation, no-allocation cleanup, resume and all consuming
barriers. The aggregate-control fixture uses at most nine actual entry-created
frames and exact test-only common Controls/live predebits; it claims no Swift
control dispatcher.

The initial source collector's missing Rust PATH, intermediate verifier scope and
artifact-kind corrections, superseded proposals and the discovered pre-entry
length gap are preserved in attempts/results. Corrected checks do not relabel
failed attempts as passes. The former 956-field packet is superseded by this
amended decision.

Swift dispatcher/initialize/invoke, later host/memory/growth/control joins,
complete target qualification, native checks after the pause ends, final physical
phones, immutable published FieldLog consumption from a separate repository,
signing/store/customer/operational and GA acceptance remain pending.

Offline revalidation requires no target directory or native runtime:
`python3 -B verification/swift-active-frame-contract-review/verify_saved.py`.
