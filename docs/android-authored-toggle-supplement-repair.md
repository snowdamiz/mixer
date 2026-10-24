# Android authored toggle isolated fixture repair

This packet repairs private supplement failure reporting and prepares a new
root-only diagnostic dispatch. Native execution is **NOT RUN** by this lane.
It provides no product acceptance and does not diagnose the earlier process
crash. Frozen supplement-3 reported `shortMsg=Process crashed` and code 0;
its missing JSON and 69-byte failed cat export do not establish a product cause.
The frozen producer, original runner, previous runtime receipts, and root's
successful original 20-action baseline review remain immutable.

The source repair changes the private fixture's main-thread dispatch so an
assertion is caught on the main thread and rethrown on its waiting worker.
The original Error/RuntimeException object is retained. Cleanup, result export,
and a separate diagnostic export are each attempted independently. A cleanup or
export failure is suppressed on the original failure rather than replacing it.
The diagnostic file contains the original stack and suppressed failures. Its
SHA256 is declared by instrumentation and checked against the finite run-as pull.
The successful native JSON schema and original component oracle remain unchanged.

All 45 case bodies are byte-identical. Callback/input state, assertion and event
counters, direct View touch observations, eighteen worker sendPointerSync requests,
and the separately constructed historical MotionEvent retain their original
semantics. Fixture acknowledgements still imply no engine commit; callback and
authoritative commit fields remain null. The Activity source is byte-identical.
The new helper is private fixture plumbing, not product engine source.

The new private package is `dev.mixer.android.authoredtogglerepair`. Candidate
`supplement-1` retains its exact APK once as gzip, with uncompressed SHA256
`919a819e42e9b3d5d530a85837b8e00bf986aab47ae01eaa99a1adde3b47d980`.
Its source closure is
`8ead95069a3538043749cf4574185c6271c8e900be02b65daee312b34f3c68e9`.
The content closure is not a Git tree. Its immutable source-used directory
includes the actual build/support sources used when that APK was built.
Later runner support code has its own explicit implementation bindings.

Host-1 freshly compiles the exact five fixture classes, compares all bytes to the
retained class archive, reruns D8 against unchanged production class bytes and
requires exact DEX reproduction. It compiles and executes the exact failure
helper with a synthetic separate main thread: original assertions return to the
worker without escaping, cleanup/export failures remain suppressed, and later
export work still runs. Python controls check unchanged case bodies and cleanup,
finite new source/package identities, unsafe paths, independently attempted
capture after an earlier diagnostic fails, owned serial scoping, process identity
refusal, and correct/wrong instrumentation diagnostic hashes. These are host
controls, not Android behavior receipts.

Composition checks require all 159 production classes and 18 native libraries to
remain byte-identical. The five fixture classes, DEX, private manifest/contract,
and private APK/signature comprise the permitted changes. Descriptor and resources
remain unchanged. Official aapt2 manifest inspection, apksigner verification and
16 KiB zipalign checks pass. Temporary debug keys are deleted. Build scratch
cleanup removed 187 files / 345930973 bytes; host replay scratch cleanup and every
owned command group's empty final state are recorded in their receipts. No Git,
physical target, simulator, emulator, CUA, or screen-capture command was executed.

The diagnostic runner derives concrete source from the exact original frozen
supplement runner, using three explicit once-only source replacements: package,
new fixture closure, and instrumentation/diagnostic collection block. Source
before/after hashes, retained concrete source, and its diff are bound in
runner-contract.json. The original emulator/extraction cleanup tail is
byte-identical. Old pins stay intact; upstream 555-file producer and 247-file
runner seals are rechecked. Before dispatch and installation the new source/APK,
184-artifact payload, tool identities, signature and packaging are checked.
The extra fixture helper accounts for the increase from 183 to 184 artifacts.

Diagnostic capture runs in finally around instrumentation and component export,
before emulator cleanup, including a failed instrumentation result or export.
It first rechecks exact owned process/PID/AVD/port identity, then independently
attempts the owned emulator crash buffer, main/system/crash log tail, and literal
private diagnostic file. Each command has a 15-second timeout, owned command
group cleanup, output hash and bounded retained tail. Diagnostic failures are
recorded without replacing the original runner failure. The diagnostic retained
budget is 2236416 bytes, separate from the inherited 33554432-byte runner log
budget and its cleanup reserve. Truncation is explicit. Missing diagnostics are
not accepted as successful capture.

Read-only packet verification:

```sh
JAVA_HOME=/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home \
  python3 -B verification/android-authored-toggle-supplement-repair/check.py
```

Root-only dispatch after root review:

```sh
JAVA_HOME=/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home \
  python3 -B verification/android-authored-toggle-supplement-repair/run.py \
    --build candidate-3 --attempt runtime-1 --execute-native
```

The runtime subtree is explicitly excluded from the frozen packet seal. Each
invocation requires a fresh contained runtime-N directory and owns at most one
read-only API37 arm64 emulator on ports 5586/5587. Existing instances are refused;
only the process it creates can be stopped. The frozen original runner's AVD,
WiFi argument, fingerprint and cleanup rules remain in effect. It must run while
the original unchanged live baseline88 inputs still match, before integrating the
frozen candidate production sources.

Component behavior, screenshot pixel acceptance, additional renderer authority,
TalkBack service workflows, physical phones, Apple parity, public/signed
transport, immutable packages consumed by separate-repository FieldLog, stores,
customer/operational checks and accountable GA acceptance remain pending. The
root's original baseline pass is separate evidence and is not repeated or widened
by this host repair packet.
