# Internal UIKit appearance V2 consumer

This implements a private ordinary consumer for product-plan §8.3. It is not
connected to `MixerUIHost`, CLI bootstrap, an engine transaction, or signed
presentation. It does not authorize a release. The independent SDK/UI/geometry
sources remain unchanged. No Patch/Skip code or new product dependency is used.

`AppearanceNativeRendererV2` is a MainActor container controller with one stable
root view. Its private native bundle capture reads
`MixerAppearanceV2/descriptor.json` through no-follow directory/file descriptors,
checks regular-file size and before/after file identity, copies bounded bytes,
requires the entire canonical Swift codec, and retains SHA-256 plus immutable
configuration. The first consumer supports `systemSans` and an empty catalog.
Any resource, including an unused entry, or either platform's bundled font
configuration rejects capture. There is no missing-resource/default-theme
fallback. Native fonts come from the selected six-role profile without a second
Dynamic Type multiplier. System script/emoji fallback is intentional.

The owner captures the attached view/window's actual bounds, safe area, screen
scale, traits, direction, locale, all twelve content categories, Bold Text,
contrast and Reduce Motion in one main-thread turn. Window, layout/safe-area,
trait and preference notifications invalidate a checked owner generation. Public
`UIAppearanceEnvironmentV2` is data and is never accepted as capture authority.
The executed runtime is iOS 26.5; other runtime versions reject. The source
compiles for an iOS 17 deployment target. Increased contrast and Bold Text reject
until their shared transformations are qualified. Reduce Motion is captured;
the authored recipe snaps navigation without an animation. The input caret's
native-managed blink is separate from that recipe transition.

`prepare(document:)` copies the value reconciler, validates/resolves the complete
snapshot, constructs detached UIKit controls, and performs TextKit measurements
and bounded authored layout. It changes no live editor, listener or parent. A
candidate has a private constructor, native owner UUID, base commit serial,
complete environment, routed interaction generation and native ephemeral-state
stamp. Every routed native action advances the checked interaction generation,
even if its final highlight/focus equals its prepared state. Commit consumes it once,
rejects foreign/stale/native-state-changed candidates, and reuses surviving exact
ID+generation records. Actual UITextField, UISwitch and UIScrollView objects
survive ordinary and same-revision environment transactions. The native-state
stamp includes editing text, selected range, focus, composition presence, switch
state/tracking/focus, button state and scroll offset. A new guest document/revision
is authoritative for field/toggle bindings even when the old/new guest-bound
value is unchanged. Only a same-revision environment transaction retains native
unacknowledged field/switch values. This shared private decision changes no schema.

Invalidation suspends committed input immediately. A stable root hit-test blocker
catches new touches, and the actual field delegate/insert/delete/marked-text entry
points reject mutation while closed. Setting the root interaction flag false
was rejected after actual UIKit evidence showed that it resigns the editor.
Every action uses the same exact-record, inherited-enabled, attached/shown native
carrier and key foreground-window gate before routing. A supported environment
transaction reopens input only after attachment and snapshot swap. Unsupported
committed recapture retires/hides/gates the owner and denies future use; old
snapshot data confers no authority in the new environment.

Attachment runs with callback routing closed and a bounded operation journal.
Native setters, parent attachment, listener setup and field paint installation
finish before the reconciler/snapshot/plan/reference swap. Finish reopens routing;
it performs no shaping or native setter. An internal harness seam can inject a
fault and a real native callback during the journal. A post-mutation fault
explicitly retires, hides and gates the whole owner, denies future use, and keeps
native owners alive through callback exit. It does not claim IME rollback or a
preserved old display. Unchanged snapshots alone cannot witness that failed new
candidate. `commit` returns `UIChangeSet?`: nil is a successful same-revision
appearance/environment transaction, while failures throw. `discard` consumes a
candidate without live effects.

