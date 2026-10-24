# Stripe webhook signature boundary

Product-plan sections 13 and 17 require verified raw-body webhook admission,
durable deduplication and an atomic Oban enqueue before acknowledging delivery.
This first isolated component verifies only the signed bytes and freshness.
It must not grant tenant access, publish an entitlement, call Stripe or acknowledge
an HTTP request. Inbox/job transactions, endpoint configuration, account/mode
binding, current-state reconciliation and provider test-mode receipts remain
separate required implementation.

Stripe documents a `t` timestamp and one or more `v1` HMAC-SHA256 values over
the timestamp text, a period and the exact request body. Other schemes do not
authenticate the request. Rotation can produce multiple signatures. The normal
freshness tolerance is five minutes, and each retry receives a fresh signature.
Use a constant-time comparison. See [Stripe's manual verification specification](https://docs.stripe.com/webhooks#verify-manually)
and [raw-body requirements](https://docs.stripe.com/events/manage-webhook-endpoints#signature-errors).

Selected Mixer boundary:

- `verify(raw_body, signature_header_values, endpoint_secrets, now_seconds)`
  returns `:ok`, `{:error, :invalid_signature}` or
  `{:error, :verification_unavailable}`. An `:ok` is not a durable receipt or
  authorization object. Every call uses the caller's current endpoint secrets
  and trusted UTC clock. There is no retained secret/configuration cache.
- Exactly one header value, 1–4,096 bytes; at most 32 comma-separated fields and
  eight v1 signatures. One canonical decimal timestamp, 0–253402300799. Duplicate
  timestamps and malformed recognized fields reject the whole request.
  ASCII space/tab may surround a field; CR/LF, non-ASCII header bytes and empty
  fields reject. Unknown nonempty `name=value` fields are ignored within the same
  bounds. No unknown algorithm can supply a match.
- The body is a nonempty binary of at most 1 MiB. It is never parsed, re-encoded,
  normalized or logged by this function. JSON/schema validity is a later check.
- Supply one or two distinct opaque endpoint secrets, each 16–256 bytes. These
  are server configuration, never values selected by the request. Validate this
  configuration and the trusted clock before verifying input. Invalid/missing
  configuration returns unavailable. A future configuration owner must bind
  endpoint/account/mode/generation and keep real secrets out of logs/builds.
- The timestamp must lie within 300 seconds of the trusted clock in either
  direction, inclusive. This fixed Mixer policy cannot be disabled by passing
  zero or selecting a tolerance in the request. Fresh replay within that window
  is possible; the durable inbox must still deduplicate event identities.
- Erlang/OTP `:crypto.mac(:hmac, :sha256, ...)` and its constant-time
  `:crypto.hash_equals/2` perform cryptography. Compare every bounded signature
  against every configured key without an early match exit. Do not promise
  whole-function constant time: public parsing, size and timestamp checks vary.

The isolated candidate lives in `verification/stripe-webhook-signature/` until
independent review. No route, real key, provider call or database migration is
part of this component. Test fixtures contain explicitly synthetic secrets and
independently generated Python-standard-library HMAC vectors. No new runtime
dependency is selected: Erlang/OTP is already inventoried in `THIRD_PARTY.yml`.

Required tests cover exact bytes, modified bodies/timestamps/signatures, repeated
v1 fields and rotation, unknown schemes, header duplication/ambiguity, malformed
ASCII/hex/decimal, finite size/count bounds, past/future edges, unavailable
configuration and crypto failure. A later Plug adapter must retain every header
occurrence and capture/bound the raw request bytes before any JSON parser.
