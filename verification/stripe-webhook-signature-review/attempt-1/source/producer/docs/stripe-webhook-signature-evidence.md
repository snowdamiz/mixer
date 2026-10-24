# Isolated Stripe signature verification evidence

The standalone candidate passes 22 host tests, seven of them independently
generated Python HMAC vectors, under Elixir 1.20.4 and Erlang/OTP 29 on macOS.
The candidate remains outside `hosted/` pending independent review and an
accepted integration. No authenticated HTTP endpoint or billing state is added.

The tests cover exact binary bodies, every byte of one signed body and every
signature hex position, timestamp changes, both inclusive freshness boundaries,
current and rotated keys in all eight signature positions, bounded extensions,
malformed/ambiguous input, configuration and size limits. JSON whitespace changes
invalidate signatures. A repeated fresh request succeeds twice at this boundary;
the future durable inbox is responsible for deduplication.

Four disposable BEAM processes replace only their own loaded crypto module after
first verifying a real Python vector. Error, throw, exit and comparison faults
return `verification_unavailable`. A fifth process substitutes a counting
comparison to demonstrate that a first match still visits all sixteen pairs for
two keys and eight signatures. That fifth check tests control flow, not crypto
correctness or elapsed-time constancy. Module-redefinition warnings in these
five logs are expected fault-injection evidence; no installed library or service
is changed. Production compilation with warnings as errors passes separately.

`verification/stripe-webhook-signature/attempt-4/` contains the final exact
source snapshot, its compiled BEAM, tool versions, all twelve commands and
outputs, source digest and recursive artifact seal. Every newly owned command
group is empty after execution. The source remains unchanged across execution.
The failed first attempt used a compiler-only CLI flag with the script runner;
the second failed one fixture because OTP JSON represents null as `:null`.
Both attempts are retained. The third passes the same 22 tests and four fault
probes; the fourth adds the comparison-schedule probe. The initial source review
also corrected mixed ASCII space/tab trimming before qualification.

Read-only evidence replay:

```sh
python3 -B verification/stripe-webhook-signature/verify.py
```

The selected [contract](stripe-webhook-signature-contract.md) defines Mixer
limits. Real provider test-mode deliveries, the Plug raw-body adapter, endpoint
account/mode/generation ownership, durable deduplication and atomic Oban enqueue,
out-of-order reconciliation, metering and installed-app continuity remain
required. This receipt does not pass G23 or establish full commercial billing.
