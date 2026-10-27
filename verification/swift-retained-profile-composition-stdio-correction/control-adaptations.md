# C01 fault mechanism and preserved behavioral obligations

inputs/ contains the exact reviewed witness, findings, selection and original
required-failure streams. old/independent_case.py and new/independent_case.py are
byte-identical to that witness. Their old/raw command dispositions stay visible.
No existing assertion is changed into expected success, removed or weakened.

The old witness replaces tempfile.TemporaryFile with an owning Stream wrapper.
Its stderr __exit__ throws before real.close, while the body raises a separate
Refusal. The required assertions are that the known-open stream cannot disappear
behind healthy_zero and that the exact Refusal stays the structured primary.
The literal old-source attempt still fails and prints the actual contradictory
state. Its known open object is not retried by the witness.

The replacement uses mkstemp raw birth descriptors and no TemporaryFile object.
The same literal wrapper therefore receives no construction call on new source;
its later streams[1] expression raises IndexError. This is recorded as an unused
injection mechanism and fixture mismatch, **not** passing corrected C01 behavior.
The other five independent cases are unchanged and pass on both source variants.

The separately labeled adaptation is stdio_case.py close -p primary. It throws
before the actual stderr raw close boundary after both raw resources were captured,
and raises the original body Refusal. It keeps the same behavioral assertions:

- separately captured owned stderr number is still actually open at the known
  pre-syscall observation, before any new fd opens;
- the other independently owned stdout close was actually attempted and completed;
- unresolved stderr remains in generation/token/uncertainty accounting and
  healthy_zero is false;
- CleanupAggregate.primary is the identical original Refusal object;
- the exact cleanup exception is retained, not merely found in __context__;
- no uncertain number is retried or erased and new admission refuses.

Post-close tests use the same boundary after an actual successful os.close. They
still require unresolved accounting and no numeric retry, despite the controlled
oracle's knowledge. The two-stream and mixed retained-owner tests preserve every
original exception identity and completed observation alongside the primary.

Acquisition tests explicitly label their boundaries. Before is before the standard
acquisition primitive and acquires no returned resource. Post-acquire is after the
birth was already stored in the pre-registered token; it cannot hide a live fd by
throwing after an opaque factory returned. Prepare/unlink faults occur only after
capture and keep unresolved name obligations. The first owner is cleaned even if
second acquisition fails. Tests never wrap a successful open and intentionally
discard its unrecorded result, then claim that unknown resource was tracked.

High-level automatic file close is removed rather than modeled as a delayed
numeric obligation. The GC/reuse tests demonstrate no FileIO/BufferedRandom owner
or finalizer exists in these resources, collect closed owners while fresh owners
hold reused numbers, and confirm zero delayed close calls. Quarantined owners
retain raw data only; repeated close and collection cannot implicitly operate on
the saved numbers. Test subprocess containment is separate from cleanup health.

The previous142-case source and producer26-method source are unchanged. Existing
retained-wrapper uncertainty remains deliberately nonhealthy. Their source model,
limits and remaining real Rust/context/operational qualifications are unchanged.
