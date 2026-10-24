# Proposed Stripe webhook transport contract

Status: **root selection pending; pinned API feasibility probes pass; no public
admission or transport privacy qualification**. This is the next bounded W14/G23
development contract under product-plan 13.2, 13.4, 17 and 18. It changes no route,
provider acknowledgment, endpoint/account authority, secret owner, database,
schema or Oban job. Root must select the public/dependent contract before its
implementation. The independent catalog-inspector and authority-driver reviews
remain pending; this work neither repeats nor substitutes for them.

The exact-byte capture component is now integrated under the separate
[root acceptance](../verification/stripe-raw-body-integration/acceptance.json).
That acceptance binds 71 hosted inputs, tree digest
`ac391070ec439ecfca288b9a7657aac1eada5bc1196efb8735211cc60a6883bc` and capture
source `a420d5a54868d61c3d6e9c7cb41807698eb729df3e6babda12135a727ac657ea`.
The older 69-input candidate/reviewer receipts remain historical and immutable.
This contract preserves the [selected framing](stripe-raw-body-direction.md):
HTTP/1.1 canonical Content-Length **or** one chunked transfer coding; HTTP/2
optional canonical Content-Length, with no transfer coding. It does not narrow
the profile to Content-Length-only or HTTP/1-only.

## Pinned findings and supported boundary

The inspected and probed stack is Plug 1.20.3, Bandit 1.13.1, Thousand Island
1.6.0, telemetry 1.4.2, Mint 1.11.0, Elixir 1.20.4 and OTP 29.1.1/ERTS 17.1.
Exact source/BEAM/tool bindings and retained closures are under
[run-6](../verification/stripe-webhook-transport-contract/run-6/receipt.json).
The [API map](../verification/stripe-webhook-transport-contract/api-map.json)
binds installed official source files and line ranges. These are source and
executable API findings, not regex-based release authorization.

| Observation | Consequence for the next implementation |
| --- | --- |
| Thousand Island synchronously emits `:recv` **and** `:async_recv` with raw bytes in `measurements.data`; Bandit starts request telemetry with a full `conn` before the Plug. | There is no documented raw-event-disable/redaction setting in these pinned servers. Prove that configured sinks never receive raw payloads; do not claim that raw event payloads never exist. |
| telemetry handlers run in the emitting process, independently receive the original values, and may run in any order. A failing handler is detached. | A sanitizer handler cannot protect a second raw subscriber. Export only a newly constructed allowlisted value, inventory every subscriber, and fail closed on guard/handler failure. |
| The H2 body reader logs `Ignoring trailers ...` unconditionally. Normal protocol-error options do not cover this warning. | Use an endpoint-owned Logger sink boundary before handler formatting/persistence; matching only a message substring is insufficient. |
| H2 `read_timeout` restarts on successive messages; read lengths are advisory. The accepted independent run returned a nominal 1,000 ms read after 5,557 ms. | Keep the capture's late-result refusal and add independent owner cancellation. No detached Task may read another process's stream. |
| H2 stream termination deletes the stream mapping/pending send; it does not itself send RST_STREAM. | Killing only the stream PID is not the disposal contract. Use whole-connection disposal on timeout/failure in the proposed profile. |
| H2 receive-window replenishment grows toward `2^31-1`; header-list limits are checked after HPAX decoding. H1 available reads can contain bytes beyond the requested body. | Neither the initial window nor header/body settings prove an allocation ceiling. Treat process/VM/container memory separately. |
| H1 consumes undeclared trailers without exposing them to capture; H2 ignores valid trailers after validation and may log them. | This slice can protect configured sinks but cannot claim a no-trailers policy. A public trailer-policy/ingress decision remains explicit. |

