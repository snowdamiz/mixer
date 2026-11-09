# Generated Swift banner caller fix R35

The proposed workflow change makes `Generated consumer integration` source the same existing job-private `environment.sh` prepared by `Swift SDK, update verifier and CLI`. The accepted launcher merges stderr into stdout before exec only for the exact single argument `--version`. No wrapper, product identity rule, compiler inspection, SDK source, Java caller, canonical workflow or metadata was changed.

`workflow.patch` contains exactly two inserted lines. `afterimages/.github/workflows/verify.yml` is an isolated snapshot for review. Root should apply the two-line insertion to its latest literal job snapshot after R33 finishes and reconcile caller metadata through its existing integration procedure; do not replace the current workflow wholesale with this snapshot. No R33-owned metadata was written.

## Source finding

`ProcessRunner.run` inherits the supplied/current process environment and `POSIXCommandControl` launches literal argv via `/usr/bin/env`. `OwnedCommandExecution` drains stdout then stderr into a shared tail on each iteration. Their relative arrival can therefore change the combined banner order. `ProjectGenerator.create` and `ProjectBuild.verifyLock` both invoke `["swift", "--version"]`; both use the existing outer whitespace/newline trimming rule. Verification compares the complete resulting string and remains unchanged.

The hosted trace in run 42697826753/job 129434288111 at 21:10:57.9816360Z records driver version 1.127.15 at the end of the expected banner and at the beginning of the observed banner, with compiler version 6.2.4 and target arm64-apple-macosx15.0. That trace proves the string/order mismatch; it does not independently establish the executed binary identity or provenance. Exact raw line, UTF-8 hex and byte hashes are in `results/hosted-identity-evidence.json`.

The earlier workflow step sources the accepted host environment inside a subshell. The generated-consumer step had no corresponding source, so it did not inherit that launcher. The patch binds all three existing create/test/iOS-build commands to the same already-selected job-private environment, without changing them.

## Actual local execution

One material attempt completed in 32.048 seconds (180-second bound; second attempt unused). Reused R28's exact built `build/arm64-apple-macosx/debug/mixer` and existing launcher. No CLI source edit or rebuild occurred. The selected compiler/driver/frontend hashes and launcher were checked against the accepted receipt/selection before execution. The public `sdk/` input was copied by the actual CLI into a fresh R35-owned temporary project; the 79-file SDK digest was `bf18402881d0e88371613c337d0654fd8a51a21028a8bcd82c713833882d5265` and matched the current public source, generated copy and lock.

Environment: macOS 27.0.1, Xcode 26.6 build 17F113, Apple Swift 6.3.3 / driver 1.148.6, MacOSX26.5 SDK. `TMPDIR` and custody paths were overridden into R35 after sourcing R28's environment, so R28's temporary resources were not reused or written by these tests.

- Actual `mixer create`: exit 0.
- Actual `mixer test`: exit 0; four Swift Testing functions passed, zero XCTest methods. The inner `swift test` built the generated AppModels/AppFeatures against the public SDK. The shared draft/add/toggle test passed.
- Actual `mixer build --platform host`: exit 0.
- Both real lock-comparison diagnostics retained all identity components. Expected: 127 UTF-8 bytes; observed: exactly those bytes plus one final LF, 128 bytes. The unchanged product comparison passed. Exact strings, byte hex and hashes are in `results/identities.json`; raw diagnostics are `results/test.stderr` and `results/host-build.stderr`.
- Patch application check and rendered run-step Bash syntax check both exited 0.

Raw CLI stdout/stderr, command argv/environment/exit statuses and durations are in `results/`. `results/test-output.log` and `results/host-build-output.log` contain the original command output extracted from the corresponding raw CLI JSON; the raw JSON is preserved alongside them. Source and reused binary/launcher identities are in `inputs.json` and `results/postflight.json`.

## Cleanup and limits

All five inner command receipts recorded TERMINAL, exit 0, direct child reaped, both stream EOFs, owned group absent, closed descriptors and terminal custody. Exact receipts were retained in `results/command-receipts/`. After these observations, the owned temporary project/build/TMPDIR were removed. Consumer source/lock afterimages and SDK hash manifest remain for review. No timeout, hold, device operation or historical-path cleanup occurred. Relevant product source hashes, the reused binary and launcher remained unchanged; the canonical workflow hash also remained unchanged during this slice.

Hosted Xcode 26.3/Swift 6.2.4 rerun and the native iOS build remain pending. The iOS workflow command is preserved by the patch but was not run locally. This is host consumer development evidence, not device, simulator runtime, VM, immutable published-package, dogfood or GA qualification. Parent owns integration and the single independent slice review. Java inspection/producer/caller contracts were left unchanged.
