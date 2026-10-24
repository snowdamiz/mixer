# Android coordinator Switch click instrumentation correction

The immutable original attempt is
`verification/android-coordinator-wifi-runner/runtime-1`: its guest boot and
installed APK identity passed; 26 checks passed, and check 27 failed because the
test required `Switch.performClick()` to return true. The failure remains failed
and is hash-bound by the new runner.

Android documents the return value as whether an assigned `OnClickListener` was
called, separately from checked-state changes. See the official
[CompoundButton.performClick reference](https://developer.android.com/reference/android/widget/CompoundButton#performClick()).
The production `NativeSwitch` uses the checked-change listener, without a custom
`performClick` override or a click listener. The corrected verification source
records `hasOnClickListeners()` immediately before the actual `performClick()`
invocation and records its return. It checks that these agree. No dummy listener
is installed. Every following revision-plus-one, checked state, surviving native
view identity, contained-failure, and exported packet assertion remains exact.
All eight original operations remain exact.

`verification/android-coordinator-click-fixture/candidate-1` is a separately
frozen test-only derivative of original candidate-2. It retains 105 input paths;
104 inputs are byte-identical. The instrumentation source is the sole corrected
input and its complete diff is retained. The builder removes the whole original
instrumentation class family before compiling that source alone with Java 17
against the frozen production classes and Activity class. It re-D8s those classes,
repackages the original manifest/resources/native libraries/assets, aligns to
16 KiB, and signs with a fresh disposable test key. The private key is deleted in
`finally` and is absent from retained artifacts. No production source or engine
is rebuilt.

Observed derivative identity:

| Item | SHA-256 |
| --- | --- |
| APK | `9b87cd52a1f0eaa82ac23c7bd26c22b1c116cf54d782aac1e7ec0fd5e6924b63` |
| compiled archive | `feaa639b8b719492c5889222246cb62ebd4e9dd807379ccd984c5062f60660a4` |
| derived source closure | `00c269c70199ffb376b39394db1c2367f8e9053d92ce6a863741d2a154359c04` |

The artifact delta has exactly three changes among 177 artifacts:
`CoordinatorJoinInstrumentation.class`, `dex/classes.dex`, and the APK. All
production classes, 18 native libraries, and the Activity class are unchanged.
The APK entry delta changes `classes.dex` and the three `META-INF` debug-signature
entries. The other 22 APK entries, including the manifest, resources, descriptor,
and eight-operation fixture, are identical. The independent artifact verifier
streams the retained archive and checks every file and APK entry hash.

The build receipt retains commands, outputs, tool versions/hashes, revision/tree,
source derivation, signature verification, and alignment checks. Its owned scratch
was removed after an empty `lsof +D` holder check: 180 files, 345,794,681 bytes.
This is development test signing, with no publication or release authority.

The separate runtime wrapper derives from the accepted Wi-Fi concrete runner
`6ac0d6a88d4df6058349cc29205ea1b517009d38be011858ee1fc358e577c406`.
Eight exact replacements change only build directory, source/archive/metadata
bindings, selected build name, and explanatory labels. The concrete source and
diff are retained under `runner-source/`. All runtime assertions, packet exports,
process-local `-feature -WiFiPacketStream` fallback, exact hash-bound executable
and PID/PGID guards, and owned-extraction cleanup remain inherited. The accepted
console/ADB port limitation (5586/5587 beyond installed help's recommendation)
remains explicit. Existing output attempts cannot be overwritten.

Host tests run the actual transformed runner with synthetic SDK operations and
synthetic child objects, plus real host extraction/process guard tests. Four
accepted cleanup-test build labels change from candidate-2 to candidate-1;
their guard conditions remain inherited. Host results and archive checks do not
qualify Android runtime behavior.

After reviewing the frozen host packet, root alone can dispatch:

```sh
python3 -B verification/android-coordinator-click-fixture/run.py \
  --build candidate-1 --attempt runtime-1 --execute-native
```

Fresh Android native assertions are pending. Physical phones remain disconnected
and their final matrix is deferred. Full native fault/IME/lifecycle qualification,
public/signed release, immutable external FieldLog, store, customer, operational,
and GA acceptance remain pending. The instrumentation correction grants none of
those acceptances.
