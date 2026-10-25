# Existing ticket headroom observations

This supplement compares immutable snapshots already collected by the unchanged
original harness. No target, compiler, oracle or instrumentation is rerun. The
first result report, receipt and seal retain their bytes; the final seal binds
this supplement and the preserved predecessor `result-seal-initial.json`.

| Existing phase snapshot | Before resident index: live / peak tickets | After resident index: live / peak tickets | Resident cache entries before / after | Unused ticket capacity before / after |
| --- | ---: | ---: | ---: | ---: |
| Constructed | 21 / 21 | 22 / 22 | 0 / 0 | 65 / 64 |
| Initialize complete | 85 / 85 | 86 / 86 | 64 / 64 | 1 / 0 |
| First typed failure | 85 / 86 | 86 / 86 | 64 / 64 | 1 / 0 |

The source-backed persistent accounting delta is one buffer ticket. The frozen
before cache has three buffer-ticket slots; the integrated cache has four. Its
new `buffers[3]` admits the 192-byte resident-index vector before reserving and
initializing that vector. The original shared ticket admission implementation and
`MAX_RESERVATION_TICKETS = 86` are byte-identical before and after integration.
The constructor and completed Initialize observations each increase by one live
ticket. At the new completed Initialize snapshot the entire 86-ticket inventory
is occupied. These are observed snapshot counts and a source-supported allocation
delta; they do not identify the actual next requesting ticket owner.

The earlier failure is CacheWork exhaustion at 12,971,689 guest instructions,
64,000,000 cache work, seven frames and eight active pins. The new failure is
TicketInventory exhaustion at 6,555,490 guest instructions, 31,475,443 cache work,
12 frames and 12 active pins. These are different execution prefixes. The failure
snapshots cannot establish a performance improvement or equal-prefix ticket
behavior. The current failure cursor is Invocation, function 79,548, source offset
15,881,589; the unchanged observer emits no requesting reservation category,
owner identity or requested bytes. Its 87th ticket request therefore remains
unattributed. The failed admission does not create the refused ticket.

The existing new run's final consuming snapshot still has all current reservation
and live categories/tickets at zero, with no cleanup invariant. This supplement
does not select a repair, expand the ticket limit, alter accounting or qualify a
new full-target run. Any fixed-storage or ticket-headroom diagnosis is separate.

`ticket-headroom-observation.json` binds exact old/new event hashes, snapshot
values and frozen source excerpts. Check this observation read-only with:

```sh
python3 -B verification/swift-exact-reactor-after-resident-index/verify-ticket-headroom.py
```
