# Independent Android editor cleanup contract review

Decision: **accept the sealed producer design together with required-addendum.md
for isolated candidate preparation only**. The addendum is a required correction,
not a claim that the frozen proposal already specifies or tests it. No canonical
source was changed in this review.

The exact producer seal is
`060347101b96ecb7a5ee180828cf3437d47179fbb82e8c8ba8457a96859023b7`.
All 54 members (3,970,394 bytes), both earlier frozen packets (95+108 members),
seven canonical producer inputs and bounded source digest
`f93a01001be4636222d287d299bf2c4eb71d7e09c05959a739587fe80df9ed0c`
matched. All 24 source anchors and 12 actual source fragments matched. Independent
replay confirmed 24 producer model tests, two actual-source failure witnesses,
20 candidate Java host checks and ten schema negative controls. The Java replay
used explicit JDK25 rather than the producer's JDK27; tool output and argv are
retained. No producer file changed.

The producer accurately corrects both earlier mistakes: renderer cancellation
reporting does not participate in the coordinator's disposal predicate; and a
predicate-only amendment misses coordinator `leave` calling `disposeOnce` directly.
The proposed central guard runs before disposed/session consumption. Existing
`closeFromOwner` rejects busy before owner consumes a successful disposition; its
intervening retirement is scalar-only. The private editor-busy predicate excludes
mere DEFERRED/FAILED_UNCERTAIN states and does not block healthy compatible feature
events from entering the coordinator. This avoids deadlocking pending cleanup or
breaking normal synchronous text-change acknowledgements.

The source-backed policies are bounded and internally consistent: serialized
CREATING; exact old-target close before successor; no recursive close inside a
delegate; exact no-event callback suffix; permanent retirement separate from
temporary seal serials; fixed-null getHandler without field/thread access;
nonmonitor extraction; zero-only cursor disabling; explicit spelling refusal;
constant unsupported bounds completion; sendKeyEvent refusal because of the native
queue; configured Done only; and empty advertised handwriting gesture/previews
while retaining generic stylus text input. The exact API36 EditorInfo clearing
source confirms invalid selection followed by empty initial surrounding text
clears its private surrounding payload. Actual output scrub, mutable setter
reentry and all adapter descriptors remain implementation prerequisites.

The required correction closes two specification gaps. First, a standalone
lifecycle hook needs to acquire its counted exact lease before revoke and retain
it through super; loss eligibility must outlast the public callback because hidden
detach suffixes continue afterward. Second, a plain native delegate/super throw
must retire even without an earlier retirement request. The addendum also makes
constructor bootstrap, absent-Editable handling, no-call refusal, finite nested
callbacks, exception observation order and async owner resumption explicit.
Root confirmed these corrections during coordination and will select the combined
contract; this independent packet does not select its own product implementation.

Independent transition_review.py passed 24 additional finite authored groups,
including standalone lifecycle busy ordering, hidden-detach loss denial, off-main
refusal before native super, constructor bootstrap, known callback joining versus
same-hook recursion, plain delegate throw without prior revoke, inaccessible
creator target, first-fatal identity and cleanup precedence. Two intentionally
unsafe controls demonstrate closing an old native target against a successor
buffer and an owner-only guard bypassed by direct disposal. An independent small
exact-source Java extraction also witnesses the canonical direct leave/dispose
hazard and preserves its existing cancellation/report guards (three groups).

Evidence limits remain material. The producer model has no actual Android classes;
its lifecycle trigger strings do not execute those hooks, its getHandler test is
a handwritten constant function, and its cleanup counters cannot prove native
batch reclamation. The Java probe runs exact bounded owner/coordinator controls
with authored asynchronous Handler/renderer/core leaves; it does not execute full
owner, renderer, View, TextView or InputConnection on Android. The ten negative
controls mutate contract JSON expectations; they are schema consistency checks,
not ten hostile product-code variants. Source anchors are custody/reference checks.
The independent model likewise specifies an intended ordering, not actual adapter
behavior. No finite host run proves platform outer dispatch quiescence.

Under the accepted asynchronous Handler path, exact resource/token cleanup resumes
after native unwind. Rejected or throwing TERMINAL_CLOSE posts retain pending
resource/token without a guaranteed autonomous retry; nonreturning native code has
no finite cleanup guarantee. Public lifecycle hook leases do not cover hidden
TextView detach suffixes. These limitations are preserved, not treated as passes.

Complete adapter/views implementation, host descriptor/callback/output controls,
SDK cross-compilation and independent actual-source review remain pending. Native
IME, EditorInfo, selection/composition/batch, visibility/focus/detach, TalkBack,
physical-phone, FieldLog immutable-package, store/signing/OTA and GA checks remain
pending. The binding eventual product scope is unchanged. No computer use, capture,
UI automation, native simulator/emulator/phone, process inventory, Git action,
production publication, customer message or credential change occurred.
