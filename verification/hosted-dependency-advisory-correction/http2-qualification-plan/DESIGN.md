# Two bounded HTTP/2 wire qualifications

This is a source-only implementation proposal. No listener, Mix command, test,
network request or process probe ran during preparation. The dependency upgrade
does not itself qualify either case below.

## Selected scope and source boundary

Add only two test files: `hosted/test/support/http2_wire_fixture.ex` and
`hosted/test/mixer_hosted/billing/raw_webhook_capture_http2_test.exs`. Use five
named ExUnit methods containing seven finite subcases: three body cases, then a
package-read and a Mixer-capture method each covering SETTINGS and stream
WINDOW_UPDATE. No product source, dependency, workflow, DB fixture, callback
harness, native wrapper or external service change is needed.

The current local dependency directory still declares Bandit **1.13.1**;
Bandit **1.14.0** is the selected lock version. No 1.14.0 tar was present at the
three relevant local Hex cache paths checked. Public seams below are verified
against the locally retained source; they are not a claim to have inspected or
executed materialized 1.14.0 code. Before selecting the implementation, bind its
actual 1.14.0 `mix.exs`, adapter and HTTP/2 stream/connection sources supplied by
the normal dependency environment. Confirm the timeout result shape and the
prequeued batching witness there. Do not weaken a missing witness into a pass.

`RawWebhookCapture` uses a 32,768-byte requested read, 1,048,576-byte total cap,
64 reads, one-second individual read timeout and five-second **success admission**
deadline. It checks actual returned bytes. Its error connection is halted and
must be disposed; its deadline does not forcibly cancel arbitrary adapter work.
The existing fake-adapter tests already cover over-target returns, exact/over
body limits and declared-length mismatch. New tests must reach the real HTTP/2
transport rather than repeat those adapters.

## Hooks and fixture contract

Start one unnamed, ExUnit-supervised Bandit listener per subcase with trusted
test-only Plug options, `ip: {127,0,0,1}`, `port: 0`, cleartext HTTP and HTTP/1
disabled. Keep HTTP/2 enabled, one active stream/request and finite fixture
connection/header limits. Use a listener idle timeout above the case deadline
so it cannot masquerade as the body-read deadline. Disable protocol/exception
logging on this fixture only; do not alter global Logger handlers or activate
the private WebhookTransport role.

The concrete proposal is one acceptor/connection slot, no accept retry, a
5-second transport idle timeout, decoded headers capped at 1 KiB and advertised
max-concurrent-streams 1. The client opens exactly one request. Leave
`max_requests` at its normal default so a first-request graceful GOAWAY cannot
be mistaken for a body-deadline failure. These are fixture limits, not evidence
about the private transport profile or the deployed API's limits.

`Bandit.child_spec/1`/`start_supervised!` provides lifecycle ownership;
`ThousandIsland.listener_info/1` returns `{:ok, {ip, port}}` and
`connection_pids/1` lists only this owned server's connection children. Monitor
the actual Plug stream PID reported at entry. Never inspect Bandit's private
connection state or send it private `{:bandit,...}` messages.

The test Plug sends a correlated entry message and waits for a trusted test
release before reading. The production `RawWebhookCapture.capture/1` then runs
in that **same stream process**: the underlying Bandit adapter validates its
calling process. A test-only read observer wraps the original adapter tuple and
delegates only `get_http_protocol/1` and `read_req_body/2`, preserving the real
adapter state in every result. It reports options, tag, returned byte count and
monotonic start/end times, never body contents. Do not declare this two-method
observer a full `Plug.Conn.Adapter` implementation. On success unwrap the newest
adapter before sending a tiny 204 response. On error report the finite capture
reason/`halted` state and wait for owner disposal; never send success or reuse
the halted connection.

Use an independently authored, small HTTP/2 wire helper over passive
`:gen_tcp` with a literal IPv4 address. Encode bounded request headers with the
already locked `HPAX.encode(:never_store, headers, HPAX.new(0))`; no new package
is needed. Write the standard connection preface and only SETTINGS, HEADERS,
DATA, WINDOW_UPDATE, PING and their required ACKs. Stream ID is 1 on each fresh
connection. Parse only a bounded 9-byte frame header and a bounded payload;
reject unexpected GOAWAY/RST_STREAM except where explicitly recorded as a
fixture failure. Maintain both connection and stream send credit, honoring
server SETTINGS/WINDOW_UPDATE instead of sending past its receive window.
Mint's public HTTP/2 API is available, but using one raw helper avoids mixing
Mint's opaque protocol state with manually injected control frames.

## Body cases: Mixer guarantees through actual Bandit

**B1 — prequeued over-target read.** Send valid request headers for
`POST /api/v1/webhooks/stripe`, `content-type: application/json` and a bounded
synthetic `stripe-signature`. While the Plug waits, preload a 40,001-byte body
in legal DATA frames and END_STREAM; it fits the initial 65,535-byte receive
credit. Follow with a unique PING and wait for its matching ACK before releasing
the Plug. That standards-based fence proves the connection consumed preceding
frames without poking private process state. Require actual HTTP/2, the real
Bandit adapter, a measured return larger than the requested 32 KiB, exact
captured length/bytes and unchanged signature-header bytes. The observer must
record the oversized return; if 1.14.0's actual batching does not produce it,
report the batching qualification uncovered and refine the fixture using its
version-bound source before release. Do not silently drop that assertion.

