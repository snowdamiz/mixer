# Passive lifecycle observer: generic simulator build attempt

**The app build fails under Swift 6 UIKit typechecking.** The single selected
attempt compiles and links MixerCore, MixerUI and the unchanged XCTest target,
but rejects `PassiveLifecycleObserver.swift:25:50` while compiling the app:

```text
error: sending 'note' risks causing data races [#SendingRisksDataRace]
note: task-isolated 'note' is captured by a main actor-isolated closure.
main actor-isolated uses in closure may race against later nonisolated uses
```

The non-Sendable notification parameter enters `MainActor.assumeIsolated` from
NotificationCenter's callback. The exact failing command and complete streams
are retained in [the command receipts](../verification/apple-passive-lifecycle-generic-build/attempt-1/commands.json)
and [app stderr](../verification/apple-passive-lifecycle-generic-build/attempt-1/app.stderr),
SHA-256 `da72b5113d21d9368f9d2793b2f58c74c3b5c751ec1411357244dd920dc65c76`.
No accepted source was changed and no compiler retry was made. This compiler
failure does not invalidate the separately scoped Foundation host observations;
it establishes that those observations were insufficient to accept the UIKit
adapter for compilation.

The historical V8 result remains **Settings Passed / first Tab Failed**, Xcode
exit **65**. No simulator/device discovery, boot, launch, install, native test,
UI, capture or phone operation occurred. No native attempt, original-result
ingestion, FieldLog, signing, store, customer, operational or GA acceptance is
selected. Physical phones remain disconnected and deferred.

## Selection, exact sources and recipe

