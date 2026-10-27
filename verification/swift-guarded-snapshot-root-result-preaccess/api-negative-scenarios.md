# Probe construction and acceptance rules

Do not run these before root selects and seals the candidate, probe adaptation, and finite budget. The old source is an API map, not evidence of the repair. No negative case needs a native owner constructor: the production facade cases accept opaque admitted owners and supplied complete carriers as function parameters and are compile-only. The generic-host cases may use only the already-private root/guard seam, the actual admission/correlation/retirement core, and validator-created proof; they must not replace the owning program with a structural mirror.

For N02, express the repaired result type with the candidate's actual generic arguments and require a `'static` return from inputs whose root is only `'root`. Do not add a `'root: 'static` bound. The central shape is:

```rust
fn force_static<'root>(
    owner: AdmittedImmutableOwnerV1<'root>,
    supplied: SuppliedLoaderCarrierV1,
) -> /* actual original-root result type with 'static */ {
    let result = {
        let (expected, attempt) = owner.correlation_scope_v1().unwrap();
        correlate_admitted_loader_v1(attempt, supplied, &expected)
    };
    retire_admitted_owner_v1(owner);
    result
}
```

The matching positive companion returns the actual result with `'root`, ends the local expected/attempt views, consumes the acquisition owner, and returns the result while the caller retains its original root. It must compile through the real opaque File facade without private fields or owner fabrication. It establishes an original-root borrow, not native construction or durable funding. A stronger incidental owner borrow is not the selected minimum mechanism.

For N03–N13, start from the same actual correlated result. Follow only the relevant legitimate consuming API path, then attempt to return the original accessible payload with no original-root lifetime or as `'static`. Use that payload in the caller after the root's lexical scope, or pass it to a root-free function with the real payload type. An outer wrapper that retains a root marker while its proof, error, guard, or leaf result can be stripped is insufficient. Rejection of an absent extraction API is acceptable only after reviewing all actual exposed alternatives; a renamed method is not evidence.

Keep the actual originals: a matched validator proof, provenance-refused retained selection, association/live refusal, original `io::Error` custom payload, original validation diagnostic, source/build/session Files, and optional executable. Copying scalar kind/offset/usage observations by borrowing while the root is live is permitted. Returning the actual owning diagnostic/error/resource after stripping a root obligation is the negative target. Do not weaken a payload test into a scalar-only test or use a replacement diagnostic with matching text.

N06 and N07 are separate commands for executable `Some` and `None`. The absent optional owner does not remove the obligation for the real proof/errors and three required resources. Refused variants must remain root-bound even when correlation cannot authenticate a match; they already captured the complete original loader outcome. A foreign expected-state owner does not rehome the supplied result to its root. N02/H03 require the supplying attempt's original accountable root, with both sticky barriers retained on cross-owner refusal.

N08–N11 are compile-only through actual selected adoption and leaf APIs. Cover the successful runtime/proof tuple and original adoption failure, then both `Ok(SnapshotScopeFinishV1)` and `Err(SnapshotPreScopeFailureV1)` from the leaf. Lifetime retention may be implemented with opaque guarded carriers; no raw runtime control, adopted proof, body, cache/scope/run owner, failure, or final diagnostic may escape by an accessor, tuple conversion, `?`, closure return, match arm, `into_parts`, or final-field extraction. Do not execute the product leaf to satisfy these probes.

N12 and N13 belong inside the private owning module, at the same access level as its consuming transformations. Attempt to destructure the actual core/carrier and ignore its root field while returning the selected payload or actual resource. These cases check that internal return paths preserve the obligation; an external private-field error does not satisfy them. If the implementation intentionally permits a raw local destructure, review every resulting move and require the post-destructure raw payload to remain in the guarded scope; a new test helper that returns it exposes a real internal escape seam and must fail or be excluded by a closed API boundary with no production bypass. Record the distinction rather than claiming a raw `File` has a Rust root lifetime.

N14 is the generic-core version of the original lexical-root witness: create the original ledger in an inner block using the private host seam; acquire/admit/correlate with actual core and actual proof; end expected/attempt views; consume/drop the acquisition owner; try to move the result outside the block and inspect its same proof pointer/bytes, original error, or guard tags afterward. Require a lifetime rejection attributable to the original ledger ending. A second ledger remaining outside the block, equal metadata, the child host account, and wrapper-local counters must not repair it.

Preserve the old IR02 witness as historical evidence. Its code must remain accessible alongside the adapted negative test; do not silently delete or rewrite it to stop compilation. The exact signature's rejection plus the semantic negative/positive pair prevents missing-lifetime syntax from becoming the sole acceptance claim.

Use one independently named cfg per negative command, and retain its complete stdout/stderr, status, exact command, tool version, source/probe hashes, and diagnostic spans. A nonzero compiler exit is necessary but insufficient: rule out parse errors, unknown fields/types/methods, import/cfg failure, and unrelated errors. For N01 a missing-lifetime diagnostic is explicitly historical shape-only evidence. For semantic root escapes require the intended lifetime/ownership rejection; for intentionally closed extractors require the intended access/API boundary and review alternative conversions. Freeze adapted probes before examining diagnostics. No blind retries or compiler search is authorized.

For every final host run, inspect/drop only with the original root live. Record proof/error pointer identity, exact original fields, original guard tags/drop order, leaf count, original work/storage usage, cleanup credits, and reservation/attempt state before/after. Replay the frozen IR01 witness unchanged in meaning: issued scope means Retained and no Complete/refund, including matched, refused, extracted, destroyed, forgotten, and unused outcomes. Result destruction does not reopen retirement. The unissued control case may still complete through the existing host bridge and release storage exactly once after all original acquisition backing is destroyed; work is never refunded and reserve is not renewed.

`mem::forget(result)` and `mem::forget(root)` are expressly excluded from a lifetime-only funding conclusion. A host test can check the sticky barrier while the original ledger remains observable. It cannot turn that observation into charge ownership after the ledger ends. A normal lexical root end after all accessible obligations disappear is not a qualified root shutdown protocol for forgotten ones. Do not use `ManuallyDrop`, raw pointer reads, or `unsafe` to manufacture accessible post-root values and then label that a safe-API regression; instead review any new unsafe code separately and keep the forgotten durable owner gate Pending.
