# Paired 128-frame / 128-pin source proposal

Propose `paired-128-v1` for root's independent review and explicit selection.
Both copied arms retain 256 residents, the 256 MiB combined logical limit, and
every previous validation, source, metadata, cache, state, value/control,
memory-page, host, fuel, work, deadline and capability limit. Only frame and
active-pin profile maxima change from 64 to 128. This packet changes no canonical
source, production default, gate, Git state, process hold or published package.

The source generator and bounded remote runner are concrete. Compilation,
actual finite owner checks, compiled geometry, harness execution and full
attempts remain **unrun**. Pure Python checks do not accept Rust behavior or
host feasibility. Root must review/select this proposal before installing or
dispatching the included workflow template.

## Failure evidence and discriminating decision

The sealed actual review of run 40768719255, head
`dfd0e3196543cc1749c9cc924cc7accf28c9dc25`, proves both previous arms stopped at
frame 65 against 64, function 24126 / offset 4394310, with 64 frames and 64 pins.
Neither produced the full eleven-field first corpus observation or reached the
second corpus. The failure occurred before fuel, execution work, cache work,
deadline and combined memory ceilings. Both final owner ledgers reached zero.
The exact call stack was not retained. The bounded byte parser found only the
`.swift1_autolink_entries` custom section in the same 53,777,114-byte Wasm, with
no `name` section; no symbol or recursion chain can be inferred from it.

Competing explanations are (1) valid Swift calls need a bounded depth above 64,
or (2) execution needs more than 128 frames or exposes another remaining guard.
The retained failure does not establish that the recursive chain is legitimate.
The finite tests discriminate representation/ownership defects before the real
workload. The unchanged full target then determines whether this candidate
advances beyond the old boundary, completes both corpora, or names the next
limiting resource. A failure is diagnostic, never a pass.

Raising `budget.frames` alone would leave `min(64)` in frame entry. Raising that
clamp alone would leave active-pin adoption/admission at 64. The control arm
extends the existing actual-record first-free scan to 128 records. Dense uses
two fixed `u64` words, which avoid introducing a `u128` alignment requirement.
All shifts are below 64 and every selected slot is checked against its actual
nonce record. Owner, nonce, ticket and sticky-first-failure logic remains in the
unchanged shared publication/release core. No unbounded resize or call-stack
logging is introduced.

## Accounted storage and work

| Changed storage | Derivation and admission |
| --- | --- |
| Frame arena, both arms | `64 * size_of::<SwiftFrame>()`; selected 64-bit expectation 4,096 additional bytes. Existing State arena ticket, exact-capacity allocation and retained capacity checks. |
| Pin arena, both arms | `64 * size_of::<PinRecord>()`; selected 64-bit expectation 1,024 additional bytes. Existing Cache buffer ticket, exact-capacity allocation and consuming cleanup. |
| Dense owner bitmap | 8 to 16 bytes: +8 in each real `SwiftFunctionCache` and constructor `Partial`. No heap allocation or extra ticket. |
| Dense helper inventory | `mask` and `permitted` grow by 8 each; a new `word: usize` is 8 bytes on the selected target. Expected direct inventory delta +24 bytes. The existing three-copy `DensePinInventory` term remains in cleanup, construction and operation envelopes. |
| Dense borrow | `&mut u64` becomes `&mut [u64; 2]`, both thin pointers to fixed-sized types. No slice length or heap payload. |
| Containing owners and transfers | Existing `size_of` terms recompute every `Option`/`Result`/partial cache, whole instance, return, source/argument/caller and cleanup lifetime. `compute_cache_header_bytes`, all three cache temporary inventories, execution `terms`, execution header/construction supplements, and frame/call permanent inventories keep their original positive accounting formulas. No numeric header or operation allowance is subtracted or waived. |

The finite suite asserts the target frame/pin sizes and measures 64-versus-128
arena reservation deltas. Frame reserve remains uninitialized capacity and adds
zero constructor execution credits. Pin record initialization adds 64 cache
credits in both arms. Dense's second bitmap word adds one initialization credit
relative to its old one-word constructor. Its pin admission charges 6+4 credits
where the old one-word helper charged 3+2: five additional credits per successful
availability check. Exhaustion still scans and charges every actual record.
Control's first-free scan can examine up to 128 actual records. Release keeps
the original nonpolling terminal cleanup behavior. Guest entry/return work,
fuel and live-resource debits remain the existing per-operation charges.