[Root's explicit coordination](../verification/apple-passive-lifecycle-generic-build/selection.json)
selects generic compilation only and requires fresh app and runner products.
The source context is root-reported
`6b8aba350224ed19f678669bdbea6b359d8de68b`; this lane issues no Git command.
Root subsequently reported delivery of the unchanged accepted source candidate
at `7b6048642b42e4900cccff4e14aa0fe8949ab35e`, excluding this active build lane.
That later report is retained separately and does not replace exact input hashes.

The candidate archive is SHA-256
`042c47cc39166ad25e475a5f213815e2aab926590a520e3eb51e0e04cd97774e`.
The producer and independent-review handoffs are respectively
`9e30a9aeef107094d70b17fc83fc632f0278af9d0384a58564cd7b0456efbd75`
and `376642724000ecd82914f322337ee498b5b083f3bd927dcfab03d8259d425a27`.
Before and after compilation, all **227** members sealed by those handoffs and
the accepted prior-build/original-recipe/review handoffs match. This is seal
accounting, not a behavioral test count. The previously observed producer 116
and independent 371 Foundation checks were not rerun.

All **42** candidate archive members remain byte-exact and mode `0444` through
materialization and compilation. Against the accepted forty-member closure,
only existing `Prototype/main.swift` changes, the two passive lifecycle helpers
are added, and the other **39** files retain their bytes. The archive has **37
Swift files**: five MixerCore, sixteen MixerUI, twelve Prototype and four harness
files. The app compiler argv explicitly includes all twelve Prototype files:
`AppearanceNativePathsV2`, `AuthoredToggleCarrier`, `DiagnosticRequirement`,
`DiagnosticTrace`, `NativeInterruptionChecks`, `PanCommitChecks`,
`PassiveLifecycleData`, `PassiveLifecycleObserver`, `SemanticActivationChecks`,
`TogglePanAdmission`, `TogglePanPolicy` and `main` (each `.swift`). The unchanged
harness sources are `DiagnosticTransport.swift`, `PublicSwitchSelection.swift`,
`SettingsFailureDiagnostic.swift` and `ToggleUITests.swift`. A failed app compile
is not a claim that all app files passed typechecking.

The [recipe comparison](../verification/apple-passive-lifecycle-generic-build/attempt-1/recipe-comparison.json)
binds the original accepted full app/runner recipe. Its only argv/environment
derivations are the owned scratch-prefix substitution and insertion of the two
new helper files in the sorted app source list. Xcode **26.6 (17F113)**, Apple
Swift **6.3.3** (driver **1.148.6**), iOS Simulator SDK **26.5** and Python
**3.14.8** are actually queried and hash-bound. The same eight original tool
bindings match before and after compilation. Swift mode 6, `-Onone -g`, target
`arm64-apple-ios26.0-simulator`, and generic `build-for-testing` remain exact.
Signing, indexing, automatic package resolution and package updates are disabled
under that recipe. Historical scripts, source/product archives and runtime
programs are read only as data; none is executed or reused as a product.

## Observed products and packaging boundary

| Command group | Exit |
| --- | --- |
| Xcode, Swift, SDK and Python version queries | 0 each |
| MixerCore | 0 |
| MixerUI | 0 |
| App, including the twelve Prototype files | **1** |
| Unchanged four-source XCTest runner build | 0 |

The [build receipt](../verification/apple-passive-lifecycle-generic-build/attempt-1/receipt.json)
records failure. No app executable or app Info.plist is produced. The source
Info.plist remains byte-exact with historical `MinimumOSVersion` **17.0**. The
selected packaging rule would change only the product property to **26.0** after
a successful app compile; [the explicit unavailable receipt](../verification/apple-passive-lifecycle-generic-build/attempt-1/packaging-not-applied.json)
records that it was **not applied** here. No actual app minimum-OS claim follows.

The preserved failed partial product archive contains **50 regular files**:
eight freshly built app-framework/debug files and forty-two fresh runner files.
Its SHA-256 is
`f51a1f9585628b12bc9d2aa89b83d865855d75422b296feced07003092f5ca38`;
its canonical product-tree digest is
`c5013d1f3c4484e737a373cfb909c100c042268388ffec54ded27dd1baa53981`.
No old product or derived-data file was copied. Complete file manifests and
read-only Mach-O/plist inspection bind the bytes. The three actual compiled
linked targets (Core, UI and the test bundle) are arm64, Simulator platform 7,
minimum **26.0**, SDK **26.5**. The test bundle plist is **26.0**; Apple's provided
runner container and XCTest framework plists retain their actual **13.0**.

[The observed-product clarification](../verification/apple-passive-lifecycle-generic-build/attempt-1/observed-product-scope.json)
explicitly distinguishes these three actual targets from the generator's
unconditionally listed four expected targets in the original inspection field
named `freshCompiledLinkedTargets`. The missing app target is not a successful
product. The original generated inspection is preserved unchanged.

The rearchived exact source closure has SHA-256
`fa9bb46d483828f7e078ba7eca9e5748cadd444042d29ffba01edaa58e011324`;
its recipe-relative tree digest is
`b9f9604e246378411e9db1f8b978c7f2c1085aad985fe7ab9b9fb41746b37e79`.
The selected archive member-tree digest, retaining `accepted/` prefixes and
modes, is `a5c3fb1a0cf9a87dfcd1e2bb3651a57485d5a17c0a25b36570916bbbe5514f33`.

There are **17** `warning:` line occurrences across compilation commands: two
app lines for one pre-existing UIButton deprecation, and fifteen runner lines.
The app warning multiset is incomplete against the successful baseline because
compilation stops at the new error; it is not reported as matching. Core and UI
emit none; the runner warning multiset matches the original full qualification.
The separate Swift-version query also records one sysroot/default-MacOSX warning
in its complete stderr. It is not included in the seventeen compiler-group lines.

## Correction proposal and cleanup

[The separate minimal proposal](../verification/apple-passive-lifecycle-generic-build/correction-proposal.json)
and [proposal-only patch](../verification/apple-passive-lifecycle-generic-build/correction-proposal.patch)
would transfer only an optional String identity into the synchronous main-actor
section. `withExtendedLifetime` would hold the actual notification object
through the existing synchronous filter/snapshot so its address cannot be
recycled. Inside the actor, comparison with the actual application, owned window
or owned window's current scene would retain exact identity scope, nil/foreign
filtering and existing snapshot serialization. Off-main delivery would keep its
existing fault-only early return. No Task, asynchronous hop, broad unchecked
Sendable conformance or unsafe isolation annotation is proposed.

This is an **uncompiled, unaccepted proposal only**. Neither it nor a source
correction nor another compiler attempt is selected. Producer-owned source
revision, executable semantic checks, independent review and a separately
selected fresh complete UIKit build remain necessary before accepting a repair.

The driver has a 900-second deadline, the inner build a 780-second total deadline,
individual compilers 180 seconds and runner 240 seconds. All eight command groups
finish with both EOFs, no timeout or signal and no owned surviving process group.
The app failure is an ordinary compiler exit, not an aborted observation.
After both exact source and partial-product archives round-trip against every
manifest member, the holder check is empty, every scratch file has one link and
the owned root's device/inode remains stable immediately before removal. Cleanup
removes **448 regular files totaling 160,612,891 bytes** from this lane's scratch.
The driver also exits with both EOFs and no surviving group. Other projects'
processes and instances remain untouched. No network/provider, frozen hosted
lane or frozen V7 join was executed; no live SDK/source/tracker or Git state was
edited by this lane.

The sealed audit validates evidence integrity while explicitly retaining
`buildPassed: false`. Recheck without writes, extraction, compilation or native
commands:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-passive-lifecycle-generic-build/verify.py
```
