# HTTP/2 test source freeze

The root selected two new test files, five ExUnit methods and seven finite
subcases. This packet freezes that implementation for independent source review.
No Elixir, Mix, compiler, formatter, test, listener, network request, process
inventory, native runtime or capture was invoked. Compilation, formatting,
runtime behavior and both wire qualifications remain pending.

The exact official Bandit 1.14.0 evidence is the independent review's eight blobs
at `220b9dfd27f9a21305be2afc75cbe585ddc24e7a`; its original notice and blobs
remain in that immutable packet. The local shared dependency directory still
declares 1.13.1. New code checks the actual loaded version is 1.14.0 in CI.
Canonical dependency files match the accepted integration proposals on observed
revision `d87ce0a1b05a9ad42cd2118bbf2ccc5491499663`. This lane edited only the two
new test files and this new verification directory.

B1 sends 32 one-byte frames followed by 16,384, 16,384 and 7,201 bytes, fences
the connection before releasing the Plug, and requires the actual over-target
read witness plus exact in-memory body equality. B2 uses 32 observer-paced
32 KiB tranches with END_STREAM on the final payload. B3 paces 31 tranches,
reserves both credits for the final 32,769 bytes, and submits its three final
DATA frames in one TCP send. B3 can refuse at the nonterminal cap; it does not
prove the extra byte was consumed by Mixer's greater-than-cap comparison.

D1 and D2 each use separate SETTINGS and stream WINDOW_UPDATE profiles. They
require at least three connection-processing ACK/fence witnesses recorded before
the observed read return, a 900–1600 ms read, no preceding RST_STREAM/GOAWAY,
and the exact public empty `:more` shape. D2 separately requires Mixer's halted
`:no_progress` result. A missed witness or timing interval fails the fixture;
there is no retry or vulnerability conclusion. Connection witnesses do not
inspect private stream state, and these cases do not prove hard cancellation.

The shared monotonic module deadline is 25 seconds. Each case allows at most
3 seconds of work and reserves 500 ms for cleanup; all socket and correlated
message waits use remaining time. Public metadata queries use short owned
workers whose exits are observed. Listener start uses ExUnit supervision and is
checked immediately afterward; uncertain startup is a cleanup failure. The
26-second ExUnit timeout is an additional failed-test guard, not the module's
admission deadline. The listener's public connection shutdown timeout is 100 ms,
and its ExUnit child shutdown is 400 ms. Cleanup closes only the owned socket,
sends only the correlated Plug's disposal message, stops the owned listener and
requires the recorded stream/connection/listener/query monitors DOWN within its
reserve. Failed cleanup poisons the shared budget so another case cannot start.

The finite parser admits only the selected frame types, counts all inbound and
accepted outbound frames, and respects both send credits. It caps each body at
1 MiB + 1, suite body input at 3 MiB, DATA payloads at 16 KiB, headers at 1 KiB,
frame events at 256/body or 64/deadline, reads at 64, and control trains at eight.
Body equality and SHA256 happen within work; diagnostics do not print bodies.
Seven metrics lines of at most 2,048 JSON bytes feed the existing CI test log.
Successful capture is reported only after unwrapping the newest adapter and
successfully sending the tiny 204 response. A fixture Date header avoids starting
a separate clock service solely for that response.

The original design pins **24** inputs; its old receipt's declaration of 23 is
retained unchanged. This successor records the actual count and fresh input
hashes. The freeze's byte/count/provenance checks are source bookkeeping, not
syntax, executable-test, advisory, production, provider, memory, backpressure,
native/device or GA qualification.
