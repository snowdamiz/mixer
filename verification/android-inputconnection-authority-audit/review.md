# API36 private NativeField InputConnection authority audit

Source review and bounded host dispatch evidence only. No implementation or new
rejection has been selected. The exact present source has authority gaps in
inherited reads, platform requests, context-menu batch effects, and connection
revocation. The existing widget protects the eventual menu action; it is incorrect
to call that action an unfenced paste/cut bypass. Entry/return checks alone also
cannot fence native work occurring inside a delegate after synchronous reentry.

The reviewed canonical `NativeAppearanceViewsV2.java` is 81,532 bytes, SHA-256
`a217d0b178869f3e5c3fc2d80f30f559a22c76a303195e62bfcb73d3cce91cce`.
The exact source closure, including current owner/core/renderer/observer/platform
reader/coordinator and relevant concrete host tests/leaves, is copied under
`inputs/` and individually hashed in `collection.json`. That frozen closure, not
mutable root status, is the authority for this review. Context supplied by root:
accepted owner C5, native A, profile4; context HEAD
`a24011487bfc368512fa52125241d9c46e7cdd3f` is not independently inspected here.
The copied root profile4 acceptance is exactly SHA-256
`83f83c42d53b8bc5df50eaf84f751236f39d3fa66c827bf4e55635a4d424eea7`;
it references native acceptance
`0c15ca808c2f5684d768125674cdfc0bf48bff672193f79fcaaee47726bf2478`.
This lane did not independently rerun those historical acceptances.

## Official interface and delegate routes

The installed official SDK37 `android.jar` was enumerated with the existing
Homebrew JDK `javap -p -s`; full stdout is retained. `method-inventory.json`
enumerates **all 38 exact method descriptors**, abstract/default status, and
their API floors from official SDK37 `data/api-versions.xml`. All methods in
this interface inventory predate API36; this does not qualify API37 execution.
The current anonymous proxy implements 24 descriptors and inherits 14. The
official Android16 `android-16.0.0_r1` sources are retained unmodified under
`official/aosp36/`, with exact URLs, bytes and hashes in `collection.json`.

The [official wrapper source](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r1/core/java/android/view/inputmethod/InputConnectionWrapper.java)
explicitly forwards every one of the 38 methods directly to `mTarget`; it does
not route its implementation through overrides of sibling proxy methods.
Accordingly, overriding `getTextBeforeCursor`, `beginBatchEdit`, or
`setSelection` on the outer proxy does not intercept a delegate's internal calls.
The wrapper's extra `setTarget(InputConnection)` is not an interface member.
Its concrete nonnull target and `mutable=false` make `setTarget` throw before
replacement. There is **no present mutable-target exploit** in the reviewed code.

