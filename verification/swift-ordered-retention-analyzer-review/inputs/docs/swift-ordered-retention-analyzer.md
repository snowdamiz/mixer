# Bounded offline ordered-cache analyzer contract

This is a concrete **design contract for root and independent review**, not an
implemented analyzer, a selected target driver, or workload acceptance. The
finite Python oracle and standalone Rust layout probe support only the cases
they execute. Implementation follows a separate selection after this contract's
types, boundaries and algorithm have been reviewed. No live VM/Cargo/dependency,
production policy, old packet or root execution metadata changes here.

The binding product scope remains `mixer-product-plan.md`. This slice diagnoses
the owned Swift interpreter; it cannot close its compiler, native, signed-update,
store, FieldLog, customer, operational or accountable GA gates. Computer use,
capture and native simulator/emulator execution remain paused; phones remain
disconnected. No native or process discovery, target execution or new policy is
part of this packet.

## Authority and acceptance layers

The accepted diagnostic proposal and its independent review define intent. The
actual closed wire is the frozen `writer.rs`, `observer.rs`, source-code table
and copied cache/control source in the original Rust packet and completion
candidate. Those implementations take precedence over provisional schema prose.
The original seal is
`c19bd3fb06e2db11a5e6ecb5aad8de2ca6ee19a35e50a5ba691ecb598bde40bf`
(186 members); completion seal is
`2e427447a34357ab4ff70eb220f56754f685a930edf4a89ebc29096fff3b73ba` (222 members);
the completion candidate's 132-file manifest is
`007ba0dc9aaac2402cbf49d08ffaf8a1e2f75e5813ba4996e4936be4d0a92357`.
The packet's input receipt verifies those identities and snapshots the exact
consulted source. Root now accepts selected finite completion with independent
review seal `87a6fe21fd5c8f6590992aae8cc826e2502454686cf0d7a8c550acb7965827cc`
(158 members), as recorded in
`verification/swift-ordered-retention-diagnostic-completion-root-review/acceptance.json`.
Its independent19-phase inventory16,186/16,384 supersedes provisional16,114;
the51,712-byte named-role union is not a simultaneous peak. This contract grants
no wider acceptance and inherits all remaining replay/driver/code-coverage gates.

Every one of the completion packet's 17 new stream sidecars remains immutable
`invalid`/failure15. A future analyzer creates new evidence. It cannot rewrite
them or declare their historical classifications successful. In particular,
unknown release/refund codes set CODE; CODE prevents a partial writer buffer
from flushing. The release cases claim stored9 but serialize zero ordinary
records, so exact physical length rejects them. The synthetic foreign-ticket
case retains actual EvictTaken at record32, lacks its Commit, preserves the
original refund failure and a foreign owner's one-byte/one-ticket quarantine;
it remains CODE-invalid. No corrective writer is selected here.

There are three separate future results:

1. Rust `ReplayOutcome` validates only the stored semantic prefix and emits a
   fixed candidate report. It has **no authority to set fullReplayAccepted**.
2. A separately reviewed Python standard-library custodian verifies actual
   hashlib digests, exact retained-descriptor custody, selection/source/compiled
   analyzer identity and the authoritative original-result adapter before and
   after replay. Rust stdlib has no SHA-256 API; no new crypto implementation or
   dependency is proposed. Supplied digest bytes alone verify nothing.
3. A new bounded host acceptance receipt joins both immutable records. Only
   complete validation of every stored record, frames, context, original result,
   lifecycle and custody can set `fullReplayAccepted=true`. Flags0 can then yield
   `complete-records`; CAP1 can yield only `truncated-prefix`. Neither means the
   guest workload passed or later uncaptured transitions are known.

## Proposed API and trusted input prerequisites

The future standalone first-party Rust executable uses only std. Its narrow
library entry point is conceptually:

```rust
fn analyze(stream: &mut File, profile: &mut File,
           binding: &VerifiedBindingView, output: &mut File)
           -> Result<ReplayOutcome, AnalyzerError>;
```

`VerifiedBindingView` is a checked borrow into an 8,192-byte fixed context region;
the name describes the required host adapter, not trust granted by a Rust type.
`ReplayOutcome` is at most256 bytes: fixed integer enums/counters, accepted record
coordinate, stop/error coordinate, observed flags/masks, stream/header/context
digest echoes and the report length. It contains no String, Vec, error text or
function list. `AnalyzerError` is a fixed `{code:u32, stage:u32, offset:u64,
record:u64}` with reserved-zero padding to32 bytes. Error coordinates describe
observations; they never replace an original operation Result.

Before implementation acceptance, a reviewed strict host adapter must provide:

* A canonical closed selection record, at most4,096 bytes, bound to all132
  baseline and candidate file lengths/hashes, exact patch, schema, compiler and
  analyzer executable hash/version, original harness/parser/argv/environment,
  target length/hash and unchanged limits. The record contains fixed digest
  fields and scalar lengths/limits, no event-growing list. Its external full
  source manifest is immutable and independently verified by the host.
