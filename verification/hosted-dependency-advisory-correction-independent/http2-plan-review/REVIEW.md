# Independent HTTP/2 qualification design review

Recommend the narrow two-file implementation with the refinements below. Keep
five methods, seven finite subcases, one active listener/connection/stream and
the 25-second cumulative budget. No product change or extra runtime lane is
selected by this review; both wire qualifications remain pending.

Official GitHub tag `1.14.0` resolves to commit
`220b9dfd27f9a21305be2afc75cbe585ddc24e7a`. Eight exact-commit source files are
retained here with Git blob identities, SHA256 hashes and official URLs, beside
the exact upstream MIT license notice. Their
version is 1.14.0. The shared local Bandit source remains 1.13.1 and is not the
source of the conclusions below. No dependency was installed. This binds the
official tag source; byte equivalence with a materialized Hex package remains
outside this source-only review. Runtime must assert its actual Bandit version.

## Confirmed package and Mixer boundaries

The adapter delegates to real HTTP/2 stream reads, converts returned iodata to
binary and preserves `:ok`/`:more`. The stream establishes one monotonic deadline
for the call, retains it across nonprogress messages, and returns `:more` with
its accumulated bytes on timeout. With no DATA/END_STREAM, the selected public
shape is `{:more, <<>>, conn}`. Empty SETTINGS are ACKed at the connection and
only notify streams when the window delta changes; stream WINDOW_UPDATE does
notify the stream. The two profiles therefore exercise distinct paths. Three
matching ACK/fence witnesses establish connection processing, not a separate
inspection of private stream state. Keep the 900–1600 ms interval, eight-frame
cap, processed-control witnesses and no-refusal checks; a missed timing/witness
must fail the fixture without a vulnerability conclusion or retry.

Production RawWebhookCapture maps a successful empty `:more` to `:no_progress`
and a halted connection. Its one-second read option is separate from its
five-second success-admission deadline. Neither new case establishes hard
cancellation of arbitrary adapter work. Run capture inside the actual stream
process; the official adapter still rejects a different caller. The observer
must delegate the real adapter state faithfully and unwrap the newest state
before success response, without claiming a complete Adapter behavior.

## Required narrow fixture refinements

H2R01: B1 needs a concrete batching schedule. Three ordinary 16 KiB-or-smaller
frames for 40,001 bytes return exactly 32,768 bytes first; prequeue plus PING alone
does not force the required over-target return. Version 1.14.0 buffers DATA after
sixteen outstanding stream messages, then delivers its buffered bytes together.
Send thirty-two one-byte DATA frames, followed by 16,384 + 16,384 + 7,201 bytes,
with END_STREAM on the last frame. PING/ACK before releasing the held Plug fences
the connection's handling of the prefix/body. All 40,001 bytes fit initial
connection/stream credit; the remaining batched delivery exceeds 32 KiB. Keep
the actual oversized-return assertion mandatory. This is source-derived fixture
feasibility; only a later real observation can establish its witness.

H2R02: Pace B2 by read completion. Without pacing, batching can return a final
oversized `:more` even after END_STREAM, because the stream's negative remaining
length returns through its `:more` branch. At the application cap, Mixer's
nonterminal-cap guard then refuses admission. Use thirty-two
32,768-byte tranches, each two legal 16 KiB DATA frames, waiting for the correlated
read-observer completion before sending the next. END_STREAM belongs to the
last payload frame. This supports thirty-two reads and the finite exact-cap
input; it does not prove inclusive acceptance under every possible batching
schedule. Do not relabel an observed unpaced failure as a transport memory bound.

For B3, after thirty-one completed 32 KiB tranches, reserve 32,769 bytes of both
credits and send two 16 KiB DATA frames plus the final one-byte END_STREAM frame
in one bounded TCP write. The named 1 MiB + 1 input is then actually sent even
if Mixer refuses at the nonterminal cap. Keep the design's explicit limitation:
this need not demonstrate consumption of the extra byte by its greater-than-cap
comparison. No Content-Length is added; a Bandit framing rejection is a fixture
failure rather than Mixer length-mismatch coverage.

H2R03: Make the cleanup reserve concrete. ThousandIsland 1.6's public
shutdown_timeout defaults to 15,000 ms, which cannot supply a 500 ms failure-path
bound. Select a finite public shutdown_timeout within the cleanup reserve,
dispose only the correlated held stream, close only its client socket and stop
only the owned listener. Require recorded stream/connection DOWN within the
same monotonic cleanup deadline before advancing. A cleanup failure remains a
failed test. No global Logger/process changes or private Bandit messages are
needed; deliberate disposal occurs after the case result and cannot replace
its no-protocol-refusal assertion.

H2R04 (metadata only): the sealed source-evidence map pins twenty-four inputs,
but preparation-receipt declares twenty-three. Correct that count in a successor
receipt while preserving the original packet.

The proposed public listener options and HPAX seam otherwise fit this scope.
Keep both compressed-header and decoded-header bounds, literal loopback,
max-concurrent-streams one, no max_requests-one GOAWAY, finite frame/read/message
counts, bounded equality diagnostics and one small receipt per subcase. Disable
only fixture logs; hidden exceptions must not become expected success. Ordinary
remote Phoenix discovery can run the tests without workflow or DB/provider
changes, and source/read deadlines must remain separate from Mixer admission.

Five sealed design members and all twenty-four current local input pins passed
fresh byte checks. Official source retrieval used only the read-only GitHub
connector, plus bounded offline Python hashing/arithmetic. No Mix, compiler,
listener, fixture/test, native runtime, DNS probe or process inventory ran.
Package/CI success alone cannot close either pending wire qualification, all
upstream advisories, backpressure/memory limits, production/provider lifecycle,
native/device or GA gates.
