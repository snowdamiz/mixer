# Independent review of the Android API 28–35 V2 prerequisite

The exact prerequisite contract is **accepted for root selection of bounded A**:
isolate public environment observations, represent their availability honestly,
and retain both API 36 admission guards. No material blocker to that source slice
was found. This accepts a contract for implementation; it does not accept an
implementation, choose a source-profile ID, enable any new rendering context, or
qualify a native/compiler/public/OTA/GA gate.

The reviewed candidate is the producer manifest SHA-256
`7a006a00ed71e014efb9e854fe36b7fcacc09dd5bccae101a193d042407323ad`:
46 sealed members and 28 frozen sources, source-map digest
`276bdb5d0285cd77ecbd5306efa4eacf4fc72798768210c17662816deda709b3`.
The inherited context revision is `d275c072b6c89b8e99213e4eb4dafdc4722f5f40`.
Root reported its private C5 acceptance committed at `fb4c8f07`; this lane did not
inspect Git or claim a live HEAD/metadata identity. The producer's recorded
`PLAN.md` drift remains visible and is not refreshed. The prerequisite and this
review use the frozen product/contract/source bytes, rather than treating the
producer's failed live-source check as a pass.

The independent [receipt](../verification/android-api28-v2-support-prerequisite-independent/receipt.json)
and [source/API/control output](../verification/android-api28-v2-support-prerequisite-independent/command-1.stdout.txt)
record the command, tool version, exact evidence hashes, actual result, and scope.
The producer's checker also passed when rerun with `--manifest`; its command and
stdout/stderr are retained separately. This lane imported no producer module.

## Source and platform findings

The installed official SDK metadata at
`/opt/homebrew/share/android-commandlinetools/platforms/android-37.0/data/api-versions.xml`
has 5,911,928 bytes and SHA-256
`9fd47aaab29946a5f5d179797365b2d04e38132d2e7e942f5ea8504e41e6c8e5`.
Independent parsing verifies 34 exact class/member signatures. Their floors match
all 14 producer API categories: high contrast 36; system contrast 34; font-weight
adjustment 31; typed safe-area query 30; cursor/selection setters 29; state
description 30; IME consumption 31; TextAttribute overloads 33; replace/handwriting
34; collection factories 30/31; weighted Typeface/fallback spacing 28; platform
dimension conversion 1. This is official SDK metadata inspection, not a compiler
or runtime test.

