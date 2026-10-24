# Isolated private Swift lifecycle: full owner-entry compiler proof

October 24, 2026. The 131-file isolated candidate compiles in Swift/all ×
Debug/Release production contexts. This is uncalled type/borrow composition
proof, not behavioral, reservation-accounting, test, native, or GA acceptance.
Live VM source is unchanged. Root must select further accounting/runtime work.

The baseline is the exact live 130-file closure
`3dee84f70c852c2a26572c1d6e3463e45e56760a6bba403fabfb9c355ccb1cd3`.
Root selected the lifecycle contract at
`verification/swift-reactor-lifecycle-contract-root-review/selection.json`
(SHA-256 `5fc30aee1ab3ebd306ff24de52e18a0a18cc56abb84264920273a096db5bcc6f`)
and the required preparation seam at `preparation-seam-amendment.json`
(SHA-256 `21cf62cafe844ab4503e7cdc4d4781f8a37e78125cf12ecc6b6630e850dc7e36`).
The full product scope remains `mixer-product-plan.md`.

## Actual candidate and interface

Source lives only under
`verification/swift-reactor-lifecycle-implementation/candidate/`.
Its exact compiler-source closure is
`36369eba832214bab721d63aaad021e929ea5f13aa96c780bb5ebceacd99f20b`.
The only changed baseline file is `src/experimental_swift_reactor/memory_growth_operations.rs`;
the only new file is the private child `src/experimental_swift_reactor/lifecycle.rs`.
All other 129 baseline files retain their exact original bytes, including
`execution.rs`, the original frame completion, owner declarations/fields, shared
Frozen source, prior accounting, and original dispatch. No dependency/feature,
public Rust/C ABI, control/cache/WASI, owner, field, ticket, or ceiling changes.
No new numeric reservation credit is asserted.

The private child supplies:

```rust
fn request<'a>(
    owner: &'a mut SwiftReactorInstance,
    request: Request, // Initialize | Corpus
) -> Completion<'a>;
```

The actual result variants are `Rejected(Rejection)`, `BlockedTerminal`,
`PreparationFailed(SwiftRunFailure)`, `Completed(Reply)`, and
`Failed { failure: Option<SwiftRunFailure>, cleanup: GrowthCompletion<'a> }`.
`Reply` is `Initialized` or `Corpus(i32)`. Failure's optional copied diagnostic
is the observed execution/preparation failure; the original cleanup carrier and
its original reports remain authoritative. A completion-only failure does not
invent a diagnostic. Neither a saved i32 nor a successful reply escapes a retained
or restore-rejected completion branch.

The child implements the read-only lifecycle precondition, fixed 35/62 targets
and stages, actual preparation/entry/dispatcher, both outer and stored outcome
inspection, the final actual `check_with_wasi`, original pending growth release,
terminal drain, and consuming completion. The same owner/control/cache/WASI,
state and cumulative budgets are used throughout. The initializer's exact void
outermost result is required. The corpus requires an actual outermost i32;
nonzero values retain ordinary Wasm meaning. Rejections inspect only lifecycle.
Terminal returns only its marker and performs no fabricated cleanup observation.

The growth module has a single private `complete_growth_with_goal` helper.
Existing `complete_growth` delegates with closed `Preserve`. The lifecycle child
uses closed `Initialize` only for its fixed initializer; the helper derives
eligibility from actual stored outcome/lifecycle/wrappers. After the original
vacancy branch it destroys growth/preparation wrappers, short-reborrows the same
lifecycle into the unchanged original frame completion, and writes Ready only
after actual `FrameCompletion::Completed`. Retained carriers preserve the exact
phase, ticket borrow, transfer, fixed storage, and preparation.

## Preparation seam proven by the actual failure

The first complete owner-entry candidate failed in **all four** production
contexts with the same E0506. A failed `owner.prepare_growth(cursor)` branch
cannot assign `owner.lifecycle` while a different branch may return that owner's
borrowed `GrowthCompletion<'a>`. This failure is preserved in attempt
`20261024T195917546437Z`, including its exact candidate source/archive and all
compiler diagnostics. No unsafe pointer, second owner, alternate API, early Ready
write, or discarded retained wrapper resolves it.

Root then selected the exact preparation amendment. Existing `prepare_growth`
now delegates to private `prepare_growth_with_goal` using closed `Preserve`;
the child selects `Terminalize`. Each original failure is evaluated once, and the
already-split original lifecycle is terminalized immediately before returning
that same failure. The original failure checks/order, success admission, bound
record, and original phase construction remain intact. `original_owners` and
`enlarge_construction_with_wasi` use explicit failure branches instead of `?`.
There is no intervening fallible boundary between successful enlarge and State
bound/disposition publication. Preserve callers retain their previous behavior.

The inherited absent-control behavior remains
`control.as_mut().expect("constructed control")`. A unique control is a private
constructor precondition. This packet does not claim to recover an owner missing
that authority, manufacture a replacement control, or fabricate a runtime
failure for it. Missing WASI/cache/State with the original control follow the
existing actual failure path and terminalize only for the selected lifecycle
preparation goal.

## Compiler and cleanup evidence

Attempt `20261024T200049805938Z` passes all four fresh production commands:

```sh
cargo check --lib --locked --offline --no-default-features --features experimental-swift-reactor
cargo check --lib --locked --offline --no-default-features --features experimental-swift-reactor --release
cargo check --lib --locked --offline --no-default-features --all-features
cargo check --lib --locked --offline --no-default-features --all-features --release
```

The collector invokes the pinned official Cargo/Rust binaries explicitly and
records version output, executable hashes, full argv/environment policy,
source-before/source-after digests, process groups, exit status and compressed
raw output. Rust/Cargo are 1.99.0 (LLVM 23.1.1), Python is 3.14.8 and the host is
aarch64-apple-darwin. Cargo is locked/offline, with no wrapper or inherited flags.
These installed executable hashes are not a complete platform-toolchain supply
chain attestation.

All seven groups in each attempt are empty and both owned scratch trees were
removed after empty-holder checks: 16,536,577 logical bytes from the rejected
attempt and 102,902,011 from the successful attempt. All 130 live baseline hashes
were rechecked unchanged after each attempt. No other project's process or
simulator/emulator instance was touched.

Replay the saved packet without compiling or running a VM:

```sh
python3 -B verification/swift-reactor-lifecycle-implementation/verify.py --live
```

Archive-only replay omits `--live`. A new uncalled four-context compiler attempt
uses `collect.py`; its independently owned scratch is removed on success or
failure. Neither command grants runtime or integration acceptance.

## Remaining acceptance work

Actual compiler bodies and this carrier/interface now exist, but no MIR/layout,
positive additive accounting, allocation refusal, lifecycle test matrix, or
semantic/adversarial runtime row has been executed or accepted. Original V7
accounting is retained; it does not cover the new roles. No tests are counted as
passed. New lifecycle/compiler positions and changed common helpers need
phase-correct positive accounting before runtime selection. The finite 86-ticket
limit and State/Combined ceilings are not widened.

There has been no VM/test/native/device execution, no retained full-target
read/hash/run, no network/provider/Git action, and no live VM integration.
Physical phones remain disconnected and explicitly deferred. This packet accepts
no D3/G07/G08, dogfood-release, size, native, store, customer/operations, or GA gate.
FieldLog immutable published separate-repository consumption remains required.
