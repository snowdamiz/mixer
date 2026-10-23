# Native Swift VM sessions

`MixerRuntime` wraps the owned VM's additive C session interface. It provides typed
integer and raw floating-point values, retained memory/globals, bounded memory
copies, structured traps and fuel reports, explicit cancellation, idempotent close
and deinitialization cleanup. The session is safe to share across native threads:
overlapping work returns `session_busy`; close/cancel do not wait for the interpreter.
Already admitted work may complete before cancellation. No rollback is promised.

Guest invocation is synchronous. Native apps should schedule feature work on a
dedicated executor and cancel when its lifecycle ends. This package does not yet
provide that executor, signed-update activation, capabilities or a Swift/WASI guest.
All guest profile restrictions and resource ceilings remain unchanged.
`VMValidator.validate` checks the complete module under an explicit profile and
limits without creating an instance or consuming the native session quota.
The separate `activation/` package composes this boundary with signed cold-start
selection; it does not add guest capabilities or full Swift execution.

Build a pinned static owned library, then supply its library search directory:

```sh
python3 runtime/build-vm.py --revision 64123c5 --target host --output runtime/.build/native-host
swift test --package-path runtime -Xlinker -L"$PWD/runtime/.build/native-host/lib"
```

The staging directory contains only `libmixer_vm.a`. Passing Cargo's release
directory directly can select its dynamic library, so use this dedicated directory.
The builder exports an immutable Git revision, checks the copied C header exactly,
and records the source archive, static archive and toolchain identities. Targets
`ios`, `ios-simulator` and `android` build their respective Rust static libraries;
Android additionally requires `--ndk` pointing at the qualified official NDK.
Swift and final native application builds must use matching platform/architecture
settings and link the staged archive. The C shim checks all existing struct sizes.

```swift
let session = try VMSession(module: payload, profile: .integerV1)
defer { try? session.close() }
let result = try session.invoke("calculate", arguments: [.i32(42)])
```

This is a local development package. Immutable published packages, distribution
signatures, full installed runtime fingerprints and the FieldLog consumer remain
open. A VM session is not release authorization; only verified and eligible bytes
may be activated by the eventual updater integration. The native handle never
leaves this Swift ownership boundary. New physical-device validation is pending
while the user's phones are disconnected; prior C-level device receipts do not
qualify this later Swift wrapper.
