# Full Swift reactor after resident index: result

The single selected host run passes full module validation and Initialize, then
fails in Corpus 1 on `TicketInventory`: 87 reservations attempted against the
unchanged limit of 86. The first typed failure is at function 79548, offset
15881589, after 6,555,490 guest instructions and 31,475,443 cache-work credits.
Corpus 2 and eleven-field native parity do not pass. No retry was performed.

Root verifies all 235 result members and 203 preparation members, the exact
132-file VM closure and the unchanged original harness. The child exits 101;
the driver exits 1, with complete output, no timeout or signals and no surviving
owned group. Final consuming cleanup reaches zero for all reservations, live
counts and tickets. The raw success-oriented cleanup flag remains false because
the failure is retained; it does not contradict the separate final zero snapshot.
Owned scratch is removed after holder and ownership checks.

Compared with the previous source-bound run, construction uses 22 rather than 21
tickets and Initialize uses 86 rather than 85, with 64 cache residents in both
Initialize snapshots. Source inspection confirms one added persistent ticket for
the 192-byte index vector. The exact owner requesting the 87th ticket was not
recorded. Failure snapshots occur at different execution prefixes and cannot be
used as equivalent workload measurements.

A separate finite storage/ownership diagnosis is evaluating how to retain the
index within existing reservation headroom. The 86-ticket limit and all other
production limits remain fixed. This result accepts no full runtime, performance,
native, signed/public, FieldLog release or GA gate.

[Complete result](../verification/swift-exact-reactor-after-resident-index/result.md),
[ticket observations](../verification/swift-exact-reactor-after-resident-index/ticket-headroom-observation.md)
and [sealed result](../verification/swift-exact-reactor-after-resident-index/result-seal.json)
retain exact commands, tool/source/output hashes, failed evidence and cleanup.
