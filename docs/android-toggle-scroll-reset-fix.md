# Android toggle scroll fixture reset correction

This is a fresh private fixture candidate. Host checks do not accept the original 45 native cases. Root must run the frozen candidate and review zero offset, visible owned input endpoints, native interception/CANCEL and every original assertion. Phones remain disconnected and deferred.

The immutable extent-fix packet seal is `233f2a713571621e48e07cab2e6e2678545bb1fb64830ca77b32ebeb95bc9ace`. Root's bound review records case 18 passing with content height 6000, viewport 2622, one actual ScrollView interception, one child CANCEL, scroll offset 365, zero proposals and no pressed state. Case 19 started at offset 365 despite `scrollTo(0,0)`. The toggle screen top was 35; its original DOWN at screen y=101 was inside the actual 132px status bar. Targeted UID injection rejected it before the Activity or child received it. The source of the offset rebound remains unobserved.

Reset now cancels the old record, removes its view from its actual parent, clears old content, and replaces the private ScrollView/content with fresh instances. This also handles the original parent-rebinding case, where the old view may be attached directly to the fixture root. The new content retains minimum height 6000, and the original child frame, root/scroll sizes and placement remain unchanged. No reflection, synthetic CANCEL, input target/privilege bypass or additional sleep is introduced.

Before each original scroll injection the fixture records actual geometry and the exact first/last points, then separately requires positive measured extent plus `canScrollDown`, zero horizontal/vertical offset, and visible owned input. Owned bounds intersect the actual window-visible screen frame, root's visible screen rectangle and decor screen bounds inset by actual system bars. The first point must also be on the visible toggle. Unknown insets, detached/unfocused/hidden views, empty bounds and out-of-area endpoints fail closed. Both endpoints being in the rectangular area also contains the unchanged linear event path.

All original 45 case bodies, their assertions, the combined positive-scroll/zero-proposal/not-pressed assertion and all nine event actions, coordinates, timestamps and injection schedule are exact. There are three separately classified setup assertions per scroll case (cases 18/19), six in a complete 45-case run. The native result exports `addedSetupAssertions` and `originalAssertionCounter = assertions - addedSetupAssertions`, including attempted setup assertions on failure. This replaces the extent packet's one setup assertion per scroll case; do not subtract both sets. All 159 production classes and 18 native libraries remain byte-identical.

`stage_sources.py`, `source-adaptation.json`, `fixture-source.diff` and `contract-source.diff` describe finite adaptations from the sealed extent packet. The two independently authored sources are bound in `authored-source-bindings.json`: a pure rectangle helper and its host controls. The source closure and `supplement-1/source-used` bind/retain exact fixture/build inputs plus the frozen production closure. Frozen upstream production archives are reused by hash instead of copied. `analysis-1` binds the selection and previous failure. `supplement-1` retains one gzip copy of exact final APK bytes, the class/DEX archive, inventories, tool identities, commands and official signing/alignment/packaging output. The disposable debug key is deleted; no release key is used.

Host replay requires exact fresh fixture-class and DEX equality, unchanged production/library inventories, signature/alignment checks, failure forwarding, bounded trace storage, input bounds controls for the observed status-bar failure and original linear paths, finite source replay and deliberate invalid mutations. Exact owned-directory identity and no-open-holder checks precede scratch deletion. Fresh attempt directories preserve failed receipts/logs. Native receipt/export and emulator cleanup remain root's responsibility through the inherited bounded runner.

Read-only packet check, with no scratch, subprocess, native or Git calls:

```sh
python3 -B verification/android-toggle-scroll-reset-fix/check.py
```

Root-only native invocation after packet review:

```sh
JAVA_HOME=/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home \
  python3 -B verification/android-toggle-scroll-reset-fix/run.py \
  --build candidate-3 --attempt runtime-1 --execute-native
```

Omitting `--execute-native` refuses dispatch before runtime directory creation. The wrapper changes only package, fixture closure and status in the exact upstream concrete runner; it retains the entire failure/owned-emulator/extraction cleanup tail and finite hash-bound trace export. Runtime attempts are outside the finite host packet seal and need separate root sealing/review. Preparation ran no adb/emulator/CUA/physical-device/Git commands. Full native acceptance, physical phones, TalkBack, live renderer/engine authority, Apple parity, public transport, separately published FieldLog packages and operational/GA gates remain pending.
