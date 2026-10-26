# Independent actual-source review: changes required

Candidate seal `8f355ae83ec4d734e8d28451fc64a45200967a718eecb7c1987fa0fcc69d9920`
is **not accepted**. One selected hostile membership invariant fails: PC-C16
duplicates an existing owned A NativeState in the fixed journal array, replacing
C's slot, and successful finish releases A twice while leaving C counted and
registered. Root classified this as changes required under preaccess PC-S05 and
the selected once-only exact-hold release contract. It is a private state-invariant
finding, not an ordinary reachable path or public exploit claim. The bounded
correction must be frozen and independently reviewed before acceptance.

## Required failed invariant

`findings-1/seal.json` SHA256
`736df698b56281a71fe3621326107da463aeb4bf8237712c18d188513d96cc44`
freezes the complete control source, raw failure, invocation, class/source maps
and bounded-child receipt. Root's scope classification is recorded separately in
`root-classification.json`; the original finding packet remains unchanged.

The real three-field owner/coordinator path creates and validates two separate
inactive A/C holds plus B's actual entered EditorLease. At the existing authored
host JNI bridge's commit-beforeReturn boundary, the labelled hostile fixture
replaces only C's `journal.states` array slot with the exact existing owned A
NativeState. It changes no flag, count, original/token, stateCount, previous list,
Record, scope or callback registration. No production callback is added.

Observed result:

```
returned=true terminal=false completion=SUCCESS_DONE
shared=0 preservation=0 candidateHeld=0 busy=false
A counted=false released=true
C counted=true released=false registered=true
```

NativeRenderer.java:624 counts occupied counted array slots, allowing duplicated
A to look like two holds. The identity probe accepts that same owned A state on
both visits. The healthy scalar release loop at line723 decrements the same A
claim twice and never visits C. This violates the selected hostile fixed-membership
invariant and can make the renderer report disposal-ready with C custody still
represented. The negative control is retained as a failed test; it is not waived
or narrowed into a pass.

The separately sealed focused tail review explicitly assumes constructor-owned
fixed membership with no product mutation path, and excludes arbitrary private
reflection/Unsafe corruption. The negative control does not contradict its
narrower supported synchronous proof. Root nevertheless selected this exact
hostile membership invariant for correction; arbitrary broader memory/counter
corruption recovery remains unclaimed.

## Independent admission and source identity

Root explicitly released the candidate before access. This review independently
rehashed all9,791 producer members/49,981,814bytes, the9,790-member manifest,
root custody, and all504 members of unchanged preaccess seal
`d079d5ba16f007348dbb3fba6b0089723cccbd7169430012db5b501eb5290ccc`.
The complete sixteen-file product, unchanged86 Android/JNI leaves, producer tests,
descriptor and cross-compilation JNI signature leaf were copied before compiling.
Producer classes/results were not imported for execution; no generator or frozen
hosted/authority/worker harness ran.

`source-verification.json` independently confirms product tree
`cb5c2b813b9cb375f2907bafcb066ba9c556a2713ffd04c9d74777d9595d01e4`
and complete host tree
`702f0f88869f88b591ce6c167cc6a8fbfb967ada697947831d77ddab8efc42c9`.
Only NativeAppearanceViewsV2, NativeRenderer and NativeCoordinatorV2 differ from
the selected base. Removing the two selected failure-completion try/catch blocks
exactly reconstructs the whole original coordinator. The other13 product files,
all host leaves, original52-test source and cross JNI leaf are byte-identical.
The producer's renamed independent finding class is a class-name-only substitution;
this review additionally compiles/runs the original unrenamed source unchanged.

## Passed behavior and compilation

Independent `host-1` reproduces the original52 groups/722 assertions, all six prior
prepared replacement selections, all five additional replacement selections,
all13 producer focus-history groups, all14 earlier independent focus selections,
both additional audit groups, the admitted Api34 adapter's38 descriptors, and
all12 new producer completion groups/1,660 assertions. Selected timing-only test
changes and their old failures are preserved and reviewed; the unchanged original
52-test source retains every assertion.

Both required finding witnesses pass on these actual complete source bytes.
Unrenamed FH-C01 observes current original/snapshot, abort RETURNED, rollback
RETURNED, exact old Binding restored and unchanged Editable with zero text setters.
Unrenamed FH-C02 observes wrong Input refusal, local count2 unchanged, foreign
count1 unchanged and the foreign counted claim retained. Its two-renderer
internal-invariant label remains explicit.

Seventeen independently authored prospective/additional control groups pass,
plus the two original unrenamed finding witnesses, totaling42,884 recorded
assertions. Many assertions compare every declared scalar/reference field and
hook membership before/after refusal. `coverage.json` maps every PC-C01–15 and
PC-S01–10 requirement to exact sources/output or the separately admitted proof.
The additional PC-C16 membership control fails as described above.