Neither frame nor pin count multiplies reservation-ticket count: the existing
two vector tickets remain; maximum inventory stays 278. The 256 decoded
residents, dense 160,000-byte map and control 768-byte index are unchanged.
The two arena deltas are inside the unchanged category ceilings, so they must
not be added a second time to the conservative sum of those ceilings.

The last **compiled baseline** conservative sums were 266,788,262 control and
266,805,846 dense bytes, leaving 1,647,194 / 1,629,610 bytes below 256 MiB.
Those are not candidate measurements. Candidate padding/containing-type sizes,
header sums and conservative totals are pending compilation. Before any full
attempt the unchanged formula is recomputed from the new compiled types:

```
source ceiling + metadata ceiling + cache ceiling + state ceiling
+ maximum WASI reservation + shared owner storage
+ foundation construction floor
+ max(execution construction, frame operation + cache operation)
<= 268,435,456
```

Actual finite and full peaks must also remain within that same limit. If the
compiled candidate does not fit, stop with zero full attempts; this proposal
does not authorize shrinking an unrelated category, changing residents or
enlarging the envelope to force it through. Logical bounds are not process RSS.

## Executable controls and run bound

The common `::framepin_campaign_` filter selects nine control tests and ten
dense tests. These include all four/six previously selected controls, recursive
actual frame/pin limits at 63/64/65/127/128, distinct recursive pin nonces,
rollback at depths 63/64/127, 128 retained original frames with foreign-ticket
release rejection and later original-ticket restore, stale/reused/foreign pins
at slots 0/63/64/127, dense cross-word corruption, pin constructor payload/work
deltas, rejection of budgets 129, all 15 integrated allocation failures and all
six exact-capacity failures. Existing constructor work/cancellation prefix tests
run under the new profile. The original fixed 64-entry release-observer test
hook is unchanged; new deep tests use actual foreign tickets without enabling
that hook. Every owner uses the original consuming cleanup path.

The included `workflow.yml` is a proposal, not an installed workflow. The runner
requires first-attempt GitHub-hosted Linux and explicit
`MIXER_FRAME_PIN_SELECTION=paired-128-v1`. It retains Rust 1.99.0 release,
locked/offline dependencies, overflow checks, and two build jobs. Both builds,
finite controls, geometry receipts and original harness controls finish before
the first full attempt. Each full attempt invokes the unchanged
`exact_reactor_target_once`: initialize once, two original corpus calls on one
owner, compare all eleven original native fields, and consume cleanup.

The cap is two full attempts and eleven owned commands, 2,700 seconds aggregate;
per command: build 180, finite 90, harness 90, full 750, cleanup 10 seconds with
receipt margin. Existing capacity, identity, ticket, invariant, fuel monotonicity,
prefix, unexpected exit, cleanup and custody failures stop subsequent work.
No retry/resume is permitted. Ordinary bounded resource exhaustion preserves
the first cause and may complete the paired diagnostic campaign. Work/fuel/time
headroom remains a finite hypothesis: 1B fuel, 8B execution credits, 768M cache
credits and 600,000ms per Runtime/WASI owner. No automatic replenishment or
silent widening is selected if another limit is next.

## Local evidence and limits

`verify.py` passed 152 structural/arithmetic checks and 39 pure runner controls
under Python 3.14.8 with process/socket/signal/wait guards and writes confined to
this folder. Source closure manifests and diffs are in `source-check/`; each
`from-actual.patch` isolates the delta from its previously executed arm. The
readset and receipt bind exact inputs and outputs. Two verifier-only setup
errors are retained: loading `unittest.mock` after replacing the socket class,
then a missing proposed workflow fixture. They were fixed without a compiler,
guest, native instance, process probe or full attempt.

All held groups 20745/20770/20780/20817/20842/20851/20866, Unit A, broad hosted
work, local FieldLog compiler custody and native/UI/capture pauses remain
unchanged. Physical devices, native/mobile performance, external immutable
FieldLog distribution, signed OTA, customer use and GA are not accepted.
