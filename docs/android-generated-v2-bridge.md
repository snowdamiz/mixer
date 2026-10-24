# Generated Android private staging bridge

The CLI's explicit Android source snapshot now includes the V2 C header and the
internal renderer's Java dependencies. Generated app-owned Swift entry points
forward prepare, commit and abort to the same session registry used by legacy
exchange. The generated Activity continues to use legacy exchange; these exports
do not enable V2 appearance or signed presentation.

The production build driver links JNI with `--no-undefined` and checks the six
ordinary C exports in the generated application library. This prevents a stale
generated entry from producing a successful APK when its JNI closure requires a
missing staging decision. Existing app-owned files are never regenerated or
overwritten by the build command.

Generated session tests exercise aborted state preservation, pending-session
exclusion, abort retry isolation, exact-once commit and subsequent render bytes.
The executable collector at `verification/android-generated-v2-bridge/verify.py`
creates an actual application using a freshly built CLI, runs its host Swift
tests in Debug and Release, and builds an unsigned arm64 API28 APK with the locked
official Android toolchain. It then removes one C export from the app-owned entry
and requires a real JNI linker failure and removal of stale success artifacts.

The first collector run passed those builds and the expected negative link, then
failed its final source guard because `AGENTS.md` changed to record the user's
computer-use pause. That failed receipt and its captured inputs remain retained.
Later renderer changes require their own fresh capture; earlier compile results
do not qualify them.

Candidate 2 was deliberately stopped after review withdrew the Android source
freeze; its interrupted host build remains failed. Candidate 3 captures the
corrected final Java source and passes all ten collector commands, including the
expected missing-export failure. Root acceptance verifies 543 source, log and
artifact bindings. See `verification/android-generated-v2-bridge/acceptance.json`.
The separate independent JNI/CLI source audit found no blocking cleanup or ABI
issue. It grants no native appearance acceptance.

JNI production and separately derived failure tests are recorded under
`verification/android-v2-jni-candidate-bridge/`. Root's fresh replay reproduced
585 production and 199 derived assertions in each Debug/Release and
normal/interpreted JVM combination. This is host execution and cross-compilation
evidence. Native coordinator attachment, Android runtime behavior, the pending
appearance changes, final physical validation and published FieldLog consumption
remain unqualified. Computer use, captures and native runtime tests are paused
by the user's latest instruction.