* A canonical original-result binding at most2,048 bytes and the exact raw
  original-result bytes (maximum8,192 in a newly selected driver). The adapter
  must strictly parse its supported original-result schema, reject extra fields,
  bind its complete raw hash and expose terminal success/failure, kind, static
  source-code ID, stage, optional cursor, at-failure work/instructions, final
  work/instructions, all15 final reservation/live/ticket words and cleanup enum.
  It preserves other original fields and their raw bytes. No regex-only Debug
  parser or copied observer classification qualifies this dependency. Fields
  intentionally absent from the stream, such as original failure cursor offset,
  remain original-result observations, never purported wire comparisons.
* At most2,048 bytes of closed custody and invocation records. Context storage
  is exactly selection4096 + original2048 + custody2048; unused bytes are zero.
  All adapter versions, lengths and digest offsets are frozen with its separate
  implementation review; an unsupported adapter is `BindingUnavailable`.
* An immutable fixed profile: 512-byte closed header followed by exactly80,000
  32-byte rows, `defined:u32,type_index:u32,body_offset:u64,body_len:u64,
  reserved:u64`, total2,560,512 bytes. Defined is0/1. Undefined rows require
  type_index=MAX32, offset=MAX64, len=0 and reserved=0; defined rows require
  type_index<selected type_count<=MAX32, finite offset/len, checked end within
  selected source extent, reserved0. Imported/out-of-range functions are not
  invented as defined bodies. The header binds profile version, extent,
  type_count, baseline/candidate/input/profile-generator digests and zero padding.
  It contains no final selection digest, avoiding a cycle when the canonical
  selection binds the complete profile hash. First16 u64 are magic `MIXPRF01`,
  version1,header512,row32,rows80000,source_extent,type_count,slot_limit,pin_limit,
  initial_nonce1,cache_base,cache_capacity,entry_limit,reserved0,reserved0,reserved0.
  Next eight32-byte digests are baseline,candidate,original_input,event_schema,
  profile_adapter_binary,layout_receipt,original_validated_snapshot and
  profile-row-body; last128 bytes zero. Host independently hashes both the
  complete profile and row body through its retained descriptor; embedded hashes
  alone verify nothing.
  A separately reviewed adapter must derive these rows from the original
  validated immutable snapshot, rather than learning authority from events.
  The profile also binds actual slot/pin limits(1..64), initial nonce1, cache
  fixed/base bytes, cache capacity and entry limit from the exact selected source
  construction/layout. Unknown base/layout fails closed; no guessed ABI size or
  first observed MissReady becomes trusted construction authority.

Those adapters and real selection binding are pending. The finite writer uses
synthetic digest bytes and fixture phase masks; even all phases63 cannot qualify
a real target. Missing prerequisites can still support clearly labelled finite
metrics, with `storedPrefixValidated=false` and no accepted classification.

## Arena, checked typed access and complete logical inventory

The ceiling stays **8,388,608 arena bytes plus65,536 complete named transient
bytes**, not RSS or compiler-stack memory. The future arena is one non-growing
`Vec<u8>`: call `try_reserve_exact(8_388_608)` once, refuse allocator failure or
capacity!=8_388_608, then initialize in place with bounded pushes/zero stores.
Do not construct `[Row;80000]` or a complete Arena temporary on the stack, use
`vec![huge_struct;N]`, realloc, unsafe uninitialized memory, mmap, collections,
serde, formatting allocation or a per-event map/list. Vec's complete24-byte
header and allocation/setup Results belong to transients. The backing allocation
is arena storage; neither layer is free.

The implementation uses typed checked wrappers over explicitly little-endian
byte regions, **not** Rust references cast into bytes. Every wrapper checks
`index<capacity`, checked `base+index*stride+field_offset+width<=region_end`, then
uses `get/get_mut`, a complete4/8-byte temporary, and from/to_le_bytes. No
transmute, pointer cast, unchecked index or assumption that byte storage has
Row alignment is permitted. An internal bounds/overflow failure returns a fixed
error and never accepts a partially committed record. The standalone repr(C)
probe verifies the proposed value layout on the selected64-bit Rust toolchain;
serialization still uses explicit offsets independent of native struct bytes.

| Region | Offset | Capacity/stride | Bytes |
| --- | ---: | ---: | ---: |
| FunctionRow | 0 | 80,000/96 | 7,680,000 |
| ResidentRow | 7,680,000 | 64/64 | 4,096 |
| PinRow | 7,684,096 | 64/48 | 3,072 |
| PlanRow | 7,687,168 | 512/40 | 20,480 |
| Distinct recency | 7,707,648 | 64/u64 | 512 |
| WindowRow | 7,708,160 | 128/128 | 16,384 |
| Histograms | 7,724,544 | 6x66/u64 | 3,168 |
| TopRow | 7,727,712 | 32/64 | 2,048 |
| Fixed scalar state | 7,729,760 | 512/u64 | 4,096 |
| Fixed context | 7,733,856 | 1/8192 | 8,192 |
| Input block | 7,742,048 | 1/65536 | 65,536 |
| Report workspace | 7,807,584 | 1/65536 | 65,536 |

Used7,873,120; spare515,488 stays zero and cannot become an expanding store.
Rows beyond selected native limits remain initialized and inaccessible.
Concrete offsets/types are:

* Function96: offset:u64@0,len:u64@8,type:u32@16,flags:u32@20,
  acquisitions:u32@24,builds:u32@28,plan_hits:u32@32,plan_conflicts:u32@36,
  last_window:u32@40,reserved:u32@44,scan_credit:u64@48,
  build_credit:u64@56,last_acquire:u64@64,last_work:u64@72,
  last_instructions:u64@80,partial_credit:u64@88. Counts cannot exceed the
  4,194,304-record cap and still use checked arithmetic. Flags0/1 means undefined/
  defined immutable profile. Undefined identity sentinels match the profile.
  Last_window startsMAX32; all counters/times start0. A defined row copies its
  immutable profile once; no event may change it.
* Resident64: eight u64 at offsets0..56: occupied0/1,function,bytes,pins,
  last_used,publish_acquire,generation,reserved0. Empty starts occupied0,
  functionMAX, other fields0. Body identity always joins its FunctionRow.
* Pin48: six u64: entry,nonce,operation,acquire,work,instructions. Free starts
  entryMAX and others0. A live row is the actual published token and immutable
  publication coordinates, not a new owner/ticket.
* Plan40: five u64: function,offset,len,type,requested_bytes. Empty is functionMAX
  and others0. Publication copies a complete immutable body identity. Bytes0
  means counts' byte result not yet observed; nonzero may be filled only by a
  later successful matching MissReady in that operation, then must agree on reuse.
* Recency64: function IDs or MAX tail, no duplicates. Windows16 u64: first_acq,
  last_acq,acquisitions,hits,misses,publications,builds,completed_evictions,
  taken_events,distinct_functions,first_global,reuse_ge64,scan_credit,
  build_credit,min_headroom,max_held_pins. Empty windows are zero except
  min_headroomMAX meaning unknown. Windows contain8,192 acquisitions; opening
  window129 stops before its AcquireBegin as `WindowCapacity`, never grows.
* Top64: eight u64: function,acquisitions,builds,plan_hits,plan_conflicts,
  scan_credit,build_credit,partial_credit. Empty functionMAX, others0.
* Scalar512 u64: first64 control/budget/file coordinates; next64 active operation
  (including open scan/build/failure/eviction and checked interval starts);
  next32 planned victim mask/destination/emission cursor and byte arithmetic;
  next24 lifecycle/result comparisons; next128 fixed report counters; last200
  reserved0. The exact512 word names and group boundaries are frozen in
  `interface_schema.py`; implementation proves no alias/overlap before acceptance. Spare words are not
  permission for additional capacity. Only one acquisition can be active.

Initialization zeroes all1,048,576 arena u64 cells, then installs explicit row
sentinels/profile in fixed loops. Scalar counters and masks are initialized
before reading the stream. A single2,048-byte candidate contains complete one
Function96/Resident64/Pin48/Plan40/Window128 copies, recency512, at most32 scalar
updates(256 bytes) and six histogram updates(48); all unused bytes remain zero.
That is1,192 named payload bytes inside its fixed owner. A state discriminator
guards inactive old operation fields; an acquisition never bulk-clears the
whole active region after initialization. Pure preflight builds
this delta without changing arena semantic state. Once every validation/check
and bound succeeds, no-fail checked writes apply it as one accepted-record
transition. Unexpected commit failure is internal invalidity, never an accepted
prefix coordinate. If a commit invariant is violated despite preflight, emit
only a fixed internal-error outcome with semantic metrics invalidated; do not
claim the partially written arena is the previous valid state. The previous
accepted coordinate remains historical, not authority to serialize that state.

The probe reserves disjoint transient groups: wire/decodes3072,
candidate2048, I/O4096, Metadata/Results4096, bounded paths/setup12288,
control/helper8192, report/error8192 = **41,984**, leaving23,552 unassigned under
65,536. Each group is a reservation, **not measured complete implementation
accounting**. The eventual inventory must enumerate every complete File/Metadata/
Result/error/Option/iterator, raw/decode/caller-return copies, Vec owner/allocator
Result, bounded path owner and argument, record candidate/moves, three nested
helper/borrow groups, report encoder/copies and error return against these exact
role capacities, with lexical phase lifetimes. No group may silently omit a
value or consume the unassigned margin without renewed review. Allocation,
capacity, setup or inventory failure refuses acceptance. Opaque Rust/Python/
hashlib/FileIO/allocator/kernel internals, optimizer copies, physical stack/TLS,
RSS and elapsed time remain separate unqualified costs.

## Exact wire checks

Frames are512 bytes; ordinary records128 bytes of16 LE u64:
`seq,kind,phase,op,work,instructions,function,offset,len,type,slot,pin_slot,nonce,a,b,c`.
MAX means absent **only** where specified; every unmentioned payload is0,
unmentioned slot/pin_slotMAX and nonce0. Each scalar is checked before narrowing.
Every full body must equal the immutable profile and fit the selected source.

