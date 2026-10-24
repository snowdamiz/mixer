# Frozen shared numeric primitive dispatch

The frozen numeric path now calls one private static generic primitive dispatcher
in `vm/src/experimental/execution/borrowed.rs`. This slice moves only selection
between the existing saturating, floating-point and integer helpers. The existing
`SpanInstance::numeric` still performs its literal shape/frame/type validation,
`count + 1` work charge, actual post-helper usage observation, and trap mapping.
The raw helper result remains live through observation, including when the helper
consumes operands and returns a trap without pushing a result.

Root accepted the reduced seam and its fitting derived inventory before product
application, in `verification/swift-shared-numeric-extraction/layout-review/20261024T003352353904Z/`.
The complete generic numeric owner algorithm was **not** extracted. No Swift
numeric adapter or Swift interpreter is implemented by this change.
`mixer-product-plan.md` remains binding; this host evidence changes no release or
GA gate. Phones remain disconnected.

## Applied private seam

```rust,ignore
trait NumericMode: ExecutionMode + Sized {
    type NumericState<'a>;
    fn values_mut<'short>(state: &'short mut Self::NumericState<'_>)
        -> &'short mut Vec<Value>;
}
fn numeric<M: NumericMode>(state: &mut M::NumericState<'_>, opcode: u8,
    saturating: bool) -> Result<(), &'static str>;
```

Only `FrozenMode` implements this private trait. Its state association is the
existing `SpanInstance`, and its sole adapter borrows the original value arena.
The returned arena borrow uses an independent short lifetime. No owner field,
collection, mode object, callback, public Limits/Rust/C API, failure wrapper,
work/fuel debit, usage update or allocation formula is added. The borrowed module
is now compiled for either span execution or Swift reactor; the new numeric
trait, adapter and helper are compiled only for span execution.

The mode adapter returns only a reference. The shared helper returns the same
`Result<(), &'static str>` as the original primitive helpers. It creates no
`ExecutionFailure` or `Result<_, ExecutionFailure>` storage. The original owner
retains every diagnostic operation and its existing ordering. Comments now name
actual primitive dispatch and correctly say numeric helpers emit at most one
value.

## Frozen reservation and simultaneous inventory

The fixed reservation is unchanged: exclusive owner 728 + three original
ExecutionFailure positions 1,176 + two original CacheFailure positions 400 +
DecodedInstruction 40 + Control 32 + ScalarReader 24 + scalar component 512 =
2,912 bytes on the observed aarch64 Apple host. Frame, Control and SpanInstance
remain respectively 64, 32 and 1,496 bytes with identical original field offsets.
The old borrowed-parts/operation layout test also matches between snapshots.

The executable inventory uses actual field types and offsets, including the
original run and owner caller positions, new helper argument/reborrow positions,
values adapter source/returned/caller references, raw helper return transfers,
and the existing primitive scalar/pop/conversion roles. Each phase has named,
disjoint positions; enum niches and interior padding are not reused as capacity.
Pop calls finish before divide/truncate calls begin, so those child inventories
are separate phases. Returned result positions are explicitly retained.

| Simultaneous phase | Bytes within the existing 512 |
| --- | ---: |
| Integer pop | 464 |
| Integer divide | 416 |
| Integer push | 384 |
| Floating-point operation | 456 |
| Conversion pop | 384 |
| Conversion truncate | 416 |
| Saturating pop | 392 |
| Saturating truncate | 424 |

All eight inventories and all frozen owner offsets match baseline/candidate,
Debug/Release, and minimal-span/all-features runs. Validation/work happen before
the new helper is called; observation/trap mapping happen after it has returned.
Those unchanged owner phases introduce no new adapter or diagnostic positions.
The maximum chosen inventory is 464, without changing any term of the formula.