| Current inherited descriptor family | Official API36 route and authority consequence |
| --- | --- |
| `getTextBeforeCursor(int,int)`, `getTextAfterCursor(int,int)`, `getSelectedText(int)`, `getCursorCapsMode(int)` | Wrapper forwards to BaseInputConnection using EditableInputConnection's retained TextView editable. Reads selection and/or text. No Mixer main-thread, focus, record, closed-proxy or return check occurs. Styled reads may carry spans. TextWatcher and InputFilter are not read barriers. |
| `getSurroundingText(int,int,int)` | Delegate BaseInputConnection reads its retained editable and selection, normally directly. Its fallback can call the interface default, which composes before/after/selected reads. Those calls are on the delegate, not this proxy. No Mixer authority before/after the read. |
| `takeSnapshot()` | Delegate BaseInputConnection reads composition, surrounding text and caps into a snapshot. The interface default would return null, but that default is not the actual delegate route. No Mixer authority or atomic owner check. |
| `getExtractedText(ExtractedTextRequest,int)` | EditableInputConnection extracts text. MONITOR also retains the request in Editor state via TextView.setExtracting, hides cursor/span controllers, stops text action mode and resets selection touch offsets. Later Editor reports can send extracted text through InputMethodManager. This is both a read and a subscription/native-state effect, without Mixer authority. |
| `performContextMenuAction(int)` | EditableInputConnection invokes TextView.beginBatchEdit, then virtual NativeField.onTextContextMenuItem, then TextView.endBatchEdit, and returns true regardless of the widget action result. The NativeField override checks main and input; stale widget action returns false. The preceding/following batch edits remain outside that widget barrier. Off-main execution may throw at the widget after begin, before end: the official method has no finally. |
| `performSpellCheck()` | Actual delegate calls TextView.onPerformSpellCheck and returns true; it does not use the interface false-return default. If a spell checker exists this can inspect full content, request work, later change suggestion/check spans, and schedule parsing. Those continuations do not pass through the Mixer proxy or text replacement filter. Availability is native-dependent. |
| Both `requestCursorUpdates` overloads | Actual delegate validates known flags, calls IMM.setUpdateCursorAnchorInfoMode, updates Editor cursor mode/filter, and may request layout. The two-argument form ORs mode/filter into the one-argument delegate. Later Editor position reports check Android's active connection, but have no Mixer presentation/owner check. Passing zero is native state mutation too. |
| `requestTextBoundsInfo(RectF,Executor,Consumer)` | Actual delegate computes native text geometry and invokes the supplied executor with a result callback. The executor can run inline or later. The inherited route has neither entry nor callback/return authority. Handwriting being rejected does not automatically reject this separate method. |
| `getHandler()` | Exact delegate inherits BaseInputConnection's constant null. No handler is exposed in this exact route. Still inherited and uncontrolled; do not claim it currently leaks a handler or allows intercepting callbacks. An explicit fixed-null bootstrap result can preserve behavior without native delegate access. |
| `reportFullscreenMode(boolean)` | Exact BaseInputConnection implementation returns true and performs no state change. It is uncontrolled delegation, but no current native fullscreen mutation is proven. Retaining an explicit appropriately scoped result is not equivalent to introducing a new feature rejection. |

Underlying defaults must remain distinguished from actual routes. The interface's
TextAttribute commit/composition overloads call their legacy counterparts; its
spell-check and IME-consumption defaults return false; handwriting and bounds
defaults execute unsupported-result callbacks; preview defaults false; cursor's
two-argument default calls the old method only with zero filter; snapshot defaults
null; replaceText default sequences batch/finish/selection/commit/end. The actual
wrapper forwards to its delegate instead. The present NativeField overrides all
TextAttribute overloads, IME consumption, handwriting, preview and replaceText;
these defaults do not silently bypass those particular overrides.

## Current protection and its limits

The 18 supported explicit descriptors are begin/end batch, clear meta states,
close, two commit-text forms, two composing-text forms, two composing-region
forms, finish composition, both deletion forms, selection, editor action, key
event, IME consumption and completion. They check main before `open()`, capture
Mutation, and verify its result/return. Most check field focus through `open()`.
Commit/composing/completion additionally validate a plain proposal, combining
the real composing range or selection with the proposed text, and validate the
whole buffer. `sendKeyEvent` validates Unicode for key-down insertion. Exceptions
and fatal Errors are not converted to successful returns here.

Six other descriptors are already explicitly unsupported: replaceText,
performPrivateCommand, performHandwritingGesture, previewHandwritingGesture,
commitCorrection and commitContent. They require main and do not forward.
Handwriting executes the caller's executor to deliver a constant unsupported
result even when stale; that has no native text payload, but it is still external
work and cannot be called a no-op. A future adapter must preserve required refusal
completion without treating the callback as native-edit authority or swallowing
executor/fatal failures.

The actual widget's filter guards replacement text and validates whole-buffer
contents; it is not a read, span, subscription or batch-edit barrier. The watcher
checks input before publishing a textChange event. Its before/onTextChanged
callbacks are empty, and afterTextChanged has no post-event Mutation check.
NativeField.onSelectionChanged checks Mutation before/after super, then reports
interaction when current; the selection has already been changed when this
notification runs. Its Mutation admits draw authority, not field focus by itself.
The context-menu override fences the action and validates clipboard text before
paste. Accessibility/key actions have their own entry/proposal checks. None of
these controls fences every other operation in the inherited table.

