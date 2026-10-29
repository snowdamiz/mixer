# Isolated Android view API boundary derivative

Prepared source and focused tests implement root's selected API29/30 view slice.
This packet supplies source/data custody only. No Java compiler, JVM, product,
Node oracle, SDK tool, native runtime or capture test ran in this lane.

The exact accepted input is the 16-source editor preservation/membership
correction, product tree
`a5e4888b96995bf768062bd9c2f1573dc440a4fe22270a205ab5550e79f625e4`.
The derivative product tree is
`d767f19554c88bd24f58663de268d7a80119522380cfeb4043c37d35b432a21e` using
the same sorted compact source-identity-map JSON algorithm. Only
`NativeAppearanceViewsV2.java` and `NativeRenderer.java` differ; the other fourteen
files and all 86 copied mechanical host leaves are byte-identical. The descriptor
remains 9,587 bytes, SHA256
`1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3`.
`product.diff`, `source-check.json` and `manifest.json` bind the exact bytes.

## Source changes and value contract

`source/NativeAppearanceViewsV2.java:45–56` defines the pure requirement check.
The renderer passes actual resolved recipes and corresponding decoded source
nodes at `source/NativeRenderer.java:455`, after packet/resolver validation and
before any shadow Record or preservation preparation. API28 rejects FieldRecipe
and selectable TextRecipe. The direct constructor checks corresponding source
`kind`/`selectable` at Views line 242. Direct bind checks the actual recipe and
source at line 328, including preservation calls. Both sites retain
`mutation.requireMutation()` first and reject capabilities before changing scoped
authority, calling `editorAvailable`, cancelling input, changing binding/geometry,
or touching a widget.

The source contract is precise: `UiPacket.java:9` maps absent values to the supplied
fallback; `UiPacket.java:32` admits only non-null scalar values and validates
accessibility properties as strings. `AppearanceResolverV2.java:312–314` derives
selectable text and field recipes from those decoded nodes. The accepted adjacent
preflight proposal (`verification/android-editor-api-boundary-proposal/proposal.md:370–378`)
requires property-presence refusal below30, including an explicit empty string.
Root confirmed that interpretation for this slice. A present `accessibilityValue`
therefore refuses below30. Omission below30 is a no-op. On API30+ omission still
passes actual null to clear native state; explicit empty still passes `""`.

The four existing authored drawable calls move unchanged, in cursor/center/left/
right order, to Views `Api29.authoredSelection` (lines 59–65). Its caller at line
370 uses actual `Build.VERSION.SDK_INT >= 29`. The same original Mutation is
passed and required immediately after each native setter. Drawable constructors
still receive the original Record and each call gets its own instance. No
selectable-text paint expansion was introduced.

Views `Api30.stateDescription` (lines 68–71) owns the V2 native state setter and
immediate original-Mutation postcheck. Its caller at line 344 uses actual SDK_INT.
Below30, the original no-call authority postcheck remains. Renderer
`Api30.stateDescription` (lines 65–67) isolates the existing V1 call; V1's original
property-presence refusal at line 30 is unchanged, as are its supported set/empty/
clear results. `expected-helper-topology.json` names all three expected new nested
classes. Their emitted shapes, constant pools, instruction order and DEX identities
have not been inspected.

The observer's `<36` guard is byte-identical (`NativeEnvironmentV2.java:95`), and
the renderer's guard remains exact (`NativeRenderer.java:925`). Full V2 renderer
preparation is still denied below36. Direct API29 component tests will not imply
lower-API renderer admission. The coordinator is byte-identical; no new native
call enters commitV2 → finishV2. Source comparison also preserves the broad
renderer scalar/journal region and `finishV2` through EOF exactly.

Independent interim source review caught capability checks preceding the existing
Mutation validation. That was corrected before freeze: stale/cleanup authority
keeps its original refusal priority, still with zero native effects. Focused tests
cover that ordering. The initial diff is not an accepted runtime failure and no
compiler or test experiment was used to make this correction.

## Prepared finite executable tests

`tests/ViewApiBoundaryTests.java` contains thirteen named groups and one narrowly
scoped main. It compiles the actual sixteen product sources with the copied 86
mechanical Android/JNI leaves. It does not start NativeOwner, register observers,
drain a product startup queue, use a renderer substitute, load the old suite, or
invoke the held matrix/launcher. Its operation tokens come from actual
OwnerLifecycleV2 decisions. Mutable host SDK_INT represents the actual Build field
read by unmodified product code; no SDK argument or synthetic support report is
injected into the product.

