# Apple reference-first focus runtime packet v2

This is a **host-only preparation** for exactly two simulator tests: the existing
`test000PublicSettingsFullKeyboardAccess` and `test010ReferenceFirstTab`.
The final producer run passes **111 of 111 host controls**. No simulator, physical
device, compiler, UI/capture, service or Git operation was invoked. Independent
review, root selection and native execution are still pending.

The new test starts from the existing plain native UIButton preference. Its
unique authoritative AX precondition must observe `plain-uibutton-reference`
before the one public Tab call. It has no acquisition loop and does not complete
any original keyboard cursor or six-case matrix. The unchanged original oracle,
three identifiers, timing bounds, bridge and command observer V2 remain binding.
A diagnostic success keeps `runPassed`, cursor completion, complete-case,
keyboard qualification, carrier acceptance and GA credit false.

## Frozen composition

The packet reuses the v1 reference-first source derivative and its already
compiled generic simulator products. It does not recompile Swift or alter app or
runner source:

- V1 source/compiler handoff: `9f066db167168e8ab0c78b2147f857ba3980d965a69b681e566e5e185f6a0d3c`.
- Exact 39-source tree: `696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a`.
- Exact source archive: `c1e59b3e950acfe4afa46ae69e8eed29e6c8e1816e1d845e1c40548833201294`.
- Compiled product archive: `0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8`.
- Complete 55-member product tree: `e3d60e7c69dcbe6e75e7089840b62dd4dd475f4a9db4fe87465543f822b39e20`.
- Reviewed v2 classifier handoff: `07776c2af95bcc58e126b4ceb0f0dee39dec1138ea96bc9e33bc8a4a0393a3a0`;
  classifier file: `a85d8d1e6e8dcf72dae609061ef63f03f9d6c5362399ceec85b935e134b3ce49`.
- Classifier independent review: `6ca2e2a7d7264664f50046a506b01465287dcc6d88872be528af239d8c0d5a55`,
  with 137 passing controls. That review establishes classifier consistency;
  it does not select this packet or authenticate a future runtime.

The previous runtime source archive is read and verified as data. Its retired
scratch and prepared run are never replayed. The packet derives fresh copies of
its composition, orchestration, attachment exporter and diagnostic adapter, and
adds the reviewed classifier plus a new importer. Every oracle, bridge and
observer source byte remains unchanged. The source-only archive has 30 members;
its generated selection contains no native authority until root dispatch.
All handoff members and original authored-first before/after/witness/verdict
inputs are rehashed before and after host verification. Every original v1
failure remains unchanged. The original failure still has exactly
`actualNativeFocusTraversal` false.

## Authority and data flow

A Python wrapper is not evidence of a native run. The only native importer call
path in this packet is:

1. Root separately reviews the exact packet, creates one owned simulator, and
   supplies a fresh root selection plus its out-of-band SHA-256. This includes the
   exact packet/source/product identities, a new run UUID, the simulator identity,
   the original complete device/frontend baseline from before creation, and the
   pinned Xcode directory. The selection must be at most five minutes old.
2. `prepare.py dispatch` verifies the packet and selection before importing any
   runtime module. It requires a previously absent `native-run-<run UUID>` folder
   and restores the frozen source and complete product archive there. It does not
   create a simulator. The derived orchestration uses only the root-selected owned
   instance, preserving other projects and the root baseline.
3. `join_support.select_command` accepts the exact two-method command once. It
   checks the canonical 0700 session directory and records its device/inode/owner
   identity before dispatch. The result bundle must not already exist.
   The unchanged observer V2 observes that actual selected command. The adapter
   records the resulting bundle identity before attachment export.
4. The selected command wrapper performs one official `xcresulttool export
   attachments` on that bundle. The canonical command runner then performs the
   official `get test-results summary` and `get test-results tests` calls against
   the same selected result. Actual return bytes, command argv/exit/stdout/stderr
   hashes, canonical path identities and the first attachment-export receipt are
   retained. Exact selected test identities, execution counts and device identity
   are checked **before** attachment joins. Exactly two executions are required,
   once each; duplicate, retry/subexecution, foreign, skipped or incomplete
   selected tests are rejected. Settings must pass once.
5. `adapter.capture_official` verifies the session/result identities again, reads
   only the actual manifest/exported bytes and selected app journal, and checks
   exported hashes and membership. Only then does it construct the importer's
   private immutable capture. There is no public JSON-to-capture factory.
   The capture binds the root selection/session/command outcome, official raw
   outputs, exact attachment bytes and exact app-observation bytes. Host tests
   create explicitly synthetic private fixtures; those are not native authority.
6. After all five owned cleanup operations, the final summary checks unchanged
   capture bytes, full observer terminal proof and the original oracle replay.
   The importer takes its trusted context from the selected runtime process;
   matching fields supplied inside attachments cannot mint or replace it.

