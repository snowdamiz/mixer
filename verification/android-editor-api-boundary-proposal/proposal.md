# Android editor and InputConnection boundary proposal

**Review-only proposal. No product implementation, source-profile selection,
new rendering context, native runtime result, public V2, OTA or GA approval.**

The immediate implementation selection is **blocked by native editor close and
batch-cleanup ownership**, not by wrapper signature design. An incarnation-only
repair would be source-level authority evidence, not a complete usable editor
component. First select and independently review the narrow exact-target
closing/quarantine contract below for the currently admitted API36+ editor;
then implement/review lifetime and dispatch fences, followed by extraction into
API-specific classes. Both existing SDK<36 admission guards must remain.
Isolating signatures alone would carry the present-day incarnation and cleanup
gaps forward. Root must select exact behavior and ownership before canonical edits.

## Frozen custody and sources

`source-map.json` freezes 21 selected inputs. Its revision
`5583fb2c61e2c12acb5f0120a9a072e05cdb5ac1` is contextual; file hashes are
authoritative. Relevant Java sources were checked against the frozen profile4
source map, without reading live CLI policy. Root profile4 acceptance has SHA256
`83f83c42d53b8bc5df50eaf84f751236f39d3fa66c827bf4e55635a4d424eea7` and native
acceptance has SHA256
`0c15ca808c2f5684d768125674cdfc0bf48bff672193f79fcaaee47726bf2478`.
The accepted owner/environment behavior and current collection decisions are
inputs, not authority to rewrite them. No collection changes are proposed.

The product requires host-owned native handles (§7.4), native editing,
accessibility and shared appearance (§8), proposed Android28+ qualification
(§19.1), meaningful bridge/UI evidence (§20), and W05 Android evidence. An
unavailable operation cannot be advertised as implemented.

`official-inputs.json` pins the installed official SDK36/37 metadata and JARs,
JDK25 binaries/version output and 21 named official AOSP source files: the
InputConnection/interface and platform wrapper on API28..36, plus API36
EditableInputConnection, BaseInputConnection and TextView. The SDK37 platform is revision2,
API37.0, extension22, non-preview. SDK36 and SDK37 expose the same 38 public
InputConnection method descriptors. `api-inventory.json` and
`official-defaults.json` retain exact floors, declarations and references.

