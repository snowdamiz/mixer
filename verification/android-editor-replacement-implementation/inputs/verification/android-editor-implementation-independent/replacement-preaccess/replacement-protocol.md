# Source-backed preparation: ordinary accessibility text replacement

This report uses the frozen canonical baseline and pinned Android 16 r1 sources.
It does not read, inspect or accept the active implementation. The reported
producer refusal is an implementation compatibility gap if it rejects the
ordinary admitted `ACTION_SET_TEXT` path; it cannot be relabeled as an unrun
native qualification check. No new accessibility replacement refusal was selected.
The original 53-member preaccess seal stays unchanged.

## Platform sequence that the continuation must cover

The exact source/hash/line map is in `source-observations.json`. Official sources:
[TextView](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r1/core/java/android/widget/TextView.java),
[EditText](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r1/core/java/android/widget/EditText.java),
[View](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r1/core/java/android/view/View.java).

1. Public `View.performAccessibilityAction` delegates to an installed accessibility
   delegate or the virtual internal implementation (View 16094–16099). TextView's
   internal implementation first offers actions to Editor handlers, then handles
   SET_TEXT (TextView 14934–14941, 15005–15020). The canonical field does not install
   an application accessibility delegate. This is a source premise to recheck in
   the eventual full closure, not permission to ignore an installed delegate.
2. SET_TEXT checks enabled/editable, gets the action's CharSequence, calls
   `setText(text)`, then sets selection to the new text length when nonempty and
   returns true. The selection suffix is **after setText returns** (15005–15020).
3. Final one-argument `TextView.setText` calls virtual two-argument setText
   (7268–7269). EditText overrides that two-argument entry and always passes
   EDITABLE to TextView (EditText 183–184). A subclass can guard this virtual
   boundary; it cannot override the final one-argument method.
4. TextView's private setText calls Editor.beforeSetText, normalizes null, runs
   filters, sends beforeTextChanged, schedules input restart, creates a **new**
   Editable and installs its filters (7338–7399). Its private setTextInternal
   assigns mText/mSpannable (2023–2026), with the principal swap at 7465. The
   autolink branch can assign the same candidate earlier (7451); do not assume
   exactly one private pointer assignment means exactly one buffer identity.
5. It installs change/span watchers and initializes movement; movement
   initialization can change selection before text watchers run (7480–7511).
   It then calls onTextChanged watchers, the virtual onTextChanged, accessibility
   notification, afterTextChanged watchers, native manager notification/cursor
   preparation, and scheduled IMM invalidation before returning (7519–7543;
   12831–12859; Editor 1931–1938). `onSelectionChanged`'s required super reports
   accessibility selection (12742–12744). These callbacks need their exact
   continuation even though the Editable identity changed intentionally.
6. Finally SET_TEXT performs its separate end-selection suffix. A scope ending
   when two-argument setText returns misses this suffix. Recreating native
   replacement/selection in authored code is unnecessary; preserve the platform
   super algorithm and its return behavior.

The current canonical field admits a plain bounded nonnull SET_TEXT payload and
calls the platform super under a captured Mutation (canonical views 764–770).
Its afterTextChanged listener normally emits textChange synchronously inside
setText (204); its selection callback accounts interaction (761–762). The binding
helper avoids setText for an equal string (348), but an explicit accessibility
SET_TEXT calls the native setter even for the same text and can replace Editable.
The frozen host fixture's one-argument setter and accessibility shortcut do not
faithfully establish this official two-argument dispatch/selection ordering.

Official `getEditableText()` only returns current mText if Editable (TextView
2617–2618). EditText.getText() can itself call super.setText to upgrade a
noneditable value, and returns null during construction (EditText 169–179).
Therefore a tuple-validation getter must not silently treat every getText read
as effect-free. A fresh completed field can have a real Editable and no connection;
the absence of an admitted InputConnection must not by itself deny replacement.

## Minimal safe ordering

