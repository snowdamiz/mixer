# Independent accounting and source-roster review

Disposition: the proposed arithmetic/accounting design is internally consistent
within this bounded review. One source-roster correction is required (SR01).
This is review of a private proposal, not acceptance of a working exporter,
new native layout, actual storage/work admission, or an operational grant.

The frozen producer seal is
`7787c8bbd9164ebdd360186f79c5d696739e89d6b08cd2f7cfbc71e9c156a1fe`.
Root supplied its verified 639-member / 22,970,241-byte identity. This review
independently rechecked that seal hash, all 14 source-roster member hashes and
sizes against the frozen seal and accepted 144-member manifest, and 17 copied
inputs (491,511 bytes). It does not replay producer or earlier host commands.
The accepted source tree is
`9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb`;
source revision context is `606c42876855897c315ee279dcd38fabaeb561ad`.

## SR01: existing generic preparation is misclassified as absent

The `cache.rs` entry in `source-roster.json` gives the original shared
construction admission fact a null line and the status `planned accessor absent
in actual source`, using the literal token `pub(crate) fn prepare(`. Exact
accepted `cache.rs:1473` defines `pub(crate) fn prepare<'a>(...)`; exact accepted
`cache/initial_profile_v1.rs:138` already calls that method. The lifetime generic
explains the failed literal lookup. Correct the fact's token/line and remove the
planned-absent status, retaining its existing shared-admission role. This is a
source-roster accuracy defect; it alleges no product/runtime behavior defect.

## Reviewed accounting facts

- All six private `ValidatedSwiftReactor` fields have proposed wire locations:
  source, full metadata, policy, actual resolved imports, all 10 usage fields,
  and all 18 observation fields (20 words after two option expansions).
- All eight actual Buffers are inventoried: signatures, parameters, imports,
  functions, globals, exports, data, and elements. Logical record fields match
  the accepted private source. Metadata memory/table/declaration/instruction
  scalar state is separately included. This is field presence/shape coverage;
  decoder duplicate-consistency mutations belong to the main independent review.
- Source reservation is the exact copied boxed-source extent. Native metadata
  charge is the inherited 664-byte proof plus all eight actual charged capacities.
  Capacity is independent of logical count. In particular a 79,966-function
  count may have capacity 131,072 without violating the logical count cap.
  Actual category, multiplication, count/capacity and aggregate usage must agree.
- The native element sizes 12/1/20/12/12/16/16/16 and proof size 664 are inherited
  accepted layout facts, not new measurements by this review. The proposal
  explicitly requires fresh measurement of exporter places in unit and ordinary
  production Debug/optimized builds before any admission.

The independent envelope calculation is:

`2560 + 67108864 + 512*24 + 8192*8 + 34*40 + (80000-34)*24 + 8192*32 + 4096*32 + 4096*32 + 4096*32 = 69765152`.

Every logical cap comes from accepted fixed policy/exact ABI source. The ceiling
is an independent sum of maxima, not a reachable combined proof, allocated Vec,
work grant, or RSS claim. Continuous 4,096-byte filling yields at most 17,033
blocks, a last block of 2,080 bytes, and at most 545,056 writes at 32 attempts per
block. Directory/header extents fit the stated grammar. Independent checked-u64
arithmetic controls refuse add/multiply overflow; u32 values widen losslessly.
These controls do not execute a future Rust encoder or prove its conversions.

## Admission and cleanup obligations remain pending

The storage plan names eight place groups and 59 conservative counted places:
outer caller, wrapper ingress, before-guard plan, guard-bound bridge, encoding,
writer, return moves, and cleanup. It correctly requires caller-owned File,
open/metadata/error/name obligations before their action; wrapper ingress and
retained returns in the initial foundation; and the full temporary simultaneous
set in the original shared reservation before the sole guard. Exact sizes,
actual lifetimes/peaks, additional failure moves and consuming cleanup must still
be measured against the eventual source. This roster is a planned checklist,
not proof that an implementation's complete source-place closure is admitted.

Existing `RuntimeControl::work` and `check` mutate the original control. They
cannot be invoked through the live immutable guard. The proposal explicitly
defers the checked source-backed work formula, charging category, actual
insufficient-limit refusal, and a read-only cancellation/deadline observation
with bounded checks and its own error. `cancellation()` currently clones a
handle; a selected implementation using it must account the handle/place and
retain the same backing owner. Immutable `deadline()` reads already exist.
These are explicit implementation/selection obligations, not contradictions in
the proposed wire grammar and not coverage claimed by its compile prototype.

Export failure must remain separate from the original primary outcome, with no
construction/preparation/acquisition reentry, no ledger mutation while the guard
is live, and no implicit refund or observational Drop. Temporary retirement
occurs only after guard/views die; file cleanup failures remain separate and
uncertain external descriptor/name obligations remain pending/charged. The
proposal requires these boundaries; this review did not execute them.

The original 300,000 grant still refuses the inherited 366,896-byte unit and
366,312-byte production foundations even before exporter additions. Those floors
were not remeasured here. The original 400,000 host fixture remains refusal-path
evidence only. A future positive host fixture requires a separately named grant
derived from a fresh full measured floor, with floor-minus-one/floor controls
and explicit root selection; it creates no implicit product grant increase.

## Evidence and limitations

`review_controls.py` is independent standard-library host Python and imports no
producer code. Eight finite accounting/source-data control groups pass, with
SR01 separately reported. `controls-receipt.json` retains command, Python
version, source identities, script/input hashes, output and scope. The first
successful arithmetic run is retained under `attempt-1/`; the final run adds the
source-roster finding and derives the three shared 4,096 caps from source.

No product/runtime tests, native measurements, builds, Git commands, canonical
edits, UI automation, screen capture, simulator/emulator/device runs, process
inventories, hosted investigation, stopped Android work, publication, or producer
execution were used. No actual reservation or export was performed. Semantic
validation, immutable artifact custody, operational admission, signing/store,
separate-repo FieldLog consumption, physical matrix and GA gates remain outside
this review. No memory facts were used; the quick registry lookup had no hits.
