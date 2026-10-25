# Independent ordered-cache analyzer design review

Verdict: **accept the corrected bounded design only**, for root's implementation
selection review. This is not analyzer, CLI, source-preparer or target acceptance.
The review owns only this document and
`verification/swift-ordered-retention-analyzer-review/`. It changes no product,
Cargo, dependency, historical stream, execution index or gate files.

The binding scope remains `mixer-product-plan.md`. Computer use, screen capture,
native simulator/emulator execution and physical-phone runs remain paused.
This review executes only finite Python models and a standalone Rust layout
probe. It does not import a hosted harness or run a Swift workload.

## Frozen input and source authority

The first reviewed proposal seal is
`4869a708a63be760519cf62c5d1bc42631a06049ea0d410408f3f5fb96637246`:
57 members, 1,738,360 bytes. An exact independent owned snapshot preserves every
member and the seal. Its final producer source-tree digest is
`49116e80fe3dd66888fc70080775289cae1740d22cd790215cb4b3310b1c5566`
at `68468f8fb73f21d2e4b388c41ad15fd01bfd0d93`.

The final reviewed amendment is seal
`c52828b9bbd2aea835871f1f6b68c6dd29281499ee080e5e52fefe525d1e92a8`:
67 members, 2,398,795 bytes, producer source-tree digest
`97d53ce629074ea41173c397071057e7af0325e2b2be9cc8f4b1c85ae02be2a5`
at the same revision. It is snapshotted separately; the original copy is
unchanged. The producer's preserved first-freeze archive is independently
verified against all 59 original members, including the original seal pair.

The review reads the frozen writer, observer, 24-code table, selected candidate
cache/control source and root's selected-completion acceptance. The original
prototype, completion and independent completion-review seals are independently
checked before and after the replay: 186, 222 and 158 members respectively.
Their accepted scope remains the six selected completion fixture paths and
serializer/readers/custody work. The independent 19-phase logical peak is
16,186/16,384 bytes; the 51,712-byte distinct-role union is not a simultaneous
peak. Inherited serializer inventory, CODE partial-buffer loss, source-code
coverage, INIT/lifecycle and driver limitations remain open.

Every one of the 17 captured completion sidecars is snapshotted independently
and remains `invalid`/failure 15. A new analyzer report cannot rewrite those
classifications. The review does not claim a complete replay of their streams.

## Corrections required in the first proposal

R1: `Release` joined the actual token correctly but was not explicitly forbidden
during an open acquisition. The actual source finds the first free pin slot
before `Lookup`, then executes the acquisition synchronously. A forged release
between `Lookup` and `PinPublished` could otherwise change the apparent first
free slot. The proposed FSM also needed an explicit prohibition on resuming
successful operation events after failure. The review's independent transition
model rejects release at all ten open operation stages and rejects resumption
from failed/terminal state. The producer acknowledged the gap.

R2: the standalone Rust API requires an 8,192-byte `VerifiedBindingView`, but the
launch description inherited only stream/profile inputs. There was no concrete
context transport. Separately, the proposed 18-million host debit estimate
counted stream/profile/raw-result hashing while the trust contract also required
source/manifest/executable verification. The review required an explicit fixed
context transport with all descriptor owners counted, and an explicit cost/trust
boundary for selection/source/executable verification. The producer acknowledged
both parts of this gap.

Both findings are resolved in the amended design. The acquisition state IDs
and closed transitions now require idle-only release, prohibit operation
resumption after failure, require idle terminal/phase events and stop ordinary
events after phase 5. An independent 165-case stage/event matrix agrees with
the amended operation gate. The fixed context is now an exact 8,192-byte retained
input descriptor, with 64 read/EOF attempts included in Rust's 263,584 reserved
I/O attempts. The historical arithmetic estimate is 229,870,640 authored steps,
leaving 38,564,816; it remains an estimate for that historical envelope.

The immediate host wrapper counts five retained host inputs, three Rust inputs
and one Rust report File, plus one host null sink and three child stdio owners:
13 named data/stdio descriptor owners. Its 8,192-byte host record now holds 60
fixed custody rows with explicit offsets. The complete named Rust/host lifetime
inventories remain implementation gates; descriptor arithmetic is not memory
qualification. Hash updates occur only after assembling each bounded block.
The frozen immediate host estimate is 17,802,672 of 18,000,000 debits, leaving
197,328 for the stated envelope. Neither estimate permits a cap increase.

