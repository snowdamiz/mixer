# Ordinary native appearance V2 staging proposal

**Implementation proposal for root review; no new frozen public API or support
claim.** Product-plan §8.3 and the frozen
[measured appearance contract](ui-measured-appearance-v2-contract.md) remain
binding. This proposes the next concrete native consumers of the accepted Swift
and Java V2 data resolvers and the closed CoreGraphics/Android Path adapters.
It neither narrows the product plan nor authorizes signed V2. Phones remain
disconnected. Physical interaction/parity, immutable published FieldLog packages
from its separate repository, store, customer, operational and GA evidence remain
pending.

## Current owners and the missing transaction

The inspected input closure is retained in
`verification/native-appearance-v2-staging/candidate-1/inputs/`; its manifest and
receipt distinguish source inspection and declaration compilation from execution.

| Concrete owner | Current behavior | Required next change |
| --- | --- | --- |
| `sdk/Sources/MixerUI/Reconciliation.swift` | `UIReconciler` is a value type; `apply` validates and atomically changes that value. | Copy it inside the native owner; do not change its public identity contract to stage native work. |
| `sdk/Sources/MixerApple/MixerNativeView.swift` | `MixerUIHost.update` mutates its reconciler and publishes `snapshot`; `NativeNode` subsequently creates default SwiftUI widgets. | An internal UIKit V2 consumer must stage/attach before replacing its committed native state. Publishing SwiftUI values is insufficient attachment evidence. Keep legacy and signed callers on their existing path. |
| `native/android/app/src/dev/mixer/android/NativeRenderer.java` | `apply` reuses actual records, then mutates controls/listeners/parents before assigning `packet`/`records`. | V2 staging must not call this mutation sequence on live records. Add a separate internal V2 path using the same concrete toolkit objects and a rollback journal. |
| `native/android/app/src/dev/mixer/android/MixerActivity.java` | Calls `NativeBridge.exchange`, then renderer `apply`, then changes root children. | The ordinary V2 coordinator must own engine candidate, native candidate, root attachment and final commit together. |
| `native/android/engine/Sources/MixerAndroidRuntime/DocumentSession.swift` and `SessionRegistry.swift` | Dispatch copies app state/reconciler, but commits the engine once its packet fits the exchange output buffer. | Retain one engine candidate until native staging/attachment succeeds. A Java-only transaction would leave a new engine revision behind an old display after attachment failure. |
| `cli/Sources/MixerBuild/ProjectGenerator.swift`, `AppleProject.swift`, `AndroidProject.swift`, `Resources/android-build.py`, `Configuration.swift` | No ordinary V2 bootstrap; Apple resource build phase is empty; Android rejects Resources and snapshots only its explicit legacy adapter closure. | One serial bootstrap owner must validate/package the same canonical descriptor/resource bytes and opt in explicitly. Merely adding Java files to the repository does not include them in created apps. |

`UIAppearanceResolverV2.prepare` and `AppearanceResolverV2.prepare` remain pure
data admission. `AppearanceNativePathsV2.make` only converts closed geometry.
Neither becomes a native support authority because it is called from a test.
No new abstract renderer, support protocol, style dictionary or app-supplied
capability proof is needed.

## Minimal concrete ownership and proposed internal calls

The following names are proposed internal implementation seams. Root must freeze
the lane boundaries and ordinary bridge change before dependent edits.

* Apple: `AppearanceNativeRendererV2`, a MainActor UIKit container controller,
  owns a stable `UIView` root, a value `UIReconciler`, exact-identity native
  records, one installed capture and its current window environment. Its
  `prepare(document:) throws -> Candidate`, `commit(_:) throws -> UIChangeSet`
  and `discard(_:)` are module internal. `Candidate` has a private constructor,
  is owner-bound and single use. `prepare` copies the committed reconciler,
  applies the document to that copy, resolves from that exact snapshot and
  measures actual native controls. `commit` includes attachment, not only a
  snapshot assignment. A small internal `UIViewControllerRepresentable` embeds
  this controller in a repo simulator test app. It must not be wired into the
  existing signed presentation path.
