Independent generated Java execution review — November 7, 2026

Verdict: ACCEPT. No blocking findings. This review unlocks one fresh parent-owned
Debug/Release × original/relocated/exported six-consumer run at source-pair.8,
with the explicit Xcode26.6/MacOSX26.5 environment in the reviewed integration
plan. No additional preparation round is needed. This is acceptance of the
runner and execution selection, not a successful integration or release receipt.

Reviewed identities:

- Runner `scripts/ci/check-android-generated-java.py`:
  `ba369ff360ee991acf0d0d7867e31170ad663800cadd8b78416a14c6b2a0c4aa`.
- Controls `scripts/ci/tests/test_android_generated_java_runner.py`:
  `99f5436faccd5ce74d8e7fb9d14f13a4be1a1ab2f3d83021da10732860625630`.
- Reversing only the load_profile `.8` literal to `.7` produces exactly
  `67e571ab863b552175a1ad947da453fea0692b9c7bf47353feff997889846d71`, the supplied
  corrected pre-integration runner. No other runner integration change exists.
- All 18 files in the accepted motion review's implementation identity map match
  this parent tree. All 22 SDK and 24 adapter canonical identities match current
  sources, including all 18 product Java sources. The strict live `.8` selector,
  projection digests, complete inventories, locks, and rendered driver checks
  remain intact (`runner:96-161`). The synthetic `.7` fixture in the tests is
  supplied directly to the generic validator; it does not weaken live selection.

Source checks and executable evidence:

- `runner:164-341`: javap stdout alone receives 8,388,608 bytes at the production
  call site (`:381-382`). The ordinary stdout and every stderr limit remain
  4,194,304 bytes; the shared total remains 67,108,864 bytes. One extra byte is a
  failure, never a truncated success. Limits remain 160 commands, 600 seconds
  per command, 2,400 seconds for execution and five seconds for each owned-group
  cleanup. The accepted command cleanup and outer scratch cleanup blocks are
  byte-identical to R2. Existing denial, unknown custody, drain/reap/close errors,
  receipt persistence errors, and retained-scratch controls pass in both modes.
  No historical process identity was queried or signalled.
- `runner:344-411`: every emitted class, including nested classes, goes to the
  official verbose javap invocation and D8. The parser is byte-identical to R2.
  Independently reparsed all three retained real javap outputs and independently
  decoded their retained classfile constant pools. All 4,944 entries match in
  class, constant-pool index, kind, owner, member name, and descriptor: 2,695
  Methodref, 1,947 Fieldref, 302 InterfaceMethodref. All 215 classes, including
  197 nested classes, match the recorded input digest. The two full outputs are
  byte-identical, 6,640,338 bytes, SHA256
  `bf456931ee0edb1c935de1dd9af02d75ae7533dc44a6f00aade10aab71bee1c7`.
  The `-v`-only probe is still 5,098,946 bytes, above the old ceiling. These are
  preserved pair7 measurements; pair8 output growth remains a real-run question.
- `runner:495-510,537-565,626-633`: Apple selection requires explicit absolute
  DEVELOPER_DIR/SDKROOT and an SDK inside the selected developer directory.
  Resolved paths, Xcode version/build and SDK metadata hashes are retained and
  compared after execution. Read-only re-observation matches Xcode26.6 build
  17F113 and macosx26.5; no global Xcode selection changed. Javap binary identity
  matches the recorded OpenJDK25.0.4.1 tool. Full installed distribution inspection
  and postflight remain in the actual runner; this review did not execute them.
  Independent fake execution proves missing Apple selection prevents commands
  and a changed Apple metadata result rejects the completed fake six-form flow.
- `runner:576-625`: both producer build and bin-path calls retain `-j 2`.
  Fake-boundary controls reach both producers and all six forms, require original
  removal before relocated execution, and preserve both exported tamper suites.
  No actual compiler or real six-consumer run occurred in this review.

Validation: 45 supplied tests and 10 independent controls passed normally and
under Python `-O`. The independent suite retains the seven original R2 tests,
with explicit adapters for the new javap keyword and Apple metadata boundary,
plus three new checks: changed Apple postflight, missing Apple preflight, and
exactly 8 MiB successful stdout capture. Each test process had a 40-second
execution bound; both read-only evidence audits had 25-second bounds. All six
outer processes returned zero with terminal custody. Precise argv, interpreter
identity/version, source revision/tree, stdout/stderr, output hashes, source line
ranges/hashes, and receipts are in `baseline.json`, `tests.json`,
`commands/commands.json`, `audit-commands/commands.json`, and `audit-*.json`.

Both historical failed full runs remain failures: attempt1 failed during the
Debug producer build; attempt2 completed Debug build/create/export/javac then
failed closed at the 4 MiB javap limit. All 320 previously sealed evidence files,
including both /tmp attempt trees, remain byte-identical to the fix lane's
preservation baseline. The current review baseline and final postflight also
check the current runner, controls, source files and sealed review/fix evidence.
All review temporary directories were removed; no foreign scratch was removed.

The parent should use a fresh output tree, the exact reviewed sources, explicit
Apple environment, and pinned Swift6.3.3/official Android/JDK tool selection.
Require all six actual compiler/D8 and complete member receipts, both-mode named
CLI/driver refusals, source/tool postflight, and terminal cleanup before accepting
that run. The 8 MiB budget is a measured finite hypothesis, not proof that pair8
or the Release producer fits it. Preserve a failure if the new run exceeds it.

Only this new review directory was written. No implementation fixes, children,
commits, pushes, merges, real compiler/javap/JVM/Swift/native invocation, device
probe, historical process probe/signal, held v5 retry or hosted-lane work occurred.
Phones remain disconnected. APK, runtime, API28 linkage, physical-device,
signing, immutable published packages, separate-repository FieldLog, release and
GA gates remain pending under their existing owners and holds.
