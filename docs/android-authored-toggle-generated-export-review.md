# Android authored toggle generated export independent review

Independent review passes for the bounded source-export repair. No actionable
findings remain in this scope. The [final review receipt](../verification/android-authored-toggle-generated-export-review/final-receipt.json)
binds the prior baseline, producer handoff, independent replay and review files.
This does not accept public V2 routing or any product/GA gate.

The [independent baseline](../verification/android-authored-toggle-generated-export-review/baseline.json)
was frozen before reading the implementation or collector, using the original
proposal and acceptance-bound authored integration. Its fourteen expected source
hashes, unchanged public Activity hash and four accepted authored class hashes
were preserved. All 206 producer handoff members (4,426,171 bytes) match the
announced seal; the handoff also remained unchanged after replay.

Source review confirms one production allowlist entry, the fourteen-source test
expectation and expanded lock tests. Java/control implementations, Activity,
JNI/Swift contracts, runtime floor and theme/resource support are unchanged.
Both rejected direct-driver admission and CLI lock verification are exercised.

The [independent replay](../verification/android-authored-toggle-generated-export-review/replay-1/receipt.json)
passes 784 recorded checks. It builds from all 127 frozen source snapshots, with
existing local Git dependency mirrors and no remote dependency downloads, then
uses the freshly compiled CLI to create a separate application.

| Independently observed operation | Result |
| --- | --- |
| Debug and Release host tests | Two focused test functions and six parameterized coordinator/authored edit/remove/rename cases pass in each mode. |
| Fresh CLI export | Exactly fourteen Java files match the pre-handoff accepted-source baseline. The adapter digest matches the producer, and the compile profile remains API28. |
| Isolated Java17 compile | SDK37 `android.jar` is the only explicit class path; empty source path, `-implicit:none`, full lint and warnings as errors produce 160 class files. All four authored class hashes match accepted native evidence. |
| Omitted-source control | Omitting only `AuthoredToggleInputV2.java` fails for its missing type and produces no class files. |
| D8/decompilation | Official D8 minAPI28 succeeds; `dexdump` contains all four authored descriptors. The entire 255,044-byte DEX is byte-identical to the producer: `420aa6339c3f62bada4e5d45174cf424fdb9019017301b2cb05c4baffc717308`. |
| Fresh consumer mutation controls | Edit/remove/rename for both coordinator and authored source produce twelve actual CLI/direct-driver rejections with the expected lock reason, before `.mixer` exists. |
| Retention/cleanup | Complete generated project, class output, DEX and raw command logs are retained; the owned scratch was removed and all owned command groups exited. No other processes were discovered or changed. |

Tools match the sealed producer identities: Apple Swift6.4 on arm64 macOS,
OpenJDK25.0.4.1, SDK/build-tools37 and D8 9.2.4-dev. The generated lock separately
records the installed Swift6.3.3 Android distribution. This independent replay
executes host CLI/tests and Java/D8 only; it performs no Swift/JNI/APK cross-build.

Public V2 routing, theme/resource packaging, lifecycle/platform coverage, shared
design parity, signed presentation/health, FieldLog and GA remain pending. Native
runtime, device discovery, capture and UI automation were not used. The product's
proposed Android API28+ baseline is not raised; D8 minAPI28 does not qualify the
private V2 consumer below its API36 runtime floor. The original proposal packet
is preserved unchanged. Root remains responsible for final scoped acceptance,
coherent delivery and CI inspection.
