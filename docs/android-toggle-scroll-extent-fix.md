# Android toggle scroll fixture extent correction

This is a private fixture correction candidate. Host build and replay receipts do not accept the 45 native cases. Root must run the candidate on its one owned API 37 emulator and review the exported positive extent, interception/CANCEL trace and all original assertions. Phones remain disconnected and deferred.

The original frozen diagnostic packet is `verification/android-toggle-scroll-failure-analysis/packet-seal.json`, SHA-256 `165707429ecda4f075b995508be9a16f0e87c3f013b8820138480128b6d000ef`. Its failed runtime and root review show requested content height 6000 measured as 532 in a 2622 viewport, `canScrollDown=false`, all nine original events delivered to the Activity and child, and no native intercept/CANCEL. The source sets a child layout height but no minimum. The correction sets `content.setMinimumHeight(6000)` on the fixture FrameLayout and requires both measured and laid-out content heights to exceed a positive viewport, plus `canScrollVertically(1)`, before injecting a scroll gesture. Runtime measurement is the authority for whether that setup succeeds.

All 45 original case bodies/assertions, the combined positive-scroll/zero-proposal/not-pressed assertion, and nine original events, coordinates, event timestamps and injection schedule are unchanged. Public observer hooks and failure forwarding remain intact, including the non-consuming child listener and actual ScrollView interception trace. The explicit setup assertion adds one check per scroll case (cases 18 and 19), exactly two added checks in a complete 45-case run; subtract those two only when comparing the full original assertion counter. No product code changes: all 159 production classes and 18 native libraries must match their frozen inventories. The new private package is `dev.mixer.android.authoredtogglescrollextentfix`.

`stage_sources.py` and `source-adaptation.json` describe the exact finite upstream adaptations. `fixture-source.diff` includes the adapted fixture/build/replay source differences; `contract-source.diff` records the metadata changes. `analysis-1` binds the prior failed evidence. `supplement-1/source-used` retains the exact fixture/build inputs; the source closure also binds the frozen production closure. Frozen upstream archives are referenced and hash-checked instead of copying their production payloads. `supplement-1` retains the single gzip copy of exact final APK bytes, class/DEX archive, inventories, official signing/alignment/packaging checks, commands and tool identities. The disposable local debug signing key is deleted. No release signing keys are used.

Host verification rebuilds the fixture classes and DEX from source and requires exact equality. It runs failure-preservation and bounded trace-buffer controls, finite source replay, mutations that remove/alter the correction/protocol/assertions, and serial/process/hash/truncation trace controls. Build/replay scratch cleanup checks exact owned directory identity and empty command groups. Failed attempts retain their receipts/logs; fresh attempts never overwrite prior evidence.

Read-only packet check (no scratch, subprocesses, Android commands or Git):

```sh
python3 -B verification/android-toggle-scroll-extent-fix/check.py
```

Root-only native invocation, after review and within the existing bounded emulator ownership/cleanup policy:

```sh
JAVA_HOME=/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home \
  python3 -B verification/android-toggle-scroll-extent-fix/run.py \
  --build candidate-3 --attempt runtime-1 --execute-native
```

Omitting `--execute-native` refuses dispatch before runtime directory creation. The wrapper derives only package, fixture closure and receipt status from the sealed upstream concrete runner. It preserves the complete failure/owned-emulator/extraction cleanup tail and finite private trace export. Runtime attempts live outside the finite host packet seal; root should seal/review them separately. No emulator/adb/physical target commands were run during candidate preparation. Simulator/emulator acceptance, physical phones, TalkBack, real renderer/engine authority, public transport, separately published FieldLog packages, operational and GA gates remain pending.