A live marked-text range rejects prepare/commit before effects. The current
consumer does not serialize text/focus and claim to restore an IME. Programmatic
native composition retention on a rejected update is tested; real Japanese IME
composition and cancellation remain pending. A focused field requiring native
ancestor parent replacement also rejects before attachment. Changing the
selectable/nonselectable native text topology of a surviving identity also
rejects before effects. Selectable text retains its actual UITextView selection.

All ten existing recipe cases have concrete UIKit consumers:

| Kind | Actual consumer |
| --- | --- |
| text | UILabel or noneditable/nonscrolling selectable UITextView, exact selected role/font and TextKit shaped extents |
| button | UIButton custom, native activation/focus, separate label/visual/hit geometry and explicit state paints |
| textField | UITextField with native input/selection/submit, authored insets/placeholder/outline and independent managed caret/highlight |
| toggle | UISwitch input/accessibility/tracking carrier with a zero-area public layer mask; authored sibling paint uses the closed 63×28/37×24 paths |
| vStack/hStack/zStack | Concrete UIView records, every resolved gap/alignment and original child paint order |
| list | Stable UIScrollView, stable keyed group/header parents, one full-group clip/surface, interior separators and native offset |
| section | Structural list-group identity or a separate header/content container outside a group |
| navigation | Native UIViewController hosted by UINavigationController in the harness, measured expanded/compact chrome and snapped native scroll threshold |

Shared fixed paths are converted through `AppearanceNativePathsV2` to physical
pixels, then inverse scaled once at the UIKit draw/mask boundary. Authored alpha
is applied once. Placement snaps common absolute boundaries before subtraction.
Native TextKit provides ordinary text wrapping/truncation and real shaped
first/last baselines. Field/Button/Toggle baseline scalars are unavailable in
this bounded subset; a required baseline rejects instead of guessing a native
interactive vertical offset or Latin ascender. Ordinary center/top/bottom layout
is retained. A Section's first edge selects the actual header first when present,
otherwise the first child first. Its last edge selects the actual last child last
when children exist, otherwise the header last. Child placement offsets apply;
missing selected scalars stay unavailable. HStack likewise propagates its actual
placed first/last source-child edges rather than setting both to its chosen
alignment baseline. These latest repairs have compile-only regression sources;
no native pass is inferred for them while runtime work is paused. Nested lists and non-root navigation remain resolver failures.
Nested controls inside list-row containers reject before effects in both native
consumer lanes. Direct control rows separate semantic content from minimum hit
and fixed visual bounds. A direct native control hit envelope must fit its full
row width/height, including admitted custom metrics; undersized rows reject
before effects. This leaves nested native gesture/hit proof pending. Navigation
with a List hidden under an intermediary container is rejected until that
specific scroll/chrome relationship is qualified.

Explicit source accessibility label/hint/value/identifier properties are applied
through public UIKit APIs to the actual UILabel/UITextView/UIButton/UITextField/
UISwitch traversal leaf. Container identifiers are admitted; label/hint/value
semantics on a nonleaf container reject before effects because this slice has no
qualified grouping/action model for them. Native header traits and source-order
accessibility traversal are set explicitly, including unequal wrapped HStacks.
This does not claim a completed VoiceOver workflow. Field/focus outlines use an
inside stroke; pressed switch overlay is above the track and below the thumb.

The root-approved private HStack width policy measures each child under the full
proposal first. If intrinsic widths plus exact gaps overflow, subtract gaps in
logical64, divide remaining width by source-order child count, distribute the
remainder one unit to earliest source-order children, and remeasure. Narrower
intrinsic results are not stretched; RTL mirrors placement rather than proposal
order. A fixed hit/visual width that cannot fit rejects. This is an authored
consumer policy, not a claim that unmodified SwiftUI uses the same algorithm.

