# R48 owner refresh admission

Ready for root's combined R47/R48 review and native proof. The SDK diff changes only `NativeOwnerV2.java` and `OwnerLifecycleV2.java`; `minimal-sdk.patch` and the two `afterimages/` files are the delivery. No facade, observer, renderer or field source changed.

H1 is supported by execution. The original core's schedule and drain decisions only checked window readiness. Focus/pause/stop dirtied the presentation and could then start capture even though that owner's foreground/focus lifetime was inadmissible. V3 now requires foreground and its own window focus at both scheduling and queued delivery, before starting initial/refresh operations. Deferred work retains dirty state and the committed packet, with the existing draw/input seals. Resume and focus gain coalesce into one current refresh. Close retires directly without refreshing. Resource identity, currentness, unsupported-capability checks, genuine primary failures and cleanup handling remain in their existing paths.

H2 did not require a phase correction in the executed discriminator: the actual unchanged `NativeField` stayed `IDLE` during window-focus loss, rejected `available(true)`, and admitted it after focus gain. Separate negative controls still rejected CREATING, DRAINING, CLOSING and QUARANTINED. These calls used hash-verified R25 closure-B classes whose product source bytes match R42. Its fixture uses the legacy owner; it proves the common field denial and phase distinction, not fixed V3 native integration.

| Executed control | Baseline | R48 |
| --- | --- | --- |
| Targeted owner admission scenarios | 3 pass / 12 fail | 15 pass / 0 fail, 91 assertions |
| Actual unchanged field discriminator | 12 checks pass | Field unchanged |
| Unchanged external-source controls | 24 checks pass | 24 checks pass |
| Unchanged legacy owner closure A | Historical input | 231 cases / 1,253 assertions pass |
| Strict SDK37 Java compilation | R42 input | Pass, release 17, all lint warnings fatal |
| Public facade / Frame / Events `javap -public` | R42 input | Byte-exact signatures |

The 15 scenarios cover fresh pause/stop/defocus, already queued pause/defocus, a focus loss first observed at delivery, both focus/resume orders, stale work before and after recovery/close, close while deferred, immutable packet identity/bytes and sealed app input, a genuine capture failure retaining its exact ledger primary, foreign-window rejection while deferred, and initial admission waiting for foreground/focus. Closure A uses the unchanged explicit inert renderer/framework/JNI leaves. Its capture count is the H1 discriminator; it does not execute Android native views. The R46 native failure supplied in the brief remains the actual runtime failure evidence.

The profile selection is explicit: only `MEASURED_MULTILINE_RETIREMENT_V3` gets the stricter render admission; the existing legacy/V2 constructors and scheduling behavior remain. The new internal boolean constructor is called by the owner, so merge both files together. No public SDK API changed. Both adapter source hashes change: root must bind the combined R47/R48 source and profile after review/proof. The source114/Pair12 input and descriptor remain immutable; this lane does not reseal them or qualify a published package. Synchronous initial installation still requires a completed current presentation; callers cannot treat an unfocused deferred installation as ready.

Visible unfocused/modal UI drawing is unqualified. Deferral preserves the existing seals and does not claim that an old presentation remains drawable while invalidated. Draw and input remain distinct: the tested resumed presentation can be current/drawable while the application's input gate stays sealed. No callback allowlist, new field exception, renderer currentness relaxation, arbitrary wait, poller, ledger suppression or business-presentation replay was introduced.

Exactly two compiler invocations ran sequentially with ActiveProcessorCount=2, within the 240-second active/30-second cleanup bound (7.104 seconds active, zero cleanup time). Every owned command group was observed absent. No devices, ADB, Swift/APK builds, children, Git, canonical source or held namespaces were accessed. Evidence and class outputs remain in this lane; no native test instance was created. Root owns composition, independent review, current source/profile binding and actual APK execution. Published-package, visible-unfocused/modal, physical-phone and GA qualification remain pending.

Raw commands/versions/output: `run-1/commands.json`, `run-1/*.stdout`, `run-1/*.stderr`. Exact input/source/class provenance: `provenance.json`, `run-1/source-inputs.json`, `run-1/sdk37-inputs.json`. Machine handoff: `handoff.json`; compact results: `result.json`. The two compilations were the fixed closure A plus these hand-written tests, and the complete 21-source R42 SDK roster with only the two owned replacements against the official Android37 jar. Baseline execution reused verified existing A/B bytecode and did not consume an extra compile attempt.
