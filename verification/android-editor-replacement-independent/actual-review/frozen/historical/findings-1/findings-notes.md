# Frozen baseline findings, with corrected metadata control

Subject: producer seal `99ee53d6cf73cc062d5f39f7caa743dfed68f0f22522788adabe83159cacc9cd`,
complete product tree `b661d2567574c416a8a0dc0420304a08afbc10a7ed2d807ec5a10085f1e0728e`.
No production source or sealed authored platform/JNI leaf was edited for these
controls. All tests use the complete source compiled by the independent replay.
The five defect assertions exit 1; their first output and source are preserved.

## Per-use exact tuple and cleanup dispatch

* **F1 — reentrant getter outlasts the roster check.** EditorLease.exact checks
  retained roster at NativeAppearanceViewsV2.java 774, then invokes nativeEditable
  at 775, without repeating scalar tuple/roster validation after that getter.
  The `mutation-getter-reentry` case removes roster membership in the authored
  getter's beforeReturn hook. Captured Mutation.require still returns normally.
  Output: `capturedMutationAcceptedAfterRosterLoss=true`.
* **F2 — drain consumes native close after precheck authority changes.** The
  drain precheck at 926 checks retained roster before nativeEditable; the getter
  removes roster membership, and native close still occurs at 929. Only the
  later lease postcheck catches the loss. `close-roster-reentry` observes one
  target close after loss, followed by IllegalStateException. Final scalar
  tuple/roster checks must follow any potentially reentrant getter and precede
  native dispatch; checking on the next callback is too late.
* **F3 — cleanup dispatch follows mutable attempt.target.** The lease captures
  its exact target at 769, but native close at 929 reads old.target again. The
  getter hook changes attempt.target to a foreign host target; `close-target-reentry`
  observes foreign close=1, old close=0 before postcheck reports mismatch. Verify
  the complete tuple and invoke the captured exact lease target, never a later
  mutable target read. A passive super.getEditableText getter reduces reentry
  surface but does not replace final scalar tuple validation or captured dispatch.

These are deliberately reflective hostile invariant injections into authored
getter hooks, matching the selected exact-tuple/retained-roster obligations.
They do not demonstrate that an Android getter performs reflection, that a public
caller can retarget the private attempt, or that a production exploit exists.
They establish actual implementation behavior under the chosen hostile controls.

## EditorInfo output and non-final setters

* **F4 — successful creator can advertise refused operations.** The corrected
  `MetadataReentryControls gesture` case overrides the public non-final preview
  setter and uses its superclass setters to repopulate **SelectGesture.class**,
  which both pinned official setters explicitly accept. The adapter is returned
  with gestures=[SelectGesture] and previews=[SelectGesture], terminal=false.
  Creator final validation at 1011–1019 validates field/selection/input/action
  facts but not the actual empty gesture/preview result after setter reentry.
* **F5 — failed creator silently retains public and private payload.** An
  overriding preview setter writes public inputType/hint/selection, then invokes
  the actual public surrounding setter with a nonempty payload. Both final
  scrub passes call that setter again after their direct field clearing, so
  the last call repopulates output. `MetadataReentryControls payload` observes
  adapter=false, inputType=99, hint=repopulated-output,
  privateSurrounding=private-surrounding-output, terminal=false. Calling the
  scrub helper twice is not a proof of cleared output or even reported failure.

The **first** `IndependentEditorReviewTests metadata-success` case used base
HandwritingGesture/PreviewableHandwritingGesture class tokens. The permissive
authored leaf accepted them, whereas official EditorInfo rejects those tokens.
That particular control is superseded and must not be cited as platform-faithful
evidence. Its source/output remains preserved. The corrected SelectGesture case
uses the official SDK37 class token only: no Android constructor or method is
executed. The payload case does not depend on gesture class-token permissiveness.

## Feasible scrub guarantee and new policy boundary

Pinned EditorInfo has private mInitialSurroundingText (820), non-final public
setInitialSurroundingText (845), and non-final public setInitialSurroundingSubText
(876). The first setter dynamically calls the second. Invalid selection clears
private payload in the official second method (889–895). Gesture setters/getters
and surrounding getters are likewise overridable. The final direct surrounding
setter (855) is hidden and absent from the pinned SDK API. It is not an allowed
escape hatch. The selected contract also rejects hidden field access, fabricated
successful output copies and arbitrary Parcel round-tripping.

After invoking all necessary setters, direct final public-field resets can repair
scalar/hint/selection payload repopulation without another virtual call. They
cannot universally prove private surrounding/gesture state was cleared when an
arbitrary subclass setter can ignore the request, call a superclass setter with
another value, or lie through an overriding getter. Bounded retries do not solve
that impossibility. A failed attempt must at least retain/report uncertainty and
return no adapter; it must not claim universal scrub completion.

Root subsequently selected a **new explicit private input policy**: null or a
runtime subclass of EditorInfo cleanly refuses before attempt creation, existing
target revocation, native creator, output setter/getter or any caller-output
effect. The exact framework EditorInfo object retains same-object semantics and
normal clearing behavior. This is a policy change relative to this frozen
baseline, not a retroactive pass for F4/F5 or a claim of arbitrary subclass
support. The independent review has not read the active derivative implementing
it. A future guard must follow main-first but precede live/native getter queries
and predecessor cleanup, including with an initially healthy connection. Verify
the exact object class through final Object.getClass, never a subclass getter.

All receipts are JVM/source evidence with authored Android/JNI leaves. Native
runtime, ART/IME/TalkBack, public admission and GA are unaccepted.
