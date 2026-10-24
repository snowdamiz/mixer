# Private Stripe raw-body capture integration

Root accepted and integrated the bounded capture component after independent
review and a fresh full hosted composition. The 71-input source digest is
`ac391070ec439ecfca288b9a7657aac1eada5bc1196efb8735211cc60a6883bc`.
The full host suite passes **142 tests**, with two existing Linux network-namespace
fixture tests explicitly skipped on macOS. These skips are not passes. The
production release builds, rejects missing runtime settings as expected, and
contains neither the capture test clock nor its test adapter. The four prior
identity-fixture export exclusions also pass.

The implementation accepts the root-selected normal HTTP/1.1 Content-Length or
chunked profile and HTTP/2 with optional Content-Length. It preserves unparsed
body bytes and the original exposed singleton signature header list, limits
successful capture to 1 MiB and 64 reads, checks the five-second success deadline
before/after reads and after flattening, and halts rejected connections. It reads
on the stream owner's process and emits no response or signature decision.

Three files changed: the private `RawWebhookCapture` module, fifteen production-mode
regressions, and the existing release collector's capture export/clock checks.
The new regressions exercise exact bytes and real signature composition, framing,
header occurrences, size/read limits, malformed adapter results, current connection
state, production clock exclusion and an actual late adapter return. Deterministic
deadline-edge tests remain in the separately compiled and sealed isolated packet;
the integrated suite uses the production monotonic clock.

The reviewed module SHA-256 is
`7797a09d3a99f5dabafb681bf2e5bda4bb1f01bc3974beb94176965f9f30546e`.
The integrated module SHA-256 is
`a420d5a54868d61c3d6e9c7cb41807698eb729df3e6babda12135a727ac657ea`.
Their sole difference is removal of one final blank line by the formatter; the
exact normalized source is what the composed suite and release compiled.

Independent review retains 38 passing test groups, 360 controlled subcases,
110 localhost HTTP clients and 31 directly traced signature-verifier calls.
Every traced argument matches the captured bytes/header values; capture rejection
and raised reads invoke no verifier. Producer and reviewer wire responses are
all non-2xx. Root verifies 433 producer/reviewer/composition evidence bindings.
The isolated root PostgreSQL instance, command groups and 63,766,343 bytes of
scratch were cleaned after the holder and directory-identity checks.

This component does not solve transport privacy or hard cancellation. Raw
sentinels remain observable in dependency telemetry and the HTTP/2 trailer logger.
A nominal one-second HTTP/2 read can return after five seconds; capture rejects
that result, but does not interrupt the ongoing read. Read sizes are advisory;
exact-limit chunked `:more` is conservatively rejected. Real maximum-size HTTP/2,
TLS/ALPN and deployed ingress/provider behavior are not qualified.

There is no public route, success acknowledgment, endpoint/account/mode/generation
or secret owner, durable inbox, Oban enqueue, provider reconciliation or billing
mutation in this change. Endpoint-owned logging/exporter boundaries, absolute
resource/deadline ownership and stream disposal are the next coordinated slice.
Full G23, operational and GA acceptance remain pending.

Evidence: `verification/stripe-raw-body-integration/acceptance.json` and its
`attempt-1/hosted/receipt.json`. Run
`python3 -B verification/stripe-raw-body-integration/verify.py --live` to recheck
the sealed integration and all current composed inputs. Earlier producer/reviewer
checks against their original 69 live inputs are historical after the release
collector change; their sealed archives and receipts remain immutable.
