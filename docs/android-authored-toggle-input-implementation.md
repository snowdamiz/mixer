# Android authored toggle input — isolated implementation candidate

The root-selected [input contract](android-authored-toggle-input-contract.md) is
implemented in copied production sources under
`verification/android-authored-toggle-input/candidate-source/dev/mixer/android/`.
No live product source, coordinator schema, tracker, Git state, emulator, phone,
or UI was changed by this lane. Native execution remains **NOT RUN**. The old
candidate-5 P03 failure remains immutable evidence; a new source/APK identity does
not turn it into a pass.

The selected build is `candidate-3`. It passes 33 executable host tests against
its actual production policy class bytes, fresh Java 17-target/SDK37 compilation,
D8 and private debug APK packaging/signature/alignment checks. The separate
`supplement-3` APK also builds, using the exact same production class bytes. Its
native assertions and screenshots have not executed. Neither packet grants
native dispatch or product acceptance authority.

| Identity | SHA-256 |
| --- | --- |
| Root-selected contract | `df0aa5c7641c14d080906210270552a4ac69beda08ec188b16d37db458fd0828` |
| Baseline candidate-5 source closure, 105 inputs | `9082e2de1327bd0784d752db5dfbe4484751d565b3410e01e78664321467f5ce` |
| Baseline candidate-5 APK | `57e82e4e98cdc61581c0639603ec6efa500a66d8d2754f6b47ece89c8165d714` |
| Authored candidate-3 source closure, 106 inputs | `509ef6a00bbaf034ebbe9dd6d8d3b8716fe96d9600e7fe8fa92fac41ebca3f99` |
| Authored candidate-3 baseline-fixture APK | `24d75ecc19d08f44adc95e2db123936687929ca5a9fcd71f19189865240f6d18` |
| Supplement-3 source closure | `12fc0156b7689bcf0718c404b80471e707633d93ba44196184fd68b358c5306f` |
| Supplement-3 executable APK | `96e9e790e89d8fcc0681499ba7baf4d40af20a432384e720ab43b3d7fbc1189b` |
| Supplement-3 gzip retention | `433cd47805a66ac51f194c7507acf6467f36c452f7b8b06f9f771eaeac89127c` |

## Bounded production delta

`AuthoredToggleInputV2.java` is new independent production policy. It has no
Android dependency, library dependency, framework implementation, JNI call, or
feature envelope. Its geometry uses the existing checked coordinate conversions
and authored `thumbOrigin` function: 63×28 track, 37×24 thumb, 2/24 origins and
22-unit travel. The exact drawing origin/rounding and centered 63×44 carrier are
shared by draw and touch. The release corridor expands vertically by 22 units
per edge, independent of a taller row. Unsupported metrics, empty frames or
invalid density are rejected; no minimum travel or widened hidden range exists.

The helper holds a constant-sized pending/drag/draining/idle state. It processes
stable pointer IDs and chronological samples, strict native slop/dominance,
full DOWN displacement including the crossing sample, continuous clamped logical
fraction, tie-to-initial endpoint selection, label taps/holds and cancellation.
It contains the actual latest-binding reconciliation function used by the native
adapter. Host tests import these production bytes; they do not import a second
contract model or Android substitutes.

`NativeAppearanceViewsV2.java` retains the real `Switch`, native checked listener,
accessibility role/state and superclass click/key/accessibility services. Touch
never calls `Switch.onTouchEvent`. DOWN/MOVE only update local policy, paint and
the existing native interaction epoch; no ordinary event/JNI/reducer callback is
issued there. The checked value stays committed during preview. Terminal touch
clears state and releases the exact acquired parent before rechecking binding
identity and existing `Input.open`, then proposes through one ordinary
`performClick` if its side changed. The existing checked listener is the only
ordinary `valueChange` proposal path.

`performClick` cancels a held touch and restores any native/binding discrepancy
against the latest binding in `finally`, under the preserved changing guard.
Constructor-time callbacks are null-safe. Equal binding replacement cancels,
and frame/parent/lifecycle/disabled/focus/visibility changes clear transient
state. Keyboard cancellation only clears an active touch before native key
handling; an idle key UP preserves the native pressed state established by its
key DOWN. This avoids the superseded candidate-2 keyboard hazard.

`NativeRenderer.java` closes gates before synchronous toggle cancellation at
environment invalidation, attachment, rollback and retirement. Cancellation is
idempotent over overlapping live/target/detached records. Rollback explicitly
clears toggle transients after restoring journal pressed values. Existing
`Input.open`, interaction epoch, coordinator transactions, wire schema and all
engine/reducer ownership remain the admission/commit authority. The overflow
path can retire during local interaction; the adapter rechecks its fence before
mutating preview after that call.

Only these three production source inputs change. Recompilation changes 20
production class artifacts within the assigned families: four new policy
classes, `NativeRenderer.class`, and fifteen appearance-family classes. The
appearance-family recompilation includes shifted source-line/debug metadata for
otherwise unchanged nested classes. The artifact delta names every class.
Unchanged baseline fixture classes are freshly compiled against the new
production classes and remain byte-identical. DEX and the private APK are also
new. APK entry changes are exactly `classes.dex` and the three private debug
signature entries; original manifest/resources/assets/operations and all 18
arm64-v8a native/Swift library payloads remain byte-identical.

## Host and build evidence

The tools are the pinned official OpenJDK 25 compiler with `--release 17`, SDK37
`android.jar`, Android build-tools 37.0.0 D8 (`--min-api 36`), aapt2, zipalign and
apksigner. This is Java 17 target compilation, not a claim that a JDK17 compiler
binary ran. Source/tool hashes, tool versions, complete argv/cwd/output and owned
process-group cleanup are retained in each build receipt. No runtime API is
qualified by compilation. No new general-purpose dependency was added.