The official attachment manifest must have exactly the two selected method
owners and one selected device/configuration. File names, authoritative roles,
payloads and timestamps must be unique, within the actual official run interval,
and complete with no unmanifested or unrelated JSON attachments. Unknown roles,
foreign method/device joins and duplicate premise/witness/verdict joins fail
closed. The fixed before-key attachment, premise, returned witness, retained
bridge witness and retained complete original verdict must agree exactly.
Generation/action order must be the first generation and first action. The
captured app baseline and after sample must have current run wall-time signatures;
the original oracle replays their full immutable decoded observations. Missing
or contradictory before samples cannot establish an input count.

A false premise yields `failed-reference-precondition-zero-injection` only when
the unique official premise belongs to this selected execution, the current app
baseline agrees, the original guard is false, the method officially fails, and no
before-key/returned-key/verdict/after evidence contradicts zero injection. A
passing premise with missing return evidence yields `unknown` and a null input
count. One complete unchanged strict original verdict yields
`one-strict-original-verdict-passed` or `one-strict-original-verdict-failed`, with
one returned public key witness. These are explicit diagnostic outcomes. Any
invalid join or contradictory result fails closed, with a null input count.

The raw JSON parser rejects duplicate keys, non-finite constants, overflowing
float tokens, invalid UTF-8, trailing material and excessive nesting. It delegates
complete type-preserving verdict consistency and original replay to the exact
reviewed v2 classifier. Integer/boolean and integer/float substitutions retain
strict rejection. Parsing, source inspection or synthetic success grants no OTA
or native qualification.

## Host evidence and cleanup

The final executable command is recorded in
[host-attempt-7/receipt.json](../verification/apple-focus-reference-runtime-v2/host-attempt-7/receipt.json):

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-runtime-v2/verify_host.py --attempt 7
```

The run uses Python 3.14.8 on macOS 27.0.1 arm64. The source revision label
`ba9ad4372f94463ba4d363cdfd76dd565c96413f` is inherited from compilation; exact
owned-source, frozen-input, source-archive, product-archive and output hashes
identify this preparation. Current pinned Xcode, SDK metadata, Python, xcrun and
xcresulttool files are read and bound without invoking native binaries. The
versioned SDK directory is resolved through its official SDK alias.

The 111 controls include complete passing/failing strict diagnostic fixtures,
bound false premise, missing-return uncertainty, complete original failure
replay, earlier classifier type failures, invalid JSON, cross-run/session/device/
method binding, duplicate execution and attachment cases, stale/replayed samples,
contradictory before observations, result/session inode substitution, actual
adapter traversal through fake official tools, tool failure, attachment/app byte
substitution, extra app actions, unobserved EOF and process-group/cleanup failures.
A full selected-source composition import verifies all compiled product bytes
while native process launch and socket bind/connect are forbidden. Mocked
orchestration verifies one selected command, no simulator creation, and all five
cleanup attempts even after command timeout or an earlier cleanup failure.

All Python test scratch and full product copies are removed after host evidence
collection. Preparation similarly retires its temporary source materialization.
No simulator was inventoried, created, booted or deleted by this work. Native
runtime dispatch retains official results and observations, independently shuts
down/deletes the one selected owned simulator, retires the secret configuration,
and removes only verified packet-owned source/product scratch. It preserves
scratch on a byte mismatch for root recovery. Missing cleanup evidence prevents
a diagnostic import.

Earlier host attempts remain historical: attempt 1 had one test-harness module
import error; attempt 4 hit a time-dependent stale-fixture assertion; attempt 6
stopped before tests because its tool-file preflight treated the official SDK
alias as an unapproved source path. Those harness checks were corrected. Attempt
6 has its own preflight-failure record. Attempts 2, 3 and 5 passed their then-current
96, 102 and 111 controls; only attempt 7 binds the final source. None of these
attempts ran native tools or changed frozen producer evidence.

## Review and later dispatch

The preparation and its exact member closure are frozen by `handoff.json`.
`freeze.py verify` is file/hash verification only:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-runtime-v2/freeze.py verify
```

A later root dispatch must supply all three explicit arguments:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-runtime-v2/prepare.py dispatch --reviewed-packet <exact packet SHA256> --root-selection <absolute fresh root JSON path> --root-selection-sha256 <out-of-band root selection SHA256>
```

The root selection schema is `mixer.apple-focus-reference-root-selection.1`.
Its closed fields are `schema`, `runID`, `packetSHA256`, `selectedAtUTC`,
`ownedSimulatorIdentity` (`udid`, `name`, `runtime`, `build`), `sourceTreeSHA256`,
`productArchiveSHA256`, `developerDirectory`, `baselineDevices`, and
`baselineFrontends`. The canonical owned name begins `MixerFocusReferenceV2-`;
the pinned runtime is `com.apple.CoreSimulator.SimRuntime.iOS-26-5` build `23F77`,
and the developer directory is `/Applications/Xcode_26.6.app/Contents/Developer`.
The baseline is root's actual complete pre-creation observation, not a fabricated
empty inventory. Root remains responsible for independent review, exact owned
instance selection, fresh context and bounded dispatch. This document does not
authorize or record a run.

Physical phones remain disconnected and deferred. Comparator coverage, the full
keyboard matrix, native acceptance, immutable published FieldLog consumption,
signing, store, operational, accountable-reviewer and GA requirements remain
open. The hosted authority/catalog lane was not read, imported or executed.
