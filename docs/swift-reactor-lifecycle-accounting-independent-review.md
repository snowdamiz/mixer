# Independent private Swift lifecycle source and accounting review

October 24, 2026. The independent host evidence audit found no blocking source
or accounting defect in the sealed candidate. This is a scoped review
recommendation to root. Root accounting acceptance, runtime selection, runtime
qualification and GA acceptance remain separate decisions. This review performed
no compilation, VM calls, test bodies or native application runs.

The reviewed producer seal is
`02b53f531a4cb4852cc7e99104d13bb09e969f9d6b018c4d5d8fd6cd0d3dbbdd`,
binding 1,905 files with packet closure
`aafd88cf053743e2560788bfb877adbabdbdece86f3fb77e972baf100dc2dd2d`.
The candidate is 132 files, closure
`0b36b551e2175aa713d698627493519249b6bfea023f05e13de730e6b06f977f`.
The live baseline remains 130 files, closure
`3dee84f70c852c2a26572c1d6e3463e45e56760a6bba403fabfb9c355ccb1cd3`.
Before and after snapshots independently hash the entire producer packet,
candidate, baseline, selected inputs and live baseline. All match. The original
contract and compiler-only implementation seals remain bound and unchanged.

The fresh review packet is
`verification/swift-reactor-lifecycle-accounting-independent-review/`.
`audit.py` independently reads the full retained raw compiler callbacks, all
paired source archives and compiler layouts, and the producer command/output
archives. Its separate live replays invoke only the producer's read-only
verifier. Tool versions, exact commands, complete raw output and source manifests
are retained. Two reviewer-script mistakes were preserved before correction:
the annotation split is 32 production/64 unit per context, and repeated authored
debug aliases require distinct field stems and multiplicity checks. Neither was
a producer compiler failure. Final audit output is successful.

## Actual lifecycle and ownership semantics

The source review covers the full handwritten lifecycle body, the selected
shared preparation/completion seam, the original frame completion and sticky
control failure behavior, together with all 23 authored test bodies. Reading a
test body is not executing or passing it.

`precondition` examines only lifecycle and the copied private request. Duplicate
initialization and a corpus call before initialization return before cursor
construction, control access, preparation, guest execution or allocation. The
Terminal marker remains blocked even without a recorded first failure; it
fabricates neither a diagnostic nor a cleanup observation. Pending cancellation
or deadline therefore does not turn ordinary misuse into runtime admission.

The permitted route fixes Initialize to absolute function 35 and Initialization
stage, and Corpus to absolute function 62 and Invocation stage. It takes the
same exclusive original owner. The preparation seam splits its existing
control/cache/WASI/State/lifecycle, validates the existing provenance/tickets and
clean state, and adds the original frame envelope. It creates no replacement
authority or cumulative budget. Actual preparation failures terminalize only
through the selected Terminalize goal, after obtaining the actual failure.
Existing callers select Preserve. No fallible operation intervenes between
successful enlargement and recording the original State frame bound.

The private constructor's missing-control path remains
`control.as_mut().expect("constructed control")`. It is an inherited constructor
precondition, not a tested recoverable lifecycle failure. The SL02 ledger keeps
that limitation explicit.

`execute_phase` uses actual entry and actual dispatcher execution. It checks the
outer Result and stored outcome separately: Initialize needs exactly a void
outermost return; Corpus needs exactly an i32 outermost return. The final
`check_with_wasi` runs while the admitted phase exists, with the fixed request
cursor and original WASI/control. Wrong shape, prior terminal state, final
check failure and release failure all prevent publication. Actual pending-growth
release and deepest-first drain preserve the original sticky first cause.
Control `fail` returns an already latched cause before constructing another;
the added code does not reset it or the cumulative owners, counters or deadline.

The consuming completion retains the entire actual phase/context/growth/storage/
preparation if growth is nonvacant or preparation remains occupied. Otherwise it
destroys those wrappers while their envelope still covers them and invokes the
unchanged original frame completion. That original completion checks physical
container emptiness, pin/live debt, entry/unvisited/nested restore state and the
original bound. Retained or restore-rejected inner outcomes do not publish a
reply or Ready. Fixed storage is consumed before restoration. Only genuine
inner `FrameCompletion::Completed` permits Ready, with no fallible step between
that completion and the write. Final-check/release failures already terminalize
the same lifecycle and invalidate the Initialize predicate. The closed request
route constructs empty storage; the original dispatcher rejects occupied
storage and does not populate its preparation field.

Corpus selects Preserve, leaves successful Ready intact and withholds its scalar
until the same full consuming barrier completes. Existing non-lifecycle callers
also select Preserve and cannot publish Ready through the added helper. Rust's
exclusive owner borrow and retained-result lifetime enforce the original
authority route; no unsafe pointer, forgotten carrier, second owner or new
public/C ABI entry is introduced.