| kind | Closed payload |
| --- | --- |
| 1 AcquireBegin | op=new nonzero, function<80000, offset/len/typeMAX; a/b/c0 |
| 2 Lookup | current op/full body; a0 miss with slotMAX or a1 hit with slot<selected slots; b/c0 |
| 3 PlanBegin | current op/full body; a/b0,c=function&511 |
| 4 PlanEnd | current op/full body; a0 empty/a1 conflict/a2 match; b=prior distinct function only for conflict, otherwiseMAX; c=function&511 |
| 5 MissReady | current op/full body; a>0 decoded bytes<=entry limit,b=bound fixed/base,c=bound capacity; checked b+a<=c |
| 6/7/8 EvictBegin/Taken/Commit | current op/full **acquiring** body; slot=victim<selected slots,a=victim bytes>0,b/c0 |
| 9/10 BuildBegin/Ready | current op/full body,a=requested bytes>0,b/c0 |
| 11 PinPublished | current op/full body; entry/pin slots within selected limits,nonce>0;a0 hit/a1 built,b=resident bytes>0,c=post pin count1..selected pin limit |
| 12 Release | op0,function/offset/type from actual checked resident,lenMAX; actual entry/pin slots and nonce>0;a=resident bytes,b0,c=post pin count0..63 |
| 13 Phase | op0,full identity absent; a=record phase,b/c0 |
| 14 Failure | op=current attempted pin or0 terminal; body absent,function=original optional cursor/MAX;a1..21 failure kind,b1..24 code,c1..6 stage |

Kinds1..14 only; phases0..5 only. Header words0..9 are
`MIXORDR1,1,512,128,512,cap,80000,64,512,expected_mask`, with cap1..4,194,304,
mask<64 and mask&33=33. Words10..15 and bytes256..511 are zero. Bytes128..255
are selection/schema/baseline/candidate digests and must equal actual accepted
host bindings. Byte magic is `MIXORDR1` (u64=0x315244524f58494d).

Footer words0..35 are `MIXOEND1,1,stored,attempted,dropped,last_seq,last_work,
last_instructions,last_op,flags,terminal_work,terminal_instructions,kind,code,
stage,observed_mask`, eight reservation currents16..23, tickets24, six live
currents25..30, cleanup31, original_result_kind32, final_phase33,
pre_footer_write_attempts34, cap35. Words36..43 are raw selection/schema digests;
44..63 zero. Magic u64=0x31444e454f58494d. Require stored<=cap,
attempted=stored+dropped checked, last_seq=stored, physical
length=1024+128*stored, matching cap/digests, flags<512, mask<64, phase<=5,
cleanup0..5, result_kind0/1, pre-footer attempts<=4,194,336 and terminal
work/instructions>=last stored coordinates. Footer count/last coordinates equal
the actual replay, including op0 when no acquisition occurred. Success is
kind0/code0/stageMAX/result_kind0; failure is kind1..21/code1..24/stage1..6/
result_kind1; code0 is structurally observable only with CODE128 and is invalid.
Wire attempt word is pre-footer; actual terminal-block attempts/result must
also match the accepted external writer receipt, not a guessed extra attempt.

Failure kinds in ID order: InvalidBudget,Cancelled,Deadline,Allocation,Adoption,
CategoryExhausted,CombinedExhausted,ResourceExhausted,FuelExhausted,WorkExhausted,
HostCallLimit,PinLimit,FrameLimit,ValueLimit,ControlLimit,DecoderMismatch,
UnsupportedEnvironment,GuestTrap,GuestExit,Wasi,Invariant. Stages1..6 are
Adoption,Cache,Initialization,Invocation,Wasi,Cleanup. Cleanup1..5 are
ReservationOwner,ReservationUnderflow,MissingConstruction,ConstructionBound,
LiveUnderflow;0 absent. Code IDs are the exact frozen24-name table. Unknown
code or unsupported original-result adapter is invalid, never remapped to a
similar failure. The source-bound implementation review must freeze code/kind/
resource/stage applicability from the copied source; broad enum range checks
alone are insufficient. The finite oracle deliberately does not claim this gate.

Flags are CAP1,IO2,CONTEXT4,BORROW8,RANGE16,OVERFLOW32,LIFECYCLE64,CODE128,GATE256.
Any bit>=512 or any bit except soleCAP is invalid. Flags0 requires dropped0,
observed_mask=expected_mask and final_phase5. SoleCAP additionally requires
stored=cap, attempted>stored and dropped>0, final_phase5 and observed=expected.
A shorter physical prefix, missing footer, overflow, loss of unflushed records,
unknown/reserved field or invalid record is invalid even with a custody hash.

## Streaming replay algorithm

Read the initial regular-file length; reject >536,871,936, <1024 or nonmultiple
ordinary framing. It determines physical record count N, not trusted footer
stored. Read header, N records and footer exactly once using the fixed arena
input block. The file, records and report never become an all-records list.
All counters, instruction/work coordinates and checked differences are u64;
successful work/instructions never regress. Rejected requested work is not
added. Sequence is exactly1..N; op increments exactly once at AcquireBegin and
only after prior success/failure; a failed pin prohibits another AcquireBegin.

