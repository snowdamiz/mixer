# Root validation review

`receipt.json` binds the reviewed64-input validator candidate to the owner logs,
four linked consumers, immutable native archives and derived ownership probes.
`audit.py` checks these bindings without rebuilding or editing inputs.

The original public consumer in `public.swift` passes22 checks against the frozen
release library. It rejects invalid uncalled bodies, unsupported instructions,
missing wake and a memory maximum exceeding zero; checks owned foreign-buffer
capture, two permits and one-shot cancellation; and executes a real zero-page
guest and startup trap with immutable first-failure diagnostics. It imports no
test internals and uses no report injection. The initial missing C include path
failure is preserved separately; the corrected compile and run pass.

Source review found no further actionable defect. The owner had already reproduced
and fixed a validation-permit quarantine/deinit bug before this freeze. Its three
derived controls run in debug/release/TSan: malformed-report retention, cancellation
at the real C return, and rejection of a second cancelled caller. These controls
do not claim a production C fault or hard cancellation of synchronous validation.

The API returns no reusable validation proof, constructs no instance or adapter,
and does not authorize signed activation. The two validation permits are separate
from the16 construction/live/draining permits. Physical devices remain unavailable.