## Independent accounting reconciliation

The independent audit checks all eight final Swift/all × Debug/Release ×
production/unit callback sets against immutable
`discovery-final-preinstall/`, not stale top-level discovery references.
The 268 runtime bodies contain 21,364 separate role positions. Every actual
compiler local, non-FnDef constant operand, authored alias and actual closure
capture has four distinct source/argument/returned/caller fields. Alias
multiplicity is preserved. The 44 additional whole retained/caller carrier
fields receive permanent coverage. Complete actual function-item records retain
526 zero-byte FnDef occurrences, with no function-pointer surrogate.

The audit independently binds 21,416 typed/never field witnesses in their actual
final compiler declarations. Never witnesses use the inferred actual never type.
The installed field union across contexts preserves each positive named field.
There is no prior V7 role credit, fallback type, padding subtraction or blanket
numeric substitution.

Only the root-selected original 248 finite rows and supplemental eight actual
private RawVecInner borrow rows receive finite numeric storage. Both proposal
hashes and immutable discovery queries match. The supplemental rows are the
exact eight-byte/eight-alignment local 18 in the two Release unit contexts with
four roles each. All 256 final rows retain actual identities/full layouts and
separately aligned disjoint offsets: permanent production ends at 320 bytes,
permanent unit at 880 and active unit at 320. No additional finite position is
accepted by this review.

All 96 full-body SHA changes and 7,216 sourceInfo changes are reproduced from
the original and final complete callback bodies/positions, with every retained
reconciliation row checked. Actual type/layout changes and runtime position
additions/removals are both zero. Compiler-session display indices alone are
normalized when comparing layout text; stable actual identities remain checked.

All 384 new annotation bodies are individually proven. Each must bind an exact
actual `LifecyclePermanentPositions` field and compiler parent definition hash,
whose type graph is a reference to an array of length six. Each complete CTFE
body has one usize local, one usize constant, a single `bb0` assigning exactly
six and returning, with no FnDef or call. The full retained proof record must
match those raw records. Their runtime byte credit is zero. This is not a
suffix-only or generic anonymous-constant exemption.

The sixteen paired baseline/candidate compiler queries bind exact original
source prefixes. The only overlay suffix is independently reconstructed as the
uninstantiated formula declaration containing the actual named expressions.
All original full owner/growth layouts match, including actual identities,
fields, offsets, variants, sizes and alignment. Candidate typed/never/finite
components independently sum to the observed additions. All 129 other baseline
files and every original growth accounting-struct byte remain exact. Fresh
retained official compiler expansions preserve all 39 Frozen methods exactly;
the Frozen 2,912-byte bound is unchanged.

| Formula component | Production | Unit |
| --- | ---: | ---: |
| Added permanent | 3,464,856 | 6,826,664 |
| Final header | 6,464,992 | 11,694,120 |
| Added active | 489,744 | 1,250,632 |
| Final frame | 15,847,432 | 31,278,808 |

State remains 134,217,728 bytes, Combined 268,435,456 and the maximum 86 tickets.
These are individual logical formula components. This review establishes no
aggregate headroom, runtime admission success, physical stack/RSS bound,
allocation success or measured deadline/performance result. Existing retained
categories, six arenas and growth overlap keep their original budget demands.

## Observed execution scope and remaining qualification

The reviewed producer evidence has 57 compiler/tool commands, including four
preserved failures. Its eight final compiler contexts, sixteen paired layouts,
two production Clippy checks and new-file formatting check passed. Four exact
test binaries executed only literal `--list`, each naming 23 lifecycle tests;
Swift lists 335 total and all-feature lists 365. Binary hashes, Cargo artifact
identity, full list output and cleanup remain bound. These are producer runs
independently reconciled by this review, not newly executed compiler or list
commands by the reviewer. Recorded command targets, overlays, component scratch
and list copies were removed after holder/group checks.

The entire original SL01–SL23 matrix and authored/remaining ledger are copied and
bound unchanged. All assertions remain unrun and every planned row remains
incomplete. SL09's first five cases currently check membership in the typed
failure family; they do not assert one precise kind per individual dimension.
Its broad exact/one-below matrix remains open. SL12 exercises authored memory/
global mutations and repeated indirect reads through unchanged table storage;
guest table mutation is unsupported and unrun. Other missing failure,
interruption, boundary, WASI, allocation and retained-cleanup permutations remain
listed in full. A later successful authored test must not mark its whole planned
row complete.

Root may separately select a concrete bounded runtime set against this sealed
candidate and preserve the remaining ledger. The review does not select SL24,
read/hash/run the retained full target, integrate live VM source, exercise
simulators/emulators or physical phones, publish packages, or qualify FieldLog.
Physical phones remain deferred to final acceptance. FieldLog still requires
immutable published packages from a separate repository. The binding commercial
product plan, D3, G07/G08, store/customer/operational and GA gates remain open.