The primary reference links are [InputConnection](https://developer.android.com/reference/android/view/inputmethod/InputConnection),
[InputConnectionWrapper](https://developer.android.com/reference/android/view/inputmethod/InputConnectionWrapper),
[TextView](https://developer.android.com/reference/android/widget/TextView), and
[View](https://developer.android.com/reference/android/view/View).
Official source links, exact Git tags and downloaded byte hashes are in
`official-inputs.json`; AOSP source is documentary input, never code imported
into the product. The method and type inventory below derives from the pinned
SDK artifacts and named platform files, rather than a whole-library compatibility
claim from syntax matching.

## Current API36 authority facts, distinct from older-SDK linkage

All source line references in this section address frozen `inputs/` files.

1. `NativeAppearanceViewsV2.java:729..759` creates an anonymous wrapper whose
   `open()` is `record.input.open(record) && hasFocus()`. There is no field-local
   connection identity, no closed flag, and no comparison with the most recent
   `onCreateInputConnection` attempt. Focus returning, or another connection
   being created while the same Record stays current, can therefore make the
   old object pass the authored gate again. This is a source-level retained-object
   authority gap. It does not prove ordinary Android transport delivers such an
   object, nor that a device exploit was reproduced.
2. In official API36 EditableInputConnection, `getEditable()` returns its retained
   TextView's **current** editable buffer. Its negative `mBatchEditNesting` guard
   protects only begin/end batch calls. `closeConnection()` balances batches and
   sets nesting negative, after BaseInputConnection finishes composition and
   resets IME consumption. Base commit/delete/selection/read methods do not
   consult a universal closed flag. Native close is not a substitute for an
   authored connection-incarnation fence.
3. `performContextMenuAction` is inherited from the platform wrapper. Official
   EditableInputConnection begins a TextView batch, calls
   `onTextContextMenuItem`, then ends the batch. The actual NativeField override
   at `NativeAppearanceViewsV2.java:776..785` already rejects stale menu text
   edits and validates paste; the Record InputFilter and TextWatcher at
   `193..210` also gate content/event work. Therefore **do not claim unguarded
   menu text insertion**. The enclosing native batch calls nevertheless occur
   outside the wrapper's entry/return checks. Main-thread misuse also reaches
   that native prefix before NativeField's check.
4. Read/caps methods are inherited forwarding routes. Base reads obtain the
   editable via the unfenced getter. Extraction additionally calls
   `TextView.setExtracting` when its monitor flag is present. API31 spell-check
   and cursor updates call native TextView/IMM hooks without an authored wrapper
   gate; API34 text-bounds computes native data and schedules a callback. These
   source paths bypass wrapper-level fencing. Their complete native asynchronous
   effects have not been executed or qualified.
5. `getHandler()` resolves to BaseInputConnection's null in the exact native
   connection source inspected here. Null uses the platform's normal scheduling;
   it does not mint authority. Preserve this behavior, rather than exposing an
   alternate Handler or interpreting it as a mutation exploit.
6. A nonnull target and `mutable=false` already make the current platform
   wrapper's `setTarget` throw. There is **no demonstrated retarget exploit**.
   The direct-proxy design below is selected for an exhaustive dispatch surface
   and explicit method resolution, not to repair retargeting.
7. Official API36 TextView's native creator also fills `EditorInfo` with nonempty
   supported handwriting gestures/previews; feature-gated paths set stylus and
   writing-tools flags. NativeField returns that metadata unchanged although its
   wrapper refuses gesture/replace operations. Later selected metadata policy
   must match those refusals; no actual platform result or new support is inferred.

Separately, the current anonymous class directly declares API31/33/34 members
and later signature types. A runtime `if` inside it cannot remove those
declarations. The inspected API33 platform wrapper does not declare
`takeSnapshot`; its API34 successor does. A naive API33 `super.takeSnapshot()`
backport is unsound. API33's public **interface** method exists and has a null
default. The proposed direct target-interface dispatch uses that public route,
with the same fenced nullable result, without an absent platform-super call.

## Concrete class and factory contract

Add one internal `NativeEditorConnectionV2.java`. Its package-private factory
returns `InputConnection` and accepts only an actual native target and an
API28-safe internal field port. The factory reads the real `Build.VERSION.SDK_INT`;
there is no caller-supplied SDK, configuration override, reflection or diagnostic
capture that can select a rendering context.

Use separately emitted nested classes:

- `Connection28 implements InputConnection`, with a final nonnull target and
  final field-local connection-attempt identity. Its descriptors/fields and
  initializers use only API28-safe public Android types. It explicitly declares
  all 26 methods available by API28. It has no platform wrapper superclass and
  exposes no target setter.
- `Api31 extends Connection28`: exactly `getSurroundingText`, `performSpellCheck`
  and `setImeConsumesInput`. Only here may `SurroundingText` occur.
- `Api33 extends Api31`: the three TextAttribute overloads,
  `requestCursorUpdates(int,int)` and `takeSnapshot`. TextAttribute and
  TextSnapshot occur only at this boundary or later.
- `Api34 extends Api33`: `replaceText`, perform/preview handwriting and
  `requestTextBoundsInfo`. Gesture classes and TextBoundsInfoResult, including
  its generic Consumer signature, occur only here or in separately emitted
  API34 callback helpers. The callback helpers must not capture a field/Record,
  target, Mutation or readiness object.

The base factory contains guarded construction references to these classes; it
never initializes them from shared static/instance fields. Select highest floor
no greater than the real SDK. All delegate calls are explicit target-interface
calls. No default implementation or platform `super` method is invoked to
simulate a method absent on that SDK. Base methods can be final; subclasses only
add later overloads. This is one editor boundary, not four independent editors.

Keep metadata configuration separately guarded as well. API34 public methods
`EditorInfo.setSupportedHandwritingGestures(Ljava/util/List;)V` and
`setSupportedHandwritingGesturePreviews(Ljava/util/Set;)V` can clear advertisement
of the already-refused gesture operations, after the original creation attempt
and scope are checked. The newer
`setStylusHandwritingEnabled(Z)V` is API35 and `setWritingToolsEnabled(Z)V` is
API36: place their exact method references in separately emitted `Api35Metadata`
and `Api36Metadata` helpers if root selects a flag change. There are no new
InputConnection wrappers at those floors. Disabling generic stylus text input
is not automatically implied by refusing editing gestures; root must select
that policy without removing ordinary commit/composition support. The shape-only
metadata experiment demonstrates these floors with false values, not product
selection. No base class may eagerly call any newer metadata setter.

| SDK | Shape selected if independently exercised | Field/selectable preparation | Required accessibilityValue | Actual V2 admission |
| --- | --- | --- | --- | --- |
| 28 | Connection28 | Reject before native preparation | Reject | Closed by both guards |
| 29 | Connection28 | Fields require isolated public API29 authored setters; selectable appearance remains separately reviewed | Reject | Closed |
| 30 | Connection28 | Same API29 prerequisite | API30 isolated state-description setter | Closed |
| 31 | Api31 | Same | Same | Closed |
| 32 | Api31 | Same | Same | Closed |
| 33 | Api33 | Same | Same | Closed |
| 34 | Api34 | Same | Same | Closed |
| 35 | Api34 | Same | Same | Closed |
| 36 | Api34 | Existing private field appearance, pending unchanged native qualification | Existing semantics | Existing private-only restrictions remain |
| 37 current SDK | Api34; no new public IC descriptors in pinned metadata | Same | Same | No new context selected by proposal |

This table is a method-isolation/refusal policy, not API28..35 support. Unknown
future interface methods must be audited when the SDK changes; the finite
38-method inventory cannot prove arbitrary future defaults safe.

## Connection attempt ownership and reentrancy

The field owns a local current-attempt reference and each wrapper has a local
closed/closing state. Use a fresh private object identity, not a numeric counter,
owner generation, lifecycle token, global registry, handler or readiness flag.

`onCreateInputConnection` must check main first, validate the current Record and
capture the existing direct Mutation. Before calling any platform/super method,
replace the current-attempt reference with a fresh attempt, permanently revoking
the previous wrapper. Call the native creator once. On return, compare the
**same captured attempt**, original Mutation, Record/view, focus and Editable
facts. If nested creation installed another attempt, the outer call returns
null and never overwrites the nested attempt. A null target clears its attempt
only if that attempt is still current. Ordinary throw and fatal throw revoke the
same attempt before unwinding; they preserve the original failure and cannot
clear a newer nested attempt. No retry or fallback creator runs.

Revoke before external work on field focus loss, window focus loss, detach,
visibility loss, explicit close, actual Editable replacement and field/record
replacement or retirement. NativeField currently lacks the needed focus/window/
detach/visibility overrides; the future slice must add the bounded scalar
revocation callbacks before their platform super calls. An old wrapper's
`closeConnection` may close its own local state but must not revoke a newer
current attempt. Closing the current wrapper marks it consumed before native
close can reenter. Repeated close has no native call. These scalar rules alone
do not establish native-close safety; the mandatory closing contract below must
dispose or quarantine the old target before a successor can become usable.

Do **not** revoke merely because `Record.bind` publishes a new Binding object,
because a validated engine echo acknowledges a keystroke, or because the owner
temporarily seals input during its synchronous operation. The existing renderer
preflight (`NativeRenderer.java:316..352`) preserves active editor identity,
Editable, ancestors/frame, composition and compatible binding. A retained editor
must keep a still-current connection through that ordinary accepted continuity.
After an actual focus-loss or a new creation attempt, it must require a new
connection rather than resurrect an earlier object.

## Per-dispatch authority and result contract

Every method checks the actual main Looper before examining stale state. For a
supported delegate route, capture one call object containing the actual current
Record/view/generation, connection-attempt identity, Editable identity, native
selection endpoints, composing endpoints and composing-span identities/ranges/
flags, and the **existing direct Mutation**. Use the real `input.open(record)`
and field focus. A field port may expose these checks to the wrapper without
making NativeField public or creating a second owner.

Validate text/completion/key proposals through the existing `plainProposal` and
16KiB UTF8/valid-surrogate buffer rules; preserve the current composing-only
UnderlineSpan allowance and Annotation allowance. Validate paste through the
existing NativeField route. Recheck the exact captured editor snapshot after
argument/proposal work and immediately before the one native delegate call, so
reentrant focus, selection, composition or buffer changes invalidate it. Reject
nested IME dispatch that would interleave another supported delegate inside the
same field call; ordinary TextWatcher/selection notifications remain native
callbacks, not another IME operation. Do not emulate the Android edit algorithm,
invent cursor equations or replace the platform's documented range handling.

On delegate return, recheck the captured scope, current attempt, same Record and
Editable, actual focus/input gate, and actual native selection/composition/buffer
validity. For a pure query, editor text, selection and composing snapshot must
still match; otherwise discard the result. For an edit, legitimate native
selection/composition changes are expected: do not require before/after equality
and reject every successful keystroke. Validate the returned native state using
the same field and method category; reentrant replacement/identity loss cannot
be accepted as an edit result.

Retain the original Mutation on the stack. The existing accepted-successor
boolean rule in `Mutation.result(boolean)` may acknowledge a completed true
result after a synchronous accepted feature event; it grants no next mutation,
event, native call, replay or replacement scope. Never fetch a fresh Mutation to
turn an obsolete call into a current one. Reads use the original strict result
scope and discard a changed snapshot; they do not use successor acknowledgement
to disclose data from a replacement editor.

Delegate `RuntimeException` and `Error` preserve their original identities and
are not converted to false/null. A fatal post-check/cleanup error wins over an
ordinary failure using the existing owner/renderer first-fatal precedence;
best-effort diagnostics cannot prevent cleanup or fatal escape. Do not retry,
replay, queue a delayed edit, reopen a terminal owner, or create a replacement
capture/readiness object. Existing owner cancellation/terminal ledgers remain
authoritative.

## All 38 dispatches, including inherited defaults

`contract.json` enumerates each exact descriptor and owning class; no method is
implicitly supported because a platform wrapper happens to forward it.

| Route | Explicit policy |
| --- | --- |
| begin/end batch; clear meta; delete both units; finish composition; set selection/region; editor action; fullscreen report; API31 IME consumption | Fenced single target call, preserving currently intended platform result. API33 region overload has the same fence. |
| commitText/setComposingText, both overloads; completion; key event | Preserve existing proposal validation and native dispatch with entry and return checks. TextAttribute goes to the corresponding actual API33 target method, without dropping metadata through a fabricated backport. |
| context-menu action | Fenced target call encloses the platform batch prefix/suffix; retain NativeField's existing supported menu/paste rules. |
| before/after/selected text; caps; API31 surrounding text; API33 snapshot | Fenced query and strict returned snapshot. A null snapshot remains null. No API33 wrapper-super dispatch. |
| extraction | Recommend only flags0 nonmonitor extraction in the complete boundary. Any monitor/unknown flag returns null before target work. This is a proposed tightening, not today's behavior. |
| getHandler | Main check then null, matching the exact native target's default scheduling; no delegate Handler or new queue. |
| correction, rich content, private command, replace, preview handwriting | Preserve existing unconditional false refusal, including no native target call. |
| perform handwriting | Preserve scalar UNSUPPORTED via caller executor/consumer when both exist, with no native target/gesture processing. Callback captures only consumer and constant. Never run editor checks on an arbitrary executor thread. |
| cursor request, one/two arguments | Recommend fenced disable-only zero mode/filter. Nonzero/unknown subscription/immediate flags return false before target work. This is an intentional tightening. |
| API31 explicit spell-check | Recommend false without target work until asynchronous native spelling effects are separately owned. This is an intentional tightening; it does not claim to disable all platform automatic spelling. |
| API34 text-bounds | Recommend immutable CODE_UNSUPPORTED result via caller executor and no target, field or native query in the callback. This is an intentional tightening. |

The last four ancillary policy choices require **explicit root selection**.
They are justified because extraction/cursor monitoring schedules work outside a
single dispatch, explicit spelling invokes a service/native span path, and
text-bounds has a callback lifetime. Entry/return guards alone do not own those
later effects. These operations were inherited, not previously refused. Native
IME behavior must be tested with the proposed refusals; no claim that every
keyboard gracefully tolerates them is made. If root preserves them instead, a
separate callback/subscription-lifetime contract and native evidence are needed
before calling the complete boundary accepted. Basic editing, completion,
selection, actions and nonmonitor reads are not removed by this proposal.

Official default-method audit: API28..30 has no interface defaults; API31..32
adds surrounding text, spell-check and IME consumption defaults; API33 adds the
three TextAttribute overloads, filtered cursor request and snapshot; API34 adds
handwriting, preview, text-bounds and replace; API35/36 add no further methods in
the named sources. Surrounding-text default composes getters, TextAttribute
defaults call old overloads, filtered cursor default may call the old request,
snapshot defaults null, and replace default sequences begin/finish/selection/
commit/end. Explicit declarations above prevent these from bypassing the
selected policy. In particular replace never reaches that default sequence.

## Close and batch cleanup: decisive blocker and minimal next contract

Revocation is scalar authority loss; it is not evidence of native cleanup. The
current wrapper skips native close when `open()` is false. EditableInputConnection
keeps its TextView's batch nesting contribution until its actual close balances
it, while BaseInputConnection close finishes composition and resets native IME
consumption. After TextView receives a successor Editable/connection, closing the
old target can therefore alter successor state. Simply skipping that close can
leave required cleanup permanently unattempted. Neither outcome makes an
incarnation-only change a complete development component.

Because owner seals also occur during valid synchronous text-change processing,
closing/restarting every field on every seal would break intended continuity.
Current cancellation only invokes toggle cancellation. `Mutation.cleanup`
exists but is unused, and NativeField's selection callback always obtains and
requires `record.mutation()`. A close after owner sealing can reenter that callback
and fail without an explicit scoped cleanup path. Pure wrapper extraction cannot
solve this. The minimal proposed **new contract**, requiring root amendment and
independent review before implementation, is:

1. Retain exactly one native target and the Editable identity with its local
   connection ownership record. Native-batch ownership is not inferred from a
   platform boolean result, an `endBatchEdit` return or a future stale call.
2. Before replacement/focus-loss close invokes any native code, revoke the old
   attempt and claim a field `CLOSING` guard; consume the exact old target into
   a one-shot close disposition. While CLOSING, **all** field native input,
   new `onCreateInputConnection` calls and candidate binds/preparations that could
   replace this field/Editable refuse before native work. A nested create during
   closing returns null and cannot overwrite the already-claimed outer attempt.
   Do not install a successor until this exact close returns safely.
3. An explicit narrow renderer/Record helper supplies the already-authorized
   live/transaction scope, or a sealed cleanup scope tied to the actual direct
   fence. Scope selection is not a new input token or readiness mint. It must
   verify exact retained Record/view/Editable and no successor before closing,
   retain that scope across the one native call and check after return. Temporarily
   scope the Record's native callbacks and suppress feature/interaction events
   for this cleanup; do not suppress owner/observer terminal invalidation. Existing
   selection/drawable/focus callbacks must not acquire a fresh live scope inside
   sealed cleanup. These are actual views/renderer changes, not host-model facts.
4. Invoke the retained target's actual `closeConnection` once while the old
   Editable is still its target. Reentrant callbacks cannot create or bind a
   successor while CLOSING. A close notification on an already disposed old
   wrapper only consumes its local state; it never delegates onto a successor
   buffer, invalidates the successor identity or clears successor composition.
5. If the exact target/buffer/scope cannot be established, native close throws,
   or owner invalidation occurs during close, **quarantine and terminal-retire
   the owner before allowing a successor buffer/connection**. Reuse the existing
   renderer terminal sink and original ordinary/first-fatal precedence; do not
   add a second owner or swallow the failure as a rejected keystroke. Keep the
   old target and its close outcome recorded as failed/uncertain, do not retry,
   and never report the native batch as reclaimed from a throw or ordinary return
   alone. A quarantined field remains unavailable and cannot rebind/reopen.
6. Ordinary compatible engine echoes and temporary operation seals neither close
   nor revoke a healthy connection. Permanent editor/owner retirement and actual
   field focus/window/detach/visibility loss must use the selected close-or-quarantine
   path. If a close is required while an existing edit is still on the native
   stack, consume scalar revocation immediately, prevent any successor, and let
   root select a safe unwind disposition; do not recursively close that target
   from inside its unfinished edit. Without that selected unwind/terminal policy,
   this row is an explicit implementation blocker.

The helper must be coordinated with the current renderer roster and
commit-to-finish interval; no extra native work may be inserted inside that
accepted interval. If this cannot be implemented without owner/core changes,
stop and amend ownership again. No current native receipts establish this close
protocol. The finite attempt model only demonstrates identity ordering; it does
not model/reclaim real TextView batch ownership. The complete editor prerequisite
therefore remains unselected even though the signature experiment compiles.

## Adjacent preflight and ownership/dependency order

Prefer one **separately named adjacent preflight sub-slice** in the same future
source-pair migration, rather than inventing pre30 accessibility semantics. Add a
pure capability preflight in `NativeRenderer.prepareV2` after packet/resolver
validation and **before the first shadow Record/native preparation**. Reject
API28 FieldRecipe and selectable TextRecipe; reject any pre30 required
`accessibilityValue` by property presence, even the empty value. This rejection
must also precede any preservation shortcut. Do not substitute labels or append
value text. Move API29 Drawable setters and API30 state-description calls into
guarded separately emitted helpers so base bind code does not contain the later
method references. No native TalkBack equivalence is claimed.

Selectable TextView appearance needs its own review: current handles are only
installed in the FieldRecipe branch. Do not quietly style selectable text using
an unselected field-paint policy, or call platform-default handles shared-design
evidence. The proposed API28 selectable refusal is mandatory; expanded selectable
support remains separate.

| Future ownership, to be selected by root | Dependency / limit |
| --- | --- |
| `NativeAppearanceViewsV2.java` NativeField, connection-attempt helpers, bounded scalar lifecycle callbacks and scoped close callbacks | First select exact close/quarantine, entry/return and continuity contract. Incarnation-only source evidence is insufficient for a usable component. |
| new `NativeEditorConnectionV2.java` | After synchronous behavior review; 26/3/5/4 declaration split, one factory, same field port, complete async policy selected. |
| narrow `NativeRenderer.java` exact-target close scope/quarantine helper, input/prepare closing gates, plus separately named capability preflight; nested API29/30 setters in views | Close ownership amendment and independent review are prerequisites; preflight selection remains separate. Both guards unchanged; no extra native work in commit-to-finish. |
| new explicit-source host test/leaves and runner under `native/android/tests/` | Compile the actual selected sources, not this model or unrelated harness; freeze finite leaf roster before execution. |
| frozen `AndroidSDKCompatibility.swift` policy authority plus focused common/direct rendered-driver admission tests | Root selects a successor ID only after native candidate freeze. Profile4's adapter23 becomes24 if one new source file is selected; nested API helpers add emitted classes rather than source files. Changed view/renderer bytes change that projection; SDK22 stays unchanged unless an actual SDK contract changes. Historical profile4 receipt/lock stays immutable. |
| root metadata and delivery | Root-owned PLAN/STATUS/work-graph/gates/verification and coherent validated commit/push/CI. This lane edits none of them. |

No dependency, manifest permission, credentials, published artifact or generated
public app routing change is required. The proposal selects no profile5 or other
successor. Both SDK36 guards, private dedicated-root restriction, V1 Activity,
JNI/Swift state, accepted owner/coordinator, descriptor/wire identity, signer,
OTA authority and source-pair admission flow remain outside this lane.

## Acceptance controls and current evidence limits

Required actual-source host tests must retain an old connection through
focus-loss/refocus, native close, a second creation, record reuse, Editable
replacement and owner retirement; every later stale query/edit must stop before
target access. Reentrant outer/native creation must test nested success,
nested null and nested ordinary/fatal throw; the outer attempt never overwrites
the newer attempt. Current native null/throw/fatal paths revoke before unwind.
Normal engine echoes preserve the same connection, Editable and composition.

For every supported method test off-main-first, sealed/terminal/stale ownership,
focus loss, changing/foreign Record, stale session, selection/composition changes
during proposal and during return, retained accepted successor, native ordinary/
fatal throws, malformed/oversize/spanned proposals and no replay. For queries
test no result disclosure after a changed snapshot. For edits test legitimate
selection/composition progress. Test unsupported/default routes with a target
sentinel proving zero target calls, no monitored extraction/cursor/spell/text-bound
work under the proposed policy, no handler creation and scalar-only callbacks.
Explicitly test live batch close, repeated/stale close and cleanup uncertainty;
do not relabel an unclosed native batch as reclaimed.

This proposal executes only 9 negative contract controls, 52 finite state-model
cases, official metadata checks and an **unselected signature experiment**.
Both prototype sources deliberately lack product authority and must never be run
or packaged. Java17/official SDK37 compilation and D8 min28 succeeded;
the real classfile parser checks all 38 declarations and emitted Android
type/member references against each class's floor. It covers fields, descriptors
and generic type references as well as method bodies. D8 output is retained,
but not executed. This is not the actual product closure, an ART verifier,
API28 linkage, a keyboard experiment or OTA authorization. The initial checker
failed on official minor API metadata `36.1`; the retained first-attempt error
and corrected numeric comparison are recorded without rounding that floor down.
A later model extension initially placed a test block in the wrong function;
its retained second-attempt NameError was corrected before the final passing run.

Actual Android class loading on API28..37, native IMEs/composition/batches,
monitor/refusal behavior, focus/lifecycle, native cleanup, TalkBack and design
parity remain pending. Computer use/capture/UI/emulator/simulator/physical runs
and process inventories were not performed. Only host tool children were
started; the compiler's owned temporary directory was removed. Other projects'
processes and data were not inspected or changed. Public integration,
immutable published separate-repository FieldLog, signing/store/operations,
final phones and accountable GA acceptance remain pending.
