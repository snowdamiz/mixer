# Independent frozen encoder work review

Status: source and geometry review complete, with two additive bookkeeping
corrections required before selecting the ledger. This review does not prove the
original total numerical bound is insufficient: its sums of mutually exclusive
success and error paths leave slack. It does establish that two explicit source
actions are absent from their named caller terms under the candidate's convention.

The immutable preaccess criteria and 305 arithmetic controls were sealed before
producer access. Root then released the exact 30-member work candidate with seal
SHA-256 `ef906a8ec95d956898347bca67658ffac82a506be66b204d35893c23acfcfdd0`
in its release receipt SHA-256
`c89dadb70bd9cbc4f350b873ca6cb68eb189fe196e6afb881bd0e951bc6d025d`.
`review.py` freshly verifies every candidate member and the unchanged preaccess
seal. It also checks the exact accepted frozen helper source identities used in
this pass. One read-only producer Python replay passed; no VM, writer, compiler,
native, UI, capture or process inventory was run.

## Findings

1. **F1: provenance receiver fetch omitted, +1.** At frozen
   `host/encoder.rs:199-205`, the call starts with `self.provenance`. Under the
   convention this named source-place reference fetch costs one. The fixed term
   `provenance bridge, region conversion and error propagation` is 2,306 + 9.
   Its nine caller actions exactly cover slice construction (1), `try_into`
   length check and Result (2), `expect` (1), `map_err` (3), and `?` (2).
   They omit the receiver fetch. The caller is 10 and the term is 2,316.
   The analogous runtime call already has helper + 10 and covers `self.initial`.
2. **F2: runtime-validation outer propagation omitted, +2.** At frozen
   `host/encoder.rs:394`, `validate_runtime(...)?` has two converted count
   arguments. The fixed term `runtime validation and two count conversions`
   counts 1,444 for the helper and 20 for those two arguments. It omits the
   separate outer `?`, which costs inspect plus extract/propagate (2).
   The term becomes 1,466.

The proposed additive correction is **14,224 fixed credits** instead of 14,221.
The proposed per-call interface remains **26 + 68 I + 39 D + 139 W + Q**.
The two findings are source-ledger coverage defects; no runtime behavior change
is needed. The original candidate, all its attempt history, original failures,
and preaccess evidence remain unchanged. Root must review any separate correction.

## Reviewed coverage

The manual pass expanded every direct encoder helper and each transitive helper
named by the candidate: `field`, `require`, `word`, `put`, `get`, `words`,
`optional`, `type_id`, `result_id`, `wasi_id`, `SpanCheckV2::check`,
`Buffer::{len,get,snapshot_inventory_v2}`, `AdoptionBodyV1`/`AdoptedProof`/
cache/guard proof and selected-provenance getters, original budget copy,
WASI configuration getter chain, `FileIdentityV1::encode`, provenance packing,
runtime packing, every inventory and preparation loop, `validate_runtime`, all
eight `record_word` branches plus unknown-section/bad-within errors, full
`next_block` branches and five opaque scalar/slice getters. The original shared
`ExecutionWork` semantics were separately read before producer access.

The 139 maximum reconstruction coefficient correctly expands the import arm's
29 common, 20 lookup, two 27 span argument/check/propagation groups, 21 type-index
check and 15 array construction actions. The candidate does not mistake a row
for a word: each word repeats full five-slot construction and validity checks.
Its 39-probe coefficient counts two header word reads per candidate and repeated
found-result work conservatively. The 68 loop coefficient includes the 31-action
common path and maximum 37-action metadata path. Its 26 fixed call coefficient
includes terminal and successful return alternatives conservatively. No further
omitted named action was found in this bounded manual source pass.

The independently sealed interval/step geometry agrees with the released
candidate's closed form for 332 profiles, including all eight alignment residues
at maximum inventory and separate small geometries with all metadata sections.
The candidate's single-block ceilings `I <= 515, D <= 9I, W <= 513, Q <= 4096`
are conservative. The independent tighter loop limit is 513; the difference is
safe. A genuine integer-geometry witness reaches 513 reconstructions and 4,617
probes in the last section. Maximum aligned inventory has 331,716 word visits;
source maximum minus one adds 648 repeats for 332,364 visits.

Failure prefixes include the attempted failing reconstruction. A failed call does
not advance `emitted` and must not reuse a consumed charge. The candidate expressly
limits a global bound to no retried error and at most one terminal call. Integer
geometry models are not executed encoder traces. Original source indexing and
unchecked increments remain justified only by the accepted private cursor's
bounded section and progress invariants; this review grants no malformed cursor
authority. A future consumer must check its bound arithmetic and preserve shared
control first-failure, cancellation/deadline and exact-limit semantics.

## Limits and cleanup

This accepts neither a work floor nor an operational grant. Caller, writer,
syscall, stop-observer, accounting arithmetic, scope cleanup and result/control
costs remain outside the encoder-only interface. Root is reviewing those terms
separately. Complete work/storage admission, writer execution and native/GA
qualification remain pending. This lane made no native, UI, capture or process
inventory changes and started no compiled or persistent test processes. Its
temporary producer stdout was relocated into this review directory for sealing.
