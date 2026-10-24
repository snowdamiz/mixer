# Independent review of private Stripe raw-body capture

Recommendation: **accept this candidate as a bounded private component development
slice**, subject to root acceptance. No new blocking implementation finding was
identified. This review grants no public webhook admission, provider
acknowledgment, billing authority or G23 acceptance.

The reviewed candidate is
`verification/stripe-raw-body-capture/candidate/lib/mixer_hosted/billing/raw_webhook_capture.ex`,
SHA-256 `7797a09d3a99f5dabafb681bf2e5bda4bb1f01bc3974beb94176965f9f30546e`.
It matches the [selected profile](stripe-raw-body-direction.md): normal HTTP/1.1
Content-Length or chunked framing and HTTP/2 with optional Content-Length. The
proposed patch remains unapplied. Only this review's files and uniquely owned
scratch were written; hosted source, producer evidence and trackers were untouched.

## Independent evidence

The reviewer independently recomputed all **273 producer seal bindings**, all
nested run seals and **9,093 archive-member bindings** across the nine retained
attempts. The candidate patch is byte-for-byte the expected addition. The root
selection, 69 accepted hosted inputs, 914 dependency-source pins, 817 dependency
BEAM pins, lockfile and executable identities match. The accepted hosted input
digest remains `eb6f50bde86c742e269a605f15e3170d8dd18646f71289c2b8e5c470f5f4808d`.
All 13 original matrix rows retain their required cases and pending limitations.

Producer run-9 has 105 uniquely correlated clients: 70 HTTP/1 and 35 h2c. Direct
reconstruction from final server events gives 28 captures, 60 capture rejections,
seven raises and ten framework rejections before Plug. The final correlations
match exactly. Historical attempts remain unchanged, including the failed
harnesses, run-6's incomplete telemetry observer and run-8's literal recorded
verifier counts. Those superseded observations were not promoted into evidence.

Fresh isolated reviewer [run-1](../verification/stripe-raw-body-capture-review/run-1/receipt.json)
passes the 14 original component groups, **eight independent component groups
with 360 controlled subcases**, and **16 wire groups with 110 clients**: 73 HTTP/1
and 37 h2c. There are 100 final Plug outcomes and ten pre-Plug rejections. None
returns a 2xx status. The original component and wire harnesses were replayed from
the verified archive; the wire harness was extended only in reviewer scratch,
with the exact [instrumentation diff](../verification/stripe-raw-body-capture-review/run-1/wire-instrumentation.diff)
and complete source closure retained.

The additional component cases independently cover 1–64-part binary partitions,
optional empty terminal chunks, declared/aggregate size boundaries, opaque errors
after partial reads, unavailable connections, all disallowed ASCII controls and
non-ASCII media bytes, unchanged arbitrary signature metadata, shrinking read
timeouts, late empty EOF, and forbidden framing/upgrade tokens. The adapter
records and asserts the original caller PID on every read.

The additional wire cases cover body bytes resembling chunk delimiters,
Content-Length segmentation, chunk extensions, identical repeated signature
occurrences on both protocols, and a signed 60,001-byte HTTP/2 body with explicit
Content-Length and four DATA parts. The latter returns 49,152 bytes against a
32,768-byte target before a final 10,849-byte read, preserving exact body/HMAC.

Verifier invocation was independently measured with the VM's function-call trace
for the actual `MixerHosted.Billing.WebhookSignature.verify/4` entry point. The
collector is a separate process and records argument body hashes/lengths, original
signature lists, secret count and trusted synthetic UTC. A trace-delivery barrier
precedes the per-request result. **31 actual calls** were observed: exactly one
for each capture and zero for all 62 capture rejections and seven raises. Every
traced body/hash/length and signature list matches the capture and adapter-exposed
values. These are observed function entries, independent of the producer's
call-site counter. No domain/provider/database/Oban entry point is present, so
zero domain calls remain a harness-scope fact.

The candidate and accepted signature module compiled freshly into isolated
targets. A separate production compilation exposes only `capture/1` plus standard
module metadata, has no test-clock atom and ignores the spoofed private/process
clock. Dependency BEAMs were reused under exact identity pins; this is not a fresh
dependency build. Tools are Elixir 1.20.4, Erlang/OTP 29.1.1/ERTS 17.1, Python
3.14.8, Plug 1.20.3, Bandit 1.13.1, Thousand Island 1.6.0 and Mint 1.11.0 on macOS.
Commands, overrides, binary hashes, outputs, source manifests and archives are
retained in the review run.

## Boundaries that remain open

The fresh run reproduces the declared transport problems. Thousand Island recv
telemetry exposes synthetic body/signature bytes in **measurements**, and Bandit
request metadata exposes synthetic connection/request fields. The HTTP/2 trailer
sentinel reaches Bandit's warning logger. The frozen proposal's metadata wording
is an erratum; the producer's measurements correction agrees with pinned
`Socket.recv/3` and `untimed_span_event/4`. Both measurements and metadata are
scanned by the final observer. This is exposure evidence, not privacy qualification.

A real 55-byte slow HTTP/2 body returns from one nominal 1,000ms read after
**5,557ms** in the independent run. Capture rejects `:read_deadline`, with zero
actual verifier invocations. The five-second check bounds successful admission;
it cannot terminate an adapter call. HTTP/2 read sizes are advisory. Undeclared
HTTP/1 trailers remain invisible to capture. Exact-limit chunked `:more` rejection
is conservative and intentional, and a real maximum-size HTTP/2 body remains
untested. These limitations agree with the selected private contract and prevent
public admission.

Endpoint-owned privacy, header-read/buffer/resource limits, hard cancellation and
stream/connection disposal, TLS/ALPN, deployed ingress/provider compatibility,
server-owned endpoint/account/mode/generation/secrets, a durable deduplicated
inbox with atomic Oban enqueue, Stripe test-mode reconciliation, usage ledger and
the full G23 account/workflow matrix all remain pending. No production route,
endpoint, response policy, signing, provider or operational qualification is inferred.
No native runtime, physical device, UI, production publication or unrelated
catalog inspector action was run.

## Replay and cleanup

```sh
python3 -B verification/stripe-raw-body-capture-review/run.py
python3 -B verification/stripe-raw-body-capture-review/verify.py
```

The fresh run removed its scratch only after holder token/device/inode validation,
an empty `lsof` result and empty owned process groups. Its single port-0 localhost
listener was stopped, all 110 client sockets were closed, telemetry/logger
handlers were detached and the port refused connections after process exit.
The owned process inventory and cleanup receipt are retained. No other process or
service was stopped. The producer seal and pins were rechecked after the fresh run.

The top review seal binds this document, the review scripts, the independently
reconstructed observations, exact fresh source archive, command outputs and nested
receipt/seal. [Review receipt](../verification/stripe-raw-body-capture-review/review.json)
records the recommendation without upgrading public or GA gates.