* Android: keep `NativeRenderer` as the concrete owner. Add internal
  `prepareV2(byte[] packetBytes, InstalledAppearanceV2 captured,
  NativeEnvironmentV2 capturedEnvironment) -> Candidate`,
  `attachV2(Candidate, FrameLayout root) -> AttachmentJournal`,
  `finishV2(Candidate, AttachmentJournal)` and `rollbackV2(...)` calls.
  The Activity's ordinary V2 coordinator invokes them. `finishV2` consists of
  already-prepared reference swaps and gate reopening; no native setter,
  listener allocation, JNI call, shaping or layout operation belongs there.
  Package-private candidates/journals cannot be constructed by the application.
* `InstalledAppearanceV2`/Apple equivalent is a private final native owner,
  created only by the native bundle/assets capture routine. It owns copied
  descriptor bytes, decoded V2 configuration, copied resource bytes and validated
  native font objects. It exposes no mutable buffers or public constructor.
  The already-public configuration/plan types remain untrusted data.
* Environment capture is a small concrete helper owned by each controller or
  Activity, not another public contract. It returns the existing resolver's
  immutable environment plus a private owner/generation stamp.

The first consumer tests call the real internal renderer from a real UIKit or
Android test app and install a tiny real packaged descriptor. Public bootstrap
and wrapper naming are a separate root decision. Do not add `MixerUIHostV2`,
silently change the current `MixerUIHost` initializer, or accept a caller's
`Environment`/support value as native installation evidence during these lanes.
After native qualification, the bootstrap owner may connect an explicitly opted-in
ordinary facade. An initial document is pending until a real window capture and
attachment succeed; it is not a committed display snapshot before that point.

## Coherent installed capture and fonts

The bootstrap proposal uses one canonical V2 descriptor produced or validated by
the Swift codec from one app configuration. The same byte sequence enters both
native bundles. There is no second maintained Java default. The eventual app
configuration key, reserved installed path and local build receipt fields require
root review together; they are not established by this document.

For the bounded repo consumer, freeze the internal installed layout as
`MixerAppearanceV2/descriptor.json` and `MixerAppearanceV2/resources/<catalog.path>`
inside the test application bundle/assets. Capture all entries, including entries
unused by the selected theme. Require the closed codec/catalog semantics: no
symlinks, path escape, ambiguous case, wrong byte count/digest/format, missing
variant or unauthorized fallback. Reject over-budget material before allocation
or retaining it. Resolve bundle root/component ownership safely; a path string
prefix check is not a containment check. Build inputs need regular-file checks
and before/after observations or immutable staging; runtime consumers only see
their own copies. Once capture completes, never reopen source/bundle paths to
shape or paint. Mutating a captured input array in a test must not change output.

Apple loads bounded bytes from its installed bundle, copies to owned immutable
storage, verifies SHA-256 with CryptoKit, validates PNG/SFNT with documented native
decoders, and retains `CGDataProvider`/`CGFont`/CoreText objects derived from those
same captured bytes. A bundled face must prove PostScript name, SFNT weight/style
and actual shaping coverage; matching a name alone is insufficient. Prefer native
font construction directly from captured bytes. If UIKit needs process font
registration, the owner must prove that the exact registered face is the one used,
reject name collisions and unregister only faces it registered when capture
fails. Installing fonts belongs before host setup; ordinary updates must not
partially change a process font registry. Native consumption of that exact face
is an executable gate, not a presumed cast or name lookup.

Android copies `AssetManager` entry bytes with bounded streams into private
storage, hashes with `MessageDigest` SHA-256 and validates decoded format. The
API29 prototype can use read-only owned `ByteBuffer` data with `Font.Builder`,
`FontFamily.Builder` and `Typeface.CustomFallbackBuilder`. It must validate SFNT
PostScript/weight/style metadata against the descriptor, rather than passing
descriptor weight to a builder and treating that override as validation.
`setTypeface(..., BOLD)` and synthetic italic are prohibited. API28 alternatives
need an explicit public-API evaluation and receipt before support freeze: they
cannot silently fall back to system faces or reopen mutable font paths.

