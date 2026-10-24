# Independent private webhook transport review

Recommendation: **accept the frozen candidate as a private development slice**.
No scoped candidate defect was found. Public admission, provider authority and
G23 remain unaccepted. Root owns any integration or later scope selection.

This source/behavior/privacy review binds producer seal
`a36676ab1ab9bf1d0f98077d86d7f375b7c46a18c13cdb4bcd1adb24ce5d430d`
and candidate source
`62cd64f8711ff5296270b38a1c679336e075705bf5845c88d82d7e4bbd28aec0`.
The accepted baseline remains 71 hosted inputs with digest
`ac391070ec439ecfca288b9a7657aac1eada5bc1196efb8735211cc60a6883bc`;
raw capture remains byte-exact at
`a420d5a54868d61c3d6e9c7cb41807698eb729df3e6babda12135a727ac657ea`.
The [receipt](../verification/stripe-webhook-transport-review/receipt.json),
[findings](../verification/stripe-webhook-transport-review/findings.json) and
[16-row assessment](../verification/stripe-webhook-transport-review/matrix.json)
give the exact observed scope and remaining prerequisites.

## Independent execution and evidence

The reviewer copied the candidate and producer harness into this owned review
lane, rebuilt capture/signature/transport in fresh dedicated BEAM processes,
and reused hash-bound original dependencies. No producer `run.py` was executed
against the sealed producer directory. No live product/tracker/Git/provider/
database/credential/native/phone changes were made. The catalog-inspector and
authority reviews were not retried or replaced.

[Run 1](../verification/stripe-webhook-transport-review/run-1/receipt.json)
reproduced all original tests: 14 component tests, 13 baseline wire groups,
13 composed wire groups with 105 clients, 13 adversarial tests and the stream-only
negative control. A return-only trace observed 27 actual composed verifier
returns, equal to inline calls; adversarial verification ran twice. The 27
common successful captures preserve exact body hashes, sizes and original
signature argument lists. Every recorded rejection has zero verifier calls;
there is no domain progression or 2xx acknowledgment.

[Run 5](../verification/stripe-webhook-transport-review/run-5/receipt.json)
passed 12 independently authored groups with 34 TCP client vectors and six
synthetic permit sequences. Its return-only trace observed eight verifier
returns matching eight inline calls; call-argument trace messages were
suppressed. The tests cover valid SETTINGS minima/maxima, duplicate/unknown
settings, eleven malformed SETTINGS/window cases, live window shrink/expansion,
zero/overflow/window-update behavior, two reset bursts, five second-stream
orderings, H1 header count, fragmented encoded H2 header limits, H2 reader/guard/
owner loss, exact/expired/delayed permits, and raw sink/crash/teardown paths.

Five attempts retain exact executed sources, command arguments/environment,
outputs, source archives, tool hashes, compiled artifacts and cleanup. Runs 2
and 3 remain failed review-harness attempts: tuple JSON serialization, a
concurrent role-stop race, a zero-window case initially reaching the shorter
idle timeout, and re-reading an already closed local socket. Those failures
were corrected only in review-owned test code. Run 4 passed the earlier ten-group
suite; run 5 passed the final expansion. The
[attempt ledger](../verification/stripe-webhook-transport-review/attempts.json)
does not promote failures to passes.

The observed environment is macOS arm64/Darwin 27, Elixir 1.20.4,
OTP 29/ERTS 17.1 and Python 3.14.8, with Plug 1.20.3, Bandit 1.13.1,
Thousand Island 1.6.0, telemetry 1.4.2 and Mint 1.11.0. Dependency source and
BEAM identity closures are retained and verified; dependencies were not rebuilt.

## Source and deadline assessment

The fixed profile has one acceptor, sixteen connections, retry count zero,
backlog 128, one request and one concurrent H2 stream, 1s handshake/header
stages, unchanged 5s capture and a 7s absolute connection lifetime. The listener
starts after the sink boundary, guard supervisor and owner. One-for-all with
zero automatic restarts closes the dedicated role on required sibling loss.

Thousand Island's documented start event registers the original connection
before parsing. Bandit's documented connection span and exact trusted Plug
identity register the original reader. Each permit binds caller, owner and
connection generations, state and monotonic deadline. Capture executes in the
original reader, checks before reading and after flattening, and refuses a
delayed reply with a final local comparison. Guards never read a body. They
monitor the original connection and distinct H2 readers, retain an absolute
timer after successful capture, and retire only after observed termination.

The fresh original probes observed H1-header/H2-preface/CONTINUATION peer closure
at 1000/1001/1001ms, frozen-reader closure at 5017ms, and held-response closure
at 7006ms. Guard disposal overshoot was 0ms in those observations. Independent
testing blocked a real H2 response with a peer stream window of zero while
PINGs continued: peer closure occurred at 7000ms and monitors installed before
the fault observed both original connection and reader `:killed`, with 0ms
guard overshoot. This is measured local scheduling evidence; it provides no
real-time guarantee during VM suspension or scheduling starvation.

