# F11 iOS Simulator compile blocker

`probe.py` reconstructs the F11 SDK from Stage `5e43e50a06` and verifies the F04 export tree, F11 exchange source, note codec, and installed owner call against the pinned evidence. It builds the actual Swift Crypto, MixerCore, MixerUI, and MixerGuest modules for both arm64 macOS and arm64 iOS Simulator. Each target type-checks a stock constructor and the private constructor used by the installed F11 owner with the same fixture flags.

The macOS compiler accepts the private constructor. The Simulator compiler accepts the stock control but rejects the private call at `fieldLogNoteFixtureGeneration:`. That constructor and its exact-byte codec are compiled only for macOS in the pinned SDK. A UIKit wrapper cannot supply the missing exchange API. The probe ends before application or XCTest linking. Installed keyboard input, the native display ticket, Save draft, and Commit remain pending on iOS.

The separate Stage macOS replay reproduced the 50 ms signed Wasm turn, exact note bytes with four line feeds, stock and F04 codec refusals, unchanged stock identity vectors, and guest put/delete denial. It also verified the two ticket-bound transactions, exact preservation of unrelated rows, one linked `entrySaved` event, and separate-process committed readback at workspace revision 3. [Compile and headless replay receipt](../../../verification/receipts/l08-d8-f11-ios-private-compile.json)

## Root replay

Run from the checkout containing this fixture. Pass the retained Stage checkout and a local Swift Crypto Git object store containing `c2cbadd7263439d8015189668f96ff5b5be565ce`.

```sh
python3 -B tests/integration/fieldlog-d8-f11-ios-private/probe.py \
  "$stage" "$swift_crypto_git"
```

Exit 0 and `status: blocked-at-pinned-sdk-simulator-exchange-constructor` mean both controls passed and the expected Simulator rejection was reproduced. The probe disallows network access, limits elapsed time to 12 minutes and sampled scratch to 1.5 GiB, and removes its scratch after confirming the owned process group is absent. It uses the SDKs on disk and requires no Simulator instance or Apple signing.

To repeat the fresh headless control separately, use the pinned Stage checkout with its retained F11/F12 inputs and the local FieldLog Git checkout containing the Pair25 base and F11 source anchors.

```sh
python3 -B "$stage/tests/integration/fieldlog-d8-f11-action-private/replay.py" \
  "$stage" "$fieldlog_git" "$stage/tests/integration/fieldlog-d8-f11-vertical-private"
```