For both adapters, `systemSans` deliberately uses native script/emoji fallback;
it does not promise identical glyphs. `bundled/fallback:none` must reject native
shaping runs that use another face or missing glyphs, including combining,
supplementary-plane and complex-script cases. Coverage is checked per actual
candidate strings before commit and again for native edit proposals before
acceptance. A per-code-unit `hasGlyph`/cmap check alone is insufficient. Undeclared
native fallback fails the complete candidate. Input rejection must retain the
last accepted native editing buffer and composition; inability to do that is
unsupported operation, not permission to lose IME state. A permissively licensed
real font fixture and its provenance must be chosen and recorded in
`THIRD_PARTY.yml` by its implementation owner before bundling; no font asset is
introduced by this design slice.

## Coherent window capture

Capture on the UI owner in one synchronous turn after the container belongs to a
window and has nonzero usable bounds. Use a private checked monotonic generation;
do not trust the public environment's arbitrary generation. Each candidate records
base committed document revision plus complete exact identity map, installed
capture identity/configuration generation and window environment generation.
Recheck them immediately before attachment and final commit. Overflow retires the
owner explicitly. No background callback may combine values from two generations.

Apple reads the actual container/window trait collection, screen scale, effective
layout direction, container viewport/safe-area geometry, current locale, preferred
content-size category, Bold Text, increased contrast and Reduce Motion. Map known
categories to all twelve existing profiles; reject unknown ones. Read traits from
the actual attached owner, not a process-global key window or guessed main screen.
Trait, content-size, locale, accessibility, safe-area and window/layout callbacks
invalidate capture. Re-capture their complete tuple and increment generation only
through this owner. The SwiftUI embedding must not apply another semantic font
scale or safe-area inset to the UIKit content.

Android reads the current Activity window's `Resources`/`DisplayMetrics`, bounds,
insets, direction, locale and configuration in its UI turn. Preference conversion
must use `TypedValue.applyDimension(SP,17,metrics)` divided by
`applyDimension(DIP,1,metrics)`, validate unrounded 14…53 support, then round to
logical64 and select the existing nearest profile. Do not derive it from
`fontScale` or `scaledDensity`; apply the selected six metrics with explicit PX
sizes afterwards. Configuration/window/insets/layout/locale and accessibility
observers invalidate the whole capture. Required Bold Text/font-weight adjustment
or contrast changes that cannot be observed faithfully on a targeted OS make
that context unsupported. The Activity must not add its legacy inset padding a
second time. API-level accessibility observation gaps need explicit evidence.

Both paths normalize actual density using the existing checked helper. UIKit
layout stays in logical points; Android layout is in native pixels. A path adapter
already returns physical-pixel coordinates: Apple converts exactly once at its
layer/drawing boundary (for example a layer whose local units are physical pixels
with a single `1/scale` placement transform); Android paints without a second
Canvas density transform. Shared absolute edges use the existing rounded-edge
helper and widths come from edge subtraction. Neither platform rounds each cubic
control to an integer pixel. Shaped extents round upward to logical64 before
checked aggregate layout. No fixed Latin line box clips scripts or emoji.

## Real consumers for all ten kinds

Custom native views below are bounded concrete containers/drawables for this
recipe, not a second cross-platform layout language. They consume the existing
closed recipe cases and reject unknown or unavailable operations.

