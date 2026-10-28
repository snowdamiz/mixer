# Independent inflight lifecycle expectations before producer access

This preaccess oracle is derived only from the accepted prepared-3 source,
earlier lifecycle contract, retained K07g/K07h/IS05 tests, and root's bounded
KOL01-KOL07 acceptance. The active inflight contract/implementation has not been
read. It grants no compiler, fixture, TLS, or runtime execution. All observations
below are prospective requirements or explicitly identified source hypotheses.

## Scope and production boundary

The two selected cases are KOL08-GRACEFUL (parent supervisor stop with one real
TLS/controller/FetchFlight) and KOL09-KILL (kill that component's exact
DynamicSupervisor while a real flight is tracked). KOL08 forced owner crash is a
different trigger and remains pending even if graceful stop later passes.
IS05 app startup/stop and full application/provider/HTTP/browser/session/GA gates
remain pending. Completed TLS handshake plus an outstanding JWKS request is not
a successful JWKS fetch, validated snapshot, authenticated token, or provider
qualification.

A test-build-only KeyOwnerSupervisor constructor may select the existing
KeyOwner.start_fixture endpoint seam. It must reuse the ordinary common child
construction, KeyOwner.child_spec identity/shutdown/start semantics apart from
the fixture start MFA, child start/reverse-stop order, DynamicSupervisor strategy,
one_for_all restart strategy and restart intensity. An independently reconstructed
ComponentFixture is not proof of the newly selected common topology. Record the
exact constructor and ordinary-vs-test child-spec differences. Fixture exports
and tuple-init branches must be guarded by the test build; no fixture option is
added to KeyOwner's production allowed list. Production initialization must keep
rejecting fixture options. Existing GlobalAddress/DNS loopback refusal,
certificate chain/hostname verification and public transport settings remain
unchanged. A source-only review can establish selected byte differences; a
production build/export claim needs its own specified compiler evidence later.

## Establish a real response-stalled flight before either trigger

Use the production Admission/KeyOwner checkout path and real FetchFlight,
BoundedTCP, Mint and OTP TLS path, with a fully isolated synthetic TLS endpoint.
The endpoint seam may only choose the test IP/port. Do not replace the verifier,
transport or controller with a success double or modify trust state. An enabled
synthetic profile may be necessary to start a real flight; its host/path and
certificate authority must be explicit and isolated.

Before suspension, prove server handshake completion and receipt of the actual
expected HTTP JWKS request, with no response released. A TCP accept count or
non-nil flight.connection alone is insufficient: the earlier K07g/K07h RawFixture
path can be stalled during TLS handshake. A server barrier must acknowledge the
post-handshake request stage, independently of the client flight state. Retain
whether application response bytes were sent and whether a snapshot was ever
installed. No response/snapshot means no JWKS-success claim.

Capture component, owner, worker-supervisor, flight, worker, client TLS controller,
raw port, caller and exact server handler/listener identities plus monitors.
Confirm raw-port ownership matches the registered client controller and the
flight is tracked by the old owner with a queued real caller. Capture old table,
epoch, pointer, generation and deadline. Record remaining flight budget at the
trigger; if setup consumed the original two-second budget, reject the trial as
fixture/deadline setup failure rather than shutdown proof. Do not extend or reset
the production deadline to manufacture a pass.

Suspend only the captured client controller, with unconditional exact-PID resume
registered before the first suspension/assertion. The fresh owned VM must be
nondistributed, have bounded schedulers/output/time, and start no application,
DB, provider or unrelated fixture. No global process or port inventory is needed.

## KOL08-GRACEFUL oracle

Trigger actual parent Supervisor.stop(component), asynchronously from an exact
owned helper; direct GenServer.stop(owner) does not test this gate. While the
controller is suspended, prove the exact admission key becomes absent and both
new acquire and authenticate deny identity_unavailable. Record admission closure
before waiter-reply/drain completion. The old table may remain alive until owner
exit; pointer absence is the admission observation.

