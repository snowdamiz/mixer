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
explicitly selected Android ADB target. The script also captures inventory
and rejection from the owned VM. It records failures rather than rewriting them
as qualification. Run `python3 compiler/qualify-fieldlog.py --help` for parameters.

Receipts bind the exported source archive, harness sources, generated package,
artifact bytes and observed executable SHA256 values. Commands stream stdout and
stderr to per-command files, retain partial logs on timeout, reject excessive
output, and parse duplicate-free JSON with exact corpus expectations. Ambient
compiler and Node injection variables are removed. Android runs use a fresh
directory, verify uploaded executable/libc++ hashes, and remove that directory.
An ADB target can be an emulator; recorded properties do not independently attest
physical hardware. Installed compilers, SDK contents, Node, adb and the owned VM
remain trusted local tools. Their hashes do not attest the complete toolchain,
prove source-build correspondence, or sandbox a deliberately malicious tool.

Run the harness regression checks with:

```sh
python3 -m unittest discover -s compiler/tests -v
```

Select the official cross Swift compiler and its matching SDK installation.
On this development Mac Swift 6.3.3 uses Xcode 26.6's macOS SDK through per-command
`DEVELOPER_DIR`; the newer Xcode 27.1 SDK contains interfaces that compiler cannot
read. Android uses `aarch64-unknown-linux-android28` and matching NDK libc++.
The Wasm artifact uses the full `swift-6.3.3-RELEASE_wasm` SDK. See
`release/toolchain-candidate.json` for the exact downloaded SDK identities.

The original model corpus is approximately 60.5 MB before compression. The
smallest qualified full-SDK variant is 52,008,982 bytes / 18,852,048 gzip bytes.
The later [reactor and WASI investigation](experiments/swift-guest-next/README.md)
records actual import calls, final memory differences and supported static
reactor linkage. A reactor initializes once and exposes repeated callable
exports. The subsequent [actual model reactor](experiments/fieldlog-reactor/README.md)
preserves the unchanged FieldLog corpus body and matches all 11 native/command
observations twice after one initialization. Its complete artifact is 53,777,114
raw / 18,976,211 gzip bytes; the owned VM still rejects it. An explicit test-boundary
flush repairs the preserved first output-buffering failure. Root audited the exact
sources, artifacts and retained results in
`verification/fieldlog-reactor-root-review.json`. This proves model parity in a
development oracle, without qualifying persistent feature/UI/effect execution.
The complete compressed artifact, including required guest runtime code, must
still meet the plan's 3 MiB budget. Reusing a store base or transferring a delta
does not qualify that metric. These are measured package-size/runtime gaps.
Full Swift interpreter execution, actual feature/UI/effect graphs, typed host
imports, source maps, language coverage and performance qualification remain open.
