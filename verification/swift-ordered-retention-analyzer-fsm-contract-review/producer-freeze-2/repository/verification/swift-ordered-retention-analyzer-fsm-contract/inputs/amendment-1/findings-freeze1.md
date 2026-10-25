# Findings for initial producer freeze

Freeze `a8cf795a8226fed9facf654b05d0ef6cf7146a289eb3c8df8946c5306f9b73b6`
is preserved in full: 137 sealed members, 3,927,907 bytes, plus seal pair.
Independent pre-access preparation seal is
`316040e19aa5d029ef1d885d59ba23f6557debce719f9f79125a227718250649`.
Verdict for this freeze: corrections required before accepting this contract.
No Rust implementation or real replay acceptance is alleged or tested.

R1. Preserve the fixed type scalar domain in the closed forms. Frozen model
`shape` lines61/81 checks only type<MAX64. Independently encoded Lookup and
Release words with type2^32 and typeMAX64-1 both return shape=true and Observed.
The accepted design's FunctionRow type is u32; accepted framing
`full_identity` checks u32 and fixture type count before profile comparison.
Doc lines61–64/77 call these closed forms, so this is an incomplete source
scalar check, separate from the deliberately unavailable profile join. The
private internal framing coupling and false validity prevent a real acceptance
escalation; they do not make this model's closed source scalar claim accurate.
Correction: explicitly retain the source's u32 width for full-body and Release
type fields, cover boundary mutations, and continue to withhold selected type
count/immutable profile identity. If the helper is intended to duplicate only
the historical writer's broader grammar, label that scope precisely rather
than call it the complete source scalar domain.

R2. Make the candidate owner and initialization lifetime explicit in the
interface, inventory and debit schedule. Doc lines165–167 pass only arena,
words and StepBudget. Lines300/333–339 charge one retained 2,048-byte candidate
and reuse; lines381–383 charge its 256 word-zero iterations only at setup.
No candidate parameter or retained owner context connects that once-initialized
transient owner to subsequent leaf calls. A per-call local fully initialized
candidate costs at least its 256 initialization iterations each time, absent
from the proposed 128 debit schedule. Candidate storage cannot silently live in
the arena's spare region or global state. Correction: specify a private retained
candidate owner initialized once and passed/borrowed explicitly, naming complete
caller/callee borrows and init/error/move/drop roles and setup debits; or define
per-call construction and charge it completely. Keep all existing caps and
withhold combined framing inventory/reserve qualification.

R3. Preserve poison through the finite finish boundary. Model lines149–151
return InternalPoisoned with state=None for a commit fault. `finish(None, True)`
then returns the normal `CapCutUnknownTail` name because lines156–157 branch
before inspecting state. Doc lines276–281 requires poison to stop and forbids
representing the mutated state as a normal previous prefix. This counterexample
does not turn either semantic validity true; it demonstrates missing finite
poison propagation, so no production vulnerability is claimed. Correction:
make finish require a nonpoisoned privately initialized state/reply and
explicitly propagate poison for CAP and non-CAP, with tests. A documented flow
precondition could scope the helper but executable poison propagation is the
clearer complete finite contract.

Evidence: `findings-freeze1-reproductions.json` records exact words and results.
`commands/run-1/contract-findings-reproduction.stdout/.stderr` preserves the
independent executable control's expected nonzero exit. The cross-check suite
otherwise passes 12 independent methods, including 5,390 independent
oracle/model comparisons; the pre-access oracle passes18 methods and frozen
producer tests pass18. Fresh host Rust1.99.0 layout compilation/execution
confirms its limited value sizes, not the missing lifetime connection. All845
upstream members and all137 producer members match before/after this run.

The requested correction boundary is only this producer contract/model/test/
layout evidence. No active Rust framing implementation, report format, real
authority adapter, product engine, target, device or gate change is selected.
