# Guest UI SDK implementation receipt

The bounded SDK slice is ready for integration review on 2026-10-23. It adds four
original `MixerGuest` source files and three original `MixerUITests` files. Existing
SDK sources, tests, and `Package.swift` were checked byte-for-byte against HEAD;
the accepted design, frozen JSON contract, and C header retain their sealed hashes.
Root owns integration, manifests, commits, and publication.

`GuestUIEventCodecV1` validates raw UTF-8 JSON before extracting a closed flat
event object. Numeric fields retain their original lexemes, and the event value
has no Codable entry point. `GuestUIExchangeV1` validates the fixed UI subset,
enforces equal-revision raw-byte identity, and shares one lock for turn, event,
effects intent, stop, and presentation state. Issuer-scoped claims and tickets
carry no owner reference. The exchange creates no task and accepts no executable
callback. Its fixed event slot remains occupied until result consumption;
document delivery permits one claimed and one replaceable pending frame.

`GuestUIWakeV1` is data-only, coalesces hints, issues one consumer, rejects a second
parked waiter, resumes continuations outside locks, and preserves a pending final
hint through finish. Exchange stop signals then finishes delivery; the existing
activation signals handoff alone finishes the coordinator source. Explicit finish
owns reader lifetime; task cancellation alone does not discard the waiter.

Root approved the implementation clarification
`finishReadyWithoutInvocation(_ claim: GuestUITurnClaimV1) throws`: only the exact
current issuer, generation, and ready claim can release a non-invoked ready turn.
It performs no harvest, frame publication, event success, or turn-count increment.
Stale, foreign, and closed attempts use ordinary local rejection. This does not
change frozen protocol bytes or the accepted design.

Run the reproducible checks with:

```sh
python3 verification/guest-ui-sdk/verify.py another-unique-run-name
```

The original implementation run is
[`2026-10-23-candidate-1/receipt.json`](2026-10-23-candidate-1/receipt.json).
Receipt SHA-256 is
`05041d1b1658fc348152cf6b1173ca138770e9c4286568a5b4f035c111c2b197`;
source manifest SHA-256 is
`6cc97791a0381e1b54751f5d2296bb962ca5a15138fdce18588b075b793e7432`.
The receipt records exact commands, tool versions, source hashes, logs, target
triples, Android SDK metadata, and actual emitted module hashes. Sources stayed
unchanged through all checks.

| Executable check | Observed result |
| --- | --- |
| Full SDK Debug, warnings as errors | 40 tests passed: UI 28, Core 10, Apple 2 |
| Full SDK Release, warnings as errors | 40 tests passed: UI 28, Core 10, Apple 2 |
| Scoped `guestUI` ThreadSanitizer, warnings as errors | 17 tests passed; no sanitizer report |
| Official iOS SDK, `arm64-apple-ios17.0` | Core, UI, Guest module emission passed |
| Official Swift 6.3.3 Android SDK, `aarch64-unknown-linux-android28` | Core, UI, Guest module emission passed |

The new tests cover exact canonical event bytes, Unicode and UInt64 boundaries,
malformed UTF-8/surrogates, duplicate decoded keys, closed fields, numeric
coercion, bounds, document subset and revision rules, stale/foreign authority,
event-result consumption, control-refresh hints, first-stop/intent arbitration,
close retirement, concurrent event/wake selection, and coalescing reader lifetime.
They check fixed slot/counter bounds over repeated documents and concurrent
operations. They are not a heap-allocation proof or exhaustive scheduler proof.

The earlier `debug-first.log` and `debug-second.log` preserve corrected test-macro
compilation errors; they are not pass receipts. `debug-third.log` and
`debug-fourth.log` are intermediate scoped host runs. The matrix above is
historical candidate 1 evidence.

The final repaired SDK run is
[`2026-10-23-candidate-4/receipt.json`](2026-10-23-candidate-4/receipt.json),
SHA-256 `f336e0a822579af8b8e24a08a62323583d4d633051321107430a177adbb60f5b`.
It passes 42 tests in Debug and Release, 19 scoped TSan tests, and official iOS
and Android module compilation. Independent adversarial review found two defects:
Swift canonical Unicode equality could substitute different identifier bytes in
a presentation snapshot, and completing an older presentation claim could retire
a terminal event result that claim never observed. Exact bounded UTF-8/scalar
document comparison and full event-result equality fix those cases. Eight
independent groups pass in Release and TSan against candidate 4; see
`../guest-ui-exchange-review/receipt.json`. Queued, running and previously
delivered event outcomes survive stop until the final matching claim consumes
them. No SPI or frozen contract change was needed.

Candidate 2 verifies the Unicode repair. Candidate 3 failed to compile its new
test because a throwing expression inside `#require` needed an inner `try`;
its original log and interrupted `running` receipt remain historical failure
evidence. Candidate 4 contains that test-only correction and the final matrix.

This receipt proves SDK host tests and mobile module compilation only. It does
not prove a native first screen, native user interaction, signed guest execution,
post-enable KV effects, app linking, simulator/device lifecycle, full Swift guest
compilation, FieldLog W07, signing, package publication, or any GA gate. Phones
remain disconnected and no device discovery or run was attempted.
