# Unselected G2 typed-row source proposal

This packet freezes a concrete safe Rust source redesign and a conservative
complete authored-source G2 model within the unchanged cap2560. The complete
upper is **24965 scalar operations +771 distinct complete copies**, or
`ceil(24965/16)+771 =2332` groups. The actual valid64 occupied/pinned-resident,
64live-token AcquireBegin witness is **23358 scalar operations +770 copies**,
or **2230** groups. The previously rejected seeded source had a necessary
2660-group subtrace on that witness. No numeric cap changes or work borrowing
fund this result. This is a producer proposal, requiring independent source
review and root selection. Its own separately authored checker is arithmetic
and finite-model evidence, not an independent reviewer or implementation pass.

The proposed source is `source/cache_state.rs.txt`, SHA256
`a43397ec7cbbec398502acae5911394fced7ed8d220fee096589940eafb49fb1`.
It is text only, never imported, compiled or executed. The exact correction3
source is the selected semantic baseline; the already failed/unselected seeded
source supplies the prior merge experiment as text only. All source preceding
G2 and following the common post-probe checks stays byte-identical to that
seeded source. This does not adopt its G3/G4 numbers as complete upper bounds.
Those2443/543 finite subtraces, G5, and sorting lifetime remain unqualified.
G6's512/514 selected bound applies to exactC3's unchanged suffix; this packet
does not blanket-inherit C3/G6 acceptance for changed callers or helpers.

The G2 redesign obtains safe fixed resident64/pin64 row references once, with
rows of eight/six complete eight-byte LE words. Every iteration borrows one row
and destructures references to its required fields. Referencing a row does not
copy64/48bytes or eagerly load unused payload. Direct `from_le_bytes(*field)`
retains each required full array8 argument and scalar output. Reserved fields
and backlink fields are loaded at their original short-circuit positions.
The pin header/backlink guard is split into consecutive source guards; their
order and first refusal reason remain identical. Generation and ignored pin
words stay unexamined. Function duplicates, sums, nonce boundaries, first-free
semantics and release duplicate detection remain unchanged.

The old timestamp `from_le_bytes(word).to_le_bytes()` round trip becomes one
complete source array8 read into its indexed scratch destination8. This is a
bijective LE-byte identity, retaining the required timestamp read and every
bit, including timestampMAX. A timestamp is never an eligibility sentinel.
The unselected eligibility-mask bytes640..648 and seeded merge are unchanged.
Every slot/tail timestamp is still initialized. No array source/result, bounds
check, primitive, actual helper/call/return or capacity is optimizer-elided.

`components.json` enumerates44 complete source components with named scalar
operands and complete payload movements. Fixed array Index uses the selected
20-operation core; fat slice Index has its actual extra received length edge.
Row element widths64/48, word width8, full Option16 checked-add returns and
full pointer/length/Range/tuple source/received fields are retained. Distinct
copies are never pooled by total byte count. The upper ledger groups each
scalar once in blocks of at most16 and each distinct copy separately at<=128.

The safe as_chunks/first_chunk/split APIs have explicit authored component
templates: full receiver, quotient/remainder, tuple source/return/receive,
Option pointer and expect message/return work. As in the selected authored
model, this is an API/source abstraction, not a proof of machine instructions
inside libstd. `range-and-coverage.json` proves each fixed view and every
expect success from admitted source preconditions; actual checks stay charged.

`recipes.json.gz` contains29440 finite configuration/early-refusal-prefix
recipes. All4096 slot/pin configurations1..64 are represented. Every resident
header/body/empty/overflow/duplicate terminal, every pin/header/backlink
terminal and all common post checks are covered. Per-iteration maximum branch
weights are `scalars+16*copies`; replacing each with its largest continuation
can only increase `ceil(scalars/16)+copies`. The repeated requested+eligible
resident and matching-release-pin dominators are deliberately incompatible
relaxations. They are not presented as a valid state or reachable maximum.
The actual necessary witness is separate. A full reject reply is included as
G2 bounding slack; its selected G7 ownership remains unchanged. No G7 credit
is spent here, and the slack must not be counted as a new ownership contract.

The independent arithmetic file imports no producer code and checks hand
equations, all recipes, every group, source/input custody and five rejection
mutations.71 finite offline logical relation cases check first reason, required
field-read sequence and partial Candidate timestamp state between old and row
read layouts. They include capacities1/64, MAX timestamps, byte overflow,
resident duplicates, nonceMAX boundaries, valid/rejected duplicate release
nonces, all13 kinds and a six-state publish/pin/release/evict sequence.386 LE
identity samples include all64 bit bases/complements. These logical checks do
not establish Rust/compiler/VM/native behavior or real profile/engine custody.

`G2-lifetimes.json` enumerates the changed G2 caller base480, new block232,
resident/pin named scopes and complete actual API source/received/return object
capacities. Named locals survive their source scope ends. The conservative
G2 Control maximum is1140 of1280; Wire24 of256 and Setup80 of256. No new arena
or Candidate payload exists. Full Option16 and tuple32 source/return/receive,
fat view16, Range16, complete arrays and full reply24 capacities are retained.
All G2 loans end at the block exit before merge/commit. This scoped inventory
does not accept the changed sorting lifetimes, entire29344 role union, machine
stack, libstd internals, compiler ABI or complete implementation.

Reproduce only this packet's own source/model commands from repository root:

```
python3 -B verification/swift-cache-state-row-probe-proposal/run.py
python3 -B verification/swift-cache-state-row-probe-proposal/freeze.py
python3 -B verification/swift-cache-state-row-probe-proposal/freeze.py --verify
```

`run.py` records exact Python tool/version, command, script/input/source digests,
stdout/stderr and exits for build and normal/optimized checks. Optimized mode
retains explicit checks. The seal fixes every packet member except itself.
No model/check command failed. One initial source-path discovery read used a
nonexistent `source/library/cache_state.rs` path and was corrected to the actual
`source/cache_state.rs.txt`; `authoring-attempts.json` retains that failed read.
The exact final run is in `latest-run.json`. No Git command, root metadata, product source, prior
packet, hosted harness/catalog/authority input, publication, process inventory,
Rust/compiler/runtime/native/UI/capture/device process was used or changed.
Only this assigned new proposal folder was written. No instance, build/runtime
directory or capture process was started and none requires cleanup. Other
projects' processes and data were preserved. Native/physical checks remain
paused and pending. G3-G5, remaining lifetime, combined work, independent
implementation review, real binding, published-package FieldLog, signing/store/
customer/operations and accountable GA gates remain pending.
