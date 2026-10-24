# Selected private raw-body capture boundary

Root selects profile 1, normal Bandit HTTP/1.1 and HTTP/2 framing, from
[the frozen proposal](stripe-raw-body-contract.md). This authorizes an isolated
capture implementation and disposable localhost tests. It does not register a
route or accept public webhook traffic. The proposal remains immutable; this
direction records the selection.

Use the proposed exact metadata, body, read-count and monotonic success-deadline
checks. HTTP/1.1 permits canonical Content-Length or a single chunked transfer
encoding, with no mixture. HTTP/2 permits optional canonical Content-Length and
no transfer coding. Preserve all adapter-exposed signature occurrences and every
body byte. Do not parse or re-encode JSON. The implementation must check actual
returned sizes before retaining chunks; a requested read length is advisory.

The fixed private test target is POST `/api/v1/webhooks/stripe`, with no query.
It is not a commitment to the final registered public URL. The private component
has no HTTP-selected secrets, UTC clock, limits or other authority. Every capture
failure makes the returned connection unusable to the caller: the caller must
halt and dispose of it, never resume routing. Capturing bytes sends no response.
Use a non-2xx success marker only in the disposable test Plug.

The five-second check bounds successful capture admission; it is not forced
termination. Both accepted results and the final flattened binary must still be
within that deadline. An error, late result or partial stream cannot authorize a
signature check or downstream action. Do not substitute a detached reader Task:
the pinned adapter requires its original stream owner. Preserve framework
exceptions as failures without inspecting or logging arbitrary request data.

All thirteen proposed evidence rows remain required. Implement component/fake
adapter tests and actual localhost HTTP/1.1 and HTTP/2 cases now. Distinguish
framework rejection before Plug from capture rejection. Bind exact source,
dependency and tool versions, all failed attempts, and cleanup on both success
and failure. Only synthetic locally generated bodies and test keys are used.

The pinned stack exposes received bytes in transport telemetry and can log
HTTP/2 trailers before application handling. Source review does not prove
redaction, memory limits or cancellation. Observe these paths with synthetic
sentinels and report unresolved transport behavior honestly; do not globally
mute or alter other applications' logging. No dependency patch, parser fork,
ingress change or broad logger policy is authorized by this component selection.
An endpoint-owned transport/logging/cancellation contract and real tests must
resolve these issues before public admission. The full provider/ingress profile,
durable inbox with atomic Oban enqueue, endpoint/account ownership, real Stripe
test-mode reconciliation, usage ledger and G23 remain pending.

Root independently replays the nine dependency API probes and binds the frozen
proposal plus the current 69-input hosted closure in
[`selection.json`](../verification/stripe-raw-body-root-review/selection.json).
Those probes establish API behavior only; no raw HTTP implementation has passed.
