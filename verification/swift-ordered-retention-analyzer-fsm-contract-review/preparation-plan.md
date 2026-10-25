# Independent preparation before producer source access

Scope: finite fixture-only acquisition/lifecycle FSM contract. No Rust
implementation is selected or executed. Source reads are limited to accepted
design/library documentation and their exact copied source authorities. No
producer FSM document, model, tests or inventory has been read at this stage.

The source-derived oracle uses predecessor sets and immutable candidate state.
Its 154 baseline pairs cover every 11-state by 14-kind combination. Additional
vectors cover both Lookup forms, Hit/Built publication forms, pin versus terminal
Failure operations, every open-stage failure, independent optional failure
cursors, no post-failure resumption, idle-only Release before phase 5 including
after failure, strict idle Phase advancement, phase-5 terminality, operation and
requested-function joins, acquisition phase and increment limits, CAP unknown
tail without closure, sequence/work/instruction checks and atomic precommit
refusal. Its abstract refusal budget is a test mechanism, not Rust debit proof.

Source seams to inspect independently:

- Copied observer: observe dispatch assigns the operation; nonterminal Failure
  uses the current operation, terminal Failure uses zero; function comes from
  original optional failure cursor.
- Copied cache: CacheOperationPhase::pin emits AcquireBegin then checks the
  header before generic pin creates M::meter, whose cursor adopts the requested
  function. Header/first-failure cursor may therefore differ or be absent.
- Copied borrowed algorithm: successful Lookup, scan, ready, eviction triplets,
  build pair and publication occur synchronously. Release emits only after live
  token removal, has op zero, and cannot interleave an acquisition.
- Copied control: first failure is preserved by value; Release live removal is
  not an invitation to restart an acquisition. Failure applicability beyond
  the operation form remains unavailable.

The frozen producer review must prove these separately:

1. Exact public input coupling: an eventual internal already-framed record and
   immutable profile-identity borrow; no caller-supplied framing/identity/
   acceptance bool confers authority. Pure arbitrary-symbol tests are finite
   model evidence only.
2. A distinct typed FixtureEnvelopeObservationV1 return proposal with closed
   fields and scope; no guessed validity-mask bit or reserved report word, no
   assertion that existing readers understand the proposal. Existing fixed
   report remains Unavailable, semantic counts/coordinates/validities invalid,
   storedPrefixValidated=false and fullReplayAccepted=false.
3. Exact existing arena cell names, absolute offsets, owner and initialized
   states. No use of spare words or expanding storage. Explicit complete
   fixed candidate delta, preflight checks and check-before-commit behavior;
   unexpected partial commit failure cannot publish prior-state authority.
4. Full arguments, borrows, raw/value/caller copies, complete Result/Option/
   error/discriminant, owner moves and lexical lifetimes for each declaration
   and nested call chain. Reconcile the unchanged 8,388,608 arena and 65,536
   transient ceilings. Retained proposal fields must not be hidden in booleans.
5. Source-derived transition/operation/cursor proof, every state/kind/variant,
   failure resumption, release/phase/CAP edge and atomic refusal. Do not infer
   resident/token/plan/victim policy or code/kind/resource/stage applicability.
6. New explicit bounded per-record debit schedule, setup/report/error/iteration
   costs and precommit reservation. Existing 22-group debit and 8,192 preflight
   do not automatically prove sufficiency. Preserve 268,435,456 steps,
   49,152-byte report and 65,536 aggregate cap; insufficient proof means the
   combined implementation gate remains unavailable, not a cap increase.
7. Producer closure before/after independent run, accepted upstream closures,
   exact commands/tool executable identities/source snapshots/digests/stdout/
   stderr/failures and synchronous child cleanup. No hosted/catalog/authority
   driver/rejected WorkerV2 or broad harness import/execution; no Cargo/live VM,
   dependencies, CLI, preparer, target/native/UI/capture/process discovery.

This plan, oracle, generated vector file, successful independent run and
timestamped/hash preflight are sealed before first producer contract access.
Native/device/signing/store/customer/operations/published-package FieldLog and
GA gates remain pending. Root remains the acceptance owner.
