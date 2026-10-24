# Stripe webhook signature component integration

The reviewed bounded signature verifier is integrated at
`hosted/lib/mixer_hosted/billing/webhook_signature.ex`. It authenticates unchanged
request bytes against the caller's current endpoint secrets and trusted clock.
It returns success, invalid signature or verification unavailable. It retains no
secret cache, performs no JSON conversion and adds no HTTP route or billing write.

Root verified the producer and independent review seals and applied exactly three
tested files: the module, its 22-test hosted suite and seven synthetic Python HMAC
vectors. The live hosted source matches the isolated composed source digest
`eb6f50bde86c742e269a605f15e3170d8dd18646f71289c2b8e5c470f5f4808d`.
The composition passed 127 host tests and production release build/rejection/
test-export checks. Two existing Linux network namespace tests were explicitly
skipped on macOS. Its private PostgreSQL fixture stopped; build scratch and all
newly owned command processes were cleaned up.

Independent review found no actionable defect across 2,352 contract cases,
four late crypto failures after an earlier match, and a comparison-schedule
probe. It also reproduced the original 22 tests and failure probes. See the
[independent review](stripe-webhook-signature-review.md) and
[selected contract](stripe-webhook-signature-contract.md) for precise limits.

The signature component is accepted as a development slice. Exact-head Linux CI
is pending delivery. Raw-body HTTP capture and header preservation, endpoint
account/mode/generation ownership, a durable deduplicated inbox with atomic Oban
enqueue before acknowledgment, current-state reconciliation, Stripe test-mode
deliveries, usage and full G23 acceptance remain required. A valid fresh request
can still be replayed at this pure boundary until inbox deduplication is added.

```sh
python3 -B verification/stripe-webhook-signature-integration/verify.py --live
```
