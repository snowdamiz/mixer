# Admission source/data review

One concrete correction is required in the reviewed packet. No workflow was installed or run.

## R1: Refuse unknown quoted Swift Testing results

`verification/android-axis-refusal-host-admission/verify.mjs:108` extracts only identifier-shaped `Test name() passed` lines. Appending `✔ Test "unknown human-readable title" passed after 0.001 seconds.` to an otherwise accepted nineteen-method fixture is silently ignored. The actual producer `parseTestOutput` accepts it, and the actual filesystem `preflight` / `recordCommand` / `postflight` / `assess` path returns `isolated-host-test-evidence-complete`. This conflicts with the packet’s stated unknown-result refusal.

The minimal sibling correction is to require exactly eleven total successful Swift Testing `Test` result lines, excluding suite and run summaries, as well as the exact eleven identifier roster. Add the quoted-display-name control to actual `controls.mjs`, rerun data controls, and refresh packet hashes. No new review campaign or broader runtime custody mechanism is needed.

## What was checked

The three root-supplied receipt/manifest/workflow hashes match. Every admission-manifest row and its projection match. All twenty-seven physical package files independently match the pinned source rows, 284,605-byte total and package projection. Actual producer `sourceSnapshot` passes.

The actual final `verify.mjs` and `controls.mjs` files were imported by file URL. The actual `runControls` export passed all thirty-seven producer controls. No implementation function was copied or mocked. The actual filesystem functions were exercised with synthetic receipts/transcripts and a mirrored twenty-seven-file source closure wholly inside this review directory. This is executable data-validator evidence, not hosted Swift evidence.

Additional controls refused changed source bytes, an extra package member, a source symlink, persisted binding drift, missing shell completion, a missing XCTest terminal summary, an identifier-shaped unknown Swift result, and an explicit skip. The quoted-result omission is reproducible in both the parser and filesystem pipeline.

Source inspection confirms root selection is JSON data from an environment variable, manual event/attempt one are required, source revision and installed workflow hash are checked, the command argv and output upload path are fixed, and the separate regular-file and accepted-output caps are preserved. The draft has no nonce field; its actual run ID starts null and the documented root run-ID/one-dispatch reconciliation remains necessary. No independent single-dispatch enforcement is inferred.

The ordinary direct Actions mechanism remains explicitly narrow: shell-step return and retained output only. Process groups, pipe EOF, arbitrary descendants, scratch deletion and runner disposal remain unknown. Compiler/manifest discovery, all nineteen Swift methods, hosted Python byte-limit readback, YAML/Actions validation, run/artifact identity, canonical integration, C ABI, native/device, external immutable FieldLog, OTA and GA remain pending.

## Tool and cleanup scope

Only Node filesystem/crypto/path and source/data operations were used through `mcp__node_repl__js`; no runtime-version/process probe was performed and no shell command was executed. No Git/gh, compiler, Swift/product/native/UI/capture/network, process/group/signal/wait/timer/ctypes operation was used. The temporary mirrored tree and synthetic evidence are removed after recording the compact checks. Only this review directory was written.