Prove the stop helper is pending while the captured controller is still alive
and suspended. Raw port DOWN/closure alone is not complete cleanup: flight,
worker and controller are distinct resources. Do not promise that the worker
is already down while a synchronous ssl.close/await_connection_down is blocked.
After resuming, require exact old flight/worker/controller/raw-port retirement,
old owner and worker-supervisor DOWN, old ETS destruction, final pointer absence,
and successful parent-stop completion. Retain old callers' actual errors and
callback output. The normal parent stop must not restart a replacement.

An existing ConfiguredVerifier caller's authenticate completion is not a direct
timestamp of terminate's waiter reply: its after block calls KeyOwner.release,
which can itself wait while termination drains. To prove an explicit queued
reply before drain, use a real Admission-owning helper's direct checkout result
or an equally source-grounded observation. Do not inject a fake GenServer.from
or state. Distinguish that direct result, a new post-closure public denial, and
safe_call's timeout/owner-exit fallback.

## KOL09-KILL oracle and suspected adverse path

Kill only the captured old DynamicSupervisor PID after the same response-stalled
preconditions. Retain its DOWN reason, old owner DOWN reason, complete callback
exception/log output, public/caller result and all old resources. Admission must
close before any replacement publication and old cleanup must never erase a new
pointer. A public identity_unavailable alone proves neither explicit waiter
reply nor resource drain.

The frozen source suggests a concrete fault, not a verified runtime outcome:
KeyOwner.terminate closes admission, replies to waiters, then calls
DynamicSupervisor.terminate_child(s.workers, flight) by registered name. After
the worker supervisor is killed, that name may be absent and the call may exit
noproc. FetchFlight traps exits and ignores ordinary EXIT messages; its worker
and suspended controller may therefore outlive that supervisor. If the owner's
callback exits early, one_for_all may start replacement children while the old
controller/flight still lives. Retain the raw exception structure rather than
asserting a guessed OTP-specific tuple or rescuing it broadly.

Probe the replacement barrier while the exact old controller is known suspended
and alive. Before releasing it, record whether a new owner/worker supervisor,
new table or new admission pointer is already published. Early replacement is a
resource-ordering failure even if it has empty caches, public denial was safe,
or the orphan later exits after its deadline. If no early replacement is seen,
do not infer a universal barrier from one short sleep: record the controlled
blocked interval and source of causal ordering. After resumption require all old
owned resources down before accepting the resource gate, replacement new
PID/table/epoch and empty state, old-result rejection, and normal final cleanup.

A callback fault or early replacement must fail its corresponding cleanup/barrier
claim and lead to a separately scoped correction. Do not label the case clean
because the test expected the defect, because the fresh VM later exited, or
because a broad rescue hid the callback error. A diagnostic expected-defect
control may pass as a reproduction while product KOL09 remains failed/pending.

## Timeouts, evidence and failure cleanup

Use named stages and monotonic observation records: fixture handshake/request,
queued checkout, controller suspension, trigger, admission close, caller result,
raw-port DOWN, callback fault/owner DOWN, replacement publication, resume,
remaining old resource DOWN, component stop. Cross-process message arrival
order alone does not prove event occurrence order. Use acknowledged barriers and
the controlled suspended resource to substantiate each ordering claim.

Classify fixture handshake/response wait, the original flight deadline, checkout's
2.2-second safe_call timeout, a bounded assertion/helper wait, and outer runner
timeout separately. Preserve cause/stage, elapsed/budget, owner state, exact
callback reason and incomplete resource identities when a check times out.
Infinite production shutdown has no latency guarantee; bounded test failure is
not permission to weaken synchronous cleanup or tune production timeouts.

Register exact cleanup first. On every assertion/timeout/signal path, resume each
owned suspended controller, finish or terminate exact helpers/components, close
the owned synthetic listener/handlers, and reap captured flight/worker/controller
PIDs and raw ports. Cleanup may recover orphan resources after retaining the
ordering failure; it cannot convert that failure into a pass. If exact cleanup
is uncertain, preserve scratch/evidence and fail. Retain node child/group cleanup
and source/tool before/after hashes. Never perform global term erasure, global
socket/process kills, broad exception swallowing, unrelated instance action or
automatic replay. Root must review a frozen exact plan before any host/TLS run.
