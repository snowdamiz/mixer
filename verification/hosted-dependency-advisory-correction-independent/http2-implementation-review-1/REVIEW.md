# Independent HTTP/2 implementation-v1 source review

No blocking source finding remains. Recommend root deliver the exact two-file
implementation for ordinary remote formatting, compilation and tests. None of
those runtime checks has run in this review; both wire qualifications remain
pending. The relation-binding correction's three accepted canonical files were
only hash checked and remain intact.

H2R01–04 are incorporated. B1 sends the source-bound thirty-two-byte small-frame
prefix and 39,969-byte tail, waits for a correlated PING ACK before release and
requires a measured read larger than 32 KiB. B2 sends thirty-two observer-paced
32 KiB tranches, with END_STREAM on the final payload, and asserts thirty-two
full reads, terminal `:ok`, exact capture/signature and timely admission. B3 paces
thirty-one tranches, reserves both credits for its final 32,769-byte single TCP
send and requires halted `:too_large` without claiming consumption of the extra
byte. The successor records twenty-four original inputs.

The trusted Plug calls capture in its real stream owner process. Its two-method
observer delegates the original Bandit adapter, records actual returned binary
length/options/times and propagates unexpected results/exceptions. Successful
response restores the newest original adapter state before sending 204 and
reporting success. The request is confirmed as HTTP/2/Bandit.Adapter with no
Content-Length. Capture error and package-read modes report their result before
waiting for correlated disposal, without reusing the halted connection.

The passive wire helper reads a bounded frame header/payload, rejects unexpected
frame shapes and RST_STREAM/GOAWAY before disposal, honors both connection and
stream credit, and counts all accepted inbound/outbound frame events. DATA and
headers stay within the selected bounds. D1 and D2 use separate SETTINGS and
stream-WINDOW_UPDATE trains, retain ACK/fence processing times before the read
return, require at least three witnesses and enforce 900–1600 ms on both actual
read and caller duration. D1 requires empty `:more`; D2 separately requires
Mixer's halted `:no_progress`. Connection processing witnesses do not inspect
private stream state or prove hard cancellation of arbitrary adapter work.

The owned listener has temporary ExUnit ownership, one acceptor/connection slot,
literal loopback, public 100 ms connection shutdown and 400 ms child shutdown.
Cleanup disposes only its correlated stream, closes its socket, stops that
listener and requires its recorded query/stream/connection/listener monitors
DOWN. Uncertain startup or incomplete cleanup fails the case and poisons the
shared budget. Logging changes remain fixture options and no global process or
Logger state is changed by this fixture.

The shared 25-second clock is an admission deadline with cooperative work/wait
checks. Listener startup and OS calls are not hard preempted at that instant.
The 26-second ExUnit timeout is an additional per-test failure guard, not a hard
module wall-time bound. Missing startup, result, timing or cleanup witnesses
cannot produce a qualified passing case. Receipt acceptance must require the
enclosing test and full CI outcome to pass as well as all seven case receipts;
receipt emission itself is followed by final deadline checks.

Ordinary discovery compiles test/support and loads the new *_test.exs module.
Official Elixir 1.20.4 source confirms that `mix test --no-start` still runs app
configuration/compilation and loads required dependency application metadata;
the Bandit version assertion does not depend on another test starting its
supervisor. Relevant primary-source excerpts and provider blob IDs are retained
in ci-primary-source.json. No product application or dependency starts were added.

Fresh hashes verify eight implementation members, both canonical copies, all
twenty-four original local pins, five protected pins, the fourteen-member prior
independent packet and eight official Bandit blob identities. The independent
audit used bounded Python file/hash/text inventory only, alongside read-only
official Mix source retrieval. It neither imported the producer freezer nor ran
a formatter, Mix, compiler, tests, listener, native runtime or process/DNS probe.
Source inventory is not a syntax or executable-test pass. Advisory completeness,
memory/backpressure, private transport lifecycle, provider/production, device
and GA acceptance remain outside this finite qualification.
