# Private Android pointer oracle repair: candidate 5

Candidate 5 is a frozen host-only repair for the five independently reproduced
[oracle findings](android-pointer-fixture-review.md). All 42 final host tests
pass, and fresh compilation reproduces its four private class files and complete
DEX byte for byte. Root independent review and explicit native dispatch remain
pending. This lane ran no emulator, UI, app, or physical-device command and made
no production, tracker, or Git mutation.

The original accepted pointer contract remains
`86c8c3e0aa8f9af12b8b853fcde3cd5dbc9d0c24bd29d3f732dac07895afd0cd`.
The candidate-4 packet remains intact: 507 bindings under seal
`317de5fb8a7e8ac7249bbb0fc49a17ba2f38a048ab6edfc1b27e24abc5ae6b52`.
The independent review's 42 bindings remain intact under seal
`0942e53a9de5b6fcf87255b7324ced091cd42b4ae42c7628c4698164a2c21f13`.
The host checker replays both sets, including their nested receipts. Earlier
failures and candidate-4's successful build remain their original evidence.

The oracle changes are bounded to the selected findings:

| Finding | Required observation and final controls |
| --- | --- |
| F01 | Reject obscured and partially obscured flags; require action index zero for the sole touchscreen pointer. Flags 1, 2 and 3, plus a nonzero index, reject. |
| F02 | Compare worker and Activity pointer pressure with the sealed event, including MOVE pressure. Zero MOVE pressure rejects. |
| F03 | Convert historical local coordinates into screen coordinates using that delivered event's actual raw/local offset. Require the historical sample to match a sealed MOVE time, coordinates and pressure, in strict order across all delivered samples. The original impossible time/coordinate control, coordinate tampering, zero history pressure, reversed/duplicate/future history all reject. |
| F04 | Require the final sealed MOVE endpoint in an actual current or historical sample for every drag. Removing every Activity MOVE without history rejects. Genuine coalescing and dropped intermediate delivery remain permitted. |
| F05 | Seal action start uptime before DOWN and export measured end/duration in both the summary and a separate observation row. Require a consistent interval of at most 5 seconds, including hold/settle, and bound every worker and Activity timestamp inside it. Worker send intervals and Activity dispatch intervals cannot overlap or backtrack. |

The coalesced positive control uses a nonzero raw/local offset and seven
historical samples in the final delivered MOVE. It passes with 124 requested
events and 117 Activity entries. A separate positive control drops intermediate
MOVE deliveries while retaining the final endpoint. Zero-gap consecutive action
intervals and equal worker interval boundaries pass; overlapping worker send
intervals reject. These are synthetic parser tests and provide no native evidence.
Duplicate revision acknowledgements and a changed saved G03 packet hash still
reject.

The only source change from candidate 4's 105-input closure is private
`CoordinatorJoinInstrumentation.java` action interval logging and its final
5-second check. The Activity and operations asset are byte-identical. The
candidate-4-to-5 compiled delta is exactly Instrumentation.class, classes.dex,
and the APK. APK entry changes are classes.dex and the three disposable debug
signature entries. All 155 production classes, 18 native libraries, 88 native/SDK
inputs (including 19 test inputs), manifest, descriptor, resources and authored
geometry remain unchanged. No event, timing, geometry, listener, engine, or
production behavior was adjusted.

The build preserves the existing real ChecklistEngine/JNI/Swift/private
coordinator/renderer path. Input remains worker `sendPointerSync`; Activity
observation remains passive around exactly one superclass dispatch. Direct
internal callback counts remain null/unobserved. The fixed 20-action, 124 nominal
/ 320 maximum event sequence and every original resource budget remain unchanged.
No new dependency was introduced.

The frozen candidate is:

- APK: `57e82e4e98cdc61581c0639603ec6efa500a66d8d2754f6b47ece89c8165d714`
- Archive: `847de52459dbe90b8fd5abbe186aaf2f936cce38981cbc28ce86b36bcdc9249b`
- 105-input closure: `9082e2de1327bd0784d752db5dfbe4484751d565b3410e01e78664321467f5ce`
- Oracle: `969dc86860e5b1bbce4941645eef68694401fc9839debf7b137c4dcaf9181dcf`
- Current runner contract: `runner-contract-4.json`, SHA-256 `a757865ecd435422d3cc1da98d4a0669d34ab7a5b0d14c3ed6ed97265541b63f`
- Concrete runner: `bd7cd16883a831aac29fa13d162eabf6fae78c88c6b523919e4d9b38c0103b31`
- Wrapper: `3aa02d1b8469ca3f14c355738f16ed774a2c0431007df9f03474b87c99a188d5`

[Candidate build evidence](../verification/android-pointer-oracle-repair/candidate-5/receipt.json)
records Java 17 language target on JDK 25, SDK 37 and D8 min API 36. The
[fresh replay](../verification/android-pointer-oracle-repair/build-replay-1/receipt.json)
uses an empty source path and fresh class/DEX destinations. It compiles both
private source files and compares all four class files and the complete DEX with
the actual signed APK's build artifacts. Official zipalign/apksigner replay and
local ZIP/ELF packaging validation pass for the exact candidate. The disposable
private debug key was removed; the signed APK is retained in this lane's
`retained-apk/` artifact directory and its archive.

The [final host receipt](../verification/android-pointer-oracle-repair/host-review-3/receipt.json)
binds all 42 executed tests and source bytes. The earlier 37- and 39-test passing
receipts remain intact. Historical runner freezes retain exact earlier source
bytes for the action-boundary correction and later worker-order/predispatch
checks. These freezes supplied no native evidence. All build, test and replay
scratch, Python compile cache, and owned command groups were cleaned after
membership/identity and empty-holder checks; receipts preserve the commands,
tool hashes/versions, outputs, source context and cleanup outcomes.

The build records repository revision `d4909e275df7e757a5218cc0a88112f4fc3f088b`;
later host/replay checks record disjoint root checkpoint
`11133e60551c46c9ea3aa4eac7356ea32d44fc72`. Frozen source content and live unchanged
native/SDK bytes remain the native input authority. Disjoint hosted or tracker
commits do not change that closure.

The runner preserves the accepted owned AVD/PID/group/5586–5587/tool checks,
serial-only targeting, Wi-Fi boot flag, read-only/no-snapshot mode, bounded
outputs, installed APK hash check and unconditional owned instance/extraction
cleanup. Before its first native command, it rechecks frozen source/APK bytes,
local packaging, official zipalign and the exact debug signing certificate.
Immediately before installation it repeats source/APK, packaging, official
zipalign and signature checks.

After root accepts the repaired source, runner and host packet, root alone may
execute the frozen command:

```sh
python3 -B verification/android-pointer-oracle-repair/run.py --build candidate-5 --attempt runtime-1 --execute-native
```

This command has not been executed here. Its output is exactly
`verification/android-pointer-oracle-repair/runtime/runtime-1`. Only the
designated `runtime/` subtree is excluded from immutable host packet membership;
path escapes, reused attempts and symlinks reject. Every runtime attempt gets
its own complete recursive seal, and root can replay the unchanged host packet
before and after the run. Host test outcomes authorize no native dispatch.

Physical phones remain disconnected/deferred. Native pointer delivery and
widget behavior, real system IME, accessibility, broader lifecycle, shared design
parity, public V2/signed OTA, immutable published FieldLog packages from a separate
repository, store/customer/operational evidence and accountable GA acceptance
remain pending.