| Kind | Apple owner/toolkit object | Android owner/toolkit object and required assertion |
| --- | --- | --- |
| text | `UILabel` for ordinary text; noneditable, nonscrolling `UITextView` for selectable text, with exact font/paint, admitted native wrapping/truncation and no default text-container inset. | `TextView`, exact PX font, disabled include-font-padding/default margins, original selection/maxLines; inspect actual `Layout` and grown bounds for complex text. |
| button | `UIButton(type:.custom)` plus explicit label/overlay/focus layers and separate hit envelope; native control tracking/keyboard/accessibility owns activation. | Native `Button`, remove default ripple/elevation/insets/capitalization/minimums; exact label, custom closed-state drawable, separate hit bounds; one activation only. |
| textField | Native `UITextField`, own placeholder/outline/insets, native selection/composition/submit. Separate caret and selection paints must first be proved with public selection-display APIs. | `EditText`, native `Editable`/InputConnection and submit; exact placeholder/text/highlight/cursor/outline. API29 public cursor API is a prototype path; API28 is unresolved. |
| toggle | Real `UISwitch` remains the native input/accessibility carrier. Public layer masking suppresses its default visual; sibling authored layers draw label and fixed track/thumb. Prove tracking/cancel/VoiceOver and hit geometry after masking. | Real `Switch` remains input/accessibility owner; suppress default track/thumb drawing with owned drawables and paint closed authored geometry in a bounded wrapper. Prove native drag cancellation, key activation and TalkBack; no platform shape substitution. |
| vStack | Concrete `UIView` container measures children and consumes each resolved gap, logical alignment and child order. | Bounded `ViewGroup` consumes actual child sizes and each gap; no `LinearLayout` default gap/layout weight. |
| hStack | Same container with actual first/last text baselines and checked width aggregation. | Same bounded `ViewGroup`; actual `TextView` first/last `Layout` line baselines and defined container baseline propagation. Required unavailable baseline rejects whole candidate. |
| zStack | Concrete container computes constrained intrinsic child sizes and overlays in original paint order. | Same native `ViewGroup` policy; prohibit current Android-only child fill. |
| list | Stable `UIScrollView` and content/group views; retain exact list identity and content offset; measure rows, fill surfaces, clip one full-group path and interior separators. | Stable `ScrollView` and content/group views with the same recipe; Canvas consumes `AppearanceNativePathsV2` for group clip and fixed toggle paths. Actual grouped layout assertions must distinguish semantic content, hit, row and visual bounds. |
| section | Existing identity record remains structural inside a list group; otherwise a concrete vertical header/content container without extra outline. | Same context handling; no second title/wrapper when List owns the immediate Section group. |
| navigation | Native container controller and `UINavigationController` host preserve system back behavior; its explicit chrome uses separately measured expanded/compact labels and snapped threshold. | Native Activity/system-back lifecycle remains authoritative; custom chrome consumes the two measured titles and threshold. No fake app back event or new navigation protocol. |

The existing packet/UI-v1 limits remain: root-only V2 navigation; no nested List
through any container. Explicit Android HStack baseline properties remain rejected
by its current packet profile. A baseline selected by admitted theme defaults
still requires native consumption or whole-candidate rejection. This slice does
not expand packet properties, navigation-stack semantics or the product's complete
future component scope.

Each renderer must consume every recipe field and state paint, including clear
paint, pressed overlay, keyboard/editor focus and disabled precedence. App-level
opacity/tint or hidden toolkit defaults cannot supply missing fields. Group
outlines call the actual path adapter using final measured dimensions. Toggle
thumb placement calls the shared geometry owner and mirrors with direction.
Group/row wrappers have no invented event IDs. Semantic field/button content and
toggle label height remain distinct from 44-high hits and 28-high track visuals.
Navigation always measures both title presentations before threshold selection;
scrolling changes only native chrome state, never the guest revision.

## Ordinary transaction and failure steps

1. Reject reentrancy. Capture the committed base tuple and acquire a short UI
   transaction gate. Native callbacks during preparation/commit cannot send
   actions. Ordinary preflight may create detached controls, but must not rewrite
   surviving `UITextField`/`EditText` buffers, live targets/listeners or parents.
2. Stage the value reconciler/engine candidate. Validate the complete document,
   identities, installed descriptor/resources and required concrete operations.
   Resolve the exact snapshot with the existing V2 resolver. Bound all records,
   references and aggregate geometry before retaining native work.
3. Create new identity records detached. For surviving ID+generation+kind retain
   the actual native editor, switch, selectable text and scroll object. Measure
   using detached native text/control measurement objects with the same captured
   font/configuration; never detach or clone a live composing editor to measure.
   Construct native paths, paints, target/listener bindings and layout operations
   before attachment. Measurement failure disposes only staged material.
4. Snapshot the native rollback journal: exact parent/index/frame/layer/style
   values changed by the candidate, old action bindings and retained selection,
   first responder/focus, composing state and scroll identity/offset. The journal
   is bounded by the admitted node count. It is not a serialized generic view
   tree or a promise that an OS editor's composition can be reconstructed.
