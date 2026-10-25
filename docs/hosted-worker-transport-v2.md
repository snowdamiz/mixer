# Worker client V2 repair candidate

V2 repairs the two findings in the frozen
[independent V1 review](hosted-worker-transport-independent-review.md). V1 is
preserved and remains rejected for integration. This candidate lives only in
`verification/hosted-worker-transport-v2/`; it changes no live hosted file,
startup role, migration, dependency, shared status or Git state. Independent V2
review remains mandatory before root integration.

The controlling review receipt SHA-256 is
`5c4e1605be31b6ba1de6feff18794c071d1dbc2dc9fee72102cf86145f46f7c7`.
The first finding reproduced seventeen authenticated TLS handlers: a suspended
old Flight retained its worker/raw socket/SSL process after both RoleGuard and
owner died, while absence of the guard's registered name admitted sixteen new
operations. The second finding observed Mint's default User-Agent outside the
original seven-header contract. The
[header amendment](hosted-worker-transport-amendment-v2.md) selects an explicit
eighth field for V2; it does not retroactively accept V1.

## VM ownership survives process replacement

The uniquely registered WorkerTransport owner installs one nonsecret
`:persistent_term` marker before creating a RoleGuard or Flight. It contains
schema 2, a fresh generation reference, owner PID and initially a nil guard.
The registered guard binds its own PID to that exact pending generation. Marker
creation is serialized by the owner's registered name, not by a non-atomic
get/put race among unregistered startup callers. Tests exercise twenty-four
concurrent startup attempts over two clean generations.

Every existing marker, including an unexpected value equal to an absence
sentinel, denies replacement. Lookup distinguishes a missing key from any stored
value. Owner/guard death or registered-name loss cannot erase it. No production
reset/clear API is provided. The only product erase site is the bound guard's
private successful teardown path.

The guard tracks every admitted Flight with a monitor, generation and a fresh
launch-bound retirement reference. A Flight acknowledges cleanup from its own
admitted PID only after observing the exact worker, raw-port and SSL-process
DOWNs. The guard accepts that generation/reference once and still retains the
entry until the matching monitored normal Flight DOWN. Normal DOWN alone is
never cleanup proof. Wrong caller, generation, reference or marker identity
cannot authorize retirement. Ordinary externally requested normal Flight stop
also closes owned resources and observes retirement before acknowledging; an
incomplete or abnormal stop leaves quarantine.

The guard can erase the marker only after observing owner DOWN, receiving the
generation's cleanup acknowledgments and matching normal monitored DOWNs for
all admitted Flights, and finding its exact generation/owner/guard marker still
present. It rechecks that marker immediately before erase. Guard death before
erase leaves quarantine. After erase, safe reuse is possible because all old
resources have already been observed retired. No per-request marker update is
needed.

The tradeoff is deliberate: death after marker installation but before guard
creation can leave an unavailable execution domain even if no socket was ever
created. Lost guard or unverifiable cleanup requires disposal of the whole BEAM
execution domain; replacing application processes is insufficient. Normal
demonstrated cleanup permits reuse. The marker is a VM-local interlock, not
durable provider state, tenant authorization or protection against privileged
arbitrary BEAM code rewriting VM state. Customer scripts remain outside BEAM.

OTP documents persistent terms as optimized for reads and infrequent updates;
replacing/erasing complex terms can trigger global garbage collection. This
candidate writes only during role initialization/binding and erases during
verified role teardown. Deployment responsiveness and hard resource limits remain
separate qualification work. See the [official persistent-term API](https://www.erlang.org/doc/apps/erts/persistent_term.html).

## Exact emitted request bytes

V2 explicitly supplies `user-agent: mixer-worker/1` through Mint's public API.
It also supplies the validated configured Host and canonical Content-Length,
so synthetic destination-port substitution does not alter the application Host.
The other six selected fields are unchanged. All eight names occur once; no
dependency, host, token or build metadata is placed in User-Agent.

The pre-send bound now counts the exact request line, every serialized selected
header, CRLF separators and final empty line. The bound remains 8,192 bytes;
JSON remains at most 16,384 bytes. A real synthetic TLS peer retains the complete
received request for query, ensure_started and stop. Executable controls compare
the complete bytes, field order/inventory, values, duplicates, canonical body
length, body bytes and bounds, and retain only the synthetic fixture credential.
The JSON protocol and immutable binding/operation-ID algorithms are unchanged.

## Evidence and remaining boundaries

The packet retains the existing twenty-five producer controls: twenty-four run
together, and the watchdog-death control runs in a separate disposable BEAM so
its VM-lifetime quarantine is preserved. Seventeen new controls cover the exact
guard+owner-loss reproduction; normal reuse; concurrent startup; crashes before/
after marker installation, guard binding and marker clear; normal Flight stop;
normal DOWN without an acknowledgment; malformed markers; generation/owner/guard
clear mismatches; an unadmitted cleanup caller; delayed cleanup acknowledgment
past the absolute deadline; and all-command emitted bytes. Cleanup may complete
after that deadline, but a post-acknowledgment monotonic check prevents a late
valid observation.
All unknown-death controls run in fresh BEAM execution domains. No test reset
function erases a retained quarantine.

The delayed-acknowledgment regression first reproduced a valid observation 51 ms
after the absolute deadline. Its failing command/output, exact source archive
and post-fix passing command/output are retained. Collection 1 remains historical;
the final receipt binds the subsequent complete rerun.

The guard-loss repair receipt requires one old authenticated handler while its
Flight is suspended and all sixteen replacement attempts are denied. It then
resumes that Flight, observes its exact resources retired and verifies that the
unverifiable dead-guard marker still blocks replacement. The after-clear test
admits sixteen new handlers only after proving the old resources gone; the
historical total of seventeen accepted connections is distinct from simultaneous
occupancy of sixteen.

The isolated runner binds the four candidate modules, the same six safe context
modules, archived locked Mint/Jason/HPAX dependencies, exact commands/tools,
current dependency inventory and complete input/output archives. It replays all
forty-two controls and the existing thirty-six Elixir/JavaScript hash vectors.
Production-mode compilation checks both fixture-start arities, test barrier
branches, test helper exclusion and absence of marker reset exports. This is a
production-BEAM component check, not a complete hosted release or CI receipt.

No frozen authority/catalog module is read, loaded or executed. No cloud,
database, native instance, physical phone, real credential, provider operation,
customer message or Git operation is used. Owned command groups, fixture keys,
listeners and processes are disposed; VM termination removes quarantined markers
without a product reset. Initial attempts and historical V1 findings are retained.

Root startup should install validated dispatch configuration, start Repo and
WorkerTransport before processor Oban queues, and retain the transport's temporary
restart policy. A premature same-VM restart may fail conservatively while normal
cleanup completes. An unknown-death failure must not cause a fallback or marker
erase. The fixed coordinator profile remains 6,000 ms callback, 30,000 ms lease
and 1,000 ms polling.

V2 supplies no durable controller ledger, provider execution, source/result/
artifact authority, public authorization, signing or release eligibility. Hard
Linux memory/CPU/task/FD/native-TLS limits, whole-domain disposal, crash/core-dump
retention and deployment sink policy remain unqualified. Independent review,
live startup integration, full hosted release/CI, real Cloudflare/Linux and
external Apple/macOS worker qualification, native/dogfood and GA gates remain
pending.
