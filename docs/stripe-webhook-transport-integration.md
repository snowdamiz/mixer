# Private webhook transport integration

The reviewed transport module is integrated as an inactive hosted component.
The complete 72-input source closure is
`789b7de9b46ef2ce65ad83a4c916dde9a513a8eaa68dfc073e4c65ec97e2ee93`.
Root verifies 1,099 producer, independent review and composition bindings.
Only `hosted/lib/mixer_hosted/billing/webhook_transport.ex` changed; capture,
signature verification, dependencies, application startup and routes are unchanged.

The module owns a private listener's connection lifetime, one-use capture permit,
original reader disposal and configured telemetry/logger boundary. Its fixed
profile admits at most sixteen connections, one request per connection and one
concurrent HTTP/2 stream, with one-second initial stages, five-second capture and
a seven-second outer lifetime. These are private, measured development constraints.
The sink boundary requires a dedicated BEAM with trusted bootstrap; privileged
code can still reconfigure sinks, and drift detection cannot undo disclosure.

Independent tests reproduce the producer matrix and add twelve protocol,
deadline, owner-loss and privacy groups. A real zero-window HTTP/2 response with
continuing PINGs closes at the outer deadline; its original connection and reader
are observed terminated. All attempts and failures remain preserved. The full
hosted composition separately passes 142 tests, formatting, warnings-as-errors
compilation, release construction and exclusion checks. Two existing namespace
fixtures are skipped on macOS. They are not passes. Four production transport
modules have the expected exports and no producer/reviewer test helpers.

Two formatter layout changes are the only difference from the reviewed module.
The exact diff, compiler-derived token comparison and metadata-free AST equality
are retained. The normalized live module hash is
`56a26cf3a56f3e5a5b2d8f5104fc7c3371b0e44918b007197be5871cf94ef1a5`.
The isolated PostgreSQL fixture, command groups and 64,138,419 bytes of composition
scratch were cleaned.

No listener or billing route is activated by this integration. Enforced deployment
resource ceilings, public trailer policy, TLS/ALPN and ingress, endpoint/account/
mode/generation/secret authority, provider deliveries, durable inbox and atomic
Oban enqueue, reconciliation and G23 remain pending. Permanent hosted transport
release regressions are also a follow-up; current behavior evidence is executable
in the sealed isolated packets. No GA gate is passed.

See `verification/stripe-webhook-transport-integration/acceptance.json`.
Run `python3 -B verification/stripe-webhook-transport-composition/verify.py --live`
to verify the exact composed source and its retained evidence.
