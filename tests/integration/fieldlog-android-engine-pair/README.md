# FieldLog Android engine upgrade pair

This development fixture supplies the two APKs for the FieldLog L04/L08 §22.2.13
in-place Android upgrade. The pair shares a freshly generated APK certificate
and one fresh OTA trust root, with distinct linked VM archives, runtime
fingerprints, signed payloads, and channel assignments.

## Build and verify on macOS

Run the recipe from the Mixer checkout.

```sh
python3 -B tests/integration/fieldlog-android-engine-pair/run.py
```

Use an arm64 Mac with Python 3.11+, Xcode 26.6 (macOS 26.5 SDK), the official
Swift 6.3.3 release toolchain and its Android SDK, Rust 1.99.0 with the
`aarch64-linux-android` target, JDK 25.0.4.1, Go 1.27.1, and Android SDK
platform 37.0 with Build Tools 36.0.0 and 37.0.0 and NDK 27.1.12297006.
The toolchain preflight confirms telemetry is off in the private home used by
Go and its subprocesses. It checks the Go driver and compiler versions and verifies
the Swift compiler, SwiftPM and Android SDK routing files. SwiftPM searches a
campaign registry containing only the SDK bundle used by the packager.
[Toolchain preflight](replay/toolchain.py)
Source and dependency downloads use pinned public commits or release tags,
with resolved Swift pins and locked Go and Rust inputs. The Android host and
appearance inputs come from Mixer `c392e762d6bb24562647fe22a2de738250ba3e7f`.
The release service is built from Mixer `9495996b00b5185c3d7fbf310615f69eadec9624`.

The runner allocates a new ignored `verification/local/` campaign with a
12 GiB admission check. It samples volume-wide free space while commands run
and requests shutdown before free space reaches 7 GiB. A custody hold preserves
the owned campaign for root if a process does not close conclusively, even when
the hold receipt cannot be written.

The old engine ID denotes a historical local verification revision. The
recipe reconstructs its exact VM tree from public Mixer
`9fd7e7f6ebd9cadfd96d71a6c71225e6b11e33b9` by reversing the validator change
and restoring the public predecessor's interpreter tests. It verifies both
VM trees and both pairs of Android and host archive hashes. The FieldLog
overlay is applied to public FieldLog `552559d2d3278abb9b1aa7dcf0288102c09a202b`
after applying the Pair 23 public-build patch from Mixer
`30846456d5d7a031b4390503e3b0afb559732a32` and verifying its SHA-256.
Missing Git objects hydrate only in the campaign cache. Packaging requires the
recorded composite consumer source digest before signing. The guest source is the pinned
saved-draft guest with the selected-task overlay used in the historical
reconstruction at Mixer `3184c398ba5e5dcded110a65772d793ba9caf9f6`.
The two Wasm output pins cover the source build in this recipe. The service
and the official Mixer identity and update verifier commands also build from
source.

Both guests execute against both host VM archives. The APK checks cover the
certificate, version, arm64 payload, embedded identity, and 16 KiB alignment.
The signed-origin replay checks distinct offers, cross-runtime refusals,
per-runtime cursor admission, and durable state across a service restart.
APK and offer bytes change on each run with fresh keys, issuance time, and
loopback port. The runner deletes the private keys and build scratch after
confirmed closure. The sealed `handoff/` is for the root-owned native run.
