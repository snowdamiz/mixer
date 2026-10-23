# CI tool selection

The Swift job selects `/Applications/Xcode_26.3.app/Contents/Developer`, requires
Xcode 26.3 build `17C529`, and refuses Swift older than 6.2. The exact
[runner inventory for the failed first run](https://github.com/actions/runner-images/blob/macos-15-arm64/20260907.0337/images/macos/macos-15-arm64-Readme.md)
lists this installation and its default Xcode 16.4. Apple's
[Xcode 26.3 release notes](https://developer.apple.com/documentation/xcode-release-notes/xcode-26_3-release-notes)
identify Swift 6.2.3. The default compiler in
[run 39875861465](https://github.com/snowdamiz/mixer/actions/runs/39875861465)
was Swift 6.1, which could run the SDK tests but rejected the CLI's tools 6.2
manifest.

`verify-apple-toolchain.py` checks the installed version/build and compiler path
before publishing the compiler directory through `GITHUB_PATH`. The job's
`DEVELOPER_DIR` and `TOOLCHAINS` also cover Xcode and CLI child processes. The
probe records the runner image, source revision, SDK versions, and compiler/probe
SHA-256 values in the job log and `$RUNNER_TEMP/apple-toolchain.json`. A removed or
replaced Xcode installation fails the job; it does not fall back to the image's
default. Hosted image labels remain rolling images, so this records selected
tools without claiming a fully immutable runner.

The Swift job tests the public root SDK package, `updates`, `capabilities`, and `cli` directly, checks
generated capability sources, then creates, tests, and builds the generated iOS
consumer. It builds a static owned VM from the checkout's exact Git revision into
an isolated library-only directory and tests `runtime`, `activation`, and the
preserved independent wrapper suite against it. The header guard is checked with
normal and optimized Python. Dependency builds alone do not execute these packages'
tests. The Linux jobs record tools, use Ubuntu 24.04, exercise
the owned VM with Cargo's locked dependency resolution in debug and release,
and verify, vet, and race-test services with Go 1.26.4.

`check-sdk-package.py` compares the public root package with `sdk/Package.swift`:
products, target dependencies, compiler settings and remapped source/test paths
must match. Both entry points compile the same SDK sources.

Run the selection regressions without Xcode:

```sh
python3 -m unittest discover -s scripts/ci/tests -v
```

For a local probe, pass the actual installed Xcode path/version/build and a fresh
receipt path. This does not modify the global `xcode-select` setting. The local
receipt records Xcode 26.6 because 26.3 is absent on this Mac; only a subsequent
GitHub run can establish the pinned hosted execution result. Run39877689050 at
17134eb passed the initial three jobs; subsequent runtime/capability/activation
steps need their own hosted receipt after they are pushed.

These jobs cover host package behavior and an unsigned generated simulator build.
They do not qualify physical devices, OTA deployment, PostgreSQL integration or
production operations. PostgreSQL's real-database
qualification stays in its explicit local harness; CI installs no database.
