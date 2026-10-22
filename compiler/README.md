# Compiler qualification

The implementation uses official full Swift SDKs. Compiler success does not
authorize an OTA release; the device must execute the exact emitted profile in
our owned VM and verify its complete dependency/capability/runtime contract.

`Fixtures/FeatureProbe` is an original small language/model probe.
`Fixtures/FieldLogCorpus/main.swift` exercises the actual models imported from an
immutable revision of the separate FieldLog repository: 1,000 tasks, 50% progress,
reordering, Unicode draft Codable restoration, entry commit/repeat rejection,
validation, durable-outbox model contents and report formatting. It does not test
the storage implementation or native UI, and it does not represent all app code.

`qualify-fieldlog.py` exports a specified Git commit to a new output directory,
builds native/Android/full-Swift Wasm executables, compares native behavior with a
development-only Node WASI oracle, and optionally runs the same model corpus on an
explicitly selected physical Android device. The script also captures inventory
and rejection from the owned VM. It records failures rather than rewriting them
as qualification. Run `python3 compiler/qualify-fieldlog.py --help` for parameters.

Select the official cross Swift compiler and its matching SDK installation.
On this development Mac Swift 6.3.3 uses Xcode 26.6's macOS SDK through per-command
`DEVELOPER_DIR`; the newer Xcode 27.1 SDK contains interfaces that compiler cannot
read. Android uses `aarch64-unknown-linux-android28` and matching NDK libc++.
The Wasm artifact uses the full `swift-6.3.3-RELEASE_wasm` SDK. See
`release/toolchain-candidate.json` for the exact downloaded SDK identities.

The current model corpus is approximately 60.5 MB before compression. This is
evidence of a package-size/runtime gap, not a passed production download budget.
Full Swift interpreter execution, actual feature/UI/effect graphs, typed host
imports, source maps, language coverage and performance qualification remain open.
