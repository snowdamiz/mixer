# Prospective custody durability correction

prepared-5 addresses CIR-01/02/03 in wrapper, runner, custody evidence and control
plumbing only. Product sources and all nine lifecycle methods remain exactly the
selected prepared-3 bytes. prepared-4 and its review remain immutable. Neither
new plan is released, and no new control, child, compiler, formatter or TLS run
has occurred.

Journal writes check the complete byte count and fsync the file and containing
directory before accepting an event in memory. A short/zero write or fsync error
closes future grants, retains proven group ownership and prevents a clean result.
Native raw audit appends also check complete writes. The full validated completion
and its hash are journaled before exit-grant intent and before immutable grant
publication. Existing ACK-race, no-replace publication and exact recipe contracts
remain in effect.

Before scratch deletion or a clean result, reconciliation parses capped canonical
JSONL, compares exact event sequence with accepted memory, and verifies request,
ACK, child, completion, exit-grant and offer bytes/bindings in the immutable spool.
It rejects missing, duplicated, changed, truncated or reordered acceptance,
unknown transitions, incorrect state/counts and extra members. The snapshot binds
the reconciled journal hash; real terminal validation rereads and checks it.
An I/O failure may leave partial evidence, but cannot obtain a clean receipt.

The separate control plan has 18 finite cases. It retains the prior no-ACK,
manager-cancellation race, timeout, immutable/helper checks and publication-gap
cases, and adds real short/zero journal writes, fsync failure, terminal truncation,
completion-acceptance short write and exit-intent fsync failure. The latter two
require native wait, no exit grant, uncertainty and scratch preservation. It also
sends actual TERM to the exact retained wrapper after its acknowledged fake child
is active, and publishes malformed and replayed full ACKs through the real wrapper
path, requiring zero native launches for those ACKs. Manager cancellation and
helper-only checks are labeled separately; they do not qualify OS signal delivery.
At most ten ACKs and eight fake native launches are possible, one at a time.

The real runtime plan remains separate: fresh production/test VMs, seven pinned
OpenSSL recipes, nine unchanged product methods, 18 required typed artifacts,
zero compiler warnings, bounded outputs and work40/cleanup46/post52/terminal55.
The actual signal control must pass before real runtime release is considered.
Output overflow, absent completion, late/partial registration and INT/HUP delivery
are explicit pending paths; no new evidence for them is claimed. Bootstrap and
leader-loss uncertainty still fail and preserve scratch. A lost/terminal numeric
PGID never re-arms; no global inventory or unowned signaling is allowed.

A future control pass means its expected ownership/error assertions held. It
cannot make deliberate journal/cancellation failures clean real-runtime states.
Root must separately review and release the exact control plan, inspect actual
terminal evidence, and then separately consider the real plan. No lifecycle or
GA acceptance follows from this source-only packet.