`NativeRenderer.inputV2().open` checks exact current Record identity, enabled,
attached, shown and window focus, plus presentation/environment and scalar input
fences. The proxy adds field focus. `Record.mutation()` is main-thread checked.
`Mutation.result(boolean)` deliberately permits a successful completed operation
after a synchronous accepted feature event published a successor presentation;
it does not acquire replacement authority or call native code on that return
path. This is intentional existing behavior, not an instruction to reject every
keystroke that synchronously updates state. Generic result requires the original
Mutation to remain current. Neither variant provides omitted inherited reads a
return barrier, and the boolean form alone does not recheck field focus/input.

An outer return check cannot undo work already performed inside the delegate.
Official BaseInputConnection's text replacement changes selection, replaces
content, can reposition selection again for position zero, then ends the batch;
EditableInputConnection.commitText subsequently updates error state. A synchronous
TextWatcher feature event can occur during replacement, before that continuation.
Likewise the menu delegate ends its batch after the widget returns. A repair must
name the permitted native completion scope after benign successor publication
and the fail/cleanup behavior after terminal/focus/owner loss. Checking a boolean
only at the outermost return cannot prove arbitrary delegate internals safe.

## Connection identity and preserved editor continuity

There is no field-local active proxy/closed identity in the current source. The
proxy captures the same NativeField/Record; its `open()` asks whether that record
is current **now**, not whether this connection remains the admitted incarnation.
`closeConnection()` returns without native close when input/focus is unavailable,
and when it does delegate it records no local revocation. A later focused/current
Record therefore admits the old proxy again. Creating another connection through
the same field also does not revoke its predecessor.

The [official EditableInputConnection](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r1/core/java/com/android/internal/inputmethod/EditableInputConnection.java)
uses a negative batch nesting value after close to stop subsequent begin/end
batch calls. It still retains its TextView, and getEditable still returns that
TextView's buffer. BaseInputConnection reads, commitText, composition and selection
do not have a universal closed guard; callers ignore unsuccessful beginBatchEdit
when performing some work. Thus native close is not proof of blanket revocation.
Whether Android normally prevents a stale IME/remote endpoint from delivering a
particular call is separate and unrun. The product proxy's retained-call control
is absent regardless; this audit does not claim a demonstrated remote exploit.

The frozen concrete host leaf is stricter than official source: it introduces a
`closed` flag and checks it in insert, selection, deletion and several other
methods. The existing `imeClose`/close assertions only verify forwarding and
that leaf flag. They cannot establish API36 revocation. Existing recovery tests
also intentionally reuse a connection after focus/pause recovery; native/session
identity has not been established by that host assumption. Their receipts remain
finite historical evidence, not false new platform qualification.

Current NativeField has no onFocusChanged override. Its generic View focus
listener only records interaction when input is open; it does not revoke a
connection before platform focus effects. The onFocusChanged/onWindowFocusChanged
methods near the end of the file belong to NativeSwitch, not NativeField.

Editor continuity is a binding requirement, not optional polish: renderer
targets preserve the same Record/View for matching id/generation/kind; active
editor preflight requires equivalent binding, ancestors and frame. Acknowledging
the real buffer removes `value` from property equality, preserves the actual
Editable object, selection and composition, and avoids setText. A connection must
survive these ordinary synchronous accepted keystrokes/preserved bindings.
Capturing a presentation token permanently at connection creation, restarting
the IME on every binding, or replacing the editable would break that behavior.

## Smallest implementation boundary for root selection

1. Introduce a private field-owned immutable-dispatch adapter for the admitted
   API36 lane. Prefer a direct InputConnection implementation with a final target,
   explicit implementations of all 38 current descriptors, and an inventory
   guard for future SDK changes. This removes inherited forwarding/defaults and
   the unnecessary public setTarget surface. Keeping a wrapper can work only if
   every route is explicit and immutable target behavior remains checked; a
   current retarget security bug is not the reason for the direct design.
