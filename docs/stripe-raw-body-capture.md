# Private Stripe raw-body capture candidate

Status: **private component candidate; scoped tests pass; independent root review pending**.
The selected normal Bandit profile is implemented only under
[`verification/stripe-raw-body-capture/candidate`](../verification/stripe-raw-body-capture/candidate).
No hosted source, route, endpoint, acknowledgment, secret owner, database or Oban
worker is changed. This is a W14/G23 development slice under product-plan 13.2/17,
not public Stripe admission or an accepted G23 gate.

The selected/frozen contract remains unchanged. The accepted 69-input hosted
closure is `eb6f50bde86c742e269a605f15e3170d8dd18646f71289c2b8e5c470f5f4808d`;
the existing signature module remains
`3fa0a2d8bee3e4eb9a4204857aaec0d16565df7c0d3f0aa8062158d51f2e3cb6`.
The candidate source SHA-256 is
`7797a09d3a99f5dabafb681bf2e5bda4bb1f01bc3974beb94176965f9f30546e`.
The proposal retains its historical preselection status; root's
[direction](stripe-raw-body-direction.md) and selection receipt choose profile 1.

## Component boundary

`MixerHosted.Billing.RawWebhookCapture.capture(conn)` returns the concatenated
exact body bytes, the original adapter-exposed singleton signature value list,
and the latest returned connection. It does not parse JSON, normalize body/header
bytes, invoke verification, read secrets or configuration, persist, enqueue,
call a provider, send a response, or select authority from HTTP input.

The fixed envelope checks the original POST/path/query, bounded ASCII JSON media
metadata, absent content encoding/Expect/Trailer/Upgrade/HTTP2 `te`, exactly one
bounded signature occurrence and selected framing. HTTP1.1 accepts canonical
Content-Length or one chunked transfer coding; HTTP2 accepts optional canonical
Content-Length without transfer coding. HTTP1.0 fails. A component rejection
happens before any body read when metadata is invalid. Framework rejection may
precede the Plug entirely. Adapter-exposed values are preserved; HTTP parsing
may already have removed wire field whitespace.

The body cap is 1..1,048,576 bytes, the read target is 32,768 bytes, there are at
most 64 calls, and each requested timeout is positive and at most 1,000ms. Actual
returned byte counts are checked before chunks are retained. Reads thread the
returned connection, including into an error that supplies no new connection.
Empty `:more`, exhausted bytes, length mismatch and call-budget exhaustion fail
closed. A maximum-size `:more` fails immediately: the observed exact-limit chunked
body therefore rejects rather than verifying an unproven prefix. A final empty
`:ok` is permitted only after nonempty earlier data.

The monotonic five-second deadline includes metadata checks, read returns and
final flattening. It limits successful admission; it cannot terminate a blocked
adapter. The adapter remains on its stream owner process. The clock seam is a
compile-time test branch with no capture options or HTTP/private-conn selection.
A separate production compilation has only `capture/1` and standard module
metadata exports, contains no TestClock atom, and ignores a spoofed conn-private
clock and process test-clock key. Production and test BEAMs are retained.

All ordinary error reasons are fixed atoms and the returned connection is halted
and unusable. The caller must dispose of it. Transport exceptions and malformed
Plug return-shape exceptions propagate as failures; capture neither inspects nor
logs arbitrary exception/request data. There is no downstream invocation after a
capture error. The disposable caller uses 400 for ordinary failures, closes its
HTTP1 responses, and uses **418 even on capture success**. Those test mappings are
not final endpoint error policy or provider acknowledgment behavior.

## Observed evidence

Authoritative producer [`run-9`](../verification/stripe-raw-body-capture/run-9)
passes **14 component tests and 13 wire test groups**, with **105 actual clients:
70 raw TCP HTTP1 and 35 Mint h2c HTTP2**. Every response/status remains non-2xx.
The private Plug is the first body consumer. A counting wrapper delegates real
reads to the original Bandit adapter on the same owner process; the separate
scripted adapter tests are explicitly component-only evidence.

Wire cases cover exact POST/path/query and original HEAD rejection; media and
content-coding metadata; repeated/mixed-case signature names; missing/empty/
4096/4097-byte values; canonical/invalid/repeated/comma Content-Length; normal
chunking/extensions; malformed/truncated bodies; undeclared trailers; maximum
and oversized streaming bodies; early disconnect/timeout; HTTP1 pipeline close;
HTTP2 DATA splitting/coalescing/END_STREAM, mismatches, duplicates and late results.
Synthetic HMAC verification succeeds on exact captured bytes and fails after
whitespace, newline, or UTF8/escaped representation changes. No JSON parse occurs.
Verifier calls are measured at the call site: one after capture success and zero
after capture error/raise. No domain/provider/DB/Oban entry point exists in this
harness, so its zero domain calls do not qualify production integration.

