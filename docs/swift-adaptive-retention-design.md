# Proposed bounded adaptive retention for the owned Swift interpreter

This packet specifies one new, **unselected** candidate. Root has withheld
implementation selection after the finite model exposed its costs. This is not
a VM implementation rejection or a full-target result. The live closure supplied for this task is
`16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd`.
The unchanged original target still fails CacheWork after 23,358,291 guest
instructions. The rejected segmented LRU and cost/age packets remain rejected;
this proposal does not retune or restore either implementation.

The candidate uses adaptive recency/frequency classes and bounded eviction
history. A resident hit adds **four fixed logical credits**, one point update,
and no scan, list relink, allocation, ghost lookup, or ticket. It retains the
existing `last_used = work_used()` timestamp publication. Its costs and benefits
on the actual target remain unknown. Root must authorize a separate bounded
candidate implementation before any product source is changed.

## Source and algorithm boundary

The general algorithm source is Megiddo and Modha's original
[FAST 2003 ARC paper, Figure 4 and section IV](https://www.usenix.org/legacy/events/fast03/tech/full_papers/megiddo/megiddo.pdf).
ARC separates recent and repeat-used residents, retains nonresident identities,
and adjusts a recency target from history hits. The paper assumes equal-sized
pages. This proposal is Mixer-authored and **ARC-inspired**, with explicit rules
for variable decoded sizes, pins, failed builds, and bounded history. Its ring
history is different from ARC's directory/list trimming; ARC's bounds or empirical
results are not evidence for this candidate. No source implementation or external
algorithm dependency is introduced.

Only the live cache modules, their existing finite trace fixture, and the two
rejection documents were consulted. No hosted catalog inspector, authority
driver, WorkerV2 lane, competitor implementation, native instance, restored
scratch, dependency fetch, or full target was used.

## State and invariants

Let `c = slots.len()`, where `0 <= c <= 64`. The configured ceilings remain 64
residents, 64 pins, 86 reservation tickets, 16 MiB cache, 8 MiB entry, 64,000,000
CacheWork and 256 MiB combined reservations. Capacity zero still fails admission
through the existing earlier capacity path.

Proposed private `#[repr(C)] SwiftAdaptiveRetention` fields, in this order:

| Field | Type | Expected offset / bytes on the current 64-bit host |
| --- | --- | ---: |
| `frequent_residents` | `u64` | 0 / 8 |
| `recent_ghosts` | `u64` | 8 / 8 |
| `frequent_ghosts` | `u64` | 16 / 8 |
| `ghost_functions` | `[u32; 64]` | 24 / 256 |
| `ghost_heads` | `[u8; 128]` | 280 / 128 |
| `ghost_next` | `[u8; 64]` | 408 / 64 |
| `next_ghost` | `u8` | 472 / 1 |
| `target_recent` | `u8` | 473 / 1 |
| trailing alignment | padding | 474 / 6 |

The expected size is **480 bytes**, alignment eight. These are specified layout
values, not measured Rust implementation evidence. A future implementation must
measure every field and transitive owner/inventory enlargement before admission.

The resident mask identifies the repeat-used class T2. An occupied slot whose
bit is clear belongs to T1. Empty and out-of-capacity bits must be clear. Pins
do not change the class or recency. Existing decoded owners, proofs, slot keys,
pin nonces, tickets and resident hash index remain authoritative.

Ghosts contain only function indices and class tags B1/B2. The two ghost masks
must be disjoint, have no bits above `c`, and contain no resident key or duplicate
key. A zero tag means inactive; its stored function is never trusted. Every
active cell appears exactly once in its correct ghost bucket. Links encode cell
index plus one; zero terminates a chain. The fixed hash is the existing integer
hash with 128 buckets. A complete bucket walk validates bounds, activity, key
hash, uniqueness and cycles using a local `u64 seen` mask; it never stops early
on the first match. At most `c` nodes may be visited. This is a bounded adversarial
lookup, not a worst-case constant-time hash claim.

`next_ghost` points to the next ring cell to overwrite. Every completed eviction
adds one history event there, first unlinking an active old ghost, then inserting
the evicted function with its old resident class. Advance by checked `+1`; reset
to zero only at exactly `c`. Admission removes the matching incoming ghost when
present. Removing a ghost leaves a hole; it does not move the hand. Thus history
remembers at most the last `c` **evictions**, possibly fewer identities after
admissions. There is no unbounded counter, timestamp, list or allocation in
history, and no hidden larger history when the ring is sparse.

## Exact policy

Preserve all existing function, nonce, pin-slot, pin-admission, scan/count,
entry-size and base-capacity failure precedence. In particular, 64 held pins
normally fail at pin-record exhaustion before replacement is considered.

On a resident hit, validate the touched timestamp is at most the current checked
work snapshot, precharge the four-credit block, prepare the T2 bit, and perform
the existing cancellation/overflow checks before publication. Publish the T2 bit
with the existing hit/pin/timestamp/nonce bundle, with no fallible operation
between these mutations. Already-T2 hits pay the same complete block. No other
resident's timestamp is inspected on a hit.

On an admissible miss, inspect the original ghost state once. Let `b1` and `b2`
be mask population counts before any eviction for this miss. Compute one local
target `p'` from the original target `p`:

- Original B1 hit: `p' = min(c, p + max(1, floor(b2 / b1)))`.
- Original B2 hit: `p' = max(0, p - max(1, floor(b1 / b2)))`.
- No original ghost hit: `p' = p`.

The denominator is nonzero by the matched tag. Use checked `u16` intermediate
addition/subtraction and explicit clamp; no float or saturating wrap is needed.
Do not apply this update again for extra victims. Admission from either original
ghost class enters T2; a new key enters T1. The classification is saved even if
this miss's evictions overwrite the incoming ghost.

For each required victim, count T1 among all occupied, not-yet-selected slots;
include pinned slots in that count. Prefer T1 if its count is greater than `p'`,
or if the original event was B2 and its positive T1 count equals `p'`. Otherwise
prefer T2. Scan slots in ascending slot order, considering only occupied,
unpinned, not-yet-selected members of the preferred class. Select the least
`last_used`; equality keeps the lower slot. If no such slot exists, scan once for
the other class with the same rule. If neither has an eligible slot, fail at the
existing all-pinned boundary before any eviction. Pins are never moved, erased,
demoted or treated as feedback. Extra byte-pressure victims use the same saved
`p'` and original event, with already selected slots excluded.

At the initial read-only slot pass, validate every occupied timestamp against one
fixed current-work snapshot and derive the occupancy mask. A future value or
invalid class bit fails before resident mutation. There is no timestamp
subtraction, age rank, rebase or new policy clock. Existing work arithmetic must
continue to fail on checked overflow/exhaustion, never wrap. Ring wrap is an
explicit finite-index operation, not timestamp wrap. Ties remain deterministic
even if a synthetic fixture supplies equal timestamps.

Retain the existing destination choice: lowest initially empty slot when no
victim is necessary, otherwise the last selected victim slot. Actual byte counts
come from the validated decoded entries, never ghost records. Memory pressure
and per-entry admission remain hard constraints.

## Prepare, eviction commit, admission commit

The cache cannot promise preservation of all old IR on build failure: the new
entry may require evictions to fit under 16 MiB. The following three stages are
the contract, rather than a claim of whole-miss rollback.

1. **Read-only prepare.** Precharge and copy the 480-byte retention state to a
   named shadow (60 eight-byte logical copy cells). Plan the complete victim
   order, simulate every ghost overwrite/unlink/insert in that shadow, and prepare
   typed deltas. Prepare the final incoming-ghost removal, T1/T2 bit and `p'`
   publication in the shadow after the simulated evictions. Validate all touched
   hash chains, link cells, ring indices, checked arithmetic, counters and full
   policy work before any live resident mutation. A rejected plan, all-pinned
   outcome, cancellation, work failure or malformed touched metadata discards
   the shadow/deltas; live retention and residents remain unchanged. Existing
   sticky work/miss observations and scan-plan publication retain their original
   behavior. No global hash audit is claimed for unreachable, untouched corrupt
   cells; reachable-state preservation and targeted corruption controls are
   required.
2. **Per-victim commit.** Existing resident-index removal may still fail before
   its own mutation and must retain its precharge contract. After it succeeds,
   take the resident, apply that victim's precharged ghost/class delta and account
   its actual eviction as one infallible metadata/ownership bundle. Then consume
   the detached owner and ticket through the existing cleanup path. No new
   cancellation, work charge, allocation or policy validation belongs inside this
   bundle. An error after earlier committed victims leaves exactly those
   evictions and their ghosts. It leaves the original target unchanged and does
   not remove the attempted incoming ghost except when actual ring overwrites
   have aged it out. Cleanup faults stay sticky; the detached owner must still
   have one named owner and consuming cleanup. The implementation must reconcile
   usage/live/ticket counters on injected cleanup faults; the current generic
   fallible drop order is not evidence this new bundle already exists.
3. **Admission commit.** Run the existing build/admit/publication checks and
   resident-index insertion. On failure, consume any new entry/ticket, clear
   construction accounting, abandon the provisional pin, discard the prepared
   success delta, and retain completed evictions only. On successful index
   insertion, immediately apply the already-prepared incoming ghost removal,
   target and resident class delta with resident/usage/pin/nonce publication.
   Nothing fallible may intervene. Single-owner mutable borrowing prevents a
   concurrent retention change between prepare and commit. This invariant must
   be enforced structurally, not assumed across callbacks.

Preparation can inspect and charge shadow operations incrementally because the
shadow is disposable. All live retention writes, including the eventual success
delta, are prepaid before stage two. If an existing resident-index hook fails
later, unused prepaid credits are not refunded. The generic baseline's
`CacheMode` path, failure observations, allocation trace and work totals must
remain unchanged. A private Swift hook/specialization may implement these stages;
default no-op hooks are acceptable only with exact generic differential receipts.

## Logical work schedule to freeze before implementation

These are authored logical operation groups, not machine-instruction counts.
Charge before each read/validation group and precharge every complete live-write
block before its first write; charge the full block on failing paths. Keep all
unchanged baseline work and decode work. Do not count these costs as measured VM
CacheWork until implemented and independently checked.

| Added operation | Credits |
| --- | ---: |
| Every resident hit: slot-bit/timestamp validation, class read, prepared class value, eventual class write | 4 |
| Constructor: three masks, ring hand, target, 64 key cells, 128 heads, 64 next links | 261 |
| Miss shadow copy: all 480 bytes, including padding | 60 |
| Miss scalar preparation: capacity/mask checks (4), snapshot (1), two population counts (2), saved ghost event (1), ratio/clamp preparation (4), prepared target/class publication values (4) | 16 |
| Each ghost lookup: hash and head | 2 |
| Each visited ghost node: encoded bounds/cycle/activity, actual key, actual key-hash, next read | 4 |
| Every initial occupied timestamp validation beyond existing slot pass | 1 |
| Per preferred/fallback victim scan: each slot's class test beyond existing eligibility work | 1 |
| Per victim: preference/count/selected-mask preparation | 4 |
| Each ghost overwrite simulation: old/new cell preparation, mask clears/sets and ring advance preparation | 8 |
| Live ghost overwrite/class commit block, even if overwrite was inactive | 10 |
| Final incoming removal preparation | 4 |
| Final live success delta: two ghost masks, ghost unlink/next clear, target, resident class | 6 |

An old active ghost needs an additional bounded ghost lookup to prepare its
unlink. Add a new-key ghost lookup before each simulated insert to prove absence;
duplicates fail closed. Final incoming removal uses the shadow lookup result,
so it adds its own `2 + 4*n` lookup. Shadow link updates are charged separately
at two cells for unlink and two for insert; the live ten-credit overwrite block
covers the prepared live equivalents. A missing old ghost, cycle, wrong key hash,
duplicate or out-of-range link fails during preparation. No per-hit work is
hidden in miss charging. No 64-slot resident promotion scan is permitted.

This schedule deliberately exposes costs that could outweigh saved builds. In
particular, a normal 256-hit finite trace would add 1,024 credits to the current
2,048, a **1.5x** hit-work ratio before any integration difference. Ghost
collision chains and multiple byte-pressure victims can make misses expensive.
Retain adversarial collision and pinned fallback controls rather than claiming
the common hash case as a hard bound.

## Named memory and ticket contract

Keep the 480-byte state inline in `SwiftFunctionCache`, under its existing header
ticket. No new buffer or entry allocation and no new ticket is proposed. Add an
explicit state borrow to `SwiftScratch`; do not put metadata in spare bytes of
the current resident index, plan cache, pins, patches or owners.

The new prepare objects are separate named storage, with specified `repr(C)`
layouts (expected sizes below require measurement):

| Object | Explicit contents | Expected bytes |
| --- | --- | ---: |
| `GhostDelta` | three `u64` post-masks; `u32 function`; eight `u8` values: cell, unlink link-cell, unlink next, insert bucket, insert next, next hand, unlink flag, reserved | 40 |
| `VictimDelta` | `GhostDelta`, `u8 resident_slot`, seven reserved bytes | 48 |
| `SuccessDelta` | three `u64` post-masks; eight `u8`: removal cell/link-cell/next/flag, new target, destination slot, class, reserved | 32 |
| `PreparedRetentionMiss` | `[VictimDelta; 64]`, `SuccessDelta`, `usize count`, `usize destination` | 3,120 |
| `retention_shadow` | one complete state copy | 480 |

The ghost unlink link-cell encoding is 0..127 for a head or 128..191 for a next
cell; flags distinguish absent unlink. Do not overload an out-of-range sentinel.
Each delta must be fully initialized before reading or committing it.

Add a dedicated `RetentionInventory` with a **distinct field for each actual
named binding** in the nonrecursive helper chain: the complete shadow; complete
prepared miss; current `GhostDelta`, `VictimDelta`, `SuccessDelta`; source and
mutable state borrows; slot-slice and mutable-slot-slice borrows; meter, scratch,
prepared-miss and shadow reborrows; ghost function and tag; ghost head/node/next;
ghost index, bucket and link-cell; seen/active/occupied/selected masks; slot bit;
snapshot; both ghost population counts; old/new target and checked ratio
intermediates; class/preference flags; two oldest `Option<usize>` candidates;
victim/destination/count indices; checked work/counter/byte intermediate Options;
both slot/hash loop ranges; array initializers; each helper's result and
caller/return transfer. Give separate fields to repeated bindings, not one
maximum-size union. A field/offset report must map every binding and return type
to its field. Missing bindings require expanding the inventory before execution.

Admit **three disjoint complete `RetentionInventory` copies** in the operation
envelope. They cover source, argument/return and caller transfers in addition to
existing inventories. The new construction inventory separately covers the
inline state's initializer/constructor argument/return copies and initialization
loop locals. The permanent header calculation must remeasure all changed owners,
including the existing three `Option<SwiftFunctionCache>` transfers, two whole
cache transfers, three `SwiftScratch` values, and three `CacheParts` values.
The six whole state owner/transfer instances alone add 2,880 bytes; this is a
lower bound, **not the final fixed reservation delta**. Remeasure every changed
existing construction/operation/generic inventory containing scratch or parts,
including padding and Results. Charge their full checked sums to cache and
combined reservations before creating the named values. Never reuse existing
inventory slack or describe these figures as physical stack/RSS/allocator proof.

Enlarge the existing construction/operation reservation ticket through its
existing checked admission path; shrink/consume it at the existing phase and
cleanup boundaries. Source, validator, decoded payload and pin tickets keep
their existing ownership. The 86-ticket ceiling is unchanged. Constructor
failure, every prepared-prefix failure, every partial eviction/build failure,
and consuming cleanup must end with the appropriate zero ledger and no lost
owner. The final byte totals, field inventory and ticket peaks are mandatory
candidate evidence; this design packet does not claim them measured.

## Bounded model observations and selection gates

The Python model in
[`verification/swift-adaptive-retention-design/model.py`](../verification/swift-adaptive-retention-design/model.py)
executes the policy decisions with unit-size entries except its explicit
multi-victim test. It uses Python dictionaries/lists, request ordinals for
recency, and direct ghost search; it does not model the proposed ghost index,
Rust layout, work schedule, decoder or VM. Its 17 checks cover eight capacities,
zero admission, held-pin/multiple-victim behavior, pre-mutation rejection,
failed build with preserved original feedback, all pinned, future recency,
checked timestamp exhaustion, slot-order ties and phase turnover.

Measured trace interval counts exclude warm-up for both policy models:

| Finite access sequence | LRU model decodes / hits | Candidate model decodes / hits | Estimated added policy credits | Policy-cost coverage per avoided decode |
| --- | ---: | ---: | ---: | ---: |
| Original hot 16 / stream 128, four rounds | 576 / 0 | 512 / 64 | 124,104 | 1,939.125 |
| Cycle of 65 keys, three rounds | 195 / 0 | 163 / 32 | 32,844 | 1,026.375 |
| Expensive hot / cheap cold, same mixed trace | 576 / 0 | 512 / 64 | 124,096 | 1,939 |
| Cheap hot / expensive cold, same mixed trace | 576 / 0 | 512 / 64 | 124,096 | 1,939 |
| Uniform hot / cold, same mixed trace | 576 / 0 | 512 / 64 | 124,096 | 1,939 |
| Expensive old 16 to twelve cheap cycles of a new 64 | 64 / 704 | 104 / 664 | 22,856 | Adds 40 decodes |
| 256 resident hits after filling 64 | 0 / 256 | 0 / 256 | 1,024 | No avoided decode |

The first shape's existing engine report includes 16 warm-up decodes; its
592/528 total comparison is consistent with this model's 576/512 interval.
The three expensive/cheap/uniform variants share the same access sequence and
therefore the same policy decisions; their different decode work is **not**
modeled. The phase change adds 40 model decodes and reaches target 64; it does
not retain the stale old set forever. These observations neither prove net work
benefit nor establish a runtime regression bound.

The estimates charge only the added policy schedule on valid reachable states,
including the shadow copy, per-occupied timestamp checks, complete-bucket
occupancies, preferred/fallback class scans, ghost edits and hit blocks. They
exclude existing VM lookup, index edits, decode/build work, reservation/cleanup
work and elapsed time. Coverage divides that added policy cost by avoided
decodes; it is not a full CacheWork forecast. The model's dictionaries and direct
search do not execute or validate the proposed ghost hash links. Constructor and
warm-up costs are excluded from the trace intervals. The unchanged constructor
would gain the specified 261 policy credits as well.

At the original failure's supplied 537,576 resident hits, four additional credits
would cost **2,150,304 credits**, or **3.35985% of the entire 64M budget**, before
counting any miss overhead. The supplied repeat-build attribution gives
34,500,496 / 61,142 = 564.268 mean credits per repeated build. At that mean, about
3,811 avoided builds are needed merely to pay for this hit charge. Hot/stream
model coverage near 1,939 credits per avoided decode is much higher than that
mean. Candidate hit counts and saved-build identities on the original target
are unknown, so this is sensitivity analysis, not a target extrapolation.

Root has therefore **withheld implementation selection**. The packet is frozen;
there is no retuning, live candidate, full-target authorization or performance
qualification. If root later selects this precise proposal, a separate isolated
implementation and finite rejection gate needs exact
generic differential tests; 256-hit work/allocation receipts; all ghost collision
and corruption boundaries; reference victim orders across capacities and equal
timestamps; pinned fallback and variable-size multiple victims; every new work
prefix and cancellation boundary; allocation/live/ticket/build failures; layout
and named-inventory reports; and all six unchanged finite work traces. Reject
without retuning if those costs do not justify the candidate. A subsequent
full-target selection requires independent review and the original unchanged
budgets/harness. No model result authorizes that run or any live integration.

No physical device, simulator/emulator, full target, signing, store, operational,
published FieldLog-package, customer or GA gate was attempted or passed here.