**B2 — inclusive application cap.** Send exactly 1 MiB without Content-Length,
respecting connection/stream window credit as it is replenished. Require capture
success, exact bytes, no late-success admission and no more than 64 reads.
Set END_STREAM on the last payload DATA frame itself, rather than leaving an
otherwise complete 1 MiB body nonterminal until a later empty frame.

**B3 — cap plus one.** Send at most 1 MiB + 1, again without Content-Length.
Require `{:error, :too_large, halted_conn}`, no captured-success event and owned
stream/connection disposal. This avoids confusing Bandit's own declared-length
framing rejection with Mixer's byte-cap branch. A future declared-length wire
case could be rejected earlier by Bandit; that must not be counted as Mixer
`:length_mismatch` coverage. Its existing fake-adapter test remains separate.
For this named input, require the client actually sent 1 MiB + 1: reserve credit
and place the final full DATA frame plus the final one-byte END_STREAM frame in
one bounded TCP write. Mixer may refuse after consuming only the nonterminal
cap; do not claim that its over-cap byte-comparison branch necessarily ran. If
the target bytes were not sent, report the input witness missing.

Do not log whole bodies or let failed equality assertions pretty-print 1 MiB.
Compare bytes in memory with a bounded failure message; retain length and SHA-256
in the receipt. This proves application admission behavior for these inputs,
not a bound on Bandit mailboxes, connection memory or all HTTP/2 denial of
service conditions.

## Deadline cases: package behavior versus Mixer admission

**D1 — one real package read.** A separate trusted Plug mode calls
`Plug.Conn.read_body(length: 32768, read_timeout: 1000)` once with no DATA and no
END_STREAM. Begin timing immediately before the call. On separate fresh
connections send only empty SETTINGS, then only stream-1 WINDOW_UPDATE(1), at
200 ms intervals while the read remains pending; cap the train at eight frames.
For WINDOW_UPDATE, bounded PING/ACK fences confirm connection processing; for
SETTINGS, count its normal ACKs. Require at least three processed controls,
no protocol refusal and a public incomplete-read result by 1,600 ms while
non-progress controls are still available. Record the exact return shape and
elapsed time; confirm the expected `{:more, <<>>, conn}` against selected 1.14.0
source before implementation. The retained 1.13.1 path has that shape, not
`{:error, :timeout}`. Require elapsed time at least 900 ms to exclude an unrelated
early failure. A scheduling or processing-witness failure is an inconclusive
fixture failure, never a vulnerability conclusion or an adaptive retry.

**D2 — the actual Mixer caller.** Repeat both control profiles through
`RawWebhookCapture.capture/1` with no body. If the underlying first read returns
the confirmed empty `:more` result, require `:no_progress`, halted state and no
capture success. Preserve the actual returned result if 1.14.0 differs rather
than remapping arbitrary exceptions to expected success. Record the same
1,000/1,600 ms read interval plus owned disposal. This links the package's
non-progress deadline behavior to Mixer's existing admission guard. It does not
prove the five-second success deadline is hard cancellation or qualify the
private WebhookTransport supervisor/permit lifecycle.

These scoped controls cover the non-progress-frame aspect of the reviewed
Bandit read-timeout advisory. They are not a replay of an exploit, an exhaustive
upstream security test suite or a broad memory/CPU stress test.

## Hard fixture bounds and CI placement

At most one listener, TCP connection and stream are active at a time. Use three
body subcases and four deadline subcases, each with a 3-second outer budget and
one 500-ms teardown budget; the selected module budget is 25 seconds. Body input
is capped at 1 MiB + 1 per connection and 3 MiB over the suite. Limit DATA payloads
to 16 KiB, total frame processing to 256 per body case/64 per deadline case,
headers to 1 KiB, read-observer events to 64 and other correlated fixture messages
to eight per case. Every send/recv/wait uses
the remaining case budget. No retry, concurrent load, oversized settings,
external hostname, external helper, subprocess or OS signal is required.
Use a shared monotonic deadline established in module setup in addition to each
subcase deadline; ExUnit's per-test timeout alone is not a cumulative module cap.

In `try/after` and ExUnit cleanup, close only the client socket, release/dispose
only the correlated test Plug and stop only the owned listener. Observe the
recorded stream and connection monitors DOWN before the next subcase. Preserve
cleanup failure as a failed test; no global process/port cleanup or production
role changes. Error connections are disposed without reuse.

The existing `test/support` compilation and default `*_test.exs` discovery feed
the ordinary remote Phoenix `mix test --warnings-as-errors --seed 0 --trace`
step. Add no local wrapper or workflow mutation. These cases themselves need no
Repo, provider, TLS certificate or external service; the existing full runner's
other fixtures remain its own scope. Emit one bounded JSON metrics line per
subcase into its already retained test log, with case/profile, dependency
version, protocol, byte/read/frame counts, return/reason, monotonic durations and
cleanup booleans. Keep raw bodies, arbitrary transport reasons and adapter state
out of that output.

Only completed case-specific receipts may close these two wire qualifications.
Product/provider/production, native/device and every GA gate remain unchanged.