Start phase0/mask1 with empty residents/pins/plans and nonce1. Phase records
strictly advance to<=5 with a=phase, no open acquisition, and no duplicate mask
bit. Normal events retain current phase. A complete lifecycle requires exactly
the selected mask and final phase5, not an inferred traversal. Cleanup phase
and a zero final consuming ledger never clear replay residents/pins/plans.

AcquireBegin establishes the only active operation, requested identity and
coordinates; counts actual attempted acquisition, computes last acquisition/
work/instruction gaps and distinct reuse from committed history. Failure may
occur before Lookup. Lookup verifies all slots for an immutable matching
resident, rejecting duplicate residents; miss requires no such resident. A hit
can only proceed to PinPublished or original Failure. A miss must have
PlanBegin -> PlanEnd -> MissReady before successful build/publication; failure
can end any partial stage. Missing transitions cannot be inferred from counters.

PlanBegin opens the scan successful-credit interval. PlanEnd checks the512-cell
direct map: empty outcome requires empty; conflict names its actual prior
distinct function; match requires equal function **and** offset/len/type.
Only successful empty/conflict scans publish a complete replacement; match
retains it. PlanEnd minus Begin work is credited as that actual interval,
including original policy/probe/check work. A failed open scan does not publish
a plan. A later Counts::bytes failure may leave a successful plan with unknown
requested_bytes; no imaginary count bytes are supplied.

At MissReady verify bound base/capacity, requested bytes, current resident-byte
sum and checked additions. Reconstruct the **actual baseline algorithm**:
choose first empty slot in ascending order; while none or base+remaining+bytes
exceeds capacity, scan all actual slots, exclude already selected/pinned/empty,
choose minimum `last_used` using strict `<` so equal timestamps keep lowest slot,
subtract that victim's bytes and replace destination with that selected slot.
The mask is an offline plan; it does not remove anything. If none eligible,
record the obstruction for an applicable original failure, never fabricate an
eviction. Original successful EvictBegin events occur **in ascending selected
slot order**, not selection order. Built publication uses the **last selected
victim**, even if an original empty slot existed; with no victim it uses that
first empty slot. Selected victim sets and order are immutable within the op.

EvictBegin requires the next planned selected slot and exact resident bytes,
pins0; before-Taken failure leaves the resident. EvictTaken removes it
immediately and marks pending taken; it does not increment completed eviction
usage. Commit must join that Begin/Taken then increments completed count/bytes.
Failure after Taken retains a removed resident and uncommitted removal; no
rollback, synthetic Commit, refund or zero quarantine is permitted. No build
may start until every selected eviction committed; an operation failure may
instead terminate any earlier prefix. Completed evictions before later failure
remain completed. Generic product index internals are not invented as wire
events; their successful source seam is checked at Taken/Commit.

BuildBegin requires the completed miss plan and requested bytes and opens its
successful-credit interval; BuildReady closes it. It is still a temporary owner,
not resident publication. Publication failure can follow Ready and leaves no
resident or token. PinPublished is the sole resident publication: built flag1
requires Ready and exact destination; flag0 requires the hit. It uses the first
free actual pin slot, exact current nonce, then increments nonce checked; no
failure path advances it. Resident pin count increases exactly one, and
`last_used=PinPublished.work`, from the source's `meter.work_used()`. There is
no analysis timestamp, instruction-count timestamp or age estimate. A complete
token row records the published nonce, never its successor.

Release has no dependence on last acquisition's op. Join exact pin_slot+nonce
to the live token, entry slot, immutable function/offset/type and resident bytes;
require lenMAX and exact post-release pin count. Clear only that pin row,
decrement its resident pins; preserve last_used. Stale/wrong-owner releases
have no success record. Refuse duplicate/stale token identities and pinned
victims. Held-pin intervals use the token's actual acquisition/work/instruction
start and its Release end; tokens still held at prefix end are censored, with
lower-bound intervals through the accepted coordinate.

A pin Failure closes the current attempted operation once with its actual
failure coordinates. A terminal op0 Failure is distinct, at most once, may have
absent or independent original cursor, and prohibits later acquisition. Both
must join the preserved original failure where the original first-failure
contract requires equality; borrowed kind/code/stage/function/work/instruction
fields are compared, not normalized. Construction/non-cache terminal failures
need no invented acquisition. Failure may legally end an open scan/build,
pre-Taken eviction, Taken without Commit, post-build pre-publication, or hit
before token publication. Preserve that exact stage; failure does not create
missing success events. Successful credit from each still-open interval to
at-failure work is reported separately from completed intervals, without adding
overlapping nested intervals into one disjoint total. Raw original result and
foreign-owner quarantine remain authoritative outside the replay state.

Footer comparison keeps **guest prefix state** (residents, tokens, pending
owners/eviction) separate from **actual original final consuming ledger**.
All15 final ledger words must match the original result. For accepted
complete-records, all currents/tickets are0 and cleanup invariant0, with exact
terminal failure/success match. Zero observations do not prove per-slot drainage.
For soleCAP, validate all stored transitions as an intact strict prefix; it may
end in any legal open stage, and its omitted tail is unknown. Its footer still
needs strict original-result/lifecycle/custody consistency, not a replay of
unrecorded transitions. No scalar footer closes an open guest interval.

## Step schedule and stopping semantics