The field discovers only public `interactions`/`textInputView.interactions` and
uses `UITextSelectionDisplayInteraction`'s managed cursor/highlight APIs. On the
qualified runtime it removes and re-adds the **same** public interaction after
assigning managed views, then requests native selection layout. There is no KVC,
private selector, subview search or manually inserted selection overlay. The
cursor implements a visible-first one-second Core Animation blink cycle and
restarts on native `resetBlinkAnimation` requests. UIKit still owns its frame,
hidden state, focus, selection geometry and activation. Blink phase/paint samples
are simulator evidence, not proof of every native cadence/reset/selection-menu
or accessibility context. Native selection handles retain native appearance.

The executable harness is `native/apple/appearance-v2/run.py`. It compiles the
exact bounded source closure into `MixerAppearanceInternal` with testing enabled,
then embeds the actual internal controller in a native app. This is deliberately
separate from public Swift package app wiring. It creates its own dedicated
simulator using an already installed runtime and never discovers or runs a
phone. Existing booted simulators are preserved. Use `--keep-simulator` only for
further interaction; owned simulator IDs are retained for cleanup.

The stable cross-platform fixture is `AppearanceFixtureV2.document(1)` in
`native/apple/appearance-v2/Fixture.swift`. Its actual Swift
`encodeNativePacketV1` output, canonical default descriptor, JSON document and
native logical64 frame/role/state map are in
`verification/apple-native-appearance-v2/shared-fixture/`. These allow an exact
Android consumer comparison without maintaining a second default table.

Evidence under `verification/apple-native-appearance-v2/` retains command exit
codes/output, compiler/tool versions, deployment/binary/descriptor hashes,
revision/tree and input SHA-256 copies, native assertions, compositor PNGs and
owned simulator lifecycle. Intermediate failures are retained: the initial app
executable collided with the reserved resource folder; an earlier initial image
had a transient system notification; and immediate trait override assertions
observed the previous run-loop generation. None is relabeled as a pass.

Simulator receipts can accept this bounded development slice under the user's
current policy. Physical paired design/interaction/accessibility review remains
final acceptance work. Secure input, real IME cancellation/selection dragging,
editing menus, keyboard navigation/focus breadth, VoiceOver, native switch drag
cancellation, live OS preference changes, locale/orientation/window relocation,
iOS 17 runtime, other iOS runtime versions, resource/font support, engine failure
atomicity, ordinary/public bootstrap, signed display/health, immutable published
FieldLog packages in its separate repository, store/customer/operational gates
and GA review remain pending. No omitted context is a pass.

Native qualification is unfinished. Candidate-13 passes100 native assertions,
including authoritative bindings, environment gating/retirement, exact identities,
all profiles, accessibility update/clear/native checked-value defaults, selectable
RTL alignment and bounded HStack overflow. Its frame map is byte-identical to the
shared export. Its switch mask still permits native elevated Liquid Glass while
held; those assertions do not qualify pressed rendering. Candidate-12 retains
actual held observer/cancellation receipts and the visible native glass leak.
Its initial combined accessibility assertion failed: the later diagnostic showed
native getters retained label/hint/identifier but regenerated value `1` instead
of authored `Value 3`. Explicit backing/public getters fix this, with absent
overrides delegating to native checked semantics. Candidate-14 tested public
CALayer opacity suppression and failed: layer.opacity0 also makes UIView.alpha0,
so ordinary native touch input cannot be accepted from that experiment.

The user then stopped all computer use, screen capture and native UI/runtime
work until further notice. The lane-created simulator
B5513F55-39E7-476A-A6D2-5A81E3FEE22B was shut down/deleted with exit0; harness
PID54245 is confirmed terminated. Root separately terminated the shared Simulator
frontend. `user-stop-native-cleanup.json` and `owned-simulator-cleanup.json` retain
exact commands and final simulator inventory. All lane-created simulators are
retired. No additional boot/install/native run, CUA call or screenshot is
permitted while that instruction remains in force. Coding/headless work alone
cannot establish new hit, accessibility or compositor behavior.

