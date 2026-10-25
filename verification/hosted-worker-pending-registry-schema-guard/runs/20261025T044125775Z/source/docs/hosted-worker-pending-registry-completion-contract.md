# Pending recovery completion retention

This additive implementation contract preserves late recovery outcomes without
letting one unavailable registry shard stop recovery on healthy shards. It extends
the selected pending-registry contract's private audit storage only; public
interfaces, runtime budgets, operation authority and production entry remain
unchanged.

The fixed audit coordinator may retain one pending completion per registry shard:
16 slots total, each at most 2,048 encoded bytes. Each slot binds the complete
validated wake ticket and disposition. A new wake requires its shard's slot to be
free. The existing single unresolved recovery task remains held until actual
settlement, and a timeout stops further wakes in that invocation. Timeout alone
does not claim cancellation or fabricate a successful disposition.

On actual settlement, preserve the exact disposition, or `unavailable` for a
rejection, in the corresponding in-memory slot before one synchronous SQLite CAS
write. The callback performs no remote call, retry, timer or await. A failed local
write retains the in-memory value for the next invocation. A process crash before
durable retention leaves an unknown reservation; it does not establish an outcome.

During a later scheduled invocation, visit occupied slots in the existing circular
shard traversal before starting another wake for that shard. Persist the next-shard
cursor first; persist any retained local value and establish its durability before
remote completion. Attempt each occupied slot's exact-ticket `finish_wake` at most
once, with the existing 250 ms wait and shared 24-second budget. Accepted or stale completion permits an exact CAS clear.
Unavailable or unknown completion retains the slot and suppresses new wakes only
for that shard. The circular shard cursor must continue through healthy shards.
Never overwrite a different ticket, or let an old callback clear a newer slot.
Retain a known ordinary completion in the same slot when its finish acknowledgement
is unknown. A local coordinator storage failure stops that invocation and preserves
its memory fallback; remote work cannot safely progress without local checkpoints.

Acceptance needs actual workerd/SQLite controls for late unavailable results and
rejections, durable restart, stale completion versus newer tracking, completion
ACK loss, local persistence/clear failure, per-shard backpressure and healthy-shard
progress. Existing failure saturation, attention, backoff, call/page/time bounds
and full cleanup checks remain required. This selects component work only; it
does not activate production scheduling or qualify a provider or deployment.
