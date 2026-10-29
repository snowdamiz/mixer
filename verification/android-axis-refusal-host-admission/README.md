# Isolated Android axis-refusal Swift host admission draft

This packet prepares one executable remote host check. It is **uninstalled and UNRUN**: root selection and dispatch remain false; the actual source revision and run ID remain unbound. No local compiler, Swift/product/native runtime, Git/gh/network, process inventory, group/signal/wait/timer/ctypes or capture operation was performed. No native cleanup obligation was created.

The exact accepted package is verification/android-axis-refusal-host-preparation/package: 27 regular files, 284,605 bytes, source manifest SHA256 601b9722df4f42c6649f0e0b6943fe5e3ad96bc6ebeeeecc186da475875e5782, package projection 257ed4dfa93d43b15d4bfe2d51372d261e4fec5fd9e80c3f1ca62b1967a3a793. The independently accepted source-review receipt is 7dce2a7630a22f095b0953444b214e5ee0b219213e168b0867c7d626f19ea3fa. The data verifier rehashes every source member, rejects additions/symlinks and requires byte-identical pre/post snapshots.

## Existing mechanism and root decision

The current ordinary .github/workflows/verify.yml Swift job directly invokes SwiftPM on macos-15, with Xcode 26.3 build 17C529, the default Apple toolchain and a 30-minute job timeout. Its exact scripts/ci/verify-apple-toolchain.py is reused without editing. That verifier runs fixed xcodebuild/xcrun/Swift-version/SDK-version/Git-revision/host probes, retains their selected values and binary hashes, and caps each probe's combined output at 262,144 bytes with a 30-second probe timeout. It establishes installed tool identity, not process-group custody. Its source is pinned in verify.mjs.

Before choosing a mechanism, this lane inspected that workflow/verifier, the Swift resource CI qualification/root receipts, and the independent FieldLog host review. The resource fixture actually uses Rust; FieldLog's helpers and cleanup records are bound to a separate repository/source/run. No specifically admitted reusable Swift test command helper for this closure was found. None is imported. Root then selected the existing ordinary direct Actions precedent for this draft. This is not a new custody framework or a transfer of JVM/Git signal-helper authority.

## Exact proposed execution

Copy workflow.draft.yml byte for byte to .github/workflows/android-axis-refusal-host.yml only after root's final source review and delivery decision. The false root-selection.template.json is not runtime authority. After delivery, root binds the delivered 40-hex source revision and passes its selected JSON as the workflow_dispatch root_selection input, alongside profile axis-refusal-host-v1. JSON is parsed as data through an environment variable and is never evaluated as code or interpolated into shell. Passing the selection after delivery avoids a self-referential commit hash in a checked-in selector.

The selected policy is one root-dispatched manual run and attempt 1. The workflow rejects nonmanual events and later attempts; it cannot independently prove that no second manual dispatch ever occurred. A null selector run ID allows the first root-dispatched run to be recorded; root must bind the actual run ID and reconcile consumption of its single allowance during actual-results review. No automatic retry, fallback tool, budget widening, second test command or canonical/source-pair change is authorized here.

The only behavior command is:

    /Applications/Xcode_26.3.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swift test --package-path <workspace>/verification/android-axis-refusal-host-preparation/package --scratch-path <runner-temp>/android-axis-refusal-<run-id>-1-scratch --jobs 2

It is unfiltered, has no skip-build option, and compiles/runs the package's only test target. The scratch path must not already exist. Command argv, selected environment, source revision/projection, run ID/attempt, Node/Python/Bash and Apple tool versions, tool binary hashes, separate raw stdout/stderr and direct shell return status are retained. The fixed Apple verifier's probes are separately identifiable by its unchanged source and receipt; they are not additional behavior test invocations.

Bounds are 30 minutes for the job, 12 minutes for the SwiftPM step, 3 minutes for tool verification, 2 minutes for each data step, 3 minutes for checkout and 3 minutes for artifact upload. Build concurrency is --jobs 2. The numbers are selected experimental hypotheses, not empirical performance claims.

Each command shell sets Bash ulimit -f 65536. Its expected 1,024-byte unit gives a 67,108,864-byte (64 MiB) limit on every regular file written by the shell and inherited children, including compiler scratch products. This is not merely a log cap. Local Bash manual source states the default 1,024-byte unit; the actual hosted interpretation is still UNRUN. A data-only Python resource.getrlimit(RLIMIT_FSIZE) readback in the same shell requires both soft and hard limits to equal exactly 67,108,864 bytes before the Apple verifier or SwiftPM starts. It retains Bash version and the ulimit value. POSIX-mode or other unit differences fail before those commands. No resource mutation is performed by the readback helper.

Successful evidence is accepted only if each retained Swift/tool stdout and stderr stream is at most 8,388,608 bytes (8 MiB). Files may grow up to the distinct 64 MiB inherited regular-file ceiling; oversized evidence is retained and refused, without widening or retry. There is no pipeline, tee, background child or signal/cleanup helper. No aggregate scratch-disk, allocation/RSS or arbitrary-descendant bound is claimed.

## Acceptance and retained limitations

required-tests.json binds exactly eight AndroidTextFieldAxisRefusalTests XCTest methods, four RuntimeTests Swift Testing methods and seven TransactionTests Swift Testing methods. Each named successful result must occur exactly once, along with the separate eight-test zero-failure XCTest summary and eleven-test Swift Testing success summary. Missing/zero/duplicate/unknown results, skips, failures, compiler errors, output overflow, nonzero exit, source drift, wrong tool/budget/argv, unobserved shell return or incomplete binding refuse acceptance. Warning lines are retained with source-compiler versus tool/SwiftPM classification; zero warnings is not inferred from success.

The 37 controls in source-checks.json exercise synthetic data only. They do not compile the Swift manifest, discover or execute tests, invoke Python, parse the workflow through GitHub's validator or establish current hosted tool availability. Those remain pending. The executable data validator uses only Node filesystem/crypto and ordinary data operations; verify-file-limit.py is a remote data-only limit readback, not a command launcher.

A successful direct Actions shell return establishes only that recorded hosted step's completion and output. Direct child reap, process-group absence, separate pipe EOF, arbitrary/escaped descendants, scratch deletion and runner/provider disposal remain unknown. No scratch cleanup is performed or inferred by this draft. Scratch is confined to the exact owned external path; compiled products are not uploaded. Timeout/cancellation can prevent a terminal command record or postflight; the partial outputs are retained where Actions permits, and this absence refuses executable acceptance. Action-level final conclusion and artifact identity must be checked by root; a result.json alone is not final run acceptance.

Raw downloads belong under this directory's ignored raw/, artifacts/, logs/ or actual/ paths. Source checks and the compact receipt are exportable; no raw remote artifact has been downloaded here.

Canonical SDK/engine manifests, package topology and C ABI integration remain pending even after a future successful isolated 19-test run. Java decoder/combined source-pair, Android cross-compilation, native simulator/emulator/UI/capture, physical phones, immutable external FieldLog packages, OTA, production/store/customer and GA acceptance remain pending. The current SDK22/adapter23 source pair is unchanged and no adapter24 selection or reservation is made. All existing native, local compiler/process/custody, Unit A, held FieldLog and broad hosted holds remain intact.

## Next concrete root action

Review and deliver this exact draft through the existing authorized root delivery mechanism, bind the delivered revision in the false template, then select and dispatch the single manual run. Until root does so, tool/manifest/compiler/test acceptance is unbound and UNRUN. No new permission request to the user is needed from this lane, and another source-only review cycle is not the discriminating test.
