# Logical action boundary requiring explicit scope

The original unchanged cache.rs161–163 uses
`AtomicU64::try_update(..., |n| n.checked_add(1))` for cache owner allocation.
The standard library may reevaluate that closure during atomic compare/exchange
retries. This is documented in the official [AtomicU64 reference](https://doc.rust-lang.org/stable/core/sync/atomic/type.AtomicU64.html)
and its [atomic source](https://doc.rust-lang.org/stable/src/core/sync/atomic.rs.html).

The candidate's logical source-operation scalar counts a fixed primitive call
and excludes library/kernel internals and arbitrary concurrent callers. It must
also explicitly exclude retry-driven reevaluation of the closed pure callback
if451,173,376 is retained as that scalar. An exact bound on actual reevaluations,
atomic instructions or progress under contention/spurious failure has not been
proved here. This is an inherited primitive boundary, not a new runtime callback
seam; no arbitrary function or owner can be passed to the profile component.

Root subsequently selected exactly that abstract primitive/callsite scope in
the retained source-action amendment/selection under `root-corrections/`.
`abstract-action-reconciliation.json` reconciles both row and added terms under
the same unit. It retains the explicit exclusions above and grants no stronger
actual execution bound. No source/cap/timeout change or broadened test follows.
The complete197,880/197,928 object union and149 fresh command outcomes are
independent of this logical-action interpretation.
