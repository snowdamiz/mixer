# Independent review of private Swift value operations

The corrected candidate has no unresolved blocking finding within this private
zero-frame slice. This review binds the 116-file VM source closure SHA-256
`96b16d4886b9218e132a2a1255c0ce4e66c60879ed7bb5f1ea1185b0ca08b8c7`.
The independent decision and complete file seal are
`verification/swift-value-operations-independent-review/{decision,seal}.json`.
Root acceptance remains separate.

This review owns no product, producer or tracker changes. It reviews only the
private original-owner zero-frame prepare/push/pop/numeric/complete route. It does
not accept initialization, invocation, an interpreter loop, active frames,
growth, host dispatch, a full Swift target, a published package or a GA gate.
All execution here is native macOS on aarch64 with Rust/Cargo 1.99.0. No simulator
or physical device was used. Physical qualification remains a final acceptance
requirement; this review does not block subsequent development on disconnected
phones.

## Accounting and original ownership

The first candidate's saved execution evidence reconstructed successfully, but
its named inventory omitted the actual `Result<Value, &str>` conversion returns,
floating range/reference roles, nested shapes/types, NaN-bit windows, proof
accessors, and distinct fallible-transfer wrappers. Its runtime size calculation
also traversed named rows before enlargement. The rejected source and findings
are preserved under `rejected-candidate-1/`.

Root supplied positive exact-type fields for those roles and made the operation
total a constant. All executable preparation, operation and completion bodies
remain literal first-candidate bytes. The source path association covers **227
fields and 561 typed positions** in `accounting-audit.json`. Array elements for
the nine primitive `?` call sites, four preparation unit-result sites, work/live
calls, integer division residuals and four conversion branches have distinct
roles. Actual payloads, `Option`/`Result`/`ControlFlow` wrappers and caller storage
are counted as complete types.

| aarch64 layout | Accepted baseline | Corrected candidate |
| --- | ---: | ---: |
| Production execution header | 207,352 | 289,536 |
| Unit execution header | 208,312 | 290,496 |
| Additional permanent positions | 0 | 82,184 |
| Additional active positions | 0 | 103,248 |
| Declared operation plus active reservation | absent | 119,576 |
| Production construction envelope | 1,062,312 | 1,062,312 |
| Unit construction envelope | 1,065,072 | 1,065,072 |

The permanent header covers pre-admission calls and returned diagnostics after
restoration. The active inventory adds to the existing 16,328-byte declaration
rows. No new caller binding borrows an old diagnostic slot, owner payload,
interior padding or Frozen scratch as credit. Unchanged internal helper windows
remain covered by their still-charged original control/cache/WASI owners, with
the same call nesting as accepted construction; the new caller/transfer positions
are additional. These are conservative logical reservations, not physical stack
or RSS measurements.

The actual original-owner route verifies WASI/cache/ticket provenance, preserves
owners on admission failure, rejects populated zero-frame state, and restores
the exact previous bound. Push predebits live usage before allocation-free value
publication. Numeric validation protects partial shape helpers, checks typed
operands, charges `count + 1` work and uses the accepted shared arithmetic body.
Actual post-helper reduction is reconciled even when a trap consumes all its
operands. Completion clears real values despite terminal failure and destroys
the supplied return storage before restoring the bound. Retained caller
diagnostics remain charged until consuming final cleanup. Original first causes
and actual WASI observations remain intact.

An abandoned phase deliberately retains its entire enlarged construction ticket
through final control cleanup and reports `ConstructionBound`. It cannot produce
a false zero-usage receipt. Fault-injected excess live usage remains visible as
an invariant outcome after actual values are destroyed; it is not ordinary
zero-invariant cleanup evidence.

Every measured accepted owner size/offset matches the baseline in eight
feature/profile/production-unit comparisons. The entire Frozen owner source and
shared arithmetic body are literal baseline bytes, with the 2,912-byte Frozen
formula and public limits unchanged. Raw logs were checked directly, including
the first unit owner row that the producer's original parser missed; the
producer retained and repaired that receipt without rerunning or relabeling its
binary executions.

## Executed evidence

The final independent receipt is
`verification/swift-value-operations-independent-review/results/20261024T013948234375Z/receipt.json`.
It records **48 passing selected unmodified-product test executions** and **44
passing independent probe executions**, each with zero ignored tests. The two
sets each cover Swift-only/all-features and Debug/Release in four fresh disjoint
targets. They are selected operation tests, not a full product-suite claim.

The independent probes check 2,570 native-expected integer results and exact
work/fuel counts; float payload bits and all eight saturating subopcodes; every
376 rejected scalar/saturating opcode case; prefix-preserving traps; cancellation,
work and capacity boundaries; underflow/type errors; repeated phase restoration
with actual caller storage; live-count corruption; and abandoned-phase charge
retention. The allocator refuses its first request in observed operation windows
and records zero attempts there. This does not simulate every asynchronous
cancellation instant or measure non-Rust allocator behavior.

The saved-evidence verifier independently reconstructs product and metadata
closures, hashes and re-lists all 48 producer binaries, checks raw compiled field
offsets, and compares all 454 Frozen trace records per profile. The baseline and
candidate retain the same 26 pre-existing broad Clippy diagnostic identities;
that broad lint command remains failing. A separate fresh Debug/all-feature
metadata replay passes one layout test and matches every corresponding raw
record. Its test is excluded from the 92 native behavior executions.

Two failed reviewer collector attempts remain saved: the first incorrectly
compared non-compile baseline archive files, and the second exposed the review
probe's incorrect zero-cleanup expectation for an abandoned phase. The corrected
expectation is verified above. Neither attempt is reported as a passing matrix.

The independent collector and verifier are
`verification/swift-value-operations-independent-review/collect.py` and
`verification/swift-value-operations-independent-review/verify.py`.
They preserve complete product and test-only derived input archives, commands,
tool versions, logs, source digests, executable hashes and runtime test lists.
Fresh unmodified product builds and the independent test harness use separate
targets for each feature/profile combination. The derived harness appends only a
test-module declaration and independently authored tests; production execution
bodies and types are literal candidate bytes. The two kinds of test counts are
reported separately. Run the collector from the repository root for a new
matrix. Verify this saved result with `python3 -B
verification/swift-value-operations-independent-review/verify.py
verification/swift-value-operations-independent-review/results/20261024T013948234375Z`;
append `--execute` to replay the eight native test configurations with new
targets. The separate metadata replay and recorded final checks are in
`completion-receipt.json`. No product, tracker, commit, push or device change was
performed by this review lane.
