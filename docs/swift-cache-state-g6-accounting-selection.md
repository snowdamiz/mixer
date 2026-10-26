# Selected correction3 G6 source accounting

Root selects the independently corrected component-source ledger for exact
`cache_state.rs` SHA-256
`0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8`.
The complete production maximum is 6,737 scalar operations, partitioned into
422 groups of at most sixteen, plus ninety bounded payload copies: **512 groups**.
The private cleanup-fault maximum is 6,778 operations, 424 scalar groups and
ninety copies: **514 groups**. Both fit the unchanged G6 ceiling of 640.

The original producer's exact 511-group claim remains preserved. At each of the
two mutually exclusive `copy_within` source sites, its two thin-receiver edges
are replaced by the six explicit array-to-slice construction and transfer edges
in [the independent correction](../verification/swift-cache-state-g6-complete-independent/receiver-correction.json).
This adds four scalar operations on an affected path, with no additional payload
copy. Bounds and address operands read the received slice components. The
standard library documents this operation as a
[slice method](https://doc.rust-lang.org/std/primitive.slice.html#method.copy_within).
The same correction adds the missing receiver, range, argument and return
phases to the local inventory. The outer `cache_walk.arena` reference is a
separate eight-byte place from its existing Vec owner; its operation was already
charged. This does not allocate new memory roles or establish their fit.

The selected complete ledger is the immutable producer packet plus the immutable
independent correction and its independently reconstructed 73 path recipes.
It includes helper/caller transfers, complete Options, loop final None, LE
returns, staging, commit, clear/restore and actual post-loan cleanup. G1
admission, G3/G4 merge body, G5 prefix work, G7 paid replies and G128 zero-debit
guard replies retain their separate ownership. The looser G1-inclusive comparison
is bounding slack only; it is not part of actual G6 partitioning.

This acceptance applies to the stated authored-source primitive model. It is
not a machine-instruction, ABI, libstd-internal or measured-runtime bound. It
changes no source, budget, global ceiling or public observation. G1–G5/G7
combined source qualification, the complete 29,344-byte role/lifetime union,
independent implementation acceptance, native targets and GA remain pending.
The proposed byte-index layout is a separate unselected source proposal.
