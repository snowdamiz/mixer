# Android authored toggle candidate runner

This lane prepares a separate root-dispatch runner for the frozen candidate-3
baseline APK and supplement-3 component APK. Native execution is **NOT RUN** by
this host packet. The predecessor candidate-5 failure and the root review's first
helper-hash transcription failure remain historical evidence. No product, fixture,
tracker, Git state, native instance or physical phone was changed by this lane.

The runner derives explicit new concrete source from the reviewed
`android-pointer-timing-correction/run.py` loader and its SHA-256-bound
`bd7cd16883a831aac29fa13d162eabf6fae78c88c6b523919e4d9b38c0103b31`
concrete source. Each finite replacement has exact occurrence counts and before/
after hashes in `runner-contract.json`, retained concrete source and a diff.
This is changed runner source and changed product source; `sourceUnchanged` is
explicitly false. Old build pins remain immutable in their original wrapper.

The candidate source authority is the 106-input closure
`509ef6a00bbaf034ebbe9dd6d8d3b8716fe96d9600e7fe8fa92fac41ebca3f99`.
`sourceTree` carries that content SHA-256, explicitly not a Git tree. Root verified
Git revision `18378bb802259a86dff43d31bf881a6d171bb8f0` is contextual only;
the candidate was produced against contextual predecessor
`8c634c49fa701c27b975789b15c0aabff3f047d6`. Binding all changed/added sources is
separate from checking the 88 unchanged live baseline native/SDK inputs. The two
changed native Java inputs and new policy input are never compared to live bytes
as if unchanged. Root must run this pre-integration packet while that baseline
remains unchanged; a later integration needs a separate truthful content contract.

Before any native command and again before installation, the runner rechecks the
exact producer seal of 555 files, candidate/supplement source identities, all 183
artifact bytes, tool identities, 18 libraries, descriptor and fixture identities,
packaging, and official zipalign/apksigner certificate checks. It assembles the
183 artifacts from the exact 179-member predecessor archive plus the frozen
candidate overlay and selected APK. Supplement APK decompression verifies the
retained gzip and exact uncompressed identity. Complete artifact allowlists exist
before extraction and govern strict cleanup.

The baseline uses the byte-identical original 20-action Java/asset fixture and
unaltered worker injection schedule. It inherits the corrected F01–F07 oracle
byte-for-byte; only duplicate JSON-key rejection changes result decoding. Native
state, packet and timing assertions keep their original authority and limits.
The original callback count remains explicitly unobserved. No control convenience
path replaces the actual instrumentation entry point.

Both variants retain the owned-process helper, 32 MiB runner log budget with
cleanup reserve, literal safe exports, fresh contained `runtime/runtime-N` paths,
read-only API37 arm64 AVD, ports 5586/5587, exact API37 fingerprint, signature/
alignment checks before dispatch and installation, installed APK hash, and
identity-checked emulator/extraction cleanup on all outcomes. Each invocation
owns at most one emulator. Baseline and component runs are separate invocations;
finish and inspect cleanup before another run. Global adb discovery and physical
phone commands are absent. Other projects' instances are preserved.

The independent host review freshly compiles four supplement classes against the
same 159 byte-verified production classes, replays exact DEX bytes and checks the supplement's
manifest/resources/descriptor/18 libraries/signature/alignment. It also freshly
runs all 55 predecessor controls and the new runner/component negative controls.
These fabricated host results do not qualify Android input behavior. The host
review also materializes and hashes both exact 183-artifact payloads. Host-1
retains a failed manifest-reference lookup and complete cleanup; later successful
passes retain their source snapshots and commands, including superseded runner
control versions. Only the latest sealed matching pass qualifies this packet. Seal-1 retains a
failed second replay caused by an ancestor import alias collision. The corrected
loader restores all generic ancestor aliases after the entire load, and a fresh
23-control pass verifies repeated new wrapper/component imports keep the owned
support module. The original corrected oracle and concrete native cleanup
source remain unchanged.

The supplement uses actual `NativeAppearanceViewsV2.Record`/`Switch`, native
keyboard and accessibility calls, direct `View.onTouchEvent` for most gestures,
and worker `sendPointerSync` for the two native ScrollView arbitration cases.
Its `Input` is a component fixture. Ordinary proposals are counted there directly;
fixture binding acknowledgements are never authoritative engine commits, and raw
checked callbacks/authoritative commit fields stay null. Its exact 45-case matrix, counters, native JSON hash and four literal PNG exports
are validated separately. The exported fixture counter covers direct touch
observations plus 18 worker `sendPointerSync` requests. One separately constructed
historical MOVE is outside that fixture counter; the oracle explicitly adds it
and requires the resulting constructed-event total to remain at most 512. These
are component construction/request counts; this supplement has no Activity
delivery log. A declared 511 plus that event is permitted; declared 512 rejects. The PNG bytes are host-bound after extraction; pixel acceptance needs
root visual inspection. Window-focus loss is an invoked native callback, not an
OS focus transition. Focus order uses `focusSearch`, not an observed Tab workflow.
Disabled native keyboard behavior and renderer authority lifecycle cases beyond
the baseline remain pending.

Root-only dispatch after independent acceptance:

```sh
python3 -B verification/android-authored-toggle-input-runner/run.py \
  --build candidate-3 --attempt runtime-1 --execute-native
python3 -B verification/android-authored-toggle-input-runner/run.py \
  --build candidate-3 --supplement supplement-3 --attempt runtime-2 --execute-native
```

Read-only host packet replay:

```sh
python3 -B verification/android-authored-toggle-input-runner/verify.py
```

Native baseline/component behavior, screenshot pixel review, renderer lifecycle
and overflow authority beyond baseline, TalkBack service workflows, disconnected
physical phones, Apple parity, public/signed transport, immutable packages consumed
by separate-repository FieldLog, store/customer/operational and accountable GA
acceptance remain independent pending gates.