5. Recheck base revision/complete identities/configuration/environment generations.
   A stale candidate is disposed and rebuilt; it cannot overwrite a newer plan.
   Freeze redraw/layout invalidation for the synchronous mutation section where
   public toolkit support allows it, and keep input/event forwarding gated.
6. Perform the prepared minimal native parent/style/frame/root changes on the UI
   thread. Reuse editors in place; unchanged model text must not call `setText` or
   replace attributed content. A guest update conflicting with active marked text
   must defer the whole candidate until composition completes or explicitly fail
   unsupported attachment; it must not unmark/clear composition to commit.
   Composition reparenting is unsupported until an actual native test proves it
   preserves the editor connection. Preserve existing list scroll state and clamp
   only to a changed valid native content range.
7. If native attachment or post-attachment validation fails, reverse the journal
   before allowing a frame/event and abort the engine candidate. No candidate
   callback, guest action, display/health witness or new committed snapshot exists.
   Dispose new controls/listeners and retain the complete old tuple. If rollback
   itself fails, gate input and retire the ordinary presentation with an explicit
   failure; do not claim the old display was preserved or route either tree.
8. After successful native attachment, commit the already-prepared engine/value
   state and atomically replace the native committed tuple
   `(snapshot/packet, identities/records, plan, capture, environment, root)`.
   Reopen forwarding only afterwards. Retire removed/replaced native listeners
   and records; publication/observer notification follows the committed tuple.
   Prepared pointer swaps cannot allocate or invoke fallible callbacks.

UIKit performs this on MainActor and disables implicit layer actions. Android
runs it on the main Looper with layout suppression where available. The gate is
released in a guaranteed cleanup path. No asynchronous suspension, nested run
loop, arbitrary application closure, draw traversal or guest dispatch is allowed
between native attachment and final tuple swap. Unexpected native reentrancy
records invalidation and forces rollback rather than exposing half a candidate.

Native listeners belong to concrete records keyed by exact identity. A binding
contains its committed document revision/identity and is activated only at commit;
saved stale envelopes still fail the current snapshot/packet router. Setters and
paint/layout changes emit no guest events. Removed records invalidate bindings.
Surviving native watchers may be installed once and consult an atomically swapped
record binding; they must verify the record is still the committed one. Staged or
retired bindings cannot reach the reducer. Press/focus/scroll callbacks also carry
the committed environment stamp so stale ephemeral work cannot repaint a newer
snapshot/environment. Accessibility focus is native state, not keyboard outline.

An environment-only change repeats resolve/measure/attach for the exact committed
snapshot, validates the complete base tuple, then swaps only environment/plan/
layout. It does not invoke the reducer, allocate document generations, increment
guest revision or emit a synthetic native input event. Failed recapture remains an
explicit unsupported context; it is not converted to an app theme override.

## Required ordinary Android bridge proposal

Root must freeze this edge before changing the registry/entry/JNI. Reusing
`exchange` operation1 and acknowledging it later cannot recover its already
committed reconciler. Keep `NativePacketV1`, existing exchange operation0/1 and all
signed `mxis_*`/Stage5 transports unchanged.

Proposed ordinary symbols, separate from signed code:

```text
mixer_android_prepare_v2(handle, operation0or1, input, inputLength,
                         output, capacity, written*, candidateToken*) -> status
mixer_android_commit_v2(handle, candidateToken) -> status
mixer_android_abort_v2(handle, candidateToken) -> status
```

The existing `AndroidSessionRegistry<Engine>` can implement this without another
engine protocol: copy the value engine, call its existing render/dispatch, and
retain the candidate plus bounded output only after output allocation/serialization
succeeds. Preserve the existing engine contract: app state has value semantics
without shared mutable reference graphs, and factory/render/reducer calls are
synchronous, nonreentrant and free of I/O, asynchronous work and external side
effects. `Sendable` alone supplies none of those guarantees; a retained candidate
cannot roll back arbitrary reference mutation or I/O. Keep at most one pending
candidate per session and the existing session,
input and output bounds. The private token is monotonically assigned and bound to
that session and registry base epoch; it supplies no release or signing authority.
While pending, reject another prepare/legacy exchange for that session. Destroy
retires the candidate. Abort is idempotent for the same retired/aborted token,
without allowing a foreign token to affect another candidate. Commit cannot revive
an aborted/retired token; repeated commit is rejected without mutation.

