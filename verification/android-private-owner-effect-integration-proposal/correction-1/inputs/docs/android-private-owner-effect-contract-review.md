# Private Android owner contract: independent source review

The original proposal **needs contract correction before implementation
selection**. Two required ownership paths have no callable seam in the proposed
surface, and its renderer acceptance row permits compilation in place of the
behavioral subject it needs. These are design findings against a preparation
packet; no new product implementation was selected, implemented or accepted by
this review.

The reviewed proposal is
[`android-private-owner-effect-integration-proposal.md`](android-private-owner-effect-integration-proposal.md),
SHA-256 `35dcf9d74fc58a26ca99a9b6678454313a2ce3e773bf292627d76b7e0fa6cdc0`.
Its manifest is
`7547220cc7f1ba6648ca2cbb3fdf96e402b5b3af9abf68906263be57688838a7`:
36 members, 606,635 bytes and 25 frozen inputs. Independent byte verification
passed without running the producer's checker. At review context
`b45963c03816112972499bd60073039f36916272`, tree
`9a54e2d84d7c15c4b50a3d69e6eaa78ead28f61c`, all 24 non-`PLAN.md` current inputs
match their frozen originals. The sole input difference is execution-plan
context; relevant Android and Swift profile/export sources are unchanged.

The observer predecessor is now separately accepted. Its root acceptance receipt
is `ca6616f73fb7c342a3a74747c571c29f78ab3b6dacf7c3227375a6807295c022`.
The proposal's statement that predecessor acceptance was pending describes its
older read boundary and is not a new source defect. That acceptance does not
cover the proposed two-phase registration or new renderer binding.

## Required corrections

### C1: expose callback-capable input cancellation through the coordinator

Proposal lines 90–105 expose `NativeCoordinatorV2.sealGatesScalar()` and
`closeFromOwner()`, while `cancelInputV2()` exists only on `NativeRenderer`.
The proposed owner field roster at lines 118–124 holds coordinators, not their
renderer; the real coordinator keeps that renderer private at
`NativeCoordinatorV2.java:11`. The scalar method explicitly forbids callbacks,
and `closeFromOwner()` is idle-only. Consequently the stated surface cannot run
the separately required toggle cancellation after sealing while an operation is
still active and close is deferred.

This is observable work: current renderer cancellation iterates current and
pending record sets at `NativeRenderer.java:355–357`, and
`NativeAppearanceViewsV2.java:622–626` calls `setPressed`, `invalidate` and the
retained parent's interception callback. Leaving it until deferred disposal
keeps gesture/parent ownership outstanding for an active or never-returned
operation. Folding it into `sealGatesScalar()` breaks the immediate scalar
barrier.

Freeze an explicit coordinator cancellation bridge, for example
`cancelInputFromOwner()`, with these minimum semantics:

- It enforces main-thread ownership, may run while `active`, and does not use the
  operation-entry or disposition path. It never creates a session, performs an
  engine operation, finishes a transaction or destroys/disposes either owner.
- Owner dirty/terminal handling first closes shared authority and actual current
  and pending gate flags, then invokes the bridge on the held opening/adopted
  coordinator. State when both fields identify the same coordinator must not
  cause duplicate work. A later acquired coordinator starts sealed.
- Publish a cancellation-in-progress/consumed state before native callbacks.
  Reentrant cancellation cannot recurse over the same records or bypass the
  scalar barrier. A dirty cancellation that encounters another dirty callback
  leaves gates shut and preserves the required subsequent drain.
- Attempt the bounded current/pending record set despite a leaf failure. Retain
  first ordinary failure and first fatal `Error` in fixed diagnostics before
  best-effort suppression. A failure terminally retires the lifetime; independent
  Handler cancellation, unregister and eventual coordinator disposition still
  get their attempts. Do not relabel toggle cancellation as Handler
  `CANCEL_QUEUED`, or claim actual parent release because a call returned.
- Tests inject ordinary/fatal failures at the first, middle and last native
  cancellation positions, including reentry, while an operation is active.
  Observe the actual flags before callback bodies and distinguish deferred
  disposal from completed cancellation attempts.

The spelling is a recommendation for the versioned correction; root owns the
final coordinated signature. The callable path and its ordering cannot remain
implicit when dependent lanes freeze against the surface.

### C2: freeze one terminal report route for renderer self-retirement

Proposal lines 196–199 require a renderer that retires itself to seal shared
authority and notify coordinator/owner outside the commit/finish interval. The
proposed renderer receives only observer, fence and native-input events.
`Fence` holds scalar fields; `Events` carries input. The observer's declared
surface exposes registration, binding, capture and ordinary invalidation, and
`Change` at line 79 has no renderer-retirement reason. The owner implements the
observer sink, but no renderer terminal-report call is defined.

