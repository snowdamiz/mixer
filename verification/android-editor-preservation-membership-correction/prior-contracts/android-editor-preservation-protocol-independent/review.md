# Independent preservation-completion protocol review

Verdict: **changes required before implementation selection**. The proposed
original-Mutation retention, callback-scope lifetime, exact receiver ownership,
precommit native validation, and two narrow coordinator failure hooks address
the directions of FH-C01 and FH-C02. Two phase contracts remain underspecified.
The minimal selectable correction is in `required-amendment.md`.

The assigned protocol seal, product seal, actual-review seal, and root
requirements SHA256 values match. All 44 protocol members (862,128 bytes) were
rehash-verified. All sixteen copied Java source files match both the frozen
product seal and the corresponding actual frozen source bytes; root requirements
and the findings/seal copies also match. `input-custody.json` distinguishes these
checks from full 5,325/1,151-member custody, which was not independently rerun.
The parent-supplied full-custody reference is recorded as provenance only.

## PC-P01 (P1 design): completion claim conflates progress and replay

Protocol lines 90–97, 162–164, and 214–217 introduce completion-claimed state and
set it before prepared swaps/count release. Lines 256–264 separately require a
once-only failed-outcome claim after even consumed candidate/journal state, while
lines 221–224 require failed-finish scalar cleanup. No exact state distinguishes
success preclaim/in-progress, failed endpoint invocation, and actual per-scope
decrement. A single completion boolean permits two incompatible readings:
failure cleanup can refuse a legitimate still-counted hold as replay, or allowing
it can reopen true completion/replay. The state table jumps directly to COMMITTED
with custody already released, omitting this distinction.

This is a protocol ambiguity, not a newly reproduced product execution bug. In
the intended production closure, all supported synchronous finish failures can
and must occur before a nonthrowing scalar tail. A model's hostile partial-release
state does not prove that tail can throw or claim asynchronous VM recovery. Root
should select separate progress/failed-invocation/per-scope-release facts and the
strict tail described in the amendment before dependent code chooses semantics.

## PC-P02 (P1 design): completion excludes legitimate no-begin states

Protocol lines 148–150 require entered+counted for End/completion, while the state
table admits CAPTURED failed entry and lines 253–260 require pre-attach completion.
The actual frozen renderer records the scope into Record and NativeState before
calling Begin (`NativeRenderer.java:586–590`); Begin acquires the count and only
the caller subsequently marks entered (`:164`, `:588`). Thus a legitimate Begin
refusal has an exact owned registration without an entered/count claim. A
pre-attach candidate can have no original Mutation at all. Neither can satisfy
the universal entered/count/original predicate, yet neither may leave a stale
registration, fabricate a count, or become a forged counted native suffix.

The protocol needs an explicit no-scope/no-original no-op branch and an exact
CAPTURED-unentered registration-revocation branch, with no decrement or fabricated
native failure. Begin should publish entered and counted in one no-throw scalar
tail; malformed split flags remain fail-closed rather than repaired. These
branches also make partial-cohort attach failure precise before a returned
journal local can be assigned.

## Source and control conclusions

- The proposed hook positions match the actual coordinator catches: after
  transact retirement (`NativeCoordinatorV2.java:118`) and refresh retirement plus
  deferred reporting (`:145–146`), before their fatal/rethrow selections. This
  preserves status classification and the existing abort/rollback/discard policy.
  Candidate.journal exists at preparation (`NativeRenderer.java:320–331`), so a
  failed attach need not depend on the caller's unassigned returned journal.
- Using candidate.originalMutation removes frozen rollback's equivalent new
  Mutation (`NativeRenderer.java:637`). Retaining the same unended scopes through
  validation/rejection corrects the frozen early end (`:576`) while preserving
  restore's refusal of a genuinely ended scope (`:649`). The real post-attach
  rejection witness must still pass against the eventual derivative.
- A separate captured scalar provenance predicate is necessary: frozen
  fieldPreservationCurrent requires current pending/unused candidate, and frozen
  scope.exact calls platform/native facts. Neither is eligible for terminal end
  or success completion. The proposed indexed existing-journal walk introduces
  no required collection allocation. This is a design conclusion; emitted Java
  bytecode/allocation closure has not yet been audited for a derivative.
- Whole-cohort success preflight and two-phase failure reporting/release preserve
  balanced C when A is imbalanced, keep A busy, and avoid post-clear reporters.
  First-fatal order needs real exception tests including earlier renderer F and
  later coordinator G, not only ordered iteration over component ledgers.
- The new abstract three-field expectation is count3 at commit, count1 after
  finish, then0 on external B unwind; refresh without B is2→0. The previous early
  release expectation remains historical. No model claim is a real EditorLease,
  actual three-field native adapter path, or Android behavior receipt.

Nine independent Python model groups pass: abstract success and known rejection;
CAPTURED/partial-cohort cleanup; no-original/no-preservation paths; selected exact
identity/foreign endpoint refusals; underfunded cohort plus first-fatal/balanced
sibling cleanup; all-or-none success preflight; synthetic partial-release progress;
and a shared-boolean counterinterpretation. Raw outputs and bounded subprocess
receipts are frozen. These model groups do not implement every real Record/View
edge, getter reentry, native suffix, owner disposal, allocation or Java exception
path. The selected actual-source tests in the frozen plan remain mandatory.

## Scope and limits

This review changed only `verification/android-editor-preservation-protocol-independent/**`.
No product source, canonical evidence, other lane, Git mutation, compiler/native
runtime, UI/capture, process inventory or external service was used or changed.
Only assigned frozen source/contracts/findings and seal data were read; no
frozen generator, broad owner/hosted harness or rejected worker was run.
Both bounded children are reaped; no native instance or scratch tree was created.

No canonical integration, native/IME/TalkBack/OEM validation, API28–35 admission,
signing/store, immutable FieldLog release, public routing, OTA, operational or GA
acceptance is made. Root must select the amended protocol, then freeze and
independently replay the actual three-file derivative with the complete real
coordinator, three-field path, both old failing controls, prior groups, SDK37/D8,
interval bytecode/callgraph checks and native checks left explicitly pending.