2. Use one local current-connection identity retained by the actual NativeField,
   plus each adapter's permanent retired/close disposition. It supplements exact
   current Record/View/owner checks; it is not a second owner/core generation,
   readiness mint, queue, or observer slot. On new creation, reserve the local
   identity before invoking super/native creation. If that call reenters and a
   newer inner creation wins, the older outer return may not publish over it.
   Failure/return cleanup may retire only the identity it still owns. Return no
   usable adapter when that claim is lost. Close/focus-loss/detach/owner retirement
   revoke local dispatch before invoking external native work. Do not reinstate
   old identities on focus regain. Normal preserved binding/keystrokes keep the
   same active identity and real native target, rather than renewing it.
3. Each synchronous operation checks main and exact field-local/current-record
   authority before any native call. Capture one Mutation per operation and use
   it through return. Reads discard payloads if authority is lost before return;
   preserve Android null/zero failure conventions. Do not expose live mutable
   buffer/foreign spans by fabricating a translated read. Supported edits retain
   current plain proposals/UTF bounds, real selection/composition, and intentional
   completed-successor boolean semantics. No call may acquire replacement
   authority halfway through an old operation. `getHandler` is an explicit
   constant-null bootstrap route without native delegate work; its calling-thread
   contract must be tested separately, rather than blindly imposing UI-thread
   enforcement on a platform bootstrap hook.
4. Menu dispatch must enter the adapter barrier before the delegate begins its
   native batch. Preserve the widget action/proposal guard. Capture and review
   the native batch/error/selection continuation across reentry; a post-delegate
   require cannot stop intermediate work. Close must permanently retire the
   adapter before its native call and distinguish dispatch authority from a
   captured, once-only cleanup disposition. This has a material ordering
   constraint: official close finishes composition and changes IME-consumption
   on the shared TextView before draining this delegate's own batch nesting.
   Calling an old delegate's close after a successor begins editing could affect
   the successor's Editable/composition. Simply refusing stale close can instead
   strand old native batch ownership. Revoke dispatch, mark the exact old target
   cleanup ATTEMPTED, then dispose it under a field-local closing/nonreentry guard
   **before** replacement native creation/publication or successor editing. A
   reentrant creation while closing must not call super or admit a target; a
   reentrant close must not duplicate disposal. Preserve returned versus failed-
   uncertain disposition; a returned close is not physical reclamation.
   When called after focus/owner loss, the new ordinary open predicate cannot be
   used to reopen or silently assume native close happened. Cleanup while sealed
   needs existing owner cleanup/fatal discipline and exact retained target,
   outside an active coordinator operation. If close throws, old ownership is
   uncertain, a successor already exists without prior disposal, or reentry
   prevents safe ordered disposal, quarantine the field from dispatch/replacement
   and enter the existing owner terminal/fatal path; do not skip cleanup and
   continue live. A concrete reviewed failure-reporting path from field to owner
   is required because the present Input interface has no such method. Changing
   that interface or renderer disposal hook requires root coordination. Source
   inspection does not prove that the guard alone controls all platform
   finish-composition/batch/subscription continuations. Until exact disposition,
   ordering, terminal/fatal reporting and continuation controls are implemented
   and independently reviewed, a local-identity patch is **not a complete repair**.
5. Preserve existing six unsupported routes. Do **not** casually add rejection of
   extraction MONITOR, spell-check, cursor updates, text bounds, or snapshots:
   those currently reach native support. New rejection is a root policy choice
   with compatibility impact, separate from repairing omitted guards. A snapshot
   is synchronous data and can receive entry/return checks. Bounds callbacks need
   a per-request immutable owner identity and result disposition at execution,
   including caller executor reentry, off-main callback threads, revocation and
   fatal precedence; do not read native state on a later arbitrary executor.
