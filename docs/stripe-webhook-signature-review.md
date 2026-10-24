# Independent Stripe webhook signature review

No actionable defect was found in the frozen signature/freshness candidate.
Accept the isolated function under the selected Mixer contract, subject to root
integration review. This acceptance does not pass W14 or G23, authorize a public
route, acknowledge HTTP delivery, deduplicate an event or grant an entitlement.

Reviewed candidate SHA-256:
`3fa0a2d8bee3e4eb9a4204857aaec0d16565df7c0d3f0aa8062158d51f2e3cb6`.
The producer packet seal is
`27191daebc5ce6dc41e93251027b72b7cabed491aa7b50450daa40346d964e16`,
and its final attempt source digest is
`d0bffad55874dc9cece9d9ec4e6ccd9adda01e4c8117623475126aab7a5f7f6f`.
Both source and independent host execution were based on revision
`d4909e275df7e757a5218cc0a88112f4fc3f088b` plus the exact frozen input manifests.
Reviewer configuration: `gpt-6.1-sol`, `xhigh`, fresh bounded review lane.

The code uses OTP HMAC-SHA256 over the supplied timestamp text, period and
unchanged body bytes. It decodes each accepted v1 hex value to exactly 32 bytes,
then compares every bounded key/signature pair through OTP `hash_equals/2`.
Canonical timestamp and finite body/header/field/signature bounds precede crypto.
Configuration and clock validation precede request validation. Every caught
crypto error, throw or exit produces unavailable, including a fault after an
earlier pair already matched. The full function has variable public parsing
work; this review makes no elapsed-time or whole-function constant-time claim.

Stripe's current [manual verification specification](https://docs.stripe.com/webhooks#verify-manually)
confirms v1 HMAC-SHA256, timestamp/body binding, multiple rotation signatures,
raw-body preservation, a normal five-minute tolerance and fresh retry signatures.
The canonical decimal grammar, symmetric inclusive 300-second policy, secret
lengths, recognized-field rejection and finite input limits are selected Mixer
policies. They are not provider-delivery compatibility evidence.
The current [OTP crypto specification](https://www.erlang.org/doc/apps/crypto/crypto.html#hash_equals/2)
documents constant-time binary comparison and a length-mismatch error; the
candidate supplies equal 32-byte lengths. The installed OTP API and backend were
also exercised directly.

The independent attempt contains 2,352 cases, generated with Python's standard
library HMAC implementation and a fixed synthetic seed. Its Elixir runner does
not generate expected signatures. Cases include 320 authentic randomized
binary bodies/keys/rotations and three tampered variants of each; signed but
noncanonical timestamps; timestamp range/freshness endpoints; every signature
nibble; malformed recognized fields amid a valid peer; forbidden octets;
improper/nonbinary terms; exact body/header/field/signature/secret bounds; and
expired key removal. Four further disposable BEAM processes inject late MAC,
comparison, throw and exit faults after an earlier match. A fifth counts all
two MACs and sixteen comparisons; that substitution proves control flow only.
Each process first verifies a real-crypto baseline and changes no installed file.

The original final 22 ExUnit tests, seven Python-vector reproduction, four
original fault processes and original schedule probe were replayed from their
exact frozen final source. Independent audit verified every one of the producer's
89 bound files, exact packet coverage, all nested receipts, source digests,
command log hashes and recorded process cleanup. Attempts 1 and 2 remain failed:
the unsupported script-runner flag and OTP JSON `:null` fixture error match their
logs. Attempts 3 and 4 remain passed. No prior evidence was rewritten.

All 22 independent qualification commands passed on macOS arm64 with Python
3.14.8, Elixir 1.20.4, Erlang/OTP 29 (ERTS 17.1), crypto 5.10 and linked OpenSSL
4.0.3. Every newly owned command group was empty afterward. Frozen inputs were
unchanged after execution. Four final read-only replays check the live producer
packet, its original verifier, the frozen producer copy and the independent
attempt seal. Their commands, outputs, receipts and nested seals are included
in the final review seal. No native device, simulator, service, real provider,
credential, database or hosted source action was performed.

Read-only review evidence replay:

```sh
python3 -B verification/stripe-webhook-signature-review/verify.py
```

The independent attempt's source digest is
`cc15ae46f32f03ca59884c9bedd694991c2296efd79f1dc33853d70deeb20ca9`.
See its [receipt](../verification/stripe-webhook-signature-review/attempt-1/receipt.json)
and [frozen inputs](../verification/stripe-webhook-signature-review/attempt-1/inputs.json).
The verifier remains an isolated candidate until root accepts and integrates it.
The required Plug raw-body/header adapter, endpoint/account/mode/generation
configuration owner, atomic deduplicated inbox/Oban transaction, reconciliation,
real Stripe test-mode deliveries, billing/usage workflows and full G23 evidence
remain pending. Fresh replay within the accepted clock window remains possible
until the durable inbox is implemented and qualified.