The 33 host tests cover five densities, both directions and starting sides,
authored endpoint conversion, unchanged P03 schedule, crossing MOVE distance,
strict slop/dominance, midpoint/epsilon, velocity-independent selection, clamp
and return, corridor edges/epsilon, taller rows, label hold/drift, pressed
leave/return, invalid geometry/input, pointer loss/extra pointers, chronological
history, binding/coherence, drain cancellation, latest restoration, guarded raw
callback suppression and replacement isolation. The fake checked-binding used
to exercise the production reconciliation function is a host fixture, not an
Android checked-listener observation.

`upstream-controls-2` replays all 55 unchanged synthetic oracle/wrapper controls
(42 prior and 13 timing correction tests), retaining F01–F07 fail-closed guards.
It starts no Android instance. In particular, MOVE-only-in-terminal-history and
delivery outside the worker/current-event interval still reject. Original
runner/oracle sources are unchanged; these controls do not authorize the new
APK or substitute for its root-selected runner.

Read-only replay:

```sh
python3 -B verification/android-authored-toggle-input/check_packet.py \
  --candidate candidate-3 --supplement supplement-3
```

This checks exact recursive attempt seals, source closure, original fixture
bytes, class/dex archive membership, exact retained APK bytes, unchanged entry
and library inventories, packaging replay, and cleanup. It invokes no Git,
Android target, emulator, UI or runtime operation. The original timing-correction
runner intentionally remains pinned to candidate-5; a separately reviewed root
runner must preserve its native timing/oracle/cleanup guards while binding the
new candidate. No `--execute-native` command was run here.

## Separate native supplement

The independent private package is `dev.mixer.android.authoredtoggle`, with its
own Activity, instrumentation and manifest under `native-supplement/`. It uses
an actual production `NativeAppearanceViewsV2.Record`, actual Android `Switch`
and `ScrollView`, native key dispatch, accessibility actions, MotionEvent history
and worker `sendPointerSync` for parent arbitration. Its fixture `Input` counts
ordinary proposals directly and can accept/reject/rebind/close/replace a record.
Fixture binding acknowledgements are explicitly separate from authoritative
engine commits; raw checked-listener callbacks and authoritative commit counts
remain null. The unchanged 20-action ordinary-join matrix retains authority
coverage and cannot be replaced by this component fixture.

The finite supplement includes LTR/RTL endpoint drags, four light/dark preview
screenshots while native/bound checked state stays false, crossing/return/tie,
outside horizontal release, corridor boundaries, held label behavior, native
vertical/diagonal scrolling, history, pointer loss/extra pointer, ACTION_OUTSIDE,
mid-gesture cancellation fences, synchronous latest-binding/retired/replacement
restoration, native accessibility metadata/click/rejection, real key DOWN/UP,
repeat/cancel, focus search and key/AX activation during held touch followed by
old UP. History timestamps are monotonic and history handling must retain an
active pressed preview before its final unchanged-side UP; a rejected sample
cannot silently satisfy that case. The fixture limits are 64 cases, 512
assertions, 512 MotionEvents, four screenshots, 8 MiB export and 120 seconds.
Actual pass counts are unobserved until native execution.

The supplement freshly compiles four private class artifacts against the exact
159 production classes, dexes and packages separately with aapt2. The empty
resource table, descriptor and 18 library bytes match the baseline. The final
86,206,457-byte APK is retained once as a 27,953,782-byte gzip. Root dispatch must
decompress it into owned scratch, verify the uncompressed hash and repeat
signature/alignment/installed APK checks before injection. The APK has not been
installed or launched by this lane.

## Retained attempts and cleanup

| Attempt | Observed result |
| --- | --- |
| `candidate-1` | Production compilation passed; host corridor test incorrectly attempted vertical admission before horizontal ownership and failed. Raw output/source retained; scratch removed. |
| `candidate-2` | 33 host cases/build passed; superseded after source review found unconditional key-event pressed clearing. Exact old source/binary retained; never run natively. |
| `candidate-3` | Final baseline-fixture host/build candidate, keyboard ownership corrected; selected here for root review only. |
| `supplement-1` | Compilation failed because a private helper collided with inherited `Instrumentation.start`; exact source/error retained. |
| `supplement-2` | Component build passed; superseded by stricter history timing/active-preview and parent-release assertions. |
| `supplement-3` | Final component supplement build; native assertions unexecuted. |
| `upstream-controls` | First host replay used a nonexistent review-script path; exact command/error retained. No target command ran. |
| `upstream-controls-2` | Correct review path; 55 synthetic controls passed. |

The historical draft fragment is retained as historical input only; adopt the
frozen candidate-3 source snapshot, not that draft. Every attempt has a receipt,
raw command logs and its own recursive seal. Sealing excludes only that exact
top-level seal path and retains nested receipts/seals. Each extraction has a
unique owned device/inode, no-open-holder check and removal record. Every child
command uses the hash-pinned owned-process helper
`209290a7b3638f7510bb1b88dfcdb272f657b89fffe96dcc2f2b631b8f244216` and records an
empty final process group. No native instance or other project's process was
started, stopped or inspected. Disposable debug signing keys are removed in
`finally` and are not retained.

The original 20-action baseline, actual component supplement, renderer overflow/
prepare/attach/rollback/retirement authority cases beyond that matrix, disabled
native key behavior, TalkBack service workflows, physical phones, Apple parity,
public/signed transport, separate-repository immutable FieldLog packages, store,
customer, operational and accountable GA acceptance remain pending. The phones
remain disconnected/deferred; no reconnect request or physical run was made.
