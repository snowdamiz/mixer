# Private native pan commit reentry contract

The accepted semantic/interruption checkpoint is `cf52825`. Its carrier passes
real gesture interruption and direct primary callback cases, but those tests do
not exercise a synchronous state observer changing the binding or input gate
inside the final native pan commit. The current pan release assigns selected
state, notifies `panAccepted`, and then emits `valueChanged`; a callback can
therefore change the value or admission before that event is sent. This source
finding is not itself a native failure receipt.

A separate private candidate must make that final transition transactional.
Snapshot the retained value, binding generation and interaction generation;
prevent nested semantic activation; clear the ending gesture's preview; assign
the proposed selection; and recheck current admission before emitting a value.
A cancellation, binding replacement, disabled/stale gate or interaction
invalidation during assignment must reject the old commit. Preserve a newer
binding, restore the prior value only when its binding generation is unchanged,
and emit no event for a rejected or no-change commit. Once a transition is
accepted, dispatch its one value event before the informational completion
observer. A later binding write is silent and cannot retroactively alter the
recorded event payload.

Use a shared busy guard for primary/accessibility and pan commit entry. Track
interaction invalidation separately from binding generation so a cancellation
or direction change cannot disappear merely because the bound value stayed
the same. Existing primary admission must retain its binding and gate checks.
Do not alter pan geometry, native touch admission, paint or public API surface.

Fixtures must trigger each callback from an actual public XCTest drag release,
record native recognizer state and identity, and establish initial value anew.
Cover replacement binding, gate closure, disable, explicit cancellation,
direction change, nested primary/accessibility calls and a binding change after
accepted event dispatch, from both starting values. Preserve event ordering,
the latest binding, traits and native identity. Rerun the accepted thirteen
input actions, thirty-six direct callback components and sixteen interruption
cases on the final changed carrier. Original reference/direct-run failures
remain separate and unchanged.

This contract authorizes private source/fixture work and bounded verification
within the existing task. It grants no acceptance before those observations,
no live Apple adapter integration, and no physical VoiceOver, full parity,
external dogfood or GA qualification. One owned simulator may run at a time;
cleanup remains mandatory on every outcome. Phones remain deferred.