Source, manifest, toolchain, compiler and build provenance verification is now
an explicitly separate prerequisite with proposed 64-million-step and fixed
byte/member caps. Its `SelectionVerificationReceiptV1` must be independently
accepted and registered for the exact closure before the consumer can accept
replay. That preparer and receipt are unimplemented and unavailable. Supplied
hash syntax, a boolean or an unregistered receipt grants no authority.

The design discloses private exactly-once `OwnedFd::from_raw_fd` adoption under
the selected trusted wrapper. Numeric FD range checks do not prove validity or
ownership. This is an internal worker, unsupported as an arbitrary caller-FD
CLI. Independent source proof of valid distinct inputs, exact ownership,
parent offset quiescence and cleanup is required before CLI acceptance. This
review accepts that truthful proposed boundary, not a safe-construction claim.
Unsafe arena access/casts/uninitialized memory remain prohibited. Physically
short Rust reports are failed output; shorter semantic prefixes still use the
fixed 49,152-byte report.

## Independently executed support

The first owned replay passes all 18 frozen producer methods and 20 independent
review methods. The latter include 35,694 small-state cache-policy comparisons
against an independently structured sorted-prefix oracle, a full 64-slot reverse
timestamp case, pinned obstruction, selection/emission/destination distinctions,
schema boundaries, explicit report offsets, checked row-access adversity,
irrevocable eviction effects, preflight reservation and commit-failure models,
frame/CODE/buffer-loss cases, host acceptance authority and separate guest versus
consuming-ledger observations. A later independent method verifies all 17
historical sidecars without reclassifying them.

The final amended replay passes **25 frozen producer methods and 23 independent
review methods**, including all 35,694 policy cases and 165 closed transitions.
Run 2 records the initial amended 22-method review; run 3 adds the independent
cross-check against the amended operation gate. All attempts and exact executed
runner/test copies are retained. The final review source-tree digest is
`8b479413faaeb3626d78c074362e29dea0945a5c6a83bb4bed5f547b593eac13`.
The candidate archive's complete 132-member, 19,326,876-byte source closure is
hashed before and after, with the three consulted candidate files matched to
their archived identities. The original writer/observer/code table copies also
match their upstream bytes. No source tree is restored, imported or executed.

The independent oracle computes the eligible timestamp/slot order once and
chooses the shortest feasible prefix; it does not reproduce the producer's
repeated minimum scan. Both agree on all 35,694 executed states. These are
finite policy and contract tests, not a parser or analyzer implementation.
The independently authored FSM and budget models establish expected rules for
future implementation tests; they do not validate missing implementation code.

A fresh Rust 1.99.0 `aarch64-apple-darwin` compile and execution confirms the
proposed value layouts: FunctionRow 96, ResidentRow 64, PinRow 48, PlanRow 40,
WindowRow 128, TopRow 64 and custody value 64 bytes. Arena regions use 7,873,120
of 8,388,608 bytes. The 41,984 bytes of named transient groups are provisional
reservations; they do not prove a complete analyzer inventory or stack/RSS.
The binary report remains 49,152 bytes and the host record 8,192, totaling 57,344
under the 65,536-byte aggregate report cap.

Python 3.14.8 and Rust 1.99.0 executable identities, exact commands, environment,
source closure, stdout/stderr and cleanup are retained in the review packet.
No disposable source/build scratch was created. Only the owned layout binary
is retained as evidence; all synchronous children were reaped. No native,
capture, target or unrelated process was started or queried.

## Acceptance boundary

The first frozen design was not accepted without R1/R2 correction. The amended
freeze resolves those design findings and is accepted only at the bounded
design level. Full analyzer acceptance still requires real strict
selection/original-result/profile/custody adapters, source-bound code/kind/stage
applicability, complete allocation and lexical lifetime inventory, independently
encoded full-field parser and FSM negatives, bounded I/O/drift refusal controls,
budget/window/report exhaustion and the exact two-record acceptance join.
Neither the finite oracle nor Rust layout sizes supply those missing gates.

Root must accept the final independently reviewed design before implementation
selection. Live integration, corrected writer, target driver/full workload,
retention policy changes, compiler/native/device, signing/store, customer,
operations, published-package FieldLog and GA remain separate pending work.

After root accepts this contract, the bounded Rust library is a concrete next
implementation scope: safe existing File borrows, fixed arena/context/report,
strict stored-prefix replay and finite fixture controls. That scope can proceed
while selection-receipt and worker-admission prerequisites remain unavailable.
Fixture observations cannot unlock real replay acceptance. CLI, host custody,
source preparer, driver and full target require their separate reviews.
