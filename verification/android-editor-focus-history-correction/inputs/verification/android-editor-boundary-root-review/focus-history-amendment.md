# Fresh field operations after settled focus loss

This additive correction preserves the cleanup contract, both frozen replacement
amendments and their recorded failures. The candidate sealed by
`4c906824fe5e2e925c3ad5ca7c4ae94ba3b1e7dd6c58e77805dd3862c165c9a3`
is not accepted. The independent findings packet is
`verification/android-editor-replacement-independent/actual-review/findings-focus-history/seal.json`,
SHA256 `a6d68fe3efd4d406b7817c73fc6307b2bb505dd07a168df900410246a5020885`.
Root verified all 20 members. Its `focus-history-requirements.md` is binding with
the clarifications below.

The supported behavior includes a field A that previously held focus, then
completed exact old-target close before another field B becomes focused.
Ordinary ACTION_SET_TEXT on enabled/current/retained/window-focused A must still
work. An ordinary compatible B edit must preserve A without failing because A
was previously focused. Neither operation revives A's old connection or permits
a fresh IME connection on unfocused A.

Separate connection authority from fresh field transaction authority. Keep
`focusLost`, the old attempt's permanent revocation and close disposition intact.
Do not weaken ordinary IME/widget entry, captured EditorLease identity, native
depth, pending close, quarantine or commit barriers. A successful ordinary
transaction must not acquire target authority from a returned/revoked attempt.
Fresh field work requires the original current Mutation and exact retained
Record/View, settled predecessor custody, compatible preservation and unchanged
native snapshot where required. A replacement continuation cannot authorize
bind/layout. This amendment grants no incompatible arbitrary setter policy.

Prior local focus loss alone must not poison a compatible retained Binding or
geometry transaction. Cover the complete path, including renderer availability,
field callbacks, actual same-buffer preservation and one ordinary completed
replacement event. If a new exact field-only callback scope is needed, propose
its ownership, entry/exit, lifetime and public internal signatures to root before
dependent edits. Never substitute an old editor lease, synthesize focus gain,
clear a loss latch to pass, or make generic availability always succeed.

New loss during a fresh operation is distinct from settled history. Select a
bounded, exhaustion-checked loss observation identity, or an equivalent exact
reservation marker, captured before callable entry observations and mutable
payload reads. Record each actual loss occurrence even if its boolean latch was
already true. Subsequent gain cannot erase that observation. Revalidate after
callable getters and at each stage boundary. New own or foreign field loss after
replacement entry invalidates that replacement's success authority through
SNAPSHOTTING, CLOSING, NATIVE and final validation. Conservatively retain existing
terminal/uncertainty and first-fatal behavior when native work or an unsettled
foreign suffix has occurred; never report successful partial replacement.
Required superclass and captured cleanup suffixes retain only their exact
existing authority. No foreign close is granted by another field's reservation.
No new asynchronous retry, owner/core slot, cap increase or synchronous owner
resumption after busy clear is selected.

Window-focus, visibility, aggregate, detach and permanent denial remain effective
under the existing policy. This amendment exempts only settled local focus
history for the specified fresh non-IME and compatible transaction paths. It does
not broaden unsupported API levels, EditorInfo subclasses, native operations,
public V2 or GA.

Implement in a new complete-source derivative. Preserve the current packet and
both failed compatibility witnesses. Run the prior 52 groups, the independent
prepared and hostile controls, both real two-field failures as required positive
cases, changed/same/empty/Annotation replacements after prior blur, old-adapter
refusal and fresh-IME refusal while unfocused, compatible B echo preserving A,
new own/foreign loss and loss/gain at every reservation stage, repeated loss when
already latched, other denials, marker exhaustion, first-fatal/busy cleanup and
all 38 interface descriptors. Pinned SDK javac/D8 remains unsigned host evidence.
Freeze exact source, commands, outputs and cleanup for independent review before
canonical integration. Native runtime remains paused.