The live [AccessibilityManager reference](https://developer.android.com/reference/android/view/accessibility/AccessibilityManager#isHighContrastTextEnabled())
independently confirms the API 36 public read and listener surface. Its advice
that platform rendering may handle high contrast does not prove V2's explicitly
painted controls and authored drawing satisfy the shared visual-accessibility
contract. The frozen V2 contract explicitly rejects unknown required contexts.
Keeping API 28–35 closed is justified without raising the product's proposed
API 28 baseline. A different rendering strategy remains a separate design.

The [UiModeManager reference](https://developer.android.com/reference/android/app/UiModeManager#getContrast())
defines a range of −1 through 1 with neutral zero. The frozen observer rejects
only positive values, so negative, NaN, and other malformed results cannot be
described as demonstrated neutral contexts. Selecting finite exact zero is a
conservative correction consistent with V2's authored colors; it does not claim
all contrast settings are implemented.

The [Configuration reference](https://developer.android.com/reference/android/content/res/Configuration#fontWeightAdjustment)
distinguishes the API 31 undefined sentinel from a known adjustment. Requiring
known zero makes that distinction explicit. Its
[fontScale guidance](https://developer.android.com/reference/android/content/res/Configuration#fontScale)
also supports preserving actual platform SP/DIP conversion rather than replacing
it with a linear multiplier. This review does not assert that stricter sentinel
rejection will preserve the number of currently admitted API 36 configurations;
new rejection receipts must record their actual native context when testing resumes.

The legacy [system-window inset definition](https://developer.android.com/reference/android/view/WindowInsets#getSystemWindowInsetBottom())
includes occlusion by the IME or other system windows, while
[systemBars](https://developer.android.com/reference/android/view/WindowInsets.Type#systemBars())
excludes IME and display cutout. Therefore a legacy/max/subtraction approximation
is not established as the exact typed `systemBars | displayCutout` source.
The proposal correctly labels exact semantics unavailable below API 30. This is
an inference from documented definitions, not an observation on an older device.

The [Settings.Global reference](https://developer.android.com/reference/android/provider/Settings.Global#getFloat(android.content.ContentResolver,%20java.lang.String))
documents a nondefaulting float read that throws when missing or nonnumeric.
The frozen observer uses a defaulting read of 1, which hides both cases. Requiring
an actual finite nonnegative result is implementable using the public API and
does not require a hidden setting, new dependency, write, or permission change.

Direct inspection confirms both independently authored SDK guards, the actual
eight observer acquisition/removal slots and retained targets, a complete second
synchronous read, the V2 state-description skip, unguarded API 29 field setters,
the later-API anonymous InputConnection signatures, and installed catalog/font
rejection. One important reachability detail is that the current API 34/36
listener field initializers occur before the Observer constructor body executes.
The existing constructor guard is an admission rule, not proof that class loading
or initialization avoids later symbols. A must move those types and creation into
the guarded adapter classes; adding conditionals only at the old call sites is
insufficient. Actual Android verification/linkage remains pending.

The 28 files are an exact bounded evidence closure, not a complete transitive
Android application or executable-library closure. In particular the evidence
shows modern collection factories in the accepted core and no explicit library
desugaring configuration in the named D8 calls. It cannot establish that a new
reader makes the whole private lane API-28-compatible. The proposal states this
limit and keeps the library/editor/inset/accessibility-value blockers separate.

## Exact implementation boundary accepted

Root can select the proposed owned files and stricter policy now, then assign an
independent implementation lane. Selection must retain these conditions:

1. The new platform-reader base surface, fields, return types and signatures use
   API-28-safe public types. Isolate API30/31/34/36 symbols and listener objects in
   separately emitted guarded classes. Do not accidentally add newer collection
   factories to the base diagnostic path. Finite host leaves must check branch
   reachability; native linkage remains a later pending receipt.
2. Availability-bearing immutable internal observations are pure data. Only
   `KNOWN` carries a value. Missing APIs, undefined data, missing/denied settings,
   and read failures cannot become false/zero/default 1. A diagnostic snapshot
   starts no subscription, owner, coordinator, session, or readiness transition
   and cannot mint the private capture. It is not public support authority.
3. Select explicit YES/NO night mask; resolved LTR/RTL; actual first locale;
   existing density/body bounds, platform conversion, twelve anchors and ties up;
   exact typed insets; known zero font adjustment; finite in-range exact-zero
   contrast; known false high contrast; and finite nonnegative animator scale.
   Known zero motion remains reduced motion. For locale validation, preserve
   the shared bounded, well-formed Unicode/non-control contract on the actual
   native result. Do not add an English/region whitelist or invent a replacement
   locale. Any extra locale grammar or rejection of `und` needs explicit root
   selection and cases; the proposal does not require that extra restriction.
4. Recoverable reads may produce `READ_FAILED`; an `Error`, linkage failure, or
   fatal native effect must preserve existing terminal/fatal precedence and
   cleanup. No broad `Throwable` catch may turn fatal uncertainty into neutral
   data or continue a successful owner.
5. Construct each immutable manager/listener/executor registration handle before
   attempting add. Observer records possible ownership before invoking add and
   retains that handle through reentry/throw. Remove using the exact retained
   target/listener once, with the observer's existing eight-slot ledger. The
   adapter supplies no second lifecycle state machine, generation or scheduler.
6. Every callback preserves the main-thread and retired barriers. Keep one
   Observer, one native capture mint, its once-only renderer binding, complete
   second synchronous read, existing scalar terminal fence and exact owner/drain
   identity. Do not call an adapter or other native work inside successful
   `commitV2` through `finishV2`. Retain both `<36` guards and current V1 Activity
   routing. Preserve descriptor/resource/font/unsupported-operation failures.
7. Select an immutable source-pair profile for the new Java reader plus the
   edited observer and retained closure, without rewriting historical receipts.
   Review the final bytes independently. Both common CLI and rendered driver
   must reject old, missing, changed, or recomputed locks before tool/output
   access through the existing compiled policy authority. No profile ID or final
   digest is invented by this review, and no auto-refresh is authorized.

These conditions elaborate existing proposal requirements; they do not add a
request for device execution before source work. Compiler/host-source checks can
advance the bounded development slice while native execution is paused. Changes
to the owner core, renderer/views/editor, coordinator, JNI, Swift state, descriptor
schema or public routing require a separately amended scope.

## Controls, limitations and disposition

Independent checks reproduced all nine SDK rows, including every availability
boundary and closed pre-36 admission. The independent finite observation model
rejects 55 malformed/unsupported cases and admits four known-neutral contexts
with valid motion values. Controls include unavailable-with-false/zero values,
unknown statuses, missing known values, forged known-neutral pre-36 data, font
sentinel/nonzero values, negative/nonfinite/nonzero contrast, high contrast, bad
motion and unknown observations. This model has no product capture, Environment,
or readiness object; these are specification controls, not 59 native tests.

The producer's six negative controls are meaningful guards against accidental
specification promotion because they mutate the actual contract passed to its
validator. They do not prove platform calls, API isolation, observer lifecycle,
tool-before-output refusal, or native effects. Their equality-based rejection is
appropriately labelled source/spec consistency. The existing native support
matrix and new implementation tests still need independently authored actual
reader/Observer leaves, negative add/remove/reentry/fatal cases, exact source
profile migration controls, and eventual native compilation/linkage/runtime.

No overreach or unnecessary weakening blocks A when the accepted boundary above
is retained. The stricter rules intentionally reject uncertain contexts and may
reduce existing API36 admission; they must be named in the new source profile and
receipts, rather than retroactively called the old behavior. Availability alone
must never be promoted to rendering support. Actual API28–35 rendering remains
blocked on high-contrast/other preference semantics, exact pre30 safe area,
library compatibility, editor class linkage/appearance, and pre30 native value
semantics. Public routing remains an additional distinct gate.

Computer use, capture, UI automation, simulator/emulator/physical tests and process
inventories were not run. No native compiler was run. No native or capture process
was started, so this lane had no owned cleanup to perform. Other project processes
were not inspected or changed. Product code, producer packet, root metadata, Git,
dependencies, credentials and publication were not changed. Native runtime,
TalkBack, design parity, final phones, immutable published separate-repository
FieldLog, OTA, signing/store/operations and accountable GA evidence remain pending.
