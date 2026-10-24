# Remaining SL13 ticket assertion repair; not implemented

The first V2 Swift Debug run has 22 passing identities and one failure. All SL09
constructor/initializer exact diagnostics passed. In SL13, cache work
605/1803/4196/4206, warm +4/+6, hits +2, unchanged misses/decodes/evictions/resident
bytes/active pins and **second-call tickets equal first-call tickets** passed.
The next, inherited assertion compared second-call tickets to immediately after
Initialize and failed: 24 versus 22. The deadline assertion and explicit `retire`
following that failed assertion were not reached. Runtime acceptance is false.

The independent ownership trace explains the difference:

1. `cache.rs::SwiftMode::build` admits exactly one Cache ticket through
   `admit_cache_entry_with_wasi`, increments `Live::CacheEntries`, then stores the
   actual ticket together with the decoded payload inside `SwiftResident`.
2. `borrowed.rs::pin_acquired` scans before building. A miss builds and publishes
   into its first empty slot; a hit only references the existing resident.
3. `borrowed.rs::release` clears the original pin record and decreases pin counts
   and pinned usage. It does not remove the resident or refund its Cache ticket.
4. The actual ticket is refunded only on entry eviction/failure or whole-cache
   cleanup, which consumes each resident payload and its ticket together.

The fixture first decodes 35 during Initialize, then 62 and 36 during the first
corpus call. All three stay resident. The second corpus call hits 62/36 and adds
none. This predicts **ticket deltas +1, +2, +0**, and live cache entries
**0→1→3→3**. These are source-derived counts of actual admissions, not expected
values changed to match the observed 24. If T0 is the original post-construction
ticket snapshot, the required sequence is T0, T0+1, T0+3, T0+3.

Proposed future source delta: only the body of
`swift_lifecycle_sl13_cumulative_instruction_host_and_cache_usage` in
`lifecycle_tests.rs`. Replace the invalid second==initialized comparison with
the exact cold deltas above. Keep second==first, passing work/hit/resident checks,
the original deadline assertion, and actual consuming `retire`. Add no helper,
import, hook, other test or engine change. Every other source byte, production
lifecycle/growth/accounting declaration, type/layout/formula, limit/ticket maximum
and Frozen method must remain exact. No new accounting credit is proposed.

Root must select a new isolated candidate and fresh source/compiler/position proof
before runtime. All V2 source, accepted finite/occurrence proofs and this failed
run remain immutable. No failed test was rerun. Other three focused contexts and
all broader regressions were stopped and remain unrun. Full original matrix gaps,
including guest table mutation, remain open.
