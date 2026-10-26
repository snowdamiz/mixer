# Selected cache-state clear revision

This bounded amendment applies to the next isolated cache-state candidate,
correction3. It replaces only the prerequisite's 256 zero-word iterations with
sixteen explicit 128-byte stores. It does not accept the complete implementation,
G6 ledger, G3/G4 sorting bounds, or 29,344-byte lifetime union.

Use the exact source in
`verification/swift-semantic-adapter-root-review/clear128-anonymous-proposal/cache_state.rs`
(SHA256 `0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8`).
Each statement borrows its own anonymous `[0u8; 128]` directly. No named
128-byte array binding, by-value array helper argument, second Candidate2048,
promotion, or optimizer copy elimination supplies the memory argument.

All 2,048 scratch bytes are cleared exactly once before the unchanged twelve
restores. The restore and private fault suffix remains byte-identical. Preserve
the pre-loan length/range proof, untouched scratch on pre-loan refusal, one
post-loan cleanup, poison behavior, suppression of both later leaves, source
layout, public bytes, API and all numeric limits.

The independent review is sealed at
`verification/swift-cache-state-g6-independent-review/seal.json`
(SHA256 `21343e183de35954dc39f74c27dbca01afed0f91793fac9d3d68ae1682a199e9`).
Its explicit source-operation model is selected for this clear block: 2,768
named scalar component operations form 173 blocks of at most sixteen, plus
sixteen actual 128-byte destination copies, for 189 groups. Repeat construction
charges all 128 element initializations for each statement. Do not additionally
count a fictitious initializer-array-to-array movement. Range and view fields
remain separate scalar components. This is an authored-source bound, not a
compiler ABI or machine-instruction bound; it excludes the unchanged cleanup
call, length guard, restores, fault path, returned bool and caller work, which
must still be accounted for in G6.

One anonymous 128-byte temporary ends at each statement. Its 128 bytes and the
live Paid24 form only a 152-byte wire-role subtotal; all other simultaneous
handles, values and roles still require reconciliation. The named-array variant
is not selected because its initializer/local peak already consumes wire256
before Paid24. The original guarded candidate and both proposed variants remain
immutable.

Retain G128 ownership of zero-debit absorbing guard replies, received values and
caller terminal installation. Ordinary paid replies remain G7. Actual post-loan
cleanup remains G6 under the combined prepayment. No group borrows another
group's spare allowance. The source must receive fresh host behavior/API/layout
qualification and independent review before any combined acceptance or delivery
of canonical runtime code. Native runtime and capture remain paused.