The real renderer can retire from interaction exhaustion
(`NativeRenderer.java:86`), committed capture failure (`:97`), and rollback
failure (`:309`, `:326`). Setting the shared terminal flag alone prevents input
but cannot drive the unchanged core's terminal cleanup decisions or report the
actual failure. Calling ordinary `Observer.invalidate()` alone only marks the
core dirty; `OwnerLifecycleV2.invalidate()` can leave it LIVE and schedule work
(`OwnerLifecycleV2.java:111–114`, `:200–205`, `:229–234`).

Freeze a single bound terminal-report route, either an observer method delivered
through the same owner sink or an explicit private renderer-to-coordinator/owner
callback. It must validate exact bound identity, distinguish terminal retirement
from ordinary invalidation, retain the actual cause/first fatal, close scalar
authority before dispatch, and issue unchanged `core.close(lifetime)` when no
more specific accepted core entry exists. The adapter ledger retains the
specific cause; it must not rewrite the core's `CLOSED` reason. Delivered reports
after retirement are inert after the main-thread check. Repeated reports cannot
repeat resource disposition or recursively report retirement through cleanup.

The report is forbidden inside the successful commit-to-finish interval. An
in-interval direct fence validation can fail closed; callback-capable reporting
and independent cleanup follow on the failure path. Freeze how a fatal concrete
current/capture check reaches this terminal route too, rather than leaving an
exception from a draw or input gate with a live outer core.

Require executable controls for interaction exhaustion, failed capture,
failed rollback and fatal current-check failure with actual renderer code.
Assert terminal core state, preserved cause/fatal, no new input/drain authority,
and one idle/deferred coordinator disposition as applicable.

### C3: require an executable concrete renderer subject and close its seam roster

The primary host join deliberately replaces renderer and JNI leaves (proposal
line 375). That can test actual owner/core/coordinator/observer ordering. It
cannot prove concrete gate or native-view implementation. The existing renderer
leaf says so in its class comment and sets scripted `Rig.open` fields and
`renderer.finish.before/after` hooks; it contains no actual Gate, Input, Record,
IME or setter implementation.

Proposal line 380 says concrete renderer/native-view **host or compile** closure.
A compile-only closure cannot satisfy the same row's behavioral assertions or
line 377's demand to observe actual current/pending gates at setter reentry.
Replace that alternative with a mandatory bounded executable closure using the
actual selected renderer and needed actual `NativeAppearanceViewsV2` methods,
with independently controlled Android/JNI leaves. Freeze exact production
subjects, exact substitutes, callback sites and observations. Keep full SDK
compilation as an additional signature check.

The roster must include work before a candidate is published, not just
`attachV2`'s coarse `faultV2()` calls. Concrete examples are:

- `Record` construction/defaults (`NativeAppearanceViewsV2.java:88–141`,
  `:203–210`), including multiple setters and nested constructor hierarchy adds;
- `Record.bind`, text/title helpers, `installChildren`, root/group/title layout
  and renderer rollback, where multiple native calls currently occur between
  outer checks;
- `NativeSwitch.setEnabled`/`setFrame` (`:700–703`), where `cancelTouch()` may
  reenter before `super` mutates the native view; and callback-driven navigation
  relayout (`:505–518`);
- actual Gate/Input checks, scalar current/pending sealing, new IME connection
  refusal before superclass acquisition, retained connection edit rejection and
  both corrected report/cancellation routes.

Use direct terminal plus exact-operation checks between callback-capable
transaction mutations. For native callbacks outside a transaction, freeze the
corresponding live-presentation/terminal guard; do not require a non-null
operation token for ordinary valid native scrolling. Cleanup callbacks have a
separate bounded best-effort path and must never reopen authority.

Source guards and compiled-bytecode inspection remain useful supplements for
the successful commit/finish interval. They are not behavioral substitutes and
do not authorize OTA or establish real Android framework/JNI behavior. This
correction is implementable with host work during the pause.

## Contracts that are otherwise coherent

