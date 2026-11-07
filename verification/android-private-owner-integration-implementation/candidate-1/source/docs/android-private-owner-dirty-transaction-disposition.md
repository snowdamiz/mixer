# Private owner dirty transaction and completed input results

This records two contract issues discovered during implementation of the accepted
private owner integration. It is a proposed clarification for independent review,
not an implementation acceptance or a reduction of the product scope. The original
contract packets and root implementation selection remain unchanged historical
evidence. No native runtime or capture execution is selected.

## Dirty notifications and concrete captures

The original proposal requires the actual observer to advance its generation
before notifying the owner. `NativeEnvironmentV2.current` must still compare that
generation, exact owner/window identity and a second concrete tuple read. It also
requires `OwnerLifecycleV2` to move byte-for-byte unchanged and permits
`complete(..., committed=true, ...)` only after a successful renderer finish.

The accepted core retires any matching operation completed with `committed=false`
or a failure. Therefore an observer invalidation after environment capture cannot
both fail the required current check and complete as a successful nonterminal
operation. The correction's blanket promise that every dirty notification during
an operation leaves one later drain is too broad. Substituting a lifecycle callback
for an observer callback in tests would not resolve this conflict.

The proposed disposition preserves concrete validation and the accepted core:

- An owner lifecycle invalidation that leaves the captured environment current may
  allow the operation to finish. Its changed core epoch keeps live gates closed
  and schedules one subsequent drain. The mandatory dirty callback cases must
  state this exact stimulus.
- A real observer invalidation after capture advances generation, making that
  capture stale even if its other values happen to compare equal. If transaction
  validation then fails, the operation fails closed and the unchanged core retires
  it. It must not forge a successful completion, silently refresh the capture,
  retry the operation or replace its captured token.
- Outside an active transaction, an ordinary current-presentation mismatch seals
  and invalidates through the same observer, allowing a queued refresh to take a
  new concrete capture. The mismatch alone is not a fabricated terminal report.
- Notifications before an operation's capture may be incorporated by that later
  fresh capture. They must be tested separately from invalidation after capture.

All 184 baseline V2 sites and every new selected site still require the complete
seven-case matrix. The five V1 sites still require unchanged positive baselines.
Additional actual-observer cases must distinguish invalidation before capture,
after capture, during attachment/layout, before commit, during retained-packet
refresh and during input. Each receipt must distinguish a lifecycle-only dirty
case that coalesces from a stale-capture operation that retires. Terminal cleanup
remains deferred until active frames return, with exact failures retained. The
observer notification itself is ordinary; downstream operation failure uses the
actual core failure path without inventing a renderer cause.

This clarification does not qualify seamless recovery of a transaction whose
concrete environment changed. Such recovery would require a separately specified
and reviewed lifecycle operation; it is not supplied by the fixed core here.

## Result of a completed native input call

An actual input-connection call may synchronously update an Editable. Its
TextWatcher can dispatch the event through the owner, commit a successor
presentation and return before the original native delegate returns its boolean.
The wrapper's captured presentation is then stale even though that native call
completed successfully.

The proposed rule keeps the immutable captured scope and mandatory postcheck:

- Every native forwarding call first requires its captured live scope. Transaction
  scopes remain subject to exact operation identity; this rule does not relax them.
- The same scope is checked again after the delegate returns. A terminal or dirty
  closed fence rejects the result. Fatal errors are retained and rethrown.
- If the delegate has completed and the only mismatch is a live successor
  presentation, direct scalar/reference inspection may permit returning the
  already-completed delegate result. This branch must return immediately and
  perform no additional native call, event, mutation, capture or connection work.
  It grants no authority to the stale scope and does not adopt a new live token.
- Every subsequent forwarding operation must capture and validate its own scope;
  a retained sealed connection still rejects before calling its native delegate.

Actual-successor positive controls are required for every forwarding family.
Nonforwarding overrides require explicit refusal and zero-forward controls.
Exact-current controls and terminal/dirty/stale negative controls are required
for both families; fatal behavior is exercised wherever a selected call is
reachable. No selected callback site or matrix case is removed by this distinction. A
source/bytecode check of the immediate-return branch supplements those actual
body tests. A model of a text event or a delegate returning a canned result is
insufficient to establish the synchronous TextWatcher/owner/renderer sequence.

Both dispositions require independent review before candidate acceptance. No
profile hashes, public V2 route, source-core changes or release authority are
selected by this document.