The following is a proposed bounded amendment, not an implemented or newly
selected authority path. It keeps the selected exact predecessor-close rule.

1. At the **outer widget ACTION_SET_TEXT entry**, check main first; validate an
   ordinary current field/Record/View/roster and the captured live Mutation;
   snapshot the approved bounded plain proposal. Refuse an arbitrary nested
   input/replacement request before any platform super when another native frame
   already owns the field. That existing nested-dispatch refusal does not justify
   refusing an ordinary outer accessibility action.
2. Reserve one field-local replacement continuation **before the generic widget
   native-call frame and before the accessibility super**. It blocks creation,
   adapter/native-widget reentry, other replacement, bind and incompatible
   prepare/attach, and participates in the existing scalar disposal-busy count.
   It is not readiness, a new queue, an owner/core allocation or a grant to
   another Record. A proposed payload must remain the one actually sent to the
   native setter despite mutable Bundle/CharSequence callbacks.
3. If an admitted predecessor exists, permanently revoke its adapter, close that
   exact target once while its old Editable is still current, and complete old
   cleanup callbacks/restoration/reporting under the old exact cleanup tuple.
   No other entered native frame, active coordinator operation or commit/finish
   interval may be bypassed to force this close. An ineligible/deferred,
   throwing/uncertain close prevents replacement. With no predecessor, retain
   the precise absent/already-returned disposition; do not invent a target or a
   successful close. The known old adapter never becomes live again.
4. After predecessor RETURNED or precise no-target state, revalidate original
   live authority, exact field/Record/View/current Editable, current input and
   actual loss denials. Close may itself reenter or lose authority. Remove the
   old target cleanup callback scope **before permitting a new Editable**. Do
   not use old Mutation.cleanup(fence), an old attempt tuple or a successor's
   presentation to authorize replacement.
5. Enter the matching accessibility native super once under a **field-only
   replacement continuation with no live connection target**. At the explicit
   guarded two-argument setter, permit exactly this selected native replacement
   call. Known finite callbacks may span old buffer → one new buffer identity
   and the platform's selection/paint/service suffix. Callback authority remains
   exact field/Record/View/original replacement-call authority, grants no target
   dispatch, and cannot authorize bind/layout or arbitrary new input. Unknown
   nested setters or a second different buffer transition fail closed. The
   principal assignment can occur before an authored callback observes Enew;
   equal text is not proof of buffer provenance. Exact promotion/observation
   rules need closure before implementation acceptance.
6. Keep the continuation until **the entire accessibility super returns**,
   including its final selection suffix. Check the actual replacement buffer,
   valid text, exact field/Record/roster, expected final selection and original
   authority. Reentry, mismatch or any plain native throw retires terminally;
   observe the original failure before cleanup. No accessible old target remains
   to close against Enew. Never fabricate cleanup for an absent target. Retain
   first fatal precedence, permanent loss latches and last-clear busy ordering.
7. An ordinary successful action must return success, leave Enew in the field,
   notify the feature through its normal synchronous Binding mechanism, and
   permit a **fresh later** connection on Enew only after the replacement guard
   is released and existing current facts allow it. A gain or successful
   replacement never revives an old adapter or clears unrelated loss denials.

This ordering can support a single explicit continuation without blanket
Mutation or old-target authority. The safety distinction is structural: the
old target is already consumed/closed, whereas the new continuation authorizes
one captured native field operation and known callbacks across its expected
buffer transition. Simply dropping the Editable comparison, reusing cleanup
Mutation, or closing the old target from inside the two-argument setter after
accessibility super has started does not establish that distinction.

Exact native close RETURNED still proves only that call's disposition. It does
not prove platform outer-dispatch quiescence or native service reclamation.

## Event ordering and precise open questions