| Boundary | Source-grounded review result and required implementation check |
| --- | --- |
| Stored observer before registration | Two-phase `NEW -> REGISTERING -> READY/RETIRED`, callback fields assigned before first add, and deferred core unregister completion solve constructor partial publication. Preserve all eight accepted slots, exact targets, before-add ownership, uncertain failing add and acquisition unwind. Renderer binding is one-shot, READY-only, exact-context/identity. Re-test actual changed observer; predecessor tests cannot cover new APIs. |
| Inert coordinator and late acquisition | Moving session create into initial operation lets owner hold the coordinator before callback-capable acquisition. Main-thread/context checks, allocation and binding may happen at construction; no listener/session/view acquisition or capture may. A late create handle is retained for exactly one later cleanup after its call returns; a never-returning call stays deferred. |
| Exact accepted core | Keep the 12,473-byte core `4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6` unchanged, move its sole canonical path, update host runner and export it once. Exact drain, operation, lifetime, presentation, cleanup and coordinator identities have distinct purposes; no forged/substituted tokens or copied core model. |
| Readiness and focus | Probe actual Activity/root/Window/token/size/insets, retain a stable Window+token identity, and re-probe queued delivery. `WindowFacts` has no focus field: explicitly seed/update `core.focusChanged` from actual root focus in the corrected entry mapping, alongside lifecycle resume/pause/stop. Input checks must not rely on merely reading focus into unused probe state. Zero-size/inset-less roots wait for a real notification. |
| Scalar barrier and transaction authority | Direct shared fields plus current/pending gate flags close before callback-capable cancellation, probing, core allocations or cleanup. Terminal and dirty sealing differ. Mutations use exact operation identity, not draw/input flags that are deliberately shut during normal transactions. Apply C1–C3 to the concrete setters and self-retirement paths. |
| Commit then finish | Existing coordinator `:100–105` has the successful branch, direct finish call and packet assignment. Preserve no callback/capture/allocation/native mutation on that path. Trusted direct fence reads are compatible; `core.permits` and arbitrary predicates/sinks are not. Review actual selected source/bytecode as well as counted leaves. Core completion/presentation publication occurs after finish and active-operation finally. |
| Exact-packet refresh and input | Existing refresh `:146–198` uses retained `committedPacket` without engine transaction calls. Owner retains no packet/input copy; ordinary accepted input is a synchronous stack payload. Dirty during any operation leaves gates shut and creates at most one later drain. Real coordinator + counted JNI leaf controls prove call/identity claims; renderer leaves cannot prove native gates. |
| Current tuple mismatch | Route an actual synchronous mismatch through the bound observer after scalar sealing so the core is dirty and scheduled. Preserve exact installed/capture/current-record and tuple checks. Terminal failure uses C2, not an ordinary dirty report. |
| Owned Handler work | Runnable stores its exact token. Consume only its owned slot before fresh probing; stale/foreign delivery cannot steal a newer slot. False/throwing post is terminal. Consume cancellation ownership before `removeCallbacks`; ineffective removal stays fenced without replay or polling. Re-check each effect after callback reentry before applying stale batches. |
| Cleanup and allocation failure | Preallocated independent owner/component slots retain attempted/returned/failed/deferred/uncertain outcomes and first fatal even after an ordinary primary. Core allocation/completion failure seals and uses direct independent cleanup without fabricated absent tokens. Operation remains held until its actual finally returns. Internally retired coordinator exposes retained outcomes; close must not repeat them. No OOM/native hang reclamation guarantee is possible. |
| Caller migration | Public `MixerActivity` remains the two-argument V1 path and retains its padding listener. Private integration Activity creates/starts owner and forwards only lifecycle entries; instrumentation waits for actual owner presentation and uses owner input. Renderer-only instrumentation owns explicit observer/fence and real-core token fixtures, with distinct dedicated roots and one inset setter per root. Every replacement/finally closes both component owners. |
| Future fixed source map | Current profile2 has 22 SDK / 20 adapter members and no core/owner source. Adding new owner plus moved core coherently gives 22 adapter members if no extra source is selected. Compiled `AndroidSDKCompatibility` remains the sole map authority; `AndroidProject.snapshot` exports that map. Root selects new ID/hash literals only against frozen candidate bytes; reject old/edited/recomputed locks before tool/output access. Preserve SDK/descriptor/wire identities by actual comparison, not assumption. |

## Evidence and handoff

The independent packet is
[`verification/android-private-owner-effect-contract-review/`](../verification/android-private-owner-effect-contract-review/README.md).
It retains the exact original proposal packet, all current read inputs, accepted
observer receipt, Python/Git tool versions and binary identities, source/tree
context, argv/results, current/frozen drift inventory and line-numbered source
excerpts. `custody.py` and `inspect_sources.py` are bounded offline custody and
inventory checks, expressly **not product tests**. The producer checker was not
used as an oracle. There was no product, profile, metadata or predecessor packet
edit, commit/push, network/install, signing, credential, process-discovery,
native-runtime, UI or capture action by this lane.

Root can request one versioned contract correction covering C1–C3 and the
explicit focus/callback entry mapping, preserve the original packet, then select
the coherent implementation and separate verifier only against the corrected
frozen surface. This review recommends correction, not implementation acceptance.
Host development and cross-compilation may proceed after selection without
waiting for phones. New native runtime checks remain pending under the active
pause; physical/device/accessibility, separate-repository immutable published
FieldLog, signing/store/operational and accountable GA qualification remain open.