The successful real triple holds3 through commit, scalar finish leaves B1, and
B's unchanged unwind reaches0. Known rejections1 and3–7 with abort0 restore both
exact old Binding/geometry references through the identical original scopes and
Mutation. Terminal/unknown/abort uncertainty obtains no new restoration. Refresh
holds2 from legitimate zero-count admission and reaches0 without an engine
commit. Pre-attach/no-original, no-scope, constructor-before-registration,
CAPTURED Begin refusal and entered-A/refused-C clean up only their actual custody.

Independent progress controls distinguish SUCCESS_IN_PROGRESS from failed-endpoint
invocation and actual per-scope release. Their labelled hostile partial-release
state releases remaining C exactly once and leaves already released A unchanged.
Whole-cohort preflight is observed directly at the first actual deferred reporter:
both original registrations and counts3 remain, candidate/journal success flags
and presentation references are unswapped. Later failure completion releases
balanced holds and retains the independently malformed one.

The full identity matrix checks receiving owner/Input and substitutions for
renderer/candidate/journal/Record/View/Input/original/fence/token/NativeState
membership/forwardPreserved, including an equal-token distinct original Mutation.
Every required refusal preserves both real owners, all compared scalar/reference
fields, hooks and native-probe count. Fatal chronology injects actual native F,
later restoration G and later abort H; F surfaces by identity only after every
eligible balanced preservation hold and B unwind. Imbalanced A or C remains busy.
Underfunding allows B's real shared unwind to reach0 but keeps preservation2 and
candidate custody2, preventing destruction; no repair/reset/retry is inferred.

An independent six-hook matrix reenters final validation's actual Editable getter
while A.checking=true, for own/foreign and single/repeated focus, window focus,
window visibility, visibility, aggregate visibility and detach loss. Every exact
native superclass suffix runs under the existing count3, every loss advances the
observation, no engine commit occurs, and both balanced holds release. Producer
adversarial Editable/span getter/fatal/loss-gain groups are independently replayed
as controlled host models. Exact getSelectionStart/getSelectionEnd callback
injection remains unmodeled because those unchanged host getters have no hooks.

Independent `cross-1` compiles the same sixteen-file product against official
pinned SDK37 with the unchanged JNI signature leaf, then D8 min-api28. JDK is
25.0.4.1; D8 is9.2.4-dev build084a89126ae0596c599143df57a654646af28313.
Compilation uses `--release17 -Xlint:all -Werror -proc:none`, explicit isolated
classpath/sourcepath, scrubbed Java injection variables and owned TMP. After
independent compilation, host/cross class maps and dex bytes exactly match the
admitted producer artifacts; this is an output cross-check, not inherited evidence.

## Focused source/bytecode review and retained failures

Root released focused review seal
`b1b3165a7ba5853e81a6763d40d536df4a8f156cfef89563e66d470ec3ec47c7`.
This review independently rehashed all465 members, its separately bound manifest
and root custody, and read its complete findings. Its fresh complete-source
compile/callgraph proves whole-cohort success checks precede the direct tail;
the121-instruction success tail and31-instruction Begin tail have no invocation,
allocation, explicit throw, monitor, native/main/Input/JNI/event/report/owner
resumption. It proves exact two-hook coordinator scope, independent preservation
tally funding and captured lifecycle suffix ordering under its explicitly stated
fixed-product-membership premise. Own runtime interval controls supplement that
proof. They do not waive PC-C16 or authorize native/OTA behavior.

Producer raw failed attempts were inspected, including the full-source pre-fix
getter suffix failure (superclass0/observationDelta0), initial stale signature,
explicitly superseded old release-timing assertions, chronology/refresh fixture
authoring and uninstrumented selection-getter attempts. This review's two initial
refresh failures are also retained: forward count2 did occur, but the fixture
incorrectly required a later native probe to observe scalar finish. The corrected
test binds SUCCESS_DONE and exact released/unregistered flags after real refresh
returns. Sources, outputs and the correction explanation remain in adaptations.json;
no behavior assertion was weakened. The membership failure remains required.

## Cleanup and limitations

Every version/compiler/JVM/D8 child was bounded60seconds and reaped. All owned
scratch, empty-source and TMP directories were removed, including failed runs.
Source/classes/dex, command maps, outputs and failure artifacts remain deliberate
review evidence. Deliberately retained host custody ends with its bounded JVM,
not a native reclamation or product retry claim.

No canonical/Git edit, native instance/process inventory, simulator/emulator/
physical-device run, UI automation/capture, signing, store, credential, customer
message, deployment or other-project operation occurred. Native ART/IME,
EditorInfo, batch/selection/composition, focus/hidden detach, accessibility/
TalkBack/OEM behavior, API28–35, immutable separate-repository FieldLog packages,
source-pair/CLI/public V2/canonical integration, release/OTA/operations and GA
remain pending or unselected. The current exact candidate requires PC-C16's
bounded correction and a new frozen independent review.
