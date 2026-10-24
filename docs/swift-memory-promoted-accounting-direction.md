# Memory caller promotion accounting correction

The independent behavior review identified a missing compiler-promoted body in
the unit build: `memory_pinned_step::promoted[0]` has a `LocalKey<Cell<bool>>`
backing place and a reference return. The inventory selector requires a
`memory_operations::` prefix, so it omits this standalone caller promotion.
The original caller's reference row cannot supply accounting credit for either
place. This violates the already selected positive accounting contract.

Preserve the frozen producer and independent review. Create a separate candidate
from the behavior source closure `6046a5fa8ba3800ec168b7ae6a80cb82bad5ba39b8701cb23a5db720d998bb62`.
Use the same body-selection rule for functions and promoted bodies. Account for
both typed places in all four named positions, retain every existing field, and
regenerate measured declarations and layouts. The observed expectation is eight
additional unit fields and 64 active unit bytes; measure this rather than writing
the expectation into evidence. Production bounds and executable logic should be
unchanged. Do not change runtime control flow, limits, ticket count or diagnostics.

Verify source deltas, all four production/unit canonical MIR configurations,
positive positions, disjoint measured layouts and unchanged owner/Frozen shapes.
Re-run the bounded sixteen memory groups in Swift-only/all-feature Debug/Release
and the prior frame/control/value regressions because unit reservation bounds
change. Existing immutable Frozen runtime observations can be referenced with
exact source-equivalence evidence; no need to repeat unrelated successful work.
Add a collector regression demonstrating that a selected standalone caller
promotion is included and a test-module promotion remains excluded.

Keep candidate, commands, tool versions, source/archive digests, failed attempts
and cleanup in `verification/swift-memory-promoted-correction/`. No live VM edits
or commits in this lane. Independent correction review and root acceptance remain
required. Full dispatcher/public invocation, G08 diagnostics, native execution,
physical phones and GA gates remain open.
