# Root cache control prerequisite

This bounded prerequisite adds private observation and ownership seams over
bd8a896. It does not implement or approve a cache/executor or target execution.

Existing `work`, `admit`, `admit_cache_entry`, `enlarge_construction`,
`exact_capacity`, `add_live`, `remove_live`, `drop_proof` and
`end_construction_phase` retain their signatures and delegate `None` to additive
`*_with_wasi` variants. The latter append `Option<WasiUsage>` and carry it through
every potentially failing preflight, including terminal cleanup. No control field,
layout, authoritative counter, admission order or old diagnostic changes.

`check_adopted_owner(&AdoptedProof, Cursor, Option<WasiUsage>)` borrows/checks both
original source and metadata tickets before cache effects. It never consumes,
admits, refunds or recreates a proof. The eventual consuming cache API must return
a rejected owner intact; this precondition does not supply that future wrapper.

`reservation_owner_matches(&ReservationTicket) -> bool` checks only exact nonzero
control identity; it grants no work, reservation or refund. AccountedWasi's new
`checked_usage(&self, &mut RuntimeControl, Cursor)` first uses this exact identity
to decide whether an observation belongs to the control, then performs the full
existing reservation check. A same-owner accounting invariant retains actual
context counters; foreign identity or a missing header has no attributable WASI
observation. Successful access returns the actual context's current usage.
Checks spend no work, allocate nothing, and do not inspect cancellation/deadline,
so consuming terminal cleanup can validate its pair. Existing dispatch semantics
and all stored owner layouts remain unchanged.

Tests exercise actual context dispatch before observed resource failures, all
new preflight/cleanup seams, first-cause preservation, owner mismatch, actual
storage destruction before refunds, paired observation under terminal state,
and private invariant corruption only under cfg(test). This is logical requested
storage accounting, not RSS or compiler stack measurement. Full target execution,
physical devices, published consumers and GA remain pending.
