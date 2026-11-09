# R50 independent combined correction review

PASS for the exact three R49 Java overlay inputs. No executable defect found in this slice. One independent harness passed 451 assertions against newly compiled actual facade, owner and lifecycle core, with the actual existing coordinator and observer and unchanged R42 Android/JNI/renderer host leaves. Runtime code-source output confirms all three candidate classes loaded from this review's classes directory first.

The same harness, with R42 classes first, failed both discriminators as expected: `baseline-observer.stderr` reports `expected rejection` because old close returned; `baseline-focus.stderr` reports `inadmissible native capture delta=1`. These controls make the candidate pass distinguish the corrections from the old behavior.

Executable coverage:

- Observer settlement: all eight slots tested against UNATTEMPTED, POSSIBLY_OWNED, REMOVING, RETURNED, FAILED_UNCERTAIN, DEAD_TARGET_UNCERTAIN and two unknown integer states. Only UNATTEMPTED/RETURNED pass the actual private predicate. Primary and fatal histories reject even with otherwise settled slots. This matrix directly varies a retired observer's ledger for predicate policy coverage; it does not claim every synthetic state is a reachable Android outcome.
- Reachable teardown: dead focus target produces slot3 DEAD_TARGET_UNCERTAIN while owner unregister is RETURNED and owner primary is null. First facade close rejects. Controlled failures separately reach FAILED_UNCERTAIN in each of the eight real removal calls; original primary identity survives. A fatal removal Error retains that exact Error. Repeated close/revoke retains the same failure object, owner, observer and slot outcomes without further native effects/removal attempts, even after restoring target liveness. Terminal activation/install refuse.
- Success: all eight real removal calls RETURNED and repeated close/revoke adds no effects; activated but uninstalled/unacquired observer is accepted.
- Refresh: already queued focus-loss, pause, stop and focus loss first observed at drain delivery defer capture. Both focus/resume orders recover with exactly one refresh. Dirty state, committed packet identity/bytes and sealed draw/input gates survive deferral. Stale work cannot consume the successor drain. Close while deferred retires directly, returns all eight removals and cannot be revived by stale delivery. Recovery does not create/prepare/commit a business-engine presentation.
- Genuine admissible capture failure retains its exact owner primary through terminal facade close. Legacy constructor scheduling remains unchanged. V3 initial schedule and queued initial drain both require foreground/focus.

R45 REPORT/control, R47 patch/control and R48 patch/tests/result were inspected. From R46 final-context-log.stdout, only the first relevant exception block was read: `NativeField.available` rejected editor replacement during the old owner refresh path. The reviewed deltas add observer settlement reporting and V3 render admission; they do not change editor refusal, capability or UNKNOWN handling. The executable proof here uses the renderer host leaf, so it adds no actual-editor qualification. R48's separate real-field discriminator and legacy 231-case result remain existing evidence, not fresh executions in this review.

Identity before and after execution matched R49's manifest exactly:

| Afterimage | SHA-256 |
| --- | --- |
| R47 AndroidUINativeSurface.java | e3fcff2348d06bc57ebb045c708adbfb9e5709e4c09fe2f78086d4f8bb008cfe |
| R48 NativeOwnerV2.java | 0ce92151b26c7375071cf200d1808277c397feda53983aff2161a5d4df97dbf9 |
| R48 OwnerLifecycleV2.java | 51db7469d68801bdbaf25375c836814ceeec2b638dda24d35ca64d75a03ebfe4 |

`overlay-before.json` and `overlay-after.json` retain exact paths and observed hashes. `inputs.json` includes the existing host class hashes, descriptor and harness hashes and review source-set digest `012bd50fa71d48dad36269cc99a175750db26b49f3fd31710f1fb6ac0a48acd3`. Provided root revision is `fd373fc8fed2329b31b72c918f6745e183cbb517`; no Git lookup or mutation was performed.

One material javac invocation used JDK 25.0.4.1, `--release 17`, all lint warnings fatal, processors 2 and heap 256 MiB. All Java runs used `-ea`, processors 2 and heap 256 MiB, sequentially. JDK command active time was 1.464 seconds within the 150-second bound; cleanup time was zero within the 20-second bound. All five owned JDK groups were observed absent. Exact commands/working directory/status are in `commands.json`, versions and raw results in `raw/`, bounded rerun command in `run.py`, and compact outcome in `result.json`.

The subsequently supplied canonical runner and CI step received a narrow source/input inspection, not another runner execution. The runner selects the canonical closure-A sources plus platform/facade, validates hashes for development overlays, compiles into fresh classes, runs all four explicit main classes, and cannot set passed=true after a nonzero command or observed surviving process group. The CI invocation omits the overlay; its sparse checkout includes required Android sources and descriptor and its artifact wildcard includes this evidence. No wrong-input fallback or false-pass path was identified in that inspection. The two newly copied correction tests match their reviewed originals byte-for-byte. At inspection time the canonical facade was still absent and canonical correction adoption was root-owned, so no-overlay CI success is not claimed; it requires that adoption. `runner-inspection.json` records the exact runner/workflow and observed source identities.

Only this R50 directory was written. No native/APK/Swift/ADB/device/signing work, child tasks, CI polling, Git changes, canonical edits or held-namespace access occurred. No device cleanup was needed. Root's separately reported successful R49 API37 integration remains root evidence. Visible-but-unfocused/modal drawing parity, physical phones, API floor, immutable published packages and GA remain pending; this PASS does not qualify them.
