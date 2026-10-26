# Independent actual-source review of the frozen Android editor baseline

Decision: **changes required; no canonical integration or native acceptance**.
The frozen baseline has two observed ordinary ACTION_SET_TEXT compatibility
failures and five independently demonstrated hostile-control failures. Later
root-selected replacement and EditorInfo-class amendments are prospective; this
review has not read or executed the active derivative.

The subject is producer seal
`99ee53d6cf73cc062d5f39f7caa743dfed68f0f22522788adabe83159cacc9cd`,
bound by root custody
`9c8f82dba143eb8360b9b89ff68b00ecf25095828dc13769f18170458559f2ea`.
All 6,149 members / 24,007,562 bytes matched before candidate source access.
The copied product tree is
`b661d2567574c416a8a0dc0420304a08afbc10a7ed2d807ec5a10085f1e0728e`;
the complete host closure is
`7c4e508074c7276ee39eb30019a0d7e09889ac43e5803ce08877c92ac748787a`.
Root release followed this lane's immutable preaccess and replacement preparation.

## Findings

The sealed minimal finding packet is `findings-1/seal.json`, SHA256
`f6d6c1be1278a8e40d4bedd8bfc55d64d32ce002b53e745fa099b0322268fbf2`.
It contains exact independent control source, failed output, source excerpts and
the distinction between host invariant injection and production reachability.

1. **Per-use Mutation accepts roster loss introduced by its own getter.**
   `EditorLease.exact` checks roster before the native Editable getter and does
   not repeat scalar tuple validation after it. The captured cleanup Mutation
   remains accepted when that getter's beforeReturn hook removes roster membership.
2. **Cleanup invokes native close after getter-induced roster loss.**
   The drain precheck's roster check precedes its getter; native close happens
   before the later postcheck notices the loss. A final exact tuple check must
   precede dispatch after every potentially reentrant observation.
3. **Cleanup follows mutable attempt.target.** The exact lease captured the old
   target, but the direct close reads mutable attempt.target. A deliberate getter
   hook substitution causes foreign close=1 and old close=0 before mismatch is
   reported. Dispatch must use the captured target after exact final validation.
4. **Returned creator metadata can advertise refused gestures.** Corrected
   `MetadataReentryControls gesture` uses official supported SelectGesture.class
   through public non-final superclass setters. A usable adapter returns with
   nonempty gesture and preview advertisements, terminal=false.
5. **Failed creator output can silently retain repopulated payload.** The last
   overriding scrub setter repopulates public fields and private surrounding
   payload. Null adapter returns with inputType=99, hint/private text populated,
   terminal=false. Two scrub passes do not establish final clearing or uncertainty.

F1–F3 use reflective hostile invariant injections into authored getter hooks;
they are exact implementation witnesses for selected custody obligations, not
claims of a public retargeting exploit or Android getters performing reflection.
F4's first base-gesture-token control was not platform-faithful because real
EditorInfo rejects those base tokens. Its source/output is preserved and explicitly
superseded by the supported SelectGesture control, which reproduces the failure.
F5 does not depend on that gesture-token fidelity issue. No actual Android
EditorInfo behavior was executed; the private-payload observation uses the authored
leaf's documented clearing oracle and the pinned public source behavior.

The two producer compatibility witnesses also reproduced: a fresh field rejects
valid ACTION_SET_TEXT with `editor native frame active`, retaining original
Editable/value and terminally retiring; an admitted field rejects with
`Editable replacement inside native editor call refused`, retains the old
Editable/value, closes the old target once and terminally retires. These are
implemented behavior gaps, not merely pending device qualification.

## Verified implementation structure and scoped replay

Full changed views/renderer/adapter code and their canonical owner/coordinator/core
call paths were reviewed. Current source origins matched canonical baseline hashes.
Exactly the selected existing production files change: views, renderer and the two
coordinator disposal guards; the direct adapter is new. Owner/core/observer and
other copied production files remain byte-identical. Both SDK36 admission guards
remain intact. The coordinator's central guard precedes disposed/session
consumption; ordinary entry retains its prior active/cancellation/report guards.

The exact tiered adapter implements all 38 official descriptors in its authored
class chain, with direct captured target calls or selected local refusals. An
independent compiled shape check finds no inherited interface default, abstract
implementation, platform wrapper/BaseInputConnection ancestor or setTarget exposure.
getHandler is the fixed-null any-thread exception. reportFullscreenMode delegates
both boolean arguments under captured synchronous authority. Native read flags
and nonnegative requested lengths retain root's corrected policy. Nonmonitor
extraction, zero-only cursor requests, explicit spell refusal, configured Done,
unsupported bounds/gesture completions and the other closed refusals match the
selected private policy in the inspected source and bounded host controls.

