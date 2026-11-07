# Concrete B migration without production-guard suppression

The old B loop sets `record.changing=!state.equals("successor")` and removes the
editor listener outside the successor case. Its old current assertion also
requires an unchanged token for every family and false for performEditorAction.
That setup suppresses genuine feature delivery. The new editor deliberately
requires `!record.changing` at live entry; the observed beginBatch failure is an
invalid setup, not evidence that ordinary healthy batch fails. Keep that guard.

Select **normal controlled leaves with a per-family case split**. Do not add a
transport mode, clear a product denial latch, null the real listener, skip
watchers, or write changing except in the distinct invalid-entry case below.
The machine-readable `family-migration.json` gives all 16 exact names, counted
leaf names, effects and 96 designed state rows. This data is a design, not a
record of passing cases.

| Families | Actual historical leaf effect | Ordinary healthy expectation | Explicit successor coverage |
|---|---|---|---|
| beginBatchEdit, endBatchEdit, clearMetaKeyStates, setImeConsumesInput | Counted target call, no text or listener operation | True, unchanged presentation token, no feature event | Inject one labeled same-buffer feature event at target beforeReturn |
| commitText and attributes, commitCompletion | Insert via hostReplace, real filter/Editable/selection/TextWatcher path | True, genuine textChange and compatible successor, same Editable | Natural genuine event; verify exact new token and retired old Mutation |
| setComposingText and attributes | Same real insert/watchers, then composing spans | Same genuine delivery, preserve actual composition result | Natural event plus exact final composition snapshot |
| deleteSurroundingText, deleteSurroundingTextInCodePoints | Real deletion via hostReplace/watchers | True, real changed text event and compatible successor | Natural event; non-BMP fixture required for codepoint path |
| setComposingRegion and attributes, finishComposingText | Direct composing-span changes | True, exact composition result, no text event/token change | Labeled injected same-buffer feature event plus exact composition evidence |
| setSelection | Native selection call and actual onSelectionChanged | True, exact selection, no text event/token change | Labeled injected same-buffer feature event; actual selection callback stays enabled |
| performEditorAction | Installed IME_ACTION_DONE listener sends submit | True with genuine submit and compatible successor | Natural submit event; no listener removal |

The injected event is a deliberately controlled feature stimulus: at the chosen
target beforeReturn, perform exactly one same-buffer hostReplace with matching
app reply. Retain real InputFilter and all TextWatcher/selection callbacks. It
tests completed-original-result behavior in the presence of a synchronous
compatible feature transaction. It does **not** claim beginBatchEdit, meta,
composition or selection normally sends textChange on Android. Record the
injection separately in the row, its probe event, actual bytes and class/BCI
identity. Never relabel it as native method behavior.

For every family retain all six applicable states. Healthy/current uses a fresh
field with changing=false, the actual installed listener, valid explicit cursor
and app reply matching the native result. Current means originally healthy;
text/submit cases legitimately publish a successor. The successor row must prove
the exact old Mutation no longer authorizes work while the boolean completed
result survives under the existing scalar rule. Neither row grants query,
setter, bind/layout or successor authority after return.

Terminal calls owner.close, dirty calls onPause and stale alters the actual
environment tuple without notification before trying the captured connection.
They must return false before any new target entry. Record no feature event and
no new successor from that call. Do not replace real owner/core/coordinator
paths with scalar flags or equate lifecycle dirty with stale-capture validation.

Fatal throws one exact authored fatal at the selected target's beforeReturn.
Text/submit callbacks remain active: if a real transaction already completed
before the fatal, record it. Require the exact fatal to escape and occupy the
first-fatal ledger, gates to close and late ordinary work to stop. Disposal may
rethrow the same retained fatal; cleanup must account for and compare its identity
without hiding an unrelated failure. Failure rows record actual outcomes and
remain failures until corrected; they may not be deleted to preserve an old total.

Add changing=true as an independent invalid-entry control: acquire a healthy
connection first, capture target-entry counts, set changing, call beginBatch and
the other representative read/write paths, require clean refusal with no new
target call and no fabricated terminal success. Restore only this test's flag
for fixture disposal. This verifies intentional guard behavior, not ordinary
current-state behavior.

Every text append fixture must first assert initial selection **0,0**, explicitly
set the cursor to text.length(), and then expect hello+z=helloz. Keep the pinned
default movement behavior. Deletion must likewise choose a nonempty selection
or cursor so its expected event/value is explicit. Do not change host default
selection to make old tests pass.

sendKeyEvent is an intentional direct refusal; it moves out of the positive
family list. In healthy, changed/successor, terminal, dirty, stale and fatal-hook
fixtures it returns false with no target/wrapper entry and unchanged text from
that call. A native-target fatal hook cannot fire for a refused operation. Keep
the other unsupported content/correction/private/handwriting/replace operations
and wrong-thread/unsupported argument controls. Exact editor descriptors, null
handler bootstrap, lifecycle cleanup and query snapshot rules remain mandatory.

The support harness executes nine examples of this split against the exact old
unaccepted classes; its 61 assertions are complementary preparation evidence.
It uses the frozen B Fixture by reflection and its packet producer/controlled JNI
leaf. No product bytes are compiled or rewritten by that harness. The selected
correction must get a fresh independently reviewed suite with every designed
row plus its own prepared/hostile/focus-history controls. Preserve both ordinary
two-field failures as positives; retain new loss/gain at every stage, repeated
already-latched loss, busy/fatal cleanup, restoration and event-evaluation reentry.

Native Android movement methods, batch behavior, callbacks, IME implementations,
keyboard, accessibility and focus timing remain paused/unverified. Mechanical
leaf behavior and host success cannot claim native equivalence.
