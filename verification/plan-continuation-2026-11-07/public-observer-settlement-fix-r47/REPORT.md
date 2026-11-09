# R47 public observer settlement fix

Implemented the R45 P2 correction in the isolated R42 facade afterimage. This is ready for root composition with R48; it is not canonical adoption or native qualification.

`minimal-increment.patch` changes only `AndroidUINativeSurface.java`, relative to R42's exact afterimage. The complete replacement is `afterimages/native/android/app/src/dev/mixer/android/AndroidUINativeSurface.java`. No `NativeOwnerV2`, `OwnerLifecycleV2`, or `NativeEnvironmentV2` changes are needed.

After the existing owner-wrapper cleanup checks, close now reads the owned observer through the existing package-private `externalObserver()` and `cleanupLedger()` getters. An absent observer is legitimately unacquired. Each of the eight non-null observer slots must be `UNATTEMPTED` or `RETURNED`; `POSSIBLY_OWNED`, `REMOVING`, `FAILED_UNCERTAIN`, `DEAD_TARGET_UNCERTAIN`, and unknown values reject completion. Retained observer primary/fatal history also rejects completion. Returned cleanup does not establish platform reclamation.

The existing wrapper checks, including `ledger.primary()`, remain intact. The original terminal flag, owner retention, and first-failure latch now also cover R45's wrapper-returned/nested-uncertain case. Repeat close and matching revoke throw the identical retained exception without any removal retry. The parallel R48 refresh-admission/editor-replacement defect is not changed or masked.

## Executed host evidence

`controls/DeadObserverControl.java` extends the exact reachable R45 control: actual R42 facade/owner/core/coordinator/observer classes, unchanged R42 controlled Android/JNI/renderer leaves, and only the leaf's observer-alive fact changed for the counterexample. Reflection reads the retained private owner; it does not write product fields or ledgers.

- Baseline compilation passed. The extended test against the original R42 facade exited 1 at the expected first-close rejection assertion. Its all-eight-RETURNED and unactivated/activated-but-uninstalled positive cases passed before that assertion. Raw evidence: `controls/raw/baseline-control.{stdout,stderr}`.
- Candidate strict compilation and control passed: **147 checks**. The exact dead-target control retains slot 3 as `DEAD_TARGET_UNCERTAIN(5)`, wrapper unregister as `RETURNED`, and wrapper primary as null; first close rejects, repeat close/revoke preserve exception identity and ownership, every retained slot remains unchanged, and recorded effects/removal counts do not increase. Making the leaf alive again before repeated calls still produces no retry.
- The same control injects one removal failure at each of the eight slots through the existing leaf hook. Every slot records `FAILED_UNCERTAIN`; primary history remains exact; repeat close/revoke retain the first exception with no later cleanup effects. All-eight-RETURNED and absent/unacquired-observer lifetimes close successfully and repeat without effects.
- Existing external-package public API controls: **46 checks passed**.
- Existing external-source owner controls: **24 checks passed**.
- Candidate `javap -public` output for the facade, Frame, and Events is byte-exact to R42's recorded public API output. No new public API or private observer getter was introduced.

All new strict compilations use JDK25 `javac 25.0.4.1`, `--release 17 -Xlint:all -Werror -proc:none -sourcepath ''`. Only the facade and extended control are compiled over R42's actual admitted host classes. Those classes and leaves are read-only inputs; the new classpath places the isolated R47 output first. The existing controls are the original R42 compiled controls, rerun against that replacement facade.

`commands.json` contains the nine exact command argv, working directories, owned PID/PGID, exit codes, elapsed time, and raw stdout/stderr paths. Two targeted compile commands used **1.904 seconds** total campaign time (rounded up); the bound was 120 seconds, with 20 seconds reserved for cleanup. Every owned command group was observed absent; cleanup used zero seconds. `budget.json` records the unrounded observation.

`inputs.json` identifies the direct sources, descriptor, original host-input receipt, and actual reused class bytes by SHA-256. `handoff.json` identifies the patch and exact afterimage hashes. `SHA256SUMS` records the delivered files. Parent-provided revision is `fd373fc8fed2329b31b72c918f6745e183cbb517`; source114 is `5814b0dab60dfe3fdbce2791644499fc0362072a99bf9034c7f28ea266577608`. R42's supplied source tree digest is `b5864c753b3412d4ba63ed941bc61680a944f88d3961326b788b5b1e716476cb`. These identifiers were not refreshed through Git. Frozen R42 facade/owner/core/coordinator/observer source copies were independently hashed and matched R42's host-input receipt.

## Limits and root handoff

All writes are inside this R47 directory. No canonical changes, Git operations, delegation, APK/Swift/native builds, devices, signing, CI, or production operations were performed. Native integration, combined R47/R48 rebuild, and the single slice review remain root-owned. No historical hold is released.

The initial recursive filename discovery was too broad and traversed names outside the assigned lookup scope. Subsequent discovery and content reads were immediately narrowed to R42/R45 and the named admitted R42 build inputs; no held file contents were opened or used, no held process was probed or signalled, and no held resources were changed. Root status/work-graph/gate updates remain root-owned because this task permits writes only in R47.
