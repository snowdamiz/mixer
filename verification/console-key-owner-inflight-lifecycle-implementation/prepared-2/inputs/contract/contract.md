# Active-fetch KeyOwner lifecycle contract

This packet specifies the next two host cases. It changes no product or test
source and authorizes no execution. The immutable selected prepared-3 snapshot
labels its formatting correction unexecuted. Root subsequently reported that
prepared-3's seven-method socket-free producer run passed, with final independent
terminal review pending. This packet did not inspect that new runtime receipt;
neither report accepts these TLS cases. All conclusions below are source
conclusions or expressly labeled retained or root-reported observations.

## The finite next boundary

KOL08-GRACEFUL requests normal shutdown of the real KeyOwnerSupervisor parent
while one real TLS fetch and its callers are pending. KOL09-KILL kills only that
component's worker DynamicSupervisor while one real TLS fetch is pending. Run
the cases sequentially, with one loopback TLS listener, one enabled profile, one
FetchFlight, one transport worker, and two callers per case. One caller uses the
public ConfiguredVerifier; the second records the raw checkout reply or exit so
safe_call cannot disguise a missing terminate reply.

The original KOL08 also requested an ordinary-supervisor owner-crash adaptation.
That is still pending. A pass for KOL08-GRACEFUL must not mark all original KOL08
conditions complete. KOL09-KILL selects the harsher worker-supervisor death case;
a separate graceful worker-supervisor stop is not included in this two-case run.

## Source path and the missing fixture route

The source references in source-bindings.json point to immutable input copies.
Prepared-3 KeyOwnerSupervisor starts its named DynamicSupervisor, then ordinary
KeyOwner, under one_for_all. KeyOwner's child shutdown is infinity. The common
initializer enables trap_exit before Admission.new publishes the creator-owned
ETS table. Checkout starts a FetchFlight under the named worker supervisor and
records its monitor, epoch, generation, entry, and deadline. A cold checkout
waits for flight completion. See key_owner_supervisor.ex:5-17 and
key_owner.ex:12-17, 43-96, 112-155, 299-343.

The ordinary route is FetchFlight.fetch -> JWKSTransport.fetch -> DNSResolver ->
Mint HTTPS -> BoundedTCP. The test route changes destination selection through
KeyOwner.start_fixture, FetchFlight.fixture_fetch and
JWKSTransport.fetch_fixture; it retains certificate/hostname checks, Mint,
BoundedTCP, raw-port registration, controller registration, and FetchFlight
cleanup. See fetch_flight.ex:73-85, jwks_transport.ex:10-88, and
bounded_tcp.ex:20-43, 89-124.

There is currently no ordinary KeyOwnerSupervisor local-fixture constructor.
Ordinary KeyOwner rejects the :fixture option; the production resolver denies
loopback, and Manifest requires a hostname and port 443. A DNSFixture returning
127.0.0.1 cannot make the ordinary production route reach the local TLS listener.
Do not weaken those checks, assign a public IP, change host networking, replace
DNS/transport modules, or mutate the running owner's state to pretend this route
already exists. See key_owner.ex:12, 43-66, dns_resolver.ex:5-12, 82-95,
global_address.ex:6-20, and manifest.ex:17-25, 51-58.

The smallest proposed construction seam is a test-build-only
KeyOwnerSupervisor.start_fixture constructor. It must use the same component
initializer, child order, derived worker name, child shutdown, restart strategy,
and restart limits as ordinary start_link, changing only the owner child start
function to the already existing KeyOwner.start_fixture. The fixture descriptor
is removed before ordinary owner option validation by the existing owner seam.
Production builds must expose neither this constructor nor fixture destinations.
Ordinary start_link must still reject fixture options. This is a proposal for a
separately coordinated source slice, not an implemented seam or acceptance.

