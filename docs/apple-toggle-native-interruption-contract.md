# Private iOS native drag interruption verification

The semantic activation carrier is unchanged from the candidate that passed
thirteen real simulator interactions and produced thirty-six passing direct
callback observations. This slice changes only its private diagnostic fixture
and builds a new public XCTest runner. The previous sealed source and failures
remain intact. There is no live adapter change.

Sixteen independent launches cover accessibility activation in both directions
and layouts, cancellation, disabling, stale input and a silent replacement
binding in both value directions, and no-change drag release in both layouts
and values. Every drag comes from public XCTest coordinates. The fixture queues
one closed application operation only after an actual native pan preview. It
records the native recognizer state, identity and touch count before acting.
A missing or already-ended pan is a failure; the fixture does not manufacture
touches, recognizer states, translation or callbacks.

The oracle requires native admission and preview before any semantic commit,
then immediate preview cancellation, the exact permitted value/event change,
and no replay when XCTest releases the touch. Binding replacement must preserve
the new value without emitting an event. A no-change release must traverse real
began/changed/ended callbacks and emit no event. Exact initial state, layout,
native identity, accessibility metadata, event history and scroll position are
checked for every case. Host mutation tests are separate from native evidence.

The runner reuses the reviewed loopback transport and independently attempted
cleanup controller. A fresh root review selects its immutable source, build and
test runner before execution. One owned simulator is removed after the run,
including failures; baseline instances and the Simulator frontend are preserved.

Calling accessibility activation during a real held drag establishes this
application callback interaction, not delivery by physical VoiceOver. Keyboard
and focus delivery, further lifecycle retirement cases, compositor parity,
renderer integration, the final physical matrix and external FieldLog release
qualification remain pending. This slice cannot accept the full carrier or GA.
