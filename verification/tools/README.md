# Physical runtime qualification tools

These original development harnesses bind receipts to exact source revisions,
test binaries, reference inputs and installed bytes. They do not grant release
authority, publish code, or mark a launch gate passed. Supply explicit device IDs;
Android helpers reject observed emulator identities. Temporary Android folders
have random names and are removed after each invocation.

`verify-numeric-android.py` exports the requested VM Git revision, builds the
release interpreter and C ABI, and runs the integer/boundary/float tests on the
selected device. It captures 29,794 Node reference results on the development
Mac. Only the test transport changes for Android: the generated cases must match
the captured inputs byte-for-byte before comparing device results. Node is never
installed on the device or linked into the product. The transport patch is saved.
The independent C harness checks rounding and flush control rejection; unavailable
hardware exception controls are reported as unqualified.
Pass `--profile table-memory-v3` with the corresponding frozen revision to run
the 2,996 table/memory references and v3 boundary/C ABI tests using the same
transport. Its reference records also compare resulting linear-memory spans.

`verify-numeric-ios.py` uses that captured reference directory, checks its hashes
and frozen VM archive, then builds a signed development application with the
independent Swift harness in `ios-numeric/`. Every reference module executes
through the public Rust C ABI. The application emits exact case counts and exits;
the driver checks both the marker and the device process exit code. It uses the
explicit existing signing team and does not enable provisioning portal updates.
This installs a separate `dev.mixer.numericqualification` application.

`verify-updater-android.py` runs an explicitly identified Swift Testing executable
and its matching official dynamic SDK libraries. It checks source files against
the committed source receipt and selected Git revision, verifies every installed
input hash, and requires all 28 test functions to pass with no skips. The binary's
association with that source build is recorded by the separate compiler receipt;
an arbitrary user-supplied executable is not a trusted production verifier. This
tests injected interruption/reopen behavior in shell-owned temporary storage;
it does not demonstrate Android app lifecycle, physical power-loss recovery, or
actual guest activation.

`prepare-ios-updater.py` exports a frozen updater package into a new directory and
prepares an app-hosted Xcode test target. Original package test assertions and
fixture bytes remain unchanged; a small `Bundle.module` adapter supplies Xcode's
resource lookup. Run the generated project with the recorded `xcodebuild test`
command in `updater-ios-2026-10-22.json`. The physical run covers 28 test functions
and 40 parameter executions in an iPhone app sandbox. Check resolved dependency
pins against the frozen package before treating the result as qualified.

`prepare-ios-vm-tests.py` prepares an app that runs a selected frozen Rust
integration test source on iOS. It removes test registration attributes, retains
all assertions, and adds a panic-containing C entry point that invokes every
selected function. Build its static library and Xcode app using the commands in
`table-memory-ios-2026-10-22.json`. Device console output lists individual passed
functions and an exact count; a caught panic produces failure and a nonzero exit.

Use each script's `--help` for required paths and identifiers. Recorded commands,
versions, hashes, outputs and limitations are in the dated runtime receipts in
the parent `verification/` directory. `local/` contains generated binaries and
device artifacts and is deliberately untracked. Test runtime is not a measured
application performance result.