With that seam the honest qualification label is "real KeyOwnerSupervisor
lifecycle, existing test-only local destination, real TLS client/server and
cleanup." Production DNS/global-address admission and an entirely ordinary
destination-construction path remain outside the result. If root selects no
seam, keep these cases pending; ComponentFixture alone cannot satisfy the real
KeyOwnerSupervisor constructor requirement.

## What cleanup actually does

KeyOwner.terminate first calls Admission.close(name, table), next replies
identity_unavailable to recorded waiters, then synchronously calls
DynamicSupervisor.terminate_child for each tracked flight. Guarded close checks
both ETS creator PID and the current exact pointer. This depends on serialized
registered-owner lifecycle, not atomic compare-and-erase. See
key_owner.ex:492-498 and admission.ex:73-82.

FetchFlight traps exits, owns a linked/monitored worker, and monitors its exact
raw port and TLS controller. Its terminate callback kills the worker, closes raw
and SSL sockets, waits for raw-port and controller DOWN, then worker DOWN. The
normal worker-DOWN path also waits for raw-port and controller DOWN before
reporting the flight result. The waits are unbounded in product code. See
fetch_flight.ex:15-70, 90-122, 137-170, 173-200. A bounded test runner may fail and
clean up; it must not invent a product shutdown-latency guarantee.

A flight result is addressed to its old owner PID. An untracked flight-result
message is ignored, and publication requires current generation, epoch and
entry. Old permits fail the replacement table check; old leases fail the current
fences. These are source fences, not proof of authenticated lease acquisition or
a successful real-provider authentication. See key_owner.ex:158-179, 346-377,
428-467 and configured_verifier.ex:16-61.

## Existing cases: reuse and gaps

| Existing case | Exact reusable behavior | Missing next behavior |
| --- | --- | --- |
| K07g, key_owner_test.exs:834-864 | Captures one raw port, worker and client TLS controller; suspends the controller; checks stop waits and denial; resumes in after. | Its trigger is direct GenServer.stop(owner). It uses start_fixture plus RawFixture, which stalls a TLS handshake. It does not use normal parent shutdown, prove completed TLS negotiation, or check exact Admission absence. |
| K07h, key_owner_test.exs:866-943 | Checks no replacement while old suspended controllers remain; checks workers/ports down and waiter denial. | Its parent is ComponentFixture and its trigger is owner kill, with four RawFixture handshakes. It does not exercise worker-supervisor death or the real supervisor constructor. Its ordinary-supervisor crash adaptation remains pending. |
| IS05, startup_lifecycle_test.exs:158-194 | Empty replacement epoch/snapshots, replaced worker supervisor, registration removal and public denial across application stop/restart. | It starts the application and has no active-flight matrix or exact pointer-absence assertion. Do not rerun it in this component-only slot. |
| Prepared-3 KOL01-KOL07 | Dedicated ordinary-supervisor helpers, exact name/table/epoch cleanup, permit/lease rejection, seven finite socket-free methods. | Root reports producer pass with independent terminal review pending; this packet runs no methods. They create no flights or sockets. KOL07 cannot exercise terminate_child against a dead supervisor while flights are tracked. |
| TLSFixture, identity_tls_fixture.ex:194-238, 262-287 | Real handshake, request/SNI/protocol observation, response-ready barrier, exact handler/socket bookkeeping. | Its terminate callback closes/kills owned resources without awaiting all DOWN. Future collector must retain exact IDs and independently confirm cleanup. It is not a mock verifier. |

## KOL08-GRACEFUL observations

Use TLSFixture's existing response barrier, not a raw TCP sink. Receiving its
tls_response_ready marker proves server handshake completion and a parsed HTTP
request. Also require the recorded SNI/negotiated protocol, a registered SSL
socket, raw port and controller in the real FetchFlight, exactly one tracked
flight and two waiters, and an unexpired original deadline with enough margin
for the short observation window. No response body has been released and no
JWKS fetch has completed; no snapshot or authenticated lease has been obtained.
A failed precondition fails
the run without an automatic retry or timeout increase.