The ceiling remains **268,435,456 authored Rust analysis steps**, distinct from
production CacheWork, CPU instructions, stdlib internals and wall time. Every
loop/scan/copy/initialization/report action below is charged; no unbounded work
is hidden in a comparator, decoder, iterator or formatting call.

* Initialize one8-byte arena cell:1 step (1,048,576 cells), including unused
  regions. Profile row decode/sentinel/init/check:8 fixed steps per80,000 rows.
  Fixed small-row initialization, context parsing, initial/final metadata,
  footer/error setup and final status fit an additional65,536-step allowance;
  implementation must enumerate it and refuse overrun.
* Input File read attempt:1, including Interrupted/short/zero/error. Each
  <=65,536-byte input block has<=32 attempts; error, overreported length or
  exhaustion stops it. Record slicing is borrowed. Fixed128-byte record work
  is **22 steps**, including one decode16-word batch, four closed-field groups,
  three sequence/coordinate/lifecycle groups, two immutable-profile groups,
  two FSM/payload groups, four metric/delta-check groups and six no-fail
  commit/finish groups. A fixed group performs at most16 scalar operations or
  one<=128-byte copy, with no data-dependent loop. Unneeded groups still debit.
* Each resident comparison, pin first-free comparison, recency comparison,
  recency shift, plan victim candidate comparison, report comparison/insertion
  or fixed report8-byte encode:1 additional step. Profile row body comparisons
  are included fixed groups. No sort; report top32 uses insertion into its fixed
  array, ranking descending completed(scan_credit+build_credit), then descending
  acquisitions, then ascending function ID. Every outer function row and each
  of<=32 comparisons/moves are charged. Every other fixed loop is charged by
  iteration; checked capacity fixes its maximum before entry.
* Reserve **3,000,000** of the total before replay for reporting/final footer,
  errors and output attempts. This covers80,000*(1+32)=2,640,000 top steps,
  fixed row/window/histogram/resident/pin scans, <=6,144 8-byte encodes for the
  49,152-byte report, its<=32 output attempts per block, and a separately
  enumerated remaining allowance. Unused report reserve is not returned to
  replay. Initialization/input reads use the remaining budget.

Before beginning any next record, require **8,192 available replay steps**.
This is a reservation check, not an8,192 charge; debit the actual explicit
stages/iterations. Maximum preflight is22 plus64 initial resident probes plus
at most64*64 victim probes plus bounded arithmetic/mask loops, below8,192.
Other kinds have less work (Acquire<=128 recency comparisons/shifts). No actual
event may exceed that constant: assert and refuse an implementation that does.
Since the whole event fits before semantic mutation, budget refusal happens
before the record and retains the last fully validated/applied prefix. The
current record is not half accepted; its candidate is discarded. Preserve
already spent preflight steps and the unmodified semantic state. Window-capacity,
report-capacity or any internal limit has the same conservative acceptance rule.

After budget stop Rust may drain only bounded remaining file bytes needed for
its already bounded descriptor framing; it performs **no semantic tail replay**.
Every read attempt still debits the separate pre-reserved maximum I/O allowance
of262,208 stream attempts plus1,312 profile attempts (32 per maximum block plus
bounded EOF probes); subtract this allowance from the total at setup rather than
borrowing exhausted replay credits. No record-sized unbounded tail buffer is
allocated. If even setup reserves cannot fit, return unavailable. A shorter
analysis report can be emitted if its own bound would otherwise fail. Budget,
capacity or analysis stop always yields `storedPrefixValidated=false` for the
whole stream and host `fullReplayAccepted=false`, never complete-records or an
invented successful tail. Prefix metrics have explicit scope N_accepted and
unknown semantic tail. A later malformed footer/custody failure overrides any
prefix observation's eligibility for classification.

Without executing a target, the accepted historical-count envelope gives
A599,204/M61,628/E61,564 and R=4A+5M+3E+8=2,889,656. A deliberately conservative
Rust arithmetic estimate is22R +128A recency +64A resident lookup +64A first-free
pin +64(M+E) planner probes +1,048,576 arena init +640,000 profile +3,000,000
report +263,520 reserved I/O +65,536 setup = **229,870,576**, leaving38,564,880.
It assumes that envelope and the stated stage schedule, not measured target
order or actual analyzer implementation cost. It excludes Python custody cost.
Failures/additional source checks may consume more; the full4,194,304 record cap
and window limit are **not** guaranteed full replay under this step budget.
Report a shorter analysis prefix rather than increasing any cap.

## Metrics and fixed output

Six66-bin u64 histograms are acquisition gap, successful-work gap, instruction
gap, distinct reuse, held-pin acquisition interval and resident headroom. Reuse
bins0..63 are exact;64 is prior-seen>=64;65 is first-ever (distinguished using
FunctionRow.last_acquire). Other histograms use0 for0, 1..64 for
1+floor(log2(value)),65 unknown. The fixed64-ID recency list never claims exact
distance>=64. Headroom is checked capacity-base-actual resident bytes at a known
state, with explicit unknown before a bound base is available; it is not a
live-ledger refund claim. Window distinct count uses per-function last_window;
turnover reports observed distinct functions and actual publications/evictions,
not an unbounded set. A held pin or open interval at prefix end is censored.