6. MONITOR, cursor subscriptions and spell work require a **separately explicit
   native continuation contract**. Android Editor/SpellChecker callbacks bypass
   the adapter; wrapping only their request methods does not enforce Mixer owner
   authority on later data/spans/layout/IME updates. Identify supported public
   cancellation/retirement and actual remaining subscription state first. Hidden
   TextView.setExtracting or private Editor fields are not an allowed repair.
   Android active-connection checks alone are not Mixer presentation authority.
   Native close does not clear every subscription in the inspected source. A
   separate field-local subscription/disposal model may be necessary; do not add
   it to Observer's eight slots or globally generation-stamp normal edits. If an
   exact public-native contract cannot be implemented in the bounded slice, root
   may explicitly select temporary fail-closed results and record the resulting
   IME extraction/fullscreen/suggestion/candidate-cursor/bounds loss. That is a
   new product limitation, not the old unsupported behavior. This audit selects
   neither those rejections nor pretend-preserved asynchronous support.
7. Isolate later method signatures/defaults in separately emitted API adapters
   and SDK-guarded factories for a later compatibility slice. TextAttribute and
   snapshot signatures (33), bounds/handwriting/replace (34), IME consumption and
   surrounding/spell (31) cannot remain in an API28-linked base just because a
   method returns false. Coordinate this dispatch contract with the separate API
   isolation proposal after both packets are final. Preserve **both SDK<36 guards**;
   no API28–35/public V2 support is enabled by this source repair.

None of this changes core eight-slot ownership, retained registration identities,
first fatal/terminal precedence, synchronous nativeInput with no replay, or the
successful commitV2-to-finishV2 interval. That interval remains scalar/prepared
swaps only: no adapter/callback/native read/setter/allocation hook is added there.
Any change requiring coordinator, owner core, schema/profile or delivery updates
needs root coordination and a separately bounded selection.

## Evidence and next verification

`scripts/probe.py` copies unchanged actual production Mutation,
onCreateInputConnection and onTextContextMenuItem blocks into finite authored
surroundings and compiles the unchanged official API36 wrapper. Its interface
leaf mirrors all 38 SDK37 method descriptors but deliberately does not execute
Android interface defaults. Target is a JVM reflection proxy, not TextView.
**26 host checks passed**: 13 inherited non-menu descriptors forward off-main
and stale (including the bounds callback); explicit begin rejects off-main;
the menu's native batch calls occur while the widget rejects; inherited read
returns after a controlled loss; current proxy dispatches after close and after
another creation; immutable setTarget rejects replacement. These are witnesses
of the current dispatch shape only. They do not prove native batch/layout/span/
IME effects, actual lifecycle callback order, remote reachability or a repair.

`scripts/check.py` verifies frozen source/official hashes, exact SDK descriptor
coverage, decisions, source spans and packet flags; negative controls reject a
missing descriptor, false menu-bypass claim, false native-close revocation claim,
unselected new restrictions and native-release promotion. It is packet
consistency evidence, not engine behavioral coverage or OTA authorization.
Logs preserve initial java_home lookup failure, inventory count assertion
corrections (38 methods/24 overrides), and failed host-probe compilation attempts
before annotation/descriptor leaves were made explicit. No failed command is
counted as passed.

Future implementation checks must compile the actual complete adapter/views and
test every descriptor for main/stale/focus/closed/superseded/current behavior,
entry and return reentry, newest nested creation, close/focus invalidation before
external work, no old-proxy recovery, generic read payload discard, unsupported
callback completion, terminal/fatal/cleanup uncertainty, and benign synchronous
successor continuity. Target probes must distinguish native before/inside/after
effects, instead of treating a beforeReturn hook as a complete platform model.
Selected async support/restriction needs explicit positive/negative lifetime
receipts. Native execution will eventually cover actual IME/clipboard/fullscreen,
composition, batch balance, cursor/extraction/spell/bounds callbacks, focus,
reattach/new connection, retained Editable identity, and native cleanup.

Computer use, capture, UI automation, simulator/emulator/phone runtime and process
inventories were not used. No native/capture process was started, so none required
cleanup. Host subprocesses were reaped by subprocess.run. Other projects'
processes/data were not inspected. Canonical product code, root metadata, Git,
dependencies, credentials and publication were unchanged. Native class loading,
runtime/physical matrix, TalkBack, design parity, immutable published separate-
repository FieldLog, signing/store/OTA/operations/accountable GA remain pending.