Register exact-PID cleanup before every assertion. Monitor the owner, component,
worker supervisor, flight, worker, controller, listener acceptor, server handler,
and exact raw port. Suspend only the captured client controller. Request
Supervisor.stop(component, :normal, :infinity) from one monitored owned helper;
do not call GenServer.stop(owner) or Admission.close from the test.

While that controller remains suspended, require the Admission pointer to become
absent, fresh acquire and public authenticate to deny, the raw checkout caller
to receive an explicit identity_unavailable reply before its deadline, the raw
port to be closed, and the parent-stop helper to remain pending. At the raw
reply observation, record pointer absence and old owner/table liveness. This
distinguishes terminate reply from caller exit/timeout; the final public result
alone cannot do that. The public caller's finally release may wait on the owner
and need not return during the suspension window.

Resume the exact controller and release the exact server response handler in
after, on success or failure. Require final public denial; normal component
stop completion; DOWN for all old component/flight/worker/controller processes;
old table destruction; exact pointer absence; raw-port closure; server handler
closure; and no surviving listener/acceptor after fixture shutdown. Use observed
events plus the held-controller barrier for ordering. Do not claim a total order
from unrelated DOWN message arrival order alone.

## KOL09-KILL observations and the adverse branch

Start a fresh same-shape component using a distinct finite atom name. Reach the
same completed-TLS/barrier preconditions, capture two pending callers, and
suspend only the captured client controller. Kill only the exact owned worker
DynamicSupervisor. Require its DOWN and retain the reason. Do not manually stop
the owner, erase its pointer, or release the controller to make the fault pass.

Record old owner DOWN reason; raw checkout reply versus exit/timeout; public
result; exact pointer samples; old resource liveness; and replacement
owner/worker/table/epoch publication while the old controller is still held.
Preserve full callback exception output. If a transient absent pointer is missed
because replacement races the observer, record that fact; do not report an
observed absence. Once replacement exists, its pointer must identify its own
table, and later old cleanup must not erase it. Reject an old permit/explicitly
synthetic stale Lease at replacement; this tests rejection only.

The concrete adverse possibility is that the dead DynamicSupervisor no longer
serializes its old children's drain. FetchFlights may enter their own cleanup on
parent death while KeyOwner.terminate closes admission and replies, then exits
calling terminate_child through an absent supervisor. one_for_all may publish a
replacement while an old suspended controller/flight remains alive. Source
inspection cannot settle the observed outcome. A callback exit or replacement
before old resources are down is a failed clean-lifecycle/resource gate even if
the public caller is safely denied. Do not suppress the exception, loosen waits,
change strategies or label early replacement as a pass. Propose a separate
minimal correction from the exact retained observation.

Always resume the controller and release the server handler in after. Record
eventual old-resource teardown separately from whether the ordering gate passed.
Stop the replacement normally and require its exact pointer absent and its owned
children gone. A deliberately killed worker supervisor may produce expected OTP
fault reports; retain/classify those separately from compiler warnings. A
terminate callback exception is not an innocuous expected-fault report.

## Execution and acceptance limits

execution-proposal.json is a bounded future proposal, not a released plan. A
separate root-owned implementation/review and exact single-execution host release
is required. No DB, Repo, endpoint, product application, provider, DNS fixture,
browser, native runtime, UI, capture, global process inventory or unrelated
process is included. Use existing declared host dependencies only. Each exact
runtime command, version, selected tree digest, terminal counts, stdout/stderr,
event record and cleanup outcome must be retained. Any warning, failed/missing
precondition, missing artifact, skipped/excluded method, timeout, signal or
uncertain cleanup prevents acceptance; preserve scratch on cleanup uncertainty.

This packet executes only offline Python/source/hash checks. Native checks,
application/HTTP/session/provider qualification, Neon/Cloudflare operation,
custody, physical devices, published-package FieldLog dogfooding and GA remain
pending. The computer-use/capture/native-runtime pause remains in force.