The supported building blocks are documented [Bandit listener options](https://hexdocs.pm/bandit/1.13.1/Bandit.html),
[Thousand Island lifecycle telemetry](https://hexdocs.pm/thousand_island/1.6.0/ThousandIsland.Telemetry.html),
[telemetry attach/list/execute](https://telemetry.hexdocs.pm/1.4.2/telemetry.html),
[absolute process timers](https://elixir.hexdocs.pm/1.20.4/Process.html#send_after/4),
and [OTP handler filters](https://www.erlang.org/docs/29/apps/kernel/logger.html#add_handler_filter/3).
No dependency fork, private Bandit message injection, adapter-struct manipulation,
custom HTTP parser or undocumented flag is proposed.

## Root selection requested

Select a **dedicated webhook endpoint BEAM role and listener** with a bounded
connection owner, sink inventory and whole-connection disposal. It must not share
its listener or Logger policy with unrelated API routes or processor roles.
This permits narrow filters on every sink owned by that role without changing a
shared global log level or muting another application. A dedicated role is a
proposed deployment boundary, not an assertion that it already exists.

The next slice remains private: invoke the accepted capture through an owned
boundary using fixed server policy, and return a non-2xx marker only in disposable
tests. It may not expose a production HTTP route, acknowledge an unauthenticated
event, invoke billing/domain work, or select authority from HTTP/private-conn
fields. Account/mode/generation/secret ownership remains a separate contract.

Select the following initial development constants. They are intentionally
server-owned and do not claim provider/deployed-ingress qualification:

| Boundary | Proposed value and API |
| --- | --- |
| Connections | `num_acceptors: 1`, `num_connections: 16`; total 16, because the latter is per acceptor. `max_connections_retry_count: 0` prevents retry sleeps while an accepted socket awaits a handler. Fixed listen backlog 128, verified against the selected transport. |
| Idle reads / handshake | Thousand Island `read_timeout: 1_000`, `handshake_timeout: 1_000`, `shutdown_timeout: 1_000`; these supplement independent absolute timers. |
| H1 parser envelope | `max_request_line_length: 512`, `max_header_length: 8_192`, `max_header_count: 32`, `max_requests: 1`, `log_unknown_messages: false`. These bound parsed fields, not a socket/process allocation. |
| H2 parser envelope | `max_header_block_size: 16_384`, settings `max_header_list_size: 16_384`, `header_table_size: 4_096`, `max_frame_size: 16_384`, `max_concurrent_streams: 1`; `max_requests: 1`, reset rate `{16, 1_000}`. Retain the standard 65,535 initial window; do not advertise it as a memory cap. |
| Capture | Preserve 1..1,048,576 accepted body bytes, 32,768 read target, at most 64 calls, positive requested read timeout at most 1,000 ms, exact sizes checked before retention, unchanged five-second capture success deadline. |
| Absolute transport lifetime | At most 1,000 ms for handshake; at most 1,000 ms from ready to complete request headers; at most 5,000 ms from request-start to capture-boundary completion; absolute connection lifetime at most 7,000 ms from the accepted-connection start timestamp. A stage timer never extends the outer deadline. |
| Registry / guards | At most 16 live connection entries and 16 request entries, one watchdog per live connection; no body, signature, arbitrary headers, exception, stacktrace or `conn` retained. Entry expiry is finite even if a stop telemetry event never arrives. |

These values need a composed implementation and tests. The feasibility probe
uses a 500 ms total connection watchdog, four slots, and H2 `max_requests: 4`
solely to establish cancellation and the negative stream-only case; it is not
evidence that the proposed production constants or state machine are implemented.

## Connection owner and deadline state machine

Start the bounded, supervised transport owner and its approved telemetry/Logger
configuration **before** starting the listener. The owner and listener share a
failure domain: loss of the owner, guard registration, or required handler closes
the listener and all of its owned connections. Initialization must verify
configuration before it allows a listener to start. The guard callback must not
raise and rely on telemetry to propagate the error: telemetry catches failures
and detaches the handler. A failed registration must terminate the current
connection and trip the listener failure path.

Use documented `[:thousand_island, :connection, :start]` in its emitting process
to register `self()` and the connection span reference. Its measurements contain
the accepted connection's start timestamp. This event occurs after socket
ownership transfer and before handshake or HTTP parsing. On `:ready`, shorten
the stage deadline for headers. Correlate `[:bandit, :request, :start]` using
`connection_telemetry_span_context`; the callback executes in the request owner
before the Plug. Use only fixed references/PIDs/timestamps for registration.
Require exact dedicated Plug identity and a known connection entry; never use a
request-selected PID, host, header, path, secret or policy value as authority.

The actual capture and every `Plug.Conn.read_body/2` remain in that original
request owner. A separate watchdog monitors the connection PID and uses
`Process.send_after(..., absolute_deadline, abs: true)` plus monotonic checks.
Its callback never reads the stream. Data, PINGs, empty frames, trailers,
WINDOW_UPDATEs and telemetry progress must not refresh an absolute deadline.
Timers and acknowledgments carry unguessable owner-minted references and a
generation; stale completion/timeout messages cannot disarm another request.

The boundary requires a live owner permit before body capture, after flattening,
and before returning raw bytes to any future verifier. The owner atomically
checks its generation, state, caller PID and monotonic deadline. Expired, missing,
unknown, replayed or already-consumed admission permits fail closed. Capture
admission consumes that permit without disarming the transport watchdog. The
transport lease closes only after response/failure disposal and observed owner
termination. It cannot produce a late success after expiry even if timer delivery
was delayed. The future signature/inbox contract must separately bound any
subsequent work within the selected outer lifetime and must not reinterpret this
permit as billing authority.

On deadline, capture error/exception, permit failure, or unexpected owner exit,
the watchdog uses standard `Process.exit(connection_pid, :kill)` on that exact
registered connection. It monitors `:DOWN` and retires the registry entry/timer.
H1 loses its socket owner; H2 loses its socket owner and its linked stream
processes. The pinned runtime probe observes both outcomes. This is deliberate
whole-connection disposal: no graceful response/RST_STREAM/GOAWAY or socket
draining is guaranteed. It can close sibling H2 streams; the one-stream setting
and dedicated listener make that collateral scope explicit.

After an ordinary private test response, dispose the same owned connection and
monitor all owners down. `Plug.Conn.halt/1`, setting `Connection: close`, sending
an H2 END_STREAM, or killing only an H2 request owner is not sufficient proof.
Keep the independent watchdog active while any response send could block.
Do not cancel it merely because capture returned or a response was constructed.

“Hard deadline” here means independent cancellation of a blocked reader, rather
than a check after it returns. BEAM/OS scheduling is not a real-time guarantee.
Acceptance must measure owner/socket termination by deadline +100 ms under the
declared local load, enforce no successful admission at/after the deadline, and
retain exact overshoot. VM suspension, scheduling starvation, kernel accept
backlog/startup delay and container termination require operational qualification.
If the start callback runs late, it must refuse admission and expire immediately.

## Configured-sink privacy

Before listener startup, inventory all telemetry subscribers, Logger handlers,
formatters, stdout/stderr collection and APM/error exporters in this dedicated
role. Keep the raw Thousand Island trace logger detached. Do not export Bandit
`conn`, exception, stacktrace, request fields, transport data or arbitrary error
terms. A raw subscriber cannot be made safe by attaching a second sanitizer.

An owned telemetry adapter constructs a new bounded map containing only an event
enum, fixed reason enum, bounded integer counters/durations, and server-generated
bounded correlation if needed. It discards the original measurements/metadata
and does not serialize, inspect, hash for public labels, or forward arbitrary
request data. Both measurements and metadata are covered. Guard registration
handlers are private control-plane consumers and retain no raw connection data.

Install a supported **handler filter on each configured endpoint-owned Logger
sink before its formatter/handler callback**. Accept only the owned fixed event
schema, reconstruct allowed metadata, and drop unknown messages/reports, including
Bandit trailer warnings and OTP crash reports. A domain/MFA match alone does not
make arbitrary message/metadata safe. Configure this listener's documented
`log_protocol_errors: false`, `log_client_closures: false`,
`log_exceptions_with_status_codes: []` and `log_unknown_messages: false` to avoid
unnecessary raw construction; the sink filters remain necessary. Preserve
operational visibility through independently constructed bounded reason/counter
events. Do not change shared global logger levels or depend on text substitution.

The bootstrap must reject unknown/missing filters, exporters or sinks; privileged
runtime sink changes must install the same boundary before receiving an event.
Test a subscriber/filter failure and configuration drift. A stale inventory
snapshot is not a security boundary against privileged code attaching a new raw
subscriber. Dump/core/crash-attachment configuration and collector retention need
their own operational review. This contract does not promise zero raw bytes in
in-process framework event terms or diagnostic memory.

## Resource and trailer limits

Logical body/read/header/stream/connection limits are useful but insufficient for
a hard process-memory claim. A read may allocate extra bytes before capture
rejects it; H2 DATA can be queued to a stream mailbox and the receive window is
replenished toward approximately 2 GiB. Decoded headers allocate before the
decompressed header-list check. `max_heap_size` is checked during heap activity,
and even `include_shared_binaries` is not an OS/VM/native allocation ceiling.
No fixed 1 MiB process-memory claim is permitted.

The bounded next implementation should record heap/binary/mailbox/VM RSS peaks
under large/queued frames and slow/frozen readers, plus slot exhaustion and
shutdown/drain. Public admission additionally requires an independently enforced
OS/container memory/CPU/process/socket/egress boundary, measured OOM/termination
behavior and no raw dump/export on failure. Root must select actual resource
values and an accountable operational reviewer. A local macOS probe supplies no
Linux cgroup or Cloudflare Container receipt.

Retain capture's rejection of declared `Trailer`/`te` metadata. Valid undeclared
trailers remain an adapter semantic limitation under this normal Bandit profile.
Root must explicitly choose whether public ingress may discard them while
authenticating only the exact body/original signature values, or must reject them
using a separately qualified ingress capability. No claim that every trailer is
rejected follows from this contract. No parser fork is implied.

## Evidence and acceptance sequence

[run-6](../verification/stripe-webhook-transport-contract/run-6/probe.json) passes
eight synthetic localhost clients. Four 500 ms watchdogs terminate stalled H1
headers, H2 preface without request HEADERS, H1 body, and continuously dripped H2
body at **500–502 ms**; the H2 client observes closure at **511 ms**. No blocked
body capture returns. H1 Content-Length and chunked and H2 no-Content-Length
captures still return only the private 418 marker. The H2 trailer sentinel reaches
the unfiltered/default Logger, while the newly owned filtered handler receives
three exact safe messages and no body/signature/trailer sentinel. Killing only
the H2 stream leaves no response/reset in the bounded observation and a later
PING receives PONG. All eight client sockets, connection/request owners, guards,
listener, probe handlers, scratch and child process groups are cleaned.

This proves API feasibility, **not** full sink inventory, a production deadline
state machine, maximum-body memory, TLS/ALPN or deployed ingress. Five earlier
failed harness attempts and their exact sources/output/cleanup remain sealed in
[attempts.json](../verification/stripe-webhook-transport-contract/attempts.json).
No dependency was built freshly or added; pinned dependency BEAMs were copied.

The [finite matrix](../verification/stripe-webhook-transport-contract/matrix.json)
is the implementation acceptance checklist. Root first selects this contract and
owns any public profile change. The implementation lane then owns only the
transport owner, privacy adapter, fixed configuration and private harness. An
independent reviewer must replay the original capture matrix and new adversarial
deadline/privacy/resource cases before root integrates that slice. Root must
assign a named accountable reviewer to each later gate: TLS/ALPN and actual
Cloudflare Worker/DO/container ingress, OS resource behavior, provider test-mode
delivery/header/body compatibility, trailer policy, endpoint/account authority,
durable inbox + atomic Oban enqueue, realistic billing reconciliation and G23.
None of those later gates is passed here.

```sh
python3 -B verification/stripe-webhook-transport-contract/verify.py
```

For a fresh probe, `python3 -B verification/stripe-webhook-transport-contract/run.py`
freezes source/dependency/tool inputs into a new numbered run and preserves
failures. New evidence needs a new reviewed attempt index and top-level seal;
it does not silently replace run-6 or qualify a gate. The verifier checks
immutable run closures and does not re-run obsolete 69-input live-tree checks.
No native/device, production service, provider, customer, credential, deployment
or Git action is performed.