Ten cases are rejected by the framework before the Plug. Use
[`wire-correlations.json`](../verification/stripe-raw-body-capture/wire-correlations.json)
for final correlation; the raw per-client event snapshot can be null immediately
after disconnect even when the server records a later read exception. All 95
actual Plug outcomes remain preserved separately.

The scripted adapter tests separately cover returned chunks larger than the
requested target/aggregate cap, exact maximum terminal/more states, 64/65-call
behavior, empty progress, opaque errors, connection threading, nonbinary/malformed
shapes, raises, late return, deadline boundaries and post-flatten deadline refusal.
They establish no Bandit framing or forced cancellation claim.

The pinned tools are Elixir 1.20.4, Erlang/OTP 29.1.1 (ERTS 17.1), Plug 1.20.3,
Bandit 1.13.1, Thousand Island 1.6.0 and Mint 1.11.0 on macOS. The candidate and
signature source compile freshly into disposable targets. Dependency BEAM cache
copies are reused with exact source/BEAM/lock/toolchain identity pins; there is
no fresh dependency-build claim. No dependency is added. Full commands, environment
overrides, executable hashes, version outputs, source archives and outputs are
retained. All earlier failed attempts and their exact source/output are sealed;
[`attempts.json`](../verification/stripe-raw-body-capture/attempts.json) explains
harness corrections and superseded observer limits. Run-6 did not inspect raw
received-data measurements and is not cited for that observation.

## Transport findings and remaining gates

The final observer scans both telemetry measurements and metadata recursively as
bytes, plus a local logger handler. There is no global logger mute or dependency
patch. Synthetic sentinels directly show:

- ThousandIsland `[:thousand_island, :connection, :recv]` exposes received body and
  signature bytes in **`measurements.data`**. This corrects the frozen proposal's
  field description: `Socket.recv` passes the data map as the third argument to
  `untimed_span_event`, which is measurements, not metadata. The privacy
  requirement is unchanged; exporters must account for both fields.
- Bandit request telemetry metadata exposes synthetic request/connection fields.
- Bandit logs the undeclared HTTP2 trailer sentinel in its warning message.
- One real HTTP2 read requested 32,768 bytes and returned 45,001 bytes, followed by
  an empty terminal read. The full body and original HMAC were preserved.
- One real HTTP2 read with a requested 1,000ms receive timeout returned 55 bytes
  successfully after **5,564ms** of successive DATA frames. Capture rejected it
  with `:read_deadline`, zero verifier calls and no 2xx. This demonstrates late
  refusal and the unresolved hard cancellation boundary.

These observations are preserved in
[`transport-observations.json`](../verification/stripe-raw-body-capture/transport-observations.json).
Logging/privacy is **not qualified**. No 1MiB process-memory ceiling, arbitrary
adapter-allocation bound, header-read deadline, forced cancellation, real maximum
HTTP2 body test, TLS/ALPN qualification, or deployed ingress compatibility is
claimed. HTTP1 trailers remain invisible to capture; no public trailer-policy
enforcement is established. Disposable caller closure/client cleanup does not
supply the future endpoint's full stream/connection disposal contract.

All **13 original matrix rows and their original required cases** are retained in
[`matrix.json`](../verification/stripe-raw-body-capture/matrix.json), with scoped
results and accurate pending limits. Endpoint-owned transport privacy/cancellation,
server-owned endpoint/account/mode/generation/secrets, deployed ingress/provider
compatibility, durable deduplicated inbox plus atomic Oban enqueue, Stripe test-mode
reconciliation, usage ledger, independent root acceptance and G23 remain pending.

## Replay and cleanup

```sh
python3 -B verification/stripe-raw-body-capture/run.py
python3 -B verification/stripe-raw-body-capture/finalize.py
python3 -B verification/stripe-raw-body-capture/verify.py
```

`run.py` creates a new numbered evidence directory and fresh owned scratch each
run. It uses one localhost port-0 listener at a time, externally bounds each client
and child process group, and retains failed output. All attempts removed owned
scratch only after holder-token/device/inode and open-holder checks. Final runs
also verified empty owned process groups and refused listener ports after process
exit; every started listener was stopped and every socket closed. The listener's
own cleanup records handler removal, telemetry detach and connection refusal.
No other service/process, native runtime or physical phone was touched.

[`candidate.patch`](../verification/stripe-raw-body-capture/candidate.patch) is a
reviewable proposed hosted addition; it has not been applied. Retained source and
dependency archives permit review after scratch cleanup. The top seal includes
nested receipts/seals and failed attempts. This receipt is a component development
result and leaves public admission closed.