The Activity owns environment/configuration stamps and the native base tuple; the
registry owns the engine base epoch/revision/identities through its value candidate.
The Activity rechecks both sides before commit. JNI `prepareV2` returns one
already-allocated private result containing token and packet bytes. If JNI packet
array/result allocation fails, abort the retained candidate before propagating
failure. `commitV2` has a scalar result and performs no Java allocation. Error
codes for pending/stale token, capacity, rejected engine and retirement need an
explicit ordinary header contract review; do not reuse signed status meanings.

After native attach but before engine commit, any stale base, abort, owner
retirement or scalar commit rejection causes native rollback and candidate abort.
The new tree has never been made drawable/event-capable. If the scalar commit
succeeds, the Java finish step only swaps preallocated references before reopening
draw/input. A JNI/runtime error leaving commit outcome unknown retires the session
and presentation with input gated; it does not resume the old engine/display by
guessing. This is ordinary failure handling, not signed presentation recovery.

## Bounded implementation sequence and validation gates

Freeze the internal consumers/ordinary bridge and ownership first. Then the Apple
and Android renderer lanes can work independently; shared schema, packet and
signed identities stay frozen. Serial ordinary bootstrap integrates only after
both consumers and the producer transaction are reviewed.

| Lane | Prospective bounded product/test files | Completion evidence required before dependent integration |
| --- | --- | --- |
| Apple native consumer | New `sdk/Sources/MixerApple/AppearanceNativeRendererV2.swift`, `AppearanceInstalledV2.swift`, `AppearanceNativeEnvironmentV2.swift`; new iOS simulator harness and native consumer tests under `native/apple/appearance-v2/`; existing path adapter is read-only dependency. | Real controller consumes the real resolver and paths in a window; native views/layout/drawing for all ten kinds; field paint, font-byte consumption and editor retention feasibility first. Root reviews any need to split a large concrete renderer file. No existing host/signed facade edit in this first lane. |
| Android native consumer | Existing `NativeRenderer.java`; new bounded package-private installed/environment helpers and concrete layout/drawable classes only where needed; new `native/android/tests/AppearanceRendererV2Instrumentation.java` and standalone test app. | Real NativeRenderer resolves real packet bytes, uses actual Path adapter and native Views, attaches to FrameLayout and draws; all ten kinds and native rollback/state tests. First API29 prototype is only a private qualification floor. API28 remains a required gap and current public baseline stays unchanged. |
| Ordinary engine transaction, serial owner | `SessionRegistry.swift`, runtime tests, `NativeBridge.java`, ordinary `bridge/jni.c`/`mixer_android.h`, generated Android entry in `AndroidProject.swift`, Activity coordinator. | Actual reducer candidate is retained across JNI; a native failure leaves engine state, revision, identities and display unchanged; JNI output-allocation fault aborts; unknown commit outcome retires. No signed transport edit. |
| Ordinary bootstrap, serial owner | `Configuration.swift`, `ProjectGenerator.swift`, `AppleProject.swift`, `AndroidProject.swift`, `Resources/android-build.py` and CLI build tests; eventual existing facade integration only after naming/opt-in review. | Actual exported iOS app/APK contains identical canonical descriptor bytes and complete catalog; installed copies consumed by each renderer; built closure includes resolver/geometry/native adapters; mutations/omissions rejected. No silently dropped Resources or second Java theme table. |

Each meaningful implementation slice needs executable tests against its actual
consumer, not only a data projection or a support inventory. Proposed test commands
below name future harnesses; **they have not been created or run by this lane**:

```text
swift test --package-path sdk --configuration debug
swift test --package-path sdk --configuration release
python3 verification/apple-appearance-native-renderer-v2/qualify.py --output candidate-N --simulator <explicit-UUID>
python3 verification/android-appearance-native-renderer-v2/qualify.py --output candidate-N --emulator emulator-NNNN
swift test --package-path native/android/engine
swift test --package-path cli
```

