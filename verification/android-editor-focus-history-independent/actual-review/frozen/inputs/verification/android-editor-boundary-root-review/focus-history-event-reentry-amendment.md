# Replacement event evaluation reentry

This adds a scalar exclusion to the selected focus-history internal protocol
`17463b2c5399ccbf9662ee7446c798803cf332adbffb30a0c14d9f6161c432a0`.
The independent preaccess obligation identified nested replacementEvent entry
from a callable open getter before the once-only delivery claim. The producer
confirmed that its draft requires an evaluation guard; no product acceptance is
implied by this coordination.

Select an eventEvaluating scalar on the exact completed Replacement. Establish
its exact scalar Record/View/completed-operation provenance before inspecting
this guard. Same-operation reentry while evaluating, or repeated delivery after
the once-only claim, returns cleanly before callable getters, interaction or send.
It sends nothing, creates no authority, does not recurse, and must not make an
otherwise valid outer evaluation terminal. Invalid tuple or provenance retains
the selected fail-closed behavior; a foreign operation cannot borrow the guard.

Set eventEvaluating before the first callable eligibility/open check. The narrow
validation-only try/finally must clear it before ordinary interaction/send on
every path, including failure. After the existing post-getter scalar identity,
current original authority, loss observation and eligibility checks pass, claim
delivery once. Only then leave the validation region and perform the ordinary
interaction and synchronous send. No finally or evaluation cleanup may span
send: after send the field retains only its existing scalar original-result rule.

This guard is not a replacement reservation, callback lease, owner/core slot,
native busy count or authority to enter native work. A pre-send failure after
native mutation retains the existing uncertainty and first-fatal handling.
Independent tests must bind the nested open-getter control to the frozen source,
prove one outer delivery, and verify later replay sends no second event.