The live source now removes the failed opacity experiment and implements an
**unqualified headless cover prototype**. It retains the same native UISwitch at
UIView alpha1/hiddenfalse and places a noninteractive, inaccessible paint sibling
above its visuals, with its own label above the cover. Existing closed authored
track/overlay/thumb paths are translated into that cover's local pixel origin;
there is no new app color, recipe or second density scale.

Admission is deliberately narrow. A toggle must be a direct List row on its exact
resolved group surface with alpha255 and content insets at least12pt. The proposed
cover is the native hit rectangle expanded12pt. Its corners must fit inside the
closed convex group path and actual group bounds. The private Geometry helper
projects all absolute edges once; the detached hierarchy receives those exact
prepared local frames, and commit attaches the same frames without resnapping.
After every detached placement is final, UIKit conversion expresses the cover,
own label and each neighboring descendant's label/control/visual/full-fill bounds
in that same group coordinate system. Any foreground/native hit intersection
rejects. Every direct native carrier must also fit its final snapped row bounds.
Identity transforms, zero wrapper bounds origins and unzoomed scroll contexts
are preflight requirements for surviving owners. A preserved ancestor scroll
offset cancels below the common group; nested scrolling contexts remain rejected.
Existing authored separator siblings are above the cover.
A geometry failure rejects before native attachment. The12pt size is an explicit
prototype proposal, **not a proven native Liquid Glass extent**. Generic/outside-
list, transparent, rounded-edge, neighboring-content/hit, and own-label-overlap
contexts are excluded. In particular the default RTL label begins only8pt after
the track, so the12pt proposal overlaps it and rejects; long LTR labels can reject
too. The source does not relax those proofs to force a normal fixture through.

`headless-cover-baselines/` remains the historical compile-only closure. An
independent arithmetic counterexample found its logical cover/hit guard could
admit a19/64pt overlap after row-edge snapping. It is superseded by
`headless-cover-final-coordinates/`, which retains the corrected36-input closure,
commands/tool versions, source and binary archives. Eight macOS CoreGraphics
regressions executed against the production Geometry helper, including the exact
19/64 overlap, positive disjoint geometry, final carrier spill rejection, actual
group bounds and nested parent/scroll alias projection. All eight passed. This
is arithmetic evidence; the iOS17 consumer and future UIKit regression harness
compiled but were not executed. Future native regression sources
cover Section header-only/noheader/wrapped/nested LTR/RTL and unavailable edges,
HStack opposing edges, ordinary controls, and the cover's excluded contexts.
Those native tests have not run. Actual cover suppression/held/release/cancel, late denied
release retention, native touch hit, explicit/default accessibility behavior,
separators, focus/composition retention and paired compositor review remain pending.
No prior candidate's runtime output qualifies this changed source.

Candidate-6 remains complete as earlier-scope evidence. Attempts1–5 are in
`intermediate-attempts.tar.gz`; attempts7–10 are retained losslessly in
`later-intermediate-attempts.tar.gz`, both with per-member hash/size manifests.
Failed8/10 source, logs and images remain intact. Candidates11–14 retain their
exact source closures/results, and12 retains an explicitly mistimed first held
observation as well as the later observer-driven capture. None is relabeled as a
pass for newer source. Candidate11 first established that UISwitch.isTracking
stays false during a real held gesture, motivating the public nonpreventing
observer. Native actor/owner tests and binary archives cannot replace the missing
final visual/input gates.

`verify.py` is a strict offline replay helper for a supplied complete candidate;
it checks captured source, actual native assertions, built app archive/member
hashes, installed executable/dylib hashes, compositor pixels, GUI action deltas
and cleanup. It intentionally cannot pass the known failed14 or unexecuted cover.
The app archives retain executable plus three dylibs, plist and descriptor bytes.
Pillow12.3.0 from the bundled Codex Python runtime is verification tooling only.
The exact captured root AGENTS bytes stay locked; later supporting policy changes
are reported instead of silently changing native source provenance. No current
source acceptance, signed/public facade authority, physical/device/store/GA pass
or final evidence seal is claimed.