The rejected full fallible adapter candidate required 1,176 bytes for distinct
source/returned/caller result positions before scalar roles. A unit-return
out-parameter candidate still required 552 bytes in the trap window after caller
roles were included. Their source, manifests and outputs remain under
`layout-review/`; neither candidate was applied. The first deliberately
conservative primitive inventory combined non-simultaneous pop/divide phases and
failed at 528; that failed receipt is retained, rather than relabeled a pass.

## Executed evidence and limits

The successful main receipt is
`verification/swift-shared-numeric-extraction/results/20261024T003757200365Z/receipt.json`.
It records Rust 1.99.0, Cargo 1.99.0, Node v22.23.3, exact commands/cwd/targets,
source archives/manifests, outputs, runtime test lists and baseline/candidate
comparisons. Product source tree SHA-256 is
`541597e176144c8fdedc4469f0d9a42095b2ca5cd19f50af94785c064e872248`.
Metadata, product checks, Clippy and probe source use separate targets. Each
variant/feature/profile test run has a fresh target; source closures are checked
before and after every command.

These are **selected library and numeric integration targets**, not the complete
product integration suite. In each baseline/candidate snapshot and each
Debug/Release profile, the main matrix passes:

| Features | Passed selected tests | Existing oracles ignored in this main run |
| --- | ---: | ---: |
| Default | 22 | 6 |
| Minimal span execution | 48 | 6 |
| Swift reactor only | 137 | 6 |
| All features | 186 | 6 |

The selected targets are `--lib`, `differential`, `float_differential`, and
`float`; span/all additionally select `span_numeric_extraction`,
`span_execution`, `span_execution_allocations`, and `span_execution_oracle`.
The counts include the injected executable layout test where span execution is
available. They do not replace earlier full-suite counts or qualify other
unselected integration targets.
The main `*-executed-tests.json` files retain the complete listed inventory,
including ignored tests; `verified-summary.json` separately records actual
runtime passed and ignored identities.

Each span/all Debug/Release comparison matches exactly 454 independent public
SpanInstance traces: 128 scalar-opcode cases, 64 saturating cases, 10 numeric
corners, and the associated work/fuel/cancellation boundaries. Full raw result
bits, trap kinds/codes/cursors, sticky failures, state/cache usage, work and
constructor/cold/warm allocation observations match. Warm invocation requests
zero allocations/reallocations while the observer refuses its first request.
The existing allocation suite also executes its allocation-failure and
cancellation ordinals. This does not simulate cancellation at an unobserved
instruction position.

The explicit follow-up receipt is
`verification/swift-shared-numeric-extraction/oracles/20261024T004030182031Z/receipt.json`.
It runs the existing six ignored development Node oracle tests with `--ignored`
for both snapshots, default/span/all features, and Debug/Release: 72 passed test
executions with zero ignored in that follow-up. Each run includes 13,056 integer,
233 structured-control, 1,290 conversion, 27,944 floating operation and 560
float-memory cases, plus 2,693 validation mutation candidates (98 accepted).
These are existing independently authored development oracles, not Swift target
or device evidence.

Scoped product library plus new-test Clippy passes with warnings denied. The
broader all-target/all-feature Clippy command still fails on **26 identical real
diagnostic identities** in the original and candidate snapshots, in existing
Swift cache/execution/accounted and guest-UI tests. Cargo summary lines are
excluded from that count. The broad lint failure is retained and remains a
limitation. The first final-collector attempt, including the new fixture's
subsequently repaired unused observer-support warnings, remains a failed receipt
in `results/20261024T003710007819Z/`.

From the repository root, `python3 -B
verification/swift-shared-numeric-extraction/verify.py` verifies the exact saved
snapshots, command outputs, runtime-versus-listed test identities, actual
passed/ignored counts, parity, typed layouts and broad lint limitation. The
result is `verified-summary.json`. `collect.py` and `collect_oracles.py` retain
reproduction procedures for fresh targets and full output collection.

Complete numeric owner-algorithm sharing, Swift execution/initialization, the
full Swift target, physical devices, immutable published FieldLog consumption,
and GA acceptance remain pending. No commit, push, tracker change or device run
was performed by this lane.