The least additional authority appears to be suppressing/coalescing replacement
watcher feature events while the native super is on the stack, validating the
complete native result and selection, then emitting **one synchronous** textChange
on the same ACTION_SET_TEXT caller stack before returning. This changes the
baseline mid-setText notification point but introduces no queue, delayed edit,
native reimplementation or replay. It avoids authorizing the platform selection
suffix using a presentation obtained by a mid-setText Binding echo. It needs an
explicit root-selected event-order amendment and an actual complete-source
compatible Binding witness. It must not turn ordinary native text notifications
outside this one operation into a buffered/replayed system.

For this proposed notification order, finish the native super, validate Enew and
the final selection, and capture the exact event value while original authority
is still valid. On the healthy path the native replacement continuation may then
release its busy/creation guard before entering the existing ordinary feature
event path: its matching platform super is finished, and no platform call or
callback postcheck remains after the event. The synchronous owner transaction can
capture Enew and preserve that exact buffer/selection/composition during its
compatible Binding echo. After delivery, use the existing completed-result rule
and scalar facts only; an accepted successor cannot authorize another native
getter/setter or a second event. This is ordinary feature dispatch after a
finished native call, not a new synchronous owner cleanup-resumption callback.
The complete source must prove this separation rather than merely clear busy
earlier. An empty/no-op replacement must have an explicit event-count policy.

Lifecycle and owner invalidation remain operative during the native super.
Actual loss records persistent denial and blocks new work immediately; only the
already-entered exact field suffix may finish under its captured continuation.
If final original live authority or the exact new buffer cannot be verified, do
not emit the deferred feature event or claim normal success/rollback: record the
actual possibly-completed native replacement and terminal uncertainty with first
fatal ordering. An invalid proposal, stale/absent field relationship or arbitrary
nested input rejected before native execution is an ordinary no-call refusal.
It must not fabricate a partial-native cleanup failure. A throwing/uncertain
predecessor close or native replacement is a different branch and retires
terminally. A later owner close during the post-super feature event sees no
executing native replacement suffix; existing owner/token/disposal rules apply.
No gain revives the predecessor or clears another lifecycle loss denial.

The following are concrete closure decisions for root/producer review:

* **Notification point:** select post-super synchronous delivery, or demonstrate
  a bounded captured continuation that preserves the current mid-setText event
  and later selection suffix across the healthy Binding successor without
  acquiring another Mutation. An accepted-successor boolean alone authorizes
  return only. New feature events after old-target revocation require the
  explicit replacement operation, not the old target lease.
* **Buffer promotion:** specify which known callback first records Enew, how
  callbacks before the first observation remain bounded, and how a second
  foreign identity is rejected. Account for movement initialization occurring
  before text watchers, autolink assignment, post-setText end-selection and
  getter reentry. Content equality is insufficient.
* **Payload identity:** preserve the approved plain proposal through mutable
  Bundle/CharSequence reentry. Any conversion that drops currently admitted
  Annotation spans is a separate behavior choice; do not infer it from safety.
* **No-target/unchanged-content cases:** prove fresh and admitted fields without
  a connection succeed, and an admitted field with an active connection closes
  old once before the setter. Same-value and empty-string actions still run the
  intended platform replacement and final selection semantics.
* **Scope boundaries:** show ACTION_SET_TEXT is recognized before generic widget
  native entry; show arbitrary nested ACTION_SET_TEXT refuses before super; show
  close callback cannot acquire replacement scope, and replacement callback
  cannot obtain old-target cleanup scope. No normal owner seal is equated with
  permanent field retirement.
* **Delegates/platform branches:** recheck there is no unsupported custom
  accessibility delegate/factory/movement configuration in the actual closure.
  If such a branch exists, demonstrate its finite continuation or name its
  actual compatibility limitation. The canonical baseline already rejects a
  null action value although official TextView treats null as empty; this report
  does not silently expand or narrow that preexisting policy.

Producer's requested fresh/admitted field with/without connection witness will be
reviewed only after root releases its exact frozen seal. No replacement model
suite or product implementation is added here. Actual candidate compatibility,
Android/ART/IME/TalkBack, physical final matrix and GA remain unaccepted.
