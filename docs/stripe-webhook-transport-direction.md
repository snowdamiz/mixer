# Selected private webhook transport direction

Root selects the dedicated webhook BEAM role, listener, configured-sink boundary
and whole-connection disposal proposed in
[the frozen transport contract](stripe-webhook-transport-contract.md). This is
an implementation direction, not public admission or a G23 pass. The root
[selection receipt](../verification/stripe-webhook-transport-root-review/selection.json)
binds the producer packet, API findings and integrated capture source.

Use all fixed development constants in that contract: one acceptor and sixteen
connections, no connection admission retries, one request per connection and one
concurrent HTTP/2 stream, one-second handshake/header stage limits, unchanged
five-second capture limit and seven-second outer connection lifetime. Keep the
selected normal H1 Content-Length/chunked and H2 optional Content-Length framing.
The 500 ms feasibility probe does not qualify these values or their composition.

Implement this first as an isolated private candidate. Do not activate a new
application role, production listener, route, response acknowledgment, provider,
secret configuration, migration or billing job. The harness owns a separate BEAM
process and all of its sinks, clients, guards and listener. It may install the
selected sink filters on that process's default handler as well as every other
configured sink. It must preserve all unrelated host processes and log settings.
Successful private capture uses the existing non-2xx marker only.

The connection owner must register before parsing and correlate only documented
server-owned telemetry references. All reads stay in the original request owner.
Check a one-use, owner-minted permit against the original caller, generation and
monotonic deadline before returning bytes. Retain the independent connection
watchdog until disposal is observed; no body progress or request completion may
extend the outer deadline. Explicitly qualify owner/guard/listener loss and
supervision, including registration or telemetry-handler failure. Dispose the
whole registered connection and monitor both connection and stream termination.

Only exact newly constructed event enums, fixed reason enums and bounded numeric
fields may reach configured telemetry/logging sinks. Inventory both telemetry
measurements and metadata, all Logger handlers and their formatters, stdout and
stderr, and any error/exporter callbacks. Do not depend on a second sanitizer
subscriber, string replacement, log level, or domain/MFA alone. Verify the default
handler too. Preserve a safe operational counter/reason path when an arbitrary
framework or crash report is dropped.

The threat boundary is explicitly trusted application/bootstrap code and an owned
sink configuration. Supported telemetry APIs cannot atomically prevent arbitrary
privileged code from adding a raw subscriber. Bootstrap and controlled sink
changes must validate the complete inventory before admission. Detect unexpected
drift and stop admission/owned connections; do not claim this reverses data already
delivered to a newly attached raw subscriber. Dynamic third-party instrumentation
or arbitrary sink reconfiguration is outside this private profile. A polling-only
inventory is insufficient evidence of a confidentiality guarantee. Test both
bootstrap rejection and drift without mislabeling the latter as leak prevention.

The finite producer matrix remains the acceptance checklist. Measure actual
connection/socket termination and overshoot under stated load, as well as exact
no-success-at-or-after-deadline checks. Retain original capture cases and a
stream-only cancellation negative control. Measure heap, binary, mailbox and RSS
usage during bounded hostile/queued/frozen-reader cases without asserting that
body, HTTP/2 window, parser or process-heap limits establish a hard memory ceiling.

For this private slice, valid undeclared trailers may be discarded by the pinned
server and must never change the captured body or original signature arguments.
Their values must not reach any configured sink. This records existing adapter
semantics; public discard-versus-reject policy remains unselected until deployed
ingress and provider compatibility are qualified. Do not add a parser fork.

Root will assign a fresh independent implementation reviewer after the candidate
is sealed. Local implementation and review can proceed without selecting public
OS/container limits or configuring a provider. Separate accountable review is
still required for public trailer semantics, actual OS/container resource limits,
TLS/ALPN and Cloudflare ingress, provider test-mode behavior, account/endpoint/
mode/generation/secret ownership, durable inbox with atomic Oban enqueue, billing
reconciliation and G23. Earlier catalog and authority reviews remain incomplete;
this slice neither retries nor replaces them.