Report actual lookups/hits/misses, immutable plan hits/conflicts, completed scan/
build intervals and successful credit at partial failure separately, taken and
committed evictions/bytes, pin intervals/current held count, headroom and128
windows, plus top32 by the exact ranking above. All metrics arise from accepted
event endpoints; no elapsed-time inference, counterfactual policy, avoided-work
estimate, new limit or policy recommendation is smuggled into them. Selection
and source identity determine scope. Aggregate intervals with overlaps remain
separate rather than double-counted as total production work.

The Rust report is exactly**49,152 bytes**, magic `MIXANL01`, fixed LE version1, reserved zero:
header512, counters1024, histograms4096 (3,168 used), windows16,384,
top32x128=4096, residents4096, pins3072, trailing15,872 zero. Header first32
u64 include magic/version/length/decision, authoritative fullReplayAccepted=0,
accepted/physical/footer record counts, acquisition/step/stop coordinates,
work/instructions/op/flags/validity mask, guest resident/pin/taken/commit counts,
original kind/code/stage/cleanup/tickets, phase/masks, overflow/I/O/invalid-seq
and reserved0. Next eight32-byte digests echo selection/schema/stream/original/
profile/analyzer-binary/baseline/candidate; hashes are host-verification inputs,
not Rust assertions of hashing. Counter128-u64 order follows fixed scalar
report counters; `interface_schema.py` freezes all128 names, header word indices,
region offsets and closed decision/stop IDs. Reserved slots serialize0.
Each top128-byte output is function ID, completed credit
score, complete FunctionRow96, reserved16. Window/resident/pin offsets and row
layouts are identical to the arena's explicit wire fields. No formatted text,
Debug/error string or per-event stdout is emitted.

A new exclusive **at most8,192-byte** host receipt is separate and binds the
Rust report hash, all actual digests/custody observations, exact executable
identity/exit, original-result/profile adapter versions and the closed final
decision. Combined report bytes<=57,344, under65,536. Final decision enum is
CompleteRecords,TruncatedPrefix,Invalid,AnalysisLimited,Unavailable. Only the
first two can set fullReplayAccepted, and only after both verification records
pass. CAP never sets completeCoverage. AnalysisLimited records prefix-only
metric validity and an unknown tail. Invalid never overwrites original results.

## Host custody and bounded I/O boundary

This is a **new future offline consumer**, not a retry of the existing one-copy
capture. Keep its boundary separate. The existing writer/evidence streams and
their sidecars are inputs, never overwritten or reclassified in place. No
additional whole-stream copy is needed. Output creation uses exclusive no-follow
new report and host-receipt members, one attempt each; retain partial output on
failure, with fixed error codes, no retry into a new name.

The reviewed host wrapper must accept bounded raw paths (<=4,096 bytes each),
reject NUL/excess components and symlinked path components, validate a trusted
owned parent then open no-follow, compare regular-file descriptor and path
identity/length before every pass and after. If the available platform cannot
prove the parent/component contract using the selected stdlib boundary, reject
that input instead of weakening no-follow. Record dev/ino/raw mode/length and
mtime/ctime sec+nsec. Include actual metadata errors; never replace unavailable
values with zero. Passing an already-open FD must bind its original path and
custody, never accept a digest claim without reading those exact bytes.

Host opens stream/profile/raw-result descriptors, hashes each through that same
descriptor with `hashlib.sha256`, seeks to0 and invokes the exact compiled Rust
binary with only the selected inherited stream/profile descriptors. The host
retains its descriptors; it never reads/seeks them while the child runs because
inherited descriptors share offsets. After synchronous child exit/reap, seek0,
rehash those same retained descriptors and recheck descriptor/path metadata and
length. Require identical pre/post raw bytes and exact Rust consumed length/N,
report bindings and original-result adapter output. Source length drift, short
EOF, read error, replacement, nonregular file, digest disagreement, unexpected
child exit/report inconsistency or timeout invalidates the supplement. Observed stability is
not authentication against coordinated evidence rewriting or hostile races.
Parent/component races and arbitrary concurrent mutation are not solved by
timestamps. This boundary needs explicit independent adversity review.

At most six live process descriptors during the child: three retained host
inputs, two inherited Rust inputs and one Rust report output; after the child,
closed owners are out of lexical scope before host verification output opens.
The Rust named inventory charges its three live File owners and complete I/O/
Metadata Results; the host inventory charges its own three and complete closed
owners until their scope ends. Neither descriptor count is a memory byte bound.
Python hashing uses one65,536-byte buffer, no read-all or unbounded receipt read.
Each block has<=32 combined short-read/Interrupted attempts. Report writes have
<=32 attempts per block; zero/overlong/error/exhaustion retain failure and partial
bytes. Raw original-result/host context reads use cap+1 bounded reads, checked
before allocation; report/hash parsing is fixed-size.

