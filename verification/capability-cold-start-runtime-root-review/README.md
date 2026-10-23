# Independent coordinator flows

`ColdStartFlowProbe.swift` contains original root flow assertions with the signed
fixture scaffold explicitly reused from the frozen transition candidate3. Its
internal open helper controls only wall time. Monotonic time, the private durable
store, native validation/startup/enable and actual retirement remain real. Native
milestone reports are synthetic test inputs, not evidence of a product screen.

The frozen final candidate passes the same four flows in Debug, Release and
Thread Sanitizer builds (twelve executions):

- Both milestones precede the observation window; the existing notification
  consumer wakes later and commits health without another milestone call.
- After close and root-key expiry, the exact actually committed healthy candidate
  starts provisionally with retained provenance and unchanged sequence high-water.
- Sixteen idle owners fill the process pool; a seventeenth opens no directory.
  Actual close returns capacity.
- Thirty-two cancelled opens return capacity after cleanup.

`preliminary-linked-1` preserves a root harness compile failure: its asynchronous
predicate needed an explicit `@Sendable` annotation. No test ran in that attempt.
`preliminary-linked-2` changes that annotation only and passes all four flows
against the same immutable owner dylib. The owner development receipt's separate
XCTest fixture warning does not invalidate the linked production artifact, and is
not relabeled as a successful full qualification.

`run.py` links the exact owner dylib without another package graph or native
archive. It verifies the frozen export and linked artifacts, records source/tool
identity and preserves each new run separately. `audit.py` independently checks
the owner's frozen source, commands, products, retained dependencies and evidence
manifest without rewriting its seal, then binds these three identical root probes.
Run `python3 verification/capability-cold-start-runtime-root-review/audit.py --check`
to verify the saved root receipt. Independent terminal/close race review is in
`../capability-cold-start-runtime-review/`. Actual public guest event delivery,
real UI health, physical devices and published consumer evidence remain separate.