The source covers API28 field/selectable and API28/29 present/empty-state refusal
before constructor or bind effects; API28 ordinary absent text; direct API29 four-
setter order with no state setter; API30/36/37 set, actual-null clear, explicit-empty
and authored cursor/handle ownership/instance identity. The interruption loops
prepare 152 finite calls: each applicable one of the five setters at API29/30/36/37,
with ordinary/fatal throw, stale Mutation and stale nested reentry, at entry and
after native effects before return. They assert original thrown identity, no later
setter, no Mutation reacquisition, and scoped/changing restoration. Twenty stale/
cleanup constructor/bind calls retain original authority refusal across
API28/29/30/36/37. Independent observer and renderer entry tests exercise lower-API
denial at 28/29/30/35; V1 tests separately preserve property-presence refusal and
five widget/container shapes across 28/29/30/36/37.

These are prepared assertions, not passing counts. Full renderer rollback,
complete owner orchestration, callbacks on Android, platform class loading,
ART/OEM/IME/TalkBack/native parity, the historical 280 subjects and BCI evidence
remain outside this test. Old bytecode receipts do not transfer. Runtime has not
validated even the syntax of the new test source.

## Future bounded admission proposal

Root must independently review and select a separate hosted admission before any
runtime dispatch. The proposed closure has one host javac invocation of the exact
16 product + 86 mechanical leaves + one test source, then one JVM invocation of
only `dev.mixer.android.ViewApiBoundaryTests` with the frozen descriptor. Use the
reviewed pinned JDK, `--release 17 -proc:none -Xlint:all -Werror`, and bound each
child to 60 seconds. Test main has fixed loops, no nested processes, network,
threads, timers or default matrix selection. Preserve all output and failures.

Cross evidence is a separate compile-only pass against pinned official SDK37,
using the sixteen product files plus the byte-identical JNI signature leaf in
`tests/cross-leaf/NativeBridge.java`, followed by pinned D8 min-api28. The host test
and mechanical Android leaves must not be included in official SDK compilation.
Pin actual executable/library hashes and versions at admission. The prior packet
used JDK25.0.4.1 and D8 9.2.4-dev; those historical names alone do not identify a
new run. Inspect all newly emitted helper classes and exact method references,
then hash classes/DEX and preserve producer command/receiver/source identities.
No old BCI/descriptor proof can stand in for changed bytecode.

No runner, workflow, process launcher, remote dispatch or permissive admission
configuration is included. The held v5 complete-matrix startup experiment was
not retried, delegated, expanded or cleaned up; its holds and unknown cleanup
state are unchanged.

## Integration boundary

Canonical pair.5 is 22 SDK/23 adapter members, SDK
`bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0`, adapter
`2b001980e07e0d1c8a5139e79de6ad6ca83d8db66d386bd4f77689ab32a6325a`.
The held editor rebound also named pair.5 is 22/24, SDK
`4c2e74bbdb1c060ffa2219ed378d11ed390e7a4454b95df4a2ee72074bb9b5a7`, adapter
`9d47585c18c325888c6d87914808449f1a92e4a3839d02ce5c4ae8f15801c10c`.
This derivative is neither source pair. Root owns current SDK-axis reconciliation,
exact adapter topology, a new unambiguous identity and any canonical promotion.
No lock-only update or reuse of the shared pair.5 ID selects this code. Wire,
C/JNI, descriptor, source maps and public V1/V2 authority remain unchanged here.

Only the candidate directory was written. No Git/gh/network, compiler, JVM,
Rust/Swift/Elixir/product/Node oracle, VM inspection, process inventory/probe/signal,
native instance, UI/capture/phone, SDK repo/tag/release/publication, memory write or
extra-agent action occurred. Source reads, copying and guarded Python standard-
library filesystem/JSON/hash/diff checks were the only execution. One corrected
source-inspection path failure is retained under ignored `local/`; no test or
compiler failure exists because neither ran. All new native/runtime checks are
pending; this packet grants no API28–35 support, public V2 selection, release, OTA
or GA acceptance.
