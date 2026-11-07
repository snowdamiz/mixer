# Fixture wire framing library foundation

This packet implements root's selected **first library boundary only**: safe
existing File borrows, fixed arena/context/report, strict wire/profile/context
framing, bounded I/O and authored steps. It is first-party standalone Rust with
std only, compiled directly with `rustc`. It is not a semantic replay analyzer.
No live VM/Cargo/dependency, writer, target driver, host custody, source preparer,
CLI, raw-FD adoption, native run or production policy is changed.

The binding scope remains `mixer-product-plan.md`. The accepted design is
`docs/swift-ordered-retention-analyzer.md`, seal
`c52828b9bbd2aea835871f1f6b68c6dd29281499ee080e5e52fefe525d1e92a8`
(67 members), independently reviewed under
`da87dd37e0983e212bbaf9658bc3177cb47c146bb13d82ddd2fea948c1966ebc`
(212). Root accepted design only. This new producer packet is frozen for a fresh
independent implementation review; it does not self-accept. Computer use,
capture, simulator/emulator runtime and phones remain paused. No native or
unrelated process was started or queried.

`verification/swift-ordered-retention-analyzer-library/src/analyzer.rs` exports:

```rust
pub fn analyze_fixture(stream: &mut File, profile_file: &mut File,
                       context: &mut File, output: &mut File)
    -> Result<ReplayOutcome, AnalyzerError>;
```

The public boundary accepts actual Files. Small private generic read/write cores
permit scripted I/O adversity tests; they are not alternate public trust APIs.
`#![forbid(unsafe_code)]` applies to the complete library. There is no acceptance
constructor, authority boolean or digest verification implementation.

`ReplayOutcome` is104 bytes with fixed decision, observed `framed_records`,
physical count, report bytes, authored steps, observed successful-read bytes,
input/output attempt counts and a32-byte fixed error observation. A failed I/O
call contributes no invented byte count. Its getters
`stored_prefix_validated()` and `full_replay_accepted()` always return false.
`fixture_framing_observed()` describes only the finite grammar/profile join.
Successful framing returns **Unavailable / Binding**, never CompleteRecords or
TruncatedPrefix. Invalid framing returns Invalid; a bounded analysis stop can
return AnalysisLimited. No value or supplied digest can unlock real replay.

The new fixture schema is explicitly **not** `VerifiedBindingView` or a real
selection/original-result/custody adapter. Its magic is `MIXFIX01`, length exactly
8,192 bytes. Its first16 LE u64 words are:

| Words | Fields |
| --- | --- |
| 0..3 | magic, version1, length8192, fixture discriminator1 |
| 4..10 | record cap, expected phase mask, source extent, type count, slots, pins, initial nonce1 |
| 11..15 | cache base, capacity, entry limit, reserved0, reserved0 |
| 16..47 | eight opaque32-byte digest echoes: selection/schema/stream/original/profile/analyzer/baseline/candidate |
| 48..1023 | reserved zero |

Cap is1..4,194,304; mask<64 with bits0 and5 set; slots/pins1..64; type count
is0..MAX32. Extent/base/capacity/entry reject MAX64 sentinel; base<=capacity.
Finite empty fixtures can have zero extent/type count/base/capacity/entry, with
all functions undefined. Defined zero-length bodies at the finite extent fit
the checked-end rule. Unknown context magic produces BindingUnavailable and
no framing observation. Fixture digest syntax and equality grant no authority.

The profile has the reviewed exact2,560,512-byte layout: header512 plus80,000
closed32-byte rows. It rejects undefined-sentinel, reserved, defined/type,
offset/length and checked-end errors. The immutable identities are stored in
the fixed96-byte FunctionRows with initialized sentinels/counters. Profile
baseline/candidate/event-schema echoes equal the corresponding fixture context
slots. Profile `original_input` is distinct from context's original-result
echo; it is not incorrectly joined. Other profile digests remain opaque and
unverified, including the row-body digest.

Stream admission enforces regular file, zero cursor, length1024..536,871,936,
and exact128-byte ordinary framing. All64 header words and digest echoes are
closed. All14 ordinary kinds have exact absent/body/slot/nonce/payload scalar
rules, selected slot/pin bounds and immutable-profile body joins. Sequence,
nonregressing work/instructions, writer operation coordinates and increasing
phase/mask coordinates are checked. Footer checks physical count/length,
attempted=stored+dropped without overflow, cap, digests, reserved fields,
terminal scalar forms, closed enums, last stored coordinates, sole-CAP shape,
phase/mask completion and pre-footer attempt bound. Any non-CAP writer flag
refuses grammar observation. No record list or whole profile is retained.

These checks deliberately omit acquisition-state ordering, resident/plan/token
state, victim policy, failure code/kind/resource/stage applicability, exact
original-result/ledger matches, writer receipt, selected source/tool identity,
cryptographic verification and custody. Executable tests demonstrate a
semantically impossible BuildReady sequence can still have observable framing;
the result remains Unavailable with no semantic prefix validity. Footer ledger
words are unverified scalar observations. They never become original-result or
consuming-ledger authority in the report.

