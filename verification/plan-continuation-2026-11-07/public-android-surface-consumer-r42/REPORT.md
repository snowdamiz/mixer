# R42 public Android surface and real FieldLog consumer

BUILT. Root reviewed the public facade shape and requested pre-clone byte caps; those caps and their exact-limit/oversize controls are included. Actual execution of this new APK remains pending root signing/native ownership. No canonical source/profile writes, Git, device/ADB operations, children, held namespaces or physical phones were used.

- Unsigned APK: `FieldLog-public-surface-r42-unsigned.apk`
- SHA-256: `f4235dee683b17a9ca33094c5cd0de60f9672dd1f16f0eeea50d761e8688fe3d`
- Instrumentation component: `dev.fieldlog.publicsurface/dev.mixer.android.FieldLogInstrumentation`
- Activity: `dev.fieldlog.publicsurface/dev.fieldlog.android.FieldLogActivity`
- Product/application diff: `minimal-product-app.patch`; complete candidate sources: `afterimages/`.
- Test-access migration: `instrumentation-access.patch`; complete test sources: `testconsumer/`.

`AndroidUINativeSurface` is SDK-owned, with nested immutable `Frame` and `Events` types. It delegates synchronous attachment, input gating, lifecycle and terminal cleanup to the existing external `NativeOwnerV2` path. V3 selection is explicit. It exposes no owner/core/coordinator/observer/renderer types or private ledgers. Owner bytes remain opaque and exact; packet and appearance bytes are cloned without decoding or normalization. Frame construction checks all lengths before cloning: owner 1–64 bytes, packet 1–1,048,576 bytes and appearance 1–65,536 bytes. Existing schema/geometry/capability/unknown-operation guards remain in the unchanged native implementation. Close is terminal and idempotent; an original cleanup failure/incompleteness remains sticky and retains the real owner. Repeated close never repeats native cleanup.

Production FieldLog Java now lives in `dev.fieldlog.android`, uses platform `JSONObject` with strict field-type checks, and imports only the public SDK facade/profile. JNI remains app-private mechanical routing. Captured native event bytes pass through base64 into Swift and are decoded directly by `JSONDecoder` as `UIEventEnvelope`; app JSON never parses event numbers. Owner identity, packet and descriptor bytes are never rebased or normalized. The Java event callback only enqueues a captured owner/envelope copy; Swift dispatch occurs on the later app queue turn.

This APK compiles the actual R24 app afterimages and real FieldLog TaskEditorPresentation, TaskEditor, Workspace and WorkspaceRepository sources. `application-provenance.json` records consumed hashes and the pinned FieldLog checkout (`00c8fe0400bc9a06242371ce7b02cd440f64f31e`, historical recorded revision, no Git lookup). Features/models match that checkout byte-for-byte. WorkspaceRepository preserves the existing R24 portability delta adding `import Android` and `Android.close`; the exact small delta is `existing-workspace-android-portability.patch`. No repository implementation was replaced. Public Swift SDK sources are byte-exact to R24; AndroidUIHost and AndroidUIProfile also match current canonical sources. All 20 existing Java SDK source hashes match the selected Pair12 roster.

## Executed proof

Command from the worktree root:

```sh
python3 verification/plan-continuation-2026-11-07/public-android-surface-consumer-r42/prepare.py
python3 verification/plan-continuation-2026-11-07/public-android-surface-consumer-r42/build.py
```

`compile-1/commands.json` records all 24 exact tool argv, working directories, fresh PID/PGID identities, exit codes, elapsed time and observed group absence. The matching `.stdout`/`.stderr` files are raw results; `source-inputs.json`, `host-inputs.json` and `environment.json` record actual sources, digests and scope. Input source-tree digest: `b5864c753b3412d4ba63ed941bc61680a944f88d3961326b788b5b1e716476cb`. The supplied parent revision is `fd373fc8fed2329b31b72c918f6745e183cbb517`, source114 is `5814b0dab60dfe3fdbce2791644499fc0362072a99bf9034c7f28ea266577608`; these are parent-provided identifiers, not a new Git observation.

- Strict SDK37 `javac --release 17 -Xlint:all -Werror -proc:none -sourcepath ''`: SDK surface, separately compiled external-package production client, and R39 instrumentation all PASS.
- Old private R17 adapter moved to an external package: compiler exit 1, explicitly refuses access to nonpublic engine classes; no class files emitted. See `private-baseline-refusal.stderr`.
- Actual facade/owner/core/coordinator with existing closure-A Android/JNI/renderer leaves: `PASS public external-package surface checks=46`. These cover immutable/exact bytes including UInt64-scale numeric text, synchronous install, native environment refresh, input gating, pause/resume/stop, stale-owner/lifetime rejection, old-close-after-new-open, same-owner repeated revoke, sticky cleanup failure with no repeated effects, exact byte limits and oversize/empty refusal. These are host controls, not Android framework receipts.
- Existing actual external-source/owner controls: `PASS external-source owner lifecycle checks=24` with the same declared controlled leaves.
- Swift 6.3.3 Android SDK28 release build `-j 2`, NDK r27d strict JNI link, JDK25 D8 min28, aapt2 SDK37 and 16K zipalign verification: PASS. Both rebuilt ELF libraries have LOAD alignment at least 16K. NDK bin was never added to host PATH. Host SDK was Xcode 26.6 / macOS26.5; tool versions are raw `*-version` outputs.
- All 16 official runtime libraries are byte-exact to the R39 APK. Only `libAppAndroid.so` and app-private `libmixer_android_jni.so` changed. Seven app JNI exports use the new external Java package. The archive has no signing metadata.
- Full R39 terminal-ledger assertions, handoff regression and expected PASS are preserved byte-for-byte. Full onStart flow is identical after reversing mechanical test-access substitutions. `FLAG_ACTIVITY_NEW_TASK | FLAG_ACTIVITY_MULTIPLE_TASK` remains intact. Test-only access uses engine-package instrumentation/reflection; production app code has no private engine references. See `source-checks.json`.

One material attempt used 23.3698442952591 active command seconds; cleanup used 0 seconds. All 24 owned command groups were observed absent. Fresh isolated build outputs are retained at `/Users/andreyyurlov/.t3/userdata/fieldlog-public-surface-r42-shjj1zn4`; there were no device instances to clean up.

## Contract and adoption implications

One new SDK Java source adds one public top-level facade and two nested public types. The Java source roster grows 20 → 21; the selected adapter roster would grow 26 → 27 when root adopts this file. The 24-entry Swift SDK compatibility roster is unchanged. Public Swift activate/install/revoke, profiles, capabilities and engine C ABI/header sources are unchanged. Pair12/source114 metadata were not rewritten; no Pair13 or transitive identity package was generated. Profile/binding/generator adoption remains root-owned.

Root's next actual test is to sign this exact APK and run the verified instrumentation component under the existing native isolation/cleanup rules. `expected-PASS.txt` retains the complete R39 expectation, including distinct Activities, old-destroy/new-reply isolation, Unicode/newline save, repository reopen, fresh Activity, native-only refresh and complete owner/core/coordinator/renderer terminal ledgers. The APK build and host controls do not establish that runtime result. Immutable published-package, physical-phone final acceptance, full IME/API-floor qualification and GA remain pending. No historical custody hold is released.
