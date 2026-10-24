# Android keyboard fixture export review

The completed Android emulator run has a full passing native component export. This packet independently accepts that immutable export with a separate corrected offline collector. The original runtime receipt remains `failed-native-attempt-retained` with `ValueError('native mode trace exact schema')`; its bytes, raw JSON, instrumentation log, screenshots, APK and producer packet are unchanged. Root independent acceptance and product integration remain pending.

The selected producer seal is `4c3c59761c0b13a0376b7d0c2ecd1de11b2dc2b87a58c746026899452492bd36`. The completed `runtime/runtime-1` artifact seal is `d94c3610872f155124827cda0eb74d08554f9984a7b7fafdc9f98ebb8350f7af`. The native export is 255,787 bytes with SHA-256 `77a7d2c18a5296f6a040d1853073f15216fb9bbf0f54a01f0815905eedf6a017`, matching the instrumentation-declared export hash and the raw export command output.

`ScrollTraceBuffer.add()` copies each row and adds `sequence = rows.size()` before storing it. Both `keyboardTrace` and `keyboardModeTrace` use this serializer, and the instrumentation exports both snapshots directly. The frozen oracle omitted `sequence` from both exact row schemas. The actual native mode trace contains sequence `[0]`; the fourteen Activity key hook rows contain `[0, …, 13]`. The mode row is checked first, explaining the retained outer failure. The pre-runtime host controls fabricated rows without the serializer field, so their 101 passing checks did not detect this mismatch.

The separate correction changes exactly three sites in the sealed oracle: add `sequence` to the key row schema, add it to the mode row schema, and require each array's sequence values to be actual integers equal to their zero-based position. Booleans, floats, missing values, nonzero origins, gaps, duplicates, reordered rows and arbitrary extra fields fail. No raw fields are stripped. Reversing those three substitutions recovers the complete original collector and all original predicates byte for byte. The finite derivation, generated collector, adaptation receipt and exact diff are retained in `verification/android-toggle-keyboard-export-review/review-1/`.

| Observed native evidence | Count |
| --- | ---: |
| Original component cases, exact order and outcomes | 45 |
| Original assertions | 213 |
| Scroll setup assertions | 6 |
| Keyboard setup assertions | 20 |
| Total native assertions | 239 |
| Fixture-counted MotionEvents | 118 |
| Separate known historical MotionEvent | 1 |
| Separate navigation setup keys | 8 |
| Actual Activity key hook rows | 14 |
| Actual window touch-mode transition rows | 1 |
| Focus observations | 32 |
| Ordinary native Button focus controls | 4 |

The offline replay supplies only the five exact retained result/screenshot reads to the unchanged `collect()` function. It executes no argv. All 45 original case predicates, proposal and fixture-acknowledgement counts, assertion classification, MotionEvent accounting, native terminal status and export hash, four PNG exports and bounds, source/APK identities, original focus assertions, keyboard mode transition, exact key request/delivery times, focus owners, unblocked ancestors, unchanged toggle geometry and focus policy, removed controls, quiet input state and zero trace loss remain required. Case 40 begins in touch mode and has a matching native transition plus the actual navigation UP; the subsequent three helpers have actual DOWN and UP hook pairs. The existing allowance for a framework-consumed DOWN therefore has the same strict native evidence as before.

The review runs the original 101 source/export controls and 269 independent checks including 160 rejection controls against the actual completed native export. It reproduces the exact original collector failure. It also rejects the actual earlier 39-case failed export and verifies that the frozen finite two-counter adapter exposes its original `java.lang.AssertionError: native focus admitted`, rather than converting that attempt into a pass. Every original case outcome is independently corrupted and rejected; controls also alter key delivery, native mode, focus/geometry, counters, identity, native status, export binding and screenshot availability.

The independent audit recomputes source closure `92a4f1bab5bf9ae0f61437473002c58efb7f69c137b082c8edfc9766c01472ff` from the exact compiled source snapshot and production closure `509ef6a00bbaf034ebbe9dd6d8d3b8716fe96d9600e7fe8fa92fac41ebca3f99`. The recorded source revision is `18378bb802259a86dff43d31bf881a6d171bb8f0`; the closure is a canonical input-manifest digest, not a Git tree. The retained private APK hashes to `91f8b350d497fe38050ff187c261a23677026e29bf054de2b30aa17b1e3f1fdb`. Its exact 26 ZIP entries, nine fixture classes/DEX archive, 159 unchanged product classes and eighteen unchanged native libraries agree with sealed inventories. Preinstall and predispatch identities agree with the installed APK hash. The sealed official APK verifier logs report v3 verification and certificate `3bed8ee0fb1c2edd8ee0df192fb931bac4fc86fef7a01e63bea7773b6048ffb2`; this review verifies those log/APK/certificate bindings without rerunning native tools. Tool hashes, versions, commands, full outputs and source snapshots are recorded.

The actual environment is Android API 37, `sdk_gphone64_arm64`, fingerprint `google/sdk_gphone64_arm64/emu64a:17/CE2A.260420.019/15611780:userdebug/dev-keys`, using the owned read-only, no-snapshot `megpt-parity-api37` emulator at port 5586. The retained cleanup stopped that owned instance, emptied its command group and released ports 5586/5587. Its 173,064,117-byte extraction was removed after an empty open-holder result and is still absent. This review creates no native instance, queries no live native processes, uses no CUA or Git, and removes its own temporary offline replay/control directories.

The retained supplement contract contains historical reset-fixture package and `native-NOT-RUN` preparation strings. Actual runtime authority comes from the selected manifest, bound instrumentation argv, installed APK identity, native export and completed receipt; those consistently identify `dev.mixer.android.authoredtogglekeyboardfixture`. Historical preparation metadata has not been rewritten.

Root can inspect the three-site diff and reproduce the sealed audit without any native command:

```sh
python3 -B verification/android-toggle-keyboard-export-review/check.py
```

A fresh fully recorded offline test/replay attempt, if needed, is:

```sh
python3 -B verification/android-toggle-keyboard-export-review/verify.py --attempt review-2
```

This establishes component export acceptance for the completed emulator run. Screenshot pixel acceptance awaits root visual review. Physical phones remain disconnected and deferred; TalkBack service workflows, Apple parity, renderer/engine authority, immutable published FieldLog packages, store, operational and GA gates remain unverified. Fixture acknowledgements and null raw checked-listener counters do not establish authoritative engine commits.
