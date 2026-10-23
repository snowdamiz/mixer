# Independent lifecycle SPI review

Scoped approval of candidate 1, with no blocking findings. The 71-input owner
manifest is `f9e72d973b0cbc389a5b454dbf2126acb2c5e741e4d4ff7c0ec9e0b495daacb9`.
`final-receipt.json` binds this review to the immutable export, actual native
archive, reused Swift products, original probe outputs and audited owner evidence.
`finalize.py` checks those bindings and generates the final source/evidence seals.
No production source, owner test or owner receipt was changed by this review.

`PublicProbe.swift` uses the public SPI without `@testable`, an arbitrary I/O
service, transferred adapter alias or synthetic acknowledgement. Its original
Wasm imports storage_put/poll and defines memory/startup/run/ready. Seventeen
checks pass in both Debug and Release using actual native execution and concrete
KV storage. They cover persisted exact bytes, live ownership, checked spontaneous
wake failure, failure-before-retirement ordering, duplicate group transfer,
cancellation before create, malformed native construction and abandoned
group/construction cleanup. Reopening occurs only after actual retirement. Four
external compile rejections preserve ordinary-import SPI opacity and reject
private-core access or a fabricated group drain API; a positive SPI compile passes.

`InternalProbe.swift` is separately labelled `@testable` evidence against unchanged
Debug products. Its eight gate/concurrent-close checks use actual concrete KV
close but a **synthetic** native-drain notification to prove constructor-tail and
permit retention, then idempotent retirement. Its six close-failure checks run in
a separate process: deliberately closing an internal native handle before owner
close causes the real checked status3 `invalid_session`. That private ownership
violation is not a public reproduction. It proves first checked failure retention,
one cleanup task, no false drained/retired notification and retained capacity even
after concrete storage closes. Neither probe modifies production source or claims
synthetic notification establishes actual resource exit.

Source review confirms one-shot group transfer; one concrete host/KV cleanup Task
and separate native-close job; constructor inner payload/C frame return before the
logical tail; and tail gating even after successful session publication. Terminal
failure and retirement are distinct. `stop` publishes the immutable first failure
before scheduling cleanup/control signals. A native-close error publishes before
`closeFinished`, which is required by final drain. Concurrent ordinary commands
cannot retire before their command/worker gates finish; the guest pump serializes
its own failure/drain transitions. Thus a close failure cannot allow retirement
to overtake its terminal observer. Exact native success/drain, all actual exit
acks, no worker/command, concrete storage close and constructor tail are all
required for retirement. Quarantine does not retire or release its permit.

The owner matrix is audited rather than duplicated: 32 tests each in Debug,
Release and Swift TSan, one separate idle measurement, eight actual public/SPI
consumer links across host/iOS/iOS simulator/Android, and the unchanged ten-test
old public harness replay. Fifteen isolated derived owner probes cover delayed
successful constructor tail, cancellation after actual C create, held concrete
storage close, wake failure with held actual invocation exit, and malformed
create-report quarantine. The audit reconstructs every derived mutation from the
frozen base, verifies all 73 derived inputs and checks actual logs/artifacts. The
barriers and malformed report are explicitly derived controls, not unmodified
public reproductions. No additional SwiftPM or Rust graph was built for this
independent review.

The private caller must first reserve its separately counted whole attempt, then
transfer exclusively used concrete adapters with no unrelated requests. Swift
references and SPI cannot prove uniqueness. Both observers are fixed O(1),
nonblocking, nonreentrant data sinks, with no strong path back to group,
construction or session. Core strongly retains them until retirement; a back-edge
could prevent unused-group deinit cleanup. Quarantined consumed owners may retain
their bounded sinks indefinitely. The future coordinator must keep terminal
notification separate from resource release and use dedicated attempt latch/pool
sinks. The outer sixteen-attempt pool, durable coordinator and authority/health
integration are not implemented or qualified by this lifecycle slice.

Historical review-only failures are preserved: the first public compile rejected
unmutated weak variables under warnings-as-errors; the first internal fault probe
omitted the ABI-required defined memory and was rejected before reaching its
intended close fault. Both were corrected only in review code and replayed. The
gate checks already passed in that earlier internal process; neither failure is
reported as a production defect.

Mac tests are not physical iOS/Android receipts. Cross targets compile/link only.
Rust and platform frameworks are not instrumented by Swift TSan. Logical tail,
worker and close boundaries do not prove Task/allocator destruction, hard latency,
no-OOM, process-global resource caps or OS reclamation. No device, production,
trust/keychain, credential, signed execution, activation, publication or GA work
was performed. Root owns integration and any commit/push.
