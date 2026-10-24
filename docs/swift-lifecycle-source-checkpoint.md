# Private Swift lifecycle source checkpoint

The isolated lifecycle candidate now compiles through the complete original-owner
entry, preparation, execution, cleanup and retained-result path in four production
configurations: Swift-only and all features, each in Debug and Release. This is
compiler evidence, not executed lifecycle behavior. Live VM source is unchanged.

The fixed private requests initialize function 35 once and invoke corpus function
62 only from Ready. Ordinary duplicate/preinitialization refusals perform no
control or guest work. A successful result must survive the original consuming
completion; initialization publishes Ready only after inner completion succeeds.
Original state, control, cache, WASI and cumulative limits remain the same owners.

The first full-entry attempt failed E0506 in all four configurations: an error
branch could not mutate the whole owner while the returned type might retain its
borrow. Root selected a private preparation helper that terminalizes the already
split original lifecycle at the existing error return. Existing callers select
Preserve and retain their behavior. The original frame completion stays unchanged.
Both the failed and successful attempts are retained.

The 131-file candidate closure is
`36369eba832214bab721d63aaad021e929ea5f13aa96c780bb5ebceacd99f20b`.
Root replays the sealed contract and implementation packets against the unchanged
130-file live baseline. All owned command groups and 119,438,588 logical bytes of
implementation scratch are cleaned. The separate contract witness also cleaned
its scratch; no simulator or target module was opened by either packet.

See `verification/swift-reactor-lifecycle-contract-root-review/selection.json`,
`preparation-seam-amendment.json`, and
`verification/swift-reactor-lifecycle-implementation/receipt.json`.

Root selected a separate next candidate for positive memory accounting and
SL01–SL23 behavior-test authoring. Its fresh compiler/layout evidence must be
reviewed before runtime execution. Initialization, repeated calls, real Swift
target execution, live integration and GA acceptance remain pending. The inherited
private constructor requirement for a unique control is explicit; missing control
does not manufacture replacement authority.
