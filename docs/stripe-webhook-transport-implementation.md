# Private webhook transport candidate

Status: sealed isolated candidate awaiting independent implementation review. No
live product role, route, provider, DB/schema, tracker or Git state was changed.
The [root-selected direction](stripe-webhook-transport-direction.md), frozen
contract and selection receipt remain authoritative. This packet adds no public
admission or G23 acceptance and does not retry catalog-inspector or authority work.

The [candidate source](../verification/stripe-webhook-transport/candidate/lib/mixer_hosted/billing/webhook_transport.ex)
contains a dedicated supervisor, bounded owner, independently supervised guards,
and owned sink boundary. The [patch](../verification/stripe-webhook-transport/candidate.patch)
adds only that proposed hosted module; it is not applied to hosted. Capture and
signature compile freshly from the accepted 71-input source digest
`ac391070ec439ecfca288b9a7657aac1eada5bc1196efb8735211cc60a6883bc`.
Capture remains byte-identical at `a420d5a54868d61c3d6e9c7cb41807698eb729df3e6babda12135a727ac657ea`.

The profile fixes one acceptor, sixteen connections, retry count zero, backlog
128, one request and one concurrent H2 stream, 1s handshake and header settings,
5s capture, and a 7s outer lifetime. Documented Thousand Island span references
register the original connection before parsing. Documented Bandit request refs
and the exact trusted Plug identity register the original reader. The owner
mints caller/generation/deadline-bound one-use permits, checking before capture,
after flattening and before returning bytes. A final local monotonic comparison
also refuses a delayed owner reply. Permits grant no billing authority.

The per-connection guard never reads the body. Absolute timers and monotonic
checks dispose the whole registered connection using standard Process.exit,
monitoring connection and distinct H2 request owners until DOWN. Body progress
cannot extend the outer lifetime. Successful capture changes the active stage
to the unchanged absolute outer deadline; it does not disarm disposal during a
blocked response. Guard, owner, listener and required registration loss terminate
the dedicated role. Restart requires trusted bootstrap; no unguarded automatic
listener restart is enabled. Unknown/replayed permits fail closed.

The separate owned BEAM inventories all telemetry subscribers, primary Logger
callbacks, handler filters, formatters, default stdout, OTP ssl_handler, declared
collector and merged stderr capture. No APM/error exporter or raw trace subscriber
is configured. Known standard primary/filter callbacks are validated; undeclared
sinks reject bootstrap. Every handler receives the pure schema filter before its
standard logger_formatter callback. Only reconstructed fixed event/reason enums,
bounded integers and fixed domain metadata reach sinks. Arbitrary messages,
metadata, exception reports and H2 trailer warnings are dropped. Protective
filters remain through role teardown and BEAM exit, covering supervisor reports.
The harness's return-only verifier trace suppresses call messages/arguments.

Trusted application/bootstrap and controlled sink configuration are the boundary.
The supported telemetry API cannot atomically stop privileged code from attaching
a raw subscriber. Inventory checks precede registration and permit admission;
25ms drift polling is additional detection, not a confidentiality guarantee. The
privileged subscriber and removed-filter negative controls explicitly make no
prevention claim; the latter observes data already delivered to its collector.
No claim reverses delivered bytes or protects arbitrary IO/diagnostics by
privileged application code. Dynamic third-party instrumentation, dump/core
collection and collector retention need operational review.

[Run run-14](../verification/stripe-webhook-transport/run-14/receipt.json) passes
14 unchanged component tests, 13 unchanged baseline wire groups, 13 composed
wire groups (105 clients), 13 adversarial tests, and a fresh stream-only negative
control. An independent return-only trace measures 27 composed verifier returns,
equal to the actual inline invocation count. Adversarial max-body/blocked-response
cases call the actual verifier 2 times; no billing/domain work runs.
All responses are private non-2xx markers. The negative control kills only an H2
stream, observes no response/reset in 200ms, then receives PONG on the still-live
connection before explicit cleanup; it is never counted as the protected profile.

The [timing receipt](../verification/stripe-webhook-transport/receipt.json) retains
actual peer closure times and exact monitored disposal overshoot. Under the local
load, H1 headers, H2 preface and unfinished CONTINUATION close at the selected
1s stage, a frozen H2 reader closes at 5s despite PINGs, and blocked response work
closes at the absolute 7s lifetime, each within deadline+100ms. Deliberately
suspended own-guard permit tests separately refuse at/after expiry; they do not
promise real-time scheduling during VM suspension/starvation.

[Baseline comparison](../verification/stripe-webhook-transport/baseline-comparison.json)
retains exact case IDs and outputs. `h2-slow-gap` previously captured after a
1.2s gap under the older 2s idle profile; selected 1s idle disposal rejects it.
`h1-no-body`/`h1-slow-gap` may lose their connection before framework error return,
and `h2-late-success` is disposed rather than returning a late capture failure.
Every recorded rejected case has zero verifier calls. Client elapsed values in
old deliberately sleeping send loops are upper bounds, not exact peer-death
measurements; dedicated adversarial clients observe peer termination directly.
These are narrower transport timings, not a changed capture grammar or a provider
compatibility claim. Original captures and byte/signature arguments remain intact.

H1 Content-Length/chunked and H2 optional Content-Length remain supported. Real
undeclared H1/H2 trailers retain pinned adapter discard semantics and do not
change the exact body/original signature arguments. Their values reach no owned
configured sink. Public discard-versus-reject policy remains unselected.

[Resource observations](../verification/stripe-webhook-transport/resource-observations.json)
include a real accepted 1,048,576-byte H2 terminal DATA body, queued/frozen H2
hostility, sixteen occupied slots, overflow, oversize frames and compressed
headers exceeding the decompressed limit. Observed sampled maxima are RSS
136496 KiB, per-process heap 1598 words, binary references
1353568 bytes, and 64 queued messages.
These are sampled observations, not an absolute peak or memory ceiling. Shared
binary references can overcount allocations; parser/window/body/heap settings do
not establish OS/VM/native resource ceilings. SETTINGS/window extremes, reset
floods and the full new-stream matrix remain explicitly partial in the
[16-row matrix](../verification/stripe-webhook-transport/matrix.json).

All fourteen attempts retain original sources, actual outputs, tool versions,
executable hashes, compiled candidate BEAMs where compilation completed, source
archives and exact seals. Failed runs stay failed. Some early failed receipt
`freshCandidateCompilation` fields recorded intent before a compile completed;
[attempts.json](../verification/stripe-webhook-transport/attempts.json) distinguishes
observed compiled artifacts. Pinned original dependency source closures and
BEAM/source identities are retained; no dependency was added or freshly built.
Every attempt has no remaining owned process group/open scratch holder, refused
observed ports and removed identity-marked scratch. Role cleanup rows additionally
cover every sequential listener, connection/owner/guard supervisor and client.
No host simulator, native device, unrelated process or shared logger was touched.

Independent implementation/privacy review is pending. Public OS/container resource
values and enforced failure behavior, real TLS/ALPN, deployed Cloudflare ingress,
provider test-mode timing/body/header behavior, public trailers, endpoint/account/
mode/generation/secret ownership, durable inbox with atomic Oban enqueue, billing
reconciliation and G23 remain pending. Local evidence cannot pass those gates.

```sh
python3 -B verification/stripe-webhook-transport/verify.py
```

The verifier checks the immutable packet and every retained attempt. A fresh
`run.py` replay creates a new numbered attempt; it invalidates the current sealed
file set until root explicitly accepts and reseals a new packet. Never silently
replace this receipt or reinterpret failed/historical probes as qualification.
