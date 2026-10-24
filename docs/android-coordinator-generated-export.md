# Generated Android coordinator source export

New Android projects include the independently owned private
`NativeCoordinatorV2.java` in their explicit `Generated/MixerAndroid` source
snapshot. Its exact bytes participate in `mixer.lock`. Editing, removing or
renaming the snapshot invalidates the adapter lock. No test instrumentation or
host substitutes are part of the generated application's Java closure.

The generated public `MixerActivity`, app-owned manifest and Swift bootstrap are
unchanged. The Activity continues to use the V1 exchange/render path. Including
the private coordinator as compiled source does not enable V2 or widen its
private native API36 runtime support contract; the unsigned APK still targets
the existing arm64/API28 compile profile.

`verification/android-coordinator-generated-export/verify.py` captures the exact
CLI/SDK/update/native inputs, runs focused host snapshot and lock tests, creates
a fresh application and cross-compiles it with the installed official Swift,
Android SDK/NDK and JDK toolchain. It retains the source archives, generated
consumer, unsigned APK, class bytes and command logs for offline review. It also
checks that coordinator tampering is rejected by both the CLI and direct build
driver before output is created, that the coordinator is in the resulting DEX,
that the Activity class remains the accepted V1 class, and that the native
library defines the six existing ordinary C exports.

Candidate 3 passes all 13 collector commands, including two expected tamper
rejections. The two focused host tests include three lock-mutation cases. Its
compiled coordinator SHA-256 is
`14a1210ca4208b3eb58a5d70db893b5f1729f5d7587c887cd16f37c18b758992`, exactly
the accepted private candidate. The separate offline checker verifies the
captured source, generated lock, unchanged Swift entry and V1 Activity, manifest
(apart from application identity), class bytes and APK contents. These receipts
are in `verification/android-coordinator-generated-export/candidate-3/`;
root review and acceptance remain separate.

Candidates 1 and 2 retain collector setup failures: the first incorrectly looked
for the V1 profile in the coordinator-only acceptance, and the second used an
unsupported `javap --version` option. No product compilation or native execution
ran in those attempts. Candidate 3 binds the unchanged V1 profile to the prior
generated-app source manifest and uses `javap -version`. Disposable scratch from
all attempts has been removed; necessary source, logs, APK and class evidence is
retained.

This scope does not execute Android, JNI/Swift/renderer joins, input/IME,
environment refresh or lifecycle. Computer use and native runtime tests remain
paused. Physical devices, signed presentation, published package consumption,
FieldLog release qualification, store policy and GA acceptance remain pending.
