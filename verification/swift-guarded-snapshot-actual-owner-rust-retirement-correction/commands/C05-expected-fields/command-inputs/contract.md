The public accounting property is unchanged: no live correlated proof, original
loader error, or returned resource may coexist with released acquisition
storage. The frozen implementation did not enforce this in its generic shared
retirement core after the expected/attempt borrows ended.

The root-selected correction conservatively retains the acquisition charge.
`correlation_scope_core_v1` sets the private
`PrepaidInputOwnerV1::correlation_retirement_blocked` before the duplicate-scope
check and before publishing either expected or attempt. That `Cell<bool>` starts
false, has one write of true, has no reset/discharge method, and moves with the
same acquisition owner. `retire_acquired_owner_core_v1` checks it before touching
the cleanup partition or resources. A blocked owner returns `Retained`, never
`CompleteAcquisitionRetirementV1`, irrespective of matched result, original
loader refusal, provenance refusal, association refusal, extraction, destruction,
or `mem::forget`. Work and storage never refund through owner Drop.

This intentionally also retains storage when no result was produced or every
child has already been destroyed. The outer caller's destruction order is no
longer the accounting enforcement mechanism. A later independently reviewed
joint-retirement protocol is needed to restore useful post-correlation cleanup.
The production File bridge independently continues to refuse healthy retirement;
the production startup, native ownership, allocator, compile custody, root
funding, product policy and GA boundaries remain Pending.

Public Rust signatures and visibility stay unchanged. No lifetime is claimed for
the owned result. The private owner gains a `Cell<bool>` and its capture/move
shape changes; every resulting owner/call/capture/return/layout/MIR obligation
requires fresh review and pricing. No old layout, integer quote or MIR price is
carried forward as authority. No layout query is selected here.

An owner for which no correlation scope was issued retains the original healthy
cleanup route, but only when all original raw/partial/unresolved, cleanup work,
bridge retirement, backing destruction and final-carrier checks succeed. All
original validators, binary formats, five limits, selected source prefix,
diagnostics, host11, and `host_account_v1.rs` remain byte-for-byte unchanged.

Source scope: new isolated 146-member distribution derived from the root-released
producer seal `3592011c00794c12dcb76cecc41d4d2913e01a3d6e97612f3ce90f10cb4e5e23`.
Only `initial_profile_v1.rs` and `retained_profile_loader_v1.rs` differ. Neither
the frozen producer packet nor canonical engine/metadata is modified.