The File boundary explicitly checks identity rather than assuming four borrows
prove ownership. Before allocation or writes, it obtains dev/inode metadata for
all four Files, rejects unknown inode identity and every pairwise alias, and
requires regular/empty/offset-zero output. Hardlinks and `try_clone` output
aliases are tested without changing their source bytes. Input position/type/
length is checked before parsing; successful parsing compares exact initial/
final metadata tuples. Just before output it rechecks the original empty-output
tuple and cursor, then verifies final identity/length/cursor. These checks
provide local no-alias/freshness observations under a caller-quiescence
precondition; they do not authenticate paths, exclusivity or concurrent custody.

If output safety cannot be established, allocation/setup fails, or writing/
postwrite verification fails, the function returns a fixed Error. A report may
then be absent or physically partial; partial bytes are retained failed output.
There is no truncate, reopen, duplicate, retry name or source write. Every
successful report return has exactly49,152 bytes; it is not a durability claim.

All reviewed ceilings stay unchanged: one8,388,608-byte arena,
65,536 complete named transient ceiling,268,435,456 authored steps,
49,152-byte Rust report,65,536 aggregate report ceiling. Arena allocation is
fallible, exact-capacity checked and initialized in place. Typed LE field
wrappers check row, field, multiplication/addition, region and slice bounds;
there are no casts, unsafe arena references or unchecked row accesses. The
fixed regions use7,873,120 bytes; spare515,488 stays zero.

Three million steps remain reserved for reporting and263,584 for bounded
stream/profile/context I/O. Initialization costs one per8-byte arena cell,
profile rows8 each, ordinary records22 even though this slice lacks semantics,
plus charged setup loops. Next-record preflight requires8,192 replay steps.
A limit stops before the next record, drains only bounded bytes, checks footer
structure and emits AnalysisLimited. A later malformed footer overrides that
observation with Invalid. Every assembled<=65,536-byte input block and EOF
probe has at most32 read/Interrupted/short/error attempts. The exact report has
at most32 writes. Zero, impossible counts, non-Interrupted errors and attempt
exhaustion refuse. Steps_used is conservatively charged, including pre-reserved
maximum output attempts/postwrite checks; it is not CPU or elapsed time.

The report preserves the reviewed `MIXANL01`/version1/fixed-region layout.
Accepted semantic record count, guest-prefix coordinates and every semantic
counter/histogram/window/top/resident/pin region are zero/unavailable. Header
word15 bit0 is explicitly finite framing observation only; word4 is always0.
Original-result fields carry no validity (stage MAX means unavailable), while
physical/footer counts and writer flags are wire observations. Its eight
digest slots are opaque fixture echoes. No host acceptance record is emitted;
the reserved future8,192 bytes would keep combined reports57,344 under65,536.

The complete scoped inventory is in
`verification/swift-ordered-retention-analyzer-library/logical-inventory.md`
and executable `inventory.py`/`logical-inventory.json`. It includes full
arguments, File/Metadata/I/O/error/allocator Results, owner moves, decoder
copies, nested helper chains, report/return and caller receiving places.
All original41,984 bytes of reservations remain under65,536; the23,552 margin
is unused. Measured type sizes support this authored inventory and do not
qualify physical stack/RSS or a later semantic implementation.

The final producer run passes20 host methods, including249 explicit record-field
negatives, all64 header/footer scalar mutations, profile/context boundary rows,
independently encoded records, CAP/physical/footer coordinate controls,
allocation refusal/capacity mismatch, safe-region overflow, short/Interrupted/
zero/error/impossible I/O, exact32-attempt boundaries, output alias/freshness,
budget stop/drain/footer override and zero semantic report regions. Public File
tests retain their created inputs/reports as evidence. Rust1.99.0 and Python
3.14.8 identities, exact commands, source snapshots/hashes/revisions and every
failed attempt/output are preserved. Final `-Dwarnings` library/test compilation
is direct `rustc`, without Cargo, dependencies or a VM workload.

All845 original/completion/completion-review/design/design-review sealed members
are rehashed before and after each run. All17 captured sidecars are independently
copied with their raw streams, hashes and unchanged invalid/failure15 status.
Seven raw footers fail foundation grammar; ten have observable footer grammar.
Neither result reclassifies a historical sidecar or replays its missing semantic
state. Inherited CODE-buffer loss and serializer inventories remain pending.

This producer handoff requests independent review of the frozen foundation.
Semantic replay/FSM/code applicability, real adapters, host acceptance join,
source preparer, writer correction, CLI, driver/full Swift workload, compiler/
native/device/signing/store/customer/operations/published-package FieldLog and
GA remain separate pending work. No production or GA gate is promoted.