Host hashing has its **separate** <=131,072 named logical inventory and a
proposed18,000,000 authored debit limit: debit ceil(bytes/64) per hashlib update,
one per I/O attempt and explicitly bounded metadata/parse/report operation.
Two full source/profile/raw-result passes plus the independently hashed profile
row bodies charge16,937,520 byte-block units (two simultaneous hash owners only
during a profile pass);
<=32 attempts per65,536-byte block leave the remaining margin for bounded setup,
report hashing and receipt output. An implementation must enumerate/prove its
exact complete inventory and worst case before acceptance; opaque Python/hashlib
runtime and CPU rounds are unqualified. Host exhaustion cannot set acceptance.
These separate host costs never increase or borrow Rust's8MiB/64KiB/268M limits.

The host does **not** parse the49,152-byte report into JSON or Python collections.
It reads only the fixed512-byte header/verdict, validates its32 fixed u64 fields
and eight digest slots, then hashes the whole fixed report as opaque bounded
blocks. The original-result, selection and host acceptance adapters use fixed
binary fields with closed versions, lengths, reserved bytes and enum ranges;
there is no JSON nesting/key/list expansion. The host acceptance receipt is a
fixed8,192-byte binary version1 record, magic `MIXACC01`: header512, before/after descriptor/path
custody16x64=1024, digest slots16x32=512, binding/result/view scalars2048,
closed failure/adapter/I/O/exit observations1024, reserved3072. Undefined entries
have a separate obtained bit and zero reserved payload, never invented metadata.
All string/error payloads are absent; raw original result bytes remain a
separately bounded immutable input.

Host phases are lexical: (1) bounded context/original adapter read (<=8193 raw
bytes plus<=8193 context bytes), (2) pre-hash/profile streaming with one65,536
buffer and no retained raw read copies, (3) Rust child with only fixed binary
context/view owners and retained input File owners, (4) post-hash using that
one buffer, (5) tiny512-byte verdict plus opaque report hash, (6) fixed8,192-byte
acceptance receipt serialization after buffer/hash-reader scope ends. No full
profile, original-result text decode, whole report, all-source list or JSON
object tree is retained. Input maxima are stream536,871,936 +profile2,560,512
+raw original8192 +canonical context8192 +optional writer/custody input8192;
simultaneous input bytes on disk<=539,457,024, excluding the already separate
original source stream and all historical packet members. New reports total
57,344. The replay invocation's bounded paths, complete File/Metadata/stat/hash/
Result/exception/subprocess/decoded-int/header/verdict owners and helper roles
must be reconciled under the separate131,072 logical host inventory. A fixed
cap on file bytes is not a Python object-memory claim.

The six input/report data descriptor owners above are distinct from supervision
and stdio. Freeze a quiet runner: one host-owned no-follow `/dev/null` O_RDWR
descriptor becomes the child's three stdio descriptors (stdin/out/err); the
host retains its sink until child exit, then closes it. That adds four live
descriptor owners, giving **ten newly owned data/stdio descriptors** during the
child; the host's preexisting standard streams and opaque launch internals are
separately excluded, not hidden inside a two-copy-FD assertion. The approved
 Rust binary is required by reviewed source to write no stdout/stderr or owned strings; fixed binary report/error
and exit status are its interface. Its exact hash is checked before execution.
Actual stdout/stderr bytes are discarded and **unobserved** by this runner; it
cannot claim a measured zero or reject unexpected bytes by observing them.
No growing stdout/stderr file or PIPE read-all transport is introduced. The
custody wrapper is still future work, including bounded child supervision and
complete named launch-owner accounting; absence of that reviewed wrapper keeps
fullReplayAccepted=false. This has no effect on the inherited two-live-copy-FD
limit of the original capture, which is not executed here.

No target driver is built here. A future driver must separately bound and drain
original stdout/stderr and persist its original raw result before classification.
Their historical file redirection was unbounded; finite original Debug receipts
and this offline report do not retroactively bound it. A syscall attempt limit
also does not bound kernel latency. New setup/transport limits can shorten an
observed target prefix and require their own source-bound driver selection.

## Support evidence and next acceptance gate

`verification/swift-ordered-retention-analyzer-design/` contains the exact input
snapshots/hashes, finite independent oracle, Rust layout probe, commands/tool
versions/hashes, revision, output and seal. Tests cover timestamp ties, differing
selection/emission/destination, empty-slot replacement by the last victim, held
pins, failure before/after Taken, committed effects, real nonce/Release MAX,
separate consuming zeros, CAP reach, CODE/buffer-loss rejection, mandatory
bindings/lifecycle, record-budget boundaries and reuse0..63/>=64/first. They
are support controls, **not a full wire validator or runtime-analyzer pass**.

Before implementing the real consumer, root reviews this concrete contract and
an independent reviewer validates the frozen scalar/counter names and strict
adapter/code-applicability dependencies. Implementation then needs independently
encoded all-field header/record/footer mutations, full state-machine negatives,
source-bound code/stage/failure pairs, immutable identity/collision cases, real
fixture replay including all invalid completion streams, allocation failures,
complete inventory/lifetime reconciliation, every bounded-I/O/drift/refusal edge,
budget/window/report exhaustion and exact new two-record classifier joining.
No native test is needed or permitted while paused. Full target selection,
writer correction, new policy and GA remain separate unselected work.