Independent exact-expiry probes returned `:deadline` at or after the stored
deadline for both begin and finish. A finish blocked behind a deliberately
suspended guard was refused after resumption. Replay and connection-generation
checks refused or lost to the independent kill. Unknown token/caller/forged
request state and owner/listener/guard/required-subscriber failures also pass
the original replay. H2-specific injected reader/guard/owner death closes the
true peer and both pre-monitored original owners.

The trusted fixed Plug must always dispose in an `after`/`finally` path,
including capture errors. The current boundary returns a halted error
connection while its independent deadline remains active. Preserve that
integration condition and keep this permit distinct from billing authority.

## Configured sink privacy assessment

The [complete observed inventory](../verification/stripe-webhook-transport-review/sink-inventory.json)
contains only the private control telemetry subscriber over eight fixed events.
It consumes only documented references/PIDs/timestamps and the fixed Plug
identity. No raw exporter, APM/error callback or additional telemetry subscriber
is configured. Both raw measurements and metadata were injected and checked.

Logger primary callbacks are exactly the known `Logger.Utils.translator/2`
with standard `Logger.Translator`, and `Logger.Utils.process_level/2`, with
empty primary metadata. All three handlers are inventoried: default stdout,
OTP `ssl_handler` stdout, and the explicitly approved reviewer collector.
Each has `mixer_private_schema` first in its filter list before the standard
`logger_formatter`. Remaining filters are the known `remote_gl` or SSL-domain
filter. The dedicated child merges stderr into retained output. No unrelated
process or shared host logger policy was changed.

The schema filter accepts only the exact fixed report shape and bounded integer,
then reconstructs message and metadata. Arbitrary messages, reports, metadata,
body/signature/path/query/trailer/error sentinels and unknown extra fields do not
pass. Independent tests exercised real ignored H2 trailers, pre-Plug parser
failure, unknown-frame warning, genuine process crash reports, SSL/SASL/Bandit
domains and post-teardown logging. The collector saw no raw sentinel and the
merged accepted-run stdout/stderr has no raw sentinel. Safe rejection counters
remain observable. Filters remain installed through role death and teardown;
they are not removed before supervisor crash reports.

This accepts an owned configuration with trusted bootstrap/reconfiguration.
It does not prevent privileged code from adding a raw telemetry subscriber,
removing a filter, writing arbitrary IO or exporting diagnostics. Original
negative controls reproduce that risk: drift can stop admission but cannot undo
data already delivered. The 25ms poll is additional detection, not an atomic
confidentiality guarantee. Dump/core collection and collector retention remain
operational review requirements.

## Protocol and resource scope

The new P10 cases close the finite local SETTINGS/window/reset/second-stream
coverage gap. They include a 64-frame reset burst on an active stream and on
new stream IDs, plus streams opened before completion, after capture, after
reset, simultaneously, and after observed peer EOF. No second verifier ran.
Whole-connection disposal or the one-request policy can win before every
submitted reset is parsed. This qualifies protected-profile outcomes; it does
not independently isolate the dependency's 16-per-second reset threshold or
promise exhaustive hostile-input/sustained-load coverage.

Fresh resource replay contains ten samples, with sampled maxima of RSS
151280 KiB, per-process heap 2586 words, binary references 1353568 bytes and
64 queued messages. These are observations, not absolute peaks or a memory
ceiling; shared binary references may count shared allocation more than once.
Logical parser/window/body/heap limits do not establish OS/VM/native limits.
P11 still requires selected, enforced OS/container resource values and measured
failure/overload/OOM behavior reviewed by an accountable operational owner.

The [baseline comparison](../verification/stripe-webhook-transport-review/baseline-comparison.json)
retains four deliberate timing differences. The older 2s H2 idle profile captures
`h2-slow-gap` after 1.2s; the selected 1s idle profile closes it with no verifier.
H1 no-body/slow-gap may close before a framework error response, and H2 late
success is disposed before the late capture refusal returns. Old sleeping-client
elapsed values are upper bounds; dedicated probes measure actual peer closure.
There is no changed capture grammar or provider-compatibility conclusion.

H1 Content-Length/chunked and H2 optional Content-Length remain supported.
Pinned undeclared H1/H2 trailers are discarded without changing the body or
original signature values, and their values reach no configured sink. Public
discard-versus-reject policy remains unselected. TLS/ALPN, deployed Cloudflare
ingress, Stripe test mode and endpoint/account/mode/generation/secret authority,
durable inbox with atomic Oban enqueue, billing reconciliation and G23 require
their separate evidence and accountable reviews. P11/P12/P14/P15/P16 are not
marked fully passed.

All five attempts have no remaining owned process groups or scratch holders;
every observed listener port refuses connection and all identity-marked scratch
was removed. Run 5 also records cleanup for all fourteen sequential roles.
No simulators or physical devices were used.

```sh
python3 -B verification/stripe-webhook-transport-review/verify.py
```

The verifier is read-only and checks the review seal, frozen upstream bindings,
all attempts and their exact source archives, fresh compiled artifacts, outcomes,
timing, sink inventory, limitations and cleanup. A new mutable harness run requires
a new explicitly reviewed/resealed packet; it must not silently alter this one.