The harness owner must implement these commands with explicit simulator/emulator
targeting, actual app installation/launch and terminal test markers. No physical
device enumeration/run or request to reconnect phones. A compile-only run records
native execution pending. Exercise both minimum qualified API and current API;
running API37 does not qualify API28. A minimum build target is not native runtime
evidence. Every receipt records command/cwd, tool/SDK/API/target, source revision,
exact input closure/tree digest, outputs, compiled application hashes, observed
result and scope. Root/independent review checks the actual consumer call graph
and retained native output; a marker or declarative matrix alone is insufficient.

Required native corpus:

* One real ordinary screen containing all ten kinds, both schemes/directions,
  all twelve profiles, direct/Section/empty/header-only list groups, semantic
  nested Section, direct body→caption and explicit zero gaps, intrinsic overlays,
  overflow/growth and both navigation presentations. Inspect real widget fonts,
  native measurements, frames, layer/drawable geometry and rendered output.
* Independently calculated expected group edges, row heights and interior-only
  separators; actual authored group clamp and fixed track/thumb consumption;
  RGBA alpha once; default toolkit tint/ripple/elevation/font padding absent.
  Include multiline combining marks, Arabic/bidi, CJK and emoji; real selectable
  text and maxLines/ellipsis. Native raster remains platform-specific evidence.
* Exact native object identity, selection range, first responder/InputConnection,
  marked/composing text and scroll object/offset survive property, theme-profile,
  environment and reorder updates that are actually supported. A conflicting
  composition update must defer/reject atomically. Replaced/removed identity
  retires its old callbacks. Repaint, environment and programmatic binding cause
  zero guest events; real input causes exactly one current action.
* Forced failure before measurement, after detached allocation, at each live
  parent/style/root attachment step and after attachment before engine commit.
  Compare the complete old committed tuple and actual native hierarchy/bindings;
  then send a real old-tree action and prove it reaches the old engine. Fault
  rollback itself and prove input/presentation retirement. A test injection stays
  internal to the owning renderer/harness and cannot be an app support provider.
* Stale environment/config/document candidate, simultaneous invalidation,
  reentrant callback, pending second prepare, foreign/aborted/replayed token,
  output-capacity/allocation failure, destroy and unknown commit outcome.
  Check no old display/new action or new display/old action window.
* Native button/switch key and touch cancellation, native text submit, disabled
  ancestors and accessibility roles/labels/values/actions/focus order. Simulator/
  emulator automation is scoped native evidence; physical VoiceOver/TalkBack,
  keyboard/navigation and side-by-side design review remain pending.
* Packaged resource digest/size/format/path failures and real font identity,
  required weight/style and declared fallback. Mutate caller source arrays after
  capture and replace source files after bootstrap; output still consumes the
  original immutable copies. A fake resource positive case cannot qualify fonts.

The iOS17 caret/selection path and masked native-switch behavior require actual
simulator proof before advertising those operations. Installed public headers
expose `UITextSelectionDisplayInteraction`, but do not promise that a built-in
`UITextField.textInputView` exposes an instance whose highlight/cursor can be
independently styled. Inspect only public interactions/APIs; no private subview
class lookup, reflection or global appearance hack. If the proof fails, return the
specific limitation to root; a custom editor or changed contract requires a
separate decision. Likewise evaluate API28 public cursor/font alternatives before
claiming all-ten Android V2 support. The current API28 product baseline is retained.

## Unavailable signed V2 and completion boundary

No public wrapper, internal candidate token, installed resource capture, native
rendering or successful ordinary test changes signed release authority. Existing
native-closure/release fields, NativePacketV1, signed headers/events, `mxis_*` and
Stage5 transports are not reinterpreted. Signed V2 requires its separately frozen
format/digest/resources/curves/consumer/build binding and private installation
edge, then real display/input/health evidence. It remains unavailable here.

This slice adds only this document and its verification directory. It changes no
product code, tracker, GA gate, signing, published package, commit or push. Root
owns final API/ownership freeze and later integration. Its declaration probes
verify that selected toolkit calls compile against installed official SDKs only;
they neither execute a native widget nor close any of the gates above.