Independent replay compiled the **complete** copied production closure with the
sealed authored Android/JNI leaves: 38 producer groups / 505 assertions passed,
including first-fatal identity/order, plain native throws, standalone lifecycle
counting before revoke, constructor bootstrap, hidden-detach denial, same-hook
recursion/depth exhaustion, exact callback postchecks, creator finalization busy,
metadata null/throw/finalization controls, central disposal, Handler rejection,
permanent retirement before serial early-return, healthy Binding/Editable/
selection/composition preservation and no controlled native work in successful
commit→finish. Those counts include assertion-successful observations of the two
known ACTION_SET_TEXT failures; they do not turn them into product successes.

The full copied closure also passed SDK37 javac and unsigned D8 min-api28
cross-compilation using pinned official jars/tools. This proves compilation and
DEX emission, not API28 admission, ART linkage, Android runtime or device behavior.
The independent descriptor validator also passed against the actual compiled
adapter. Five additional defect assertions failed as documented; the two metadata
assertions were repeated with corrected supported token semantics and still failed.
No production or existing host leaf was edited for any independent control.

## Subsequent amendment scrutiny

The root-selected replacement amendment SHA256
`da69185315f2952248596ddd4566a1041bacff73003feff7d38ba48aa0707f92`
is consistent with the pinned native setter/selection order reviewed here. It
recognizes SET_TEXT before generic widget entry, closes old target on Eold first,
uses one field-only no-target Eold→Enew continuation, admits the captured proposal
through the filter, covers movement-before-watcher and selection-after-setter,
and chooses exactly one synchronous post-super event including same/empty values.
The event happens after native continuation release; only scalar/completed-result
return follows a healthy synchronous Binding successor. No contradiction was
found in this bounded source preparation. Actual derivative realization and all
new positive and hostile controls remain pending.

Root subsequently appended the coordinated SNAPSHOTTING reservation, exact
replacement-owned predecessor-close predicate, final tuple checks/captured close
target, and explicit EditorInfo-class policy. The reviewed immutable snapshot is
`root-replacement-amendment-at-review.md`, SHA256
`b386f832479884f2487df114fb080f14ebac99c747208bffd0428477c32d844b`.
The first final custody run rejected the earlier amendment hash; that failure
is preserved. The appended rules agree with root's coordination and the identified
source obligations; no actual derivative implementation is accepted here.

Root subsequently selected exact runtime EditorInfo class admission as a new
private boundary, following the source-backed limit on universal scrubbing of
arbitrarily overriding setters/getters. Scrub can finally reset public fields
after setters, but public virtual APIs cannot guarantee private state clearing
against an arbitrary subclass that refuses or lies. The hidden final direct
surrounding setter is absent from the SDK and cannot be used. The new class guard
must cleanly refuse null/subclass after main-first and before native/live getter,
attempt creation, healthy predecessor revocation or output effects. This review
does not silently apply that new restriction to the original candidate, accept
the active implementation, or claim universal subclass support.

## Limits and cleanup

The platform leaves remain mechanical authored doubles. TextView replacement
callbacks, default movement/selection, native manager/service/IME behavior,
gesture-token validation and full Android EditorInfo are not comprehensively
implemented by those leaves. The corrected gesture test needs only the real
SDK's supported SelectGesture class token, with no platform constructor/method
execution. Bounded host controls and method/bytecode inventories do not authorize
OTA release. A public lifecycle-hook lease does not cover hidden outer platform
dispatch or prove native batch/service reclamation.

Accepted asynchronous Handler work resumes exact pending owner disposal in the
bounded controls; rejected/throwing post keeps the resource/token pending with no
autonomous resumption guarantee. Nonreturning native code has no finite unwind
proof. Newly unrun native checks remain pending under the user's pause.

All finite owned JVM/javac/D8 children exited and were reaped; producer replay
scratch directories were removed and compiled evidence retained. No computer
use, capture, UI, simulator/emulator/device execution, process inventory, Git
mutation/delivery, canonical/root metadata edit, credential change, customer
message or production publication occurred. Native/physical final matrix,
TalkBack, public API28–35 admission, immutable separate-repository FieldLog,
store/signing/OTA, operational gates and accountable GA stay pending.
