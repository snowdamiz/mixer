The deadline correction is ready for independent review. It is not installed. The final normal runner suite passed 36/36; the final optimized suite passed 35/36, with both corrected deadline controls passing. The remaining failure is an unchanged descendant-custody control, described below. No compiler fixture, CI dispatch/rerun, commit, push, native test, cloud machine or subagent was started.

The first bad assumption was that `cleanup_elapsed_seconds < 0.20` proved timely interruption by the test's 50 ms alarm. The runner measures that field from `cleanup_start` through terminal exception bookkeeping, timer cancellation and signal-handler restoration. The old helper excludes preparation of the target stage with its held/offset clock, but it does not exclude terminal processing or descheduling after handler delivery. Therefore that field cannot independently measure signal delivery. The failed CI artifact establishes functional interruption and preservation, followed by only this assertion failing at `0.200852`; it does not establish which terminal/scheduling interval consumed the excess time. Its helper saved the diagnostic control receipt after the assertion, so that failure lacks the necessary fresh phase timestamps.

Two bounded reproduction attempts were used. The first stopped before timer registration because the no-child guard blocked Python's lazy `platform.platform()` subprocess; its stdout/stderr and command receipt are retained. The second explicitly disabled that metadata subprocess and used the original helper with observational instrumentation plus a 160 ms terminal delay after the real cleanup handler had raised. The actual timer requested 49.991 ms; handler entry occurred about 59.489 ms after stage arming; the old assertion nevertheless failed at `0.229594`. All earlier functional assertions passed. This falsifies the inference from that elapsed field to handler lateness. It does not assign the historical CI delay to a particular cause. See `reproduction-2.stderr` and `evidence/repro-2-terminal-delay/raw-before-assertions.json`; raw evidence was written before assertions and teardown. No further reproduction was attempted.

The proposed correction consists of:

- `runner-controls.py` and `controls.diff`: replace only the shared deadline helper in the already accepted clock-corrected source. All 36 original test method names and bodies remain byte-identical. The original frozen sources and original 200 ms bound remain untouched.
- `deadline_control.py`: keep the real registered `ITIMER_REAL`, actual frozen cleanup handler, 50 ms test allowance and 250 ms hook. Hold only the runner's injected logic clock fixed so `remaining()` cannot impersonate signal delivery. Require the actual handler to raise, no continued hook work, unchanged scratch identity/marker, terminal deadline failure, zero child commands and restored signal state. Record real wall timestamps separately, without a wall-latency qualification. Save observations before validation or teardown.
- `test_contracts.py`: execute negative mutations for a missing handler, work performed after the handler, and scratch deletion after the handler. Separately test the actual runner's deterministic `remaining()` boundary at 49, 50 and 51 ms with no scheduled timer. Test exact old/new seals, the 36 unchanged method bodies, exact installed-job matching and reuse of the previous fixture execution adapter.
- `adopt_fixture.py`, `sources.json` and `workflow.diff`: bind the exact new derivative/helper and exact prospective job. Pin the previous compiler adapter and its source seal, then execute all its existing checks. Only the installed workflow comparison is delegated to the new full job binding. The previous execution, identity selection and postflight logic remain in use. The workflow retains the original adoption, materializer and selection controls; it adds optimized runner/contract checks and archives this directory.

`local_support.py` routes test materialization, temporary directories and evidence into this new namespace. Fresh unique directories make committed evidence safe to retain without colliding with the next run. It loads the original runner bytes and makes exact pack copies; it does not change the original runner. Disposable pack copies are excluded from staging by the local `.gitignore`; raw receipts and held scratch remain visible.

The final checks used Python 3.14.8 on macOS 27.0.1 arm64, source revision `e7254f3703d5b8191aa72ec2fb11fa91b5ea99ba`, Git tree `482fb5b41a203edfd517627b0e014d31eb7f02e2`. Each final command had a 60-second ceiling and 1 MiB per captured output stream. Exact commands, outputs, source-manifest hashes, owned supervisor PIDs and reap outcomes are in `final-*-command.json` and the corresponding stdout/stderr files.

| Final check | Result |
| --- | --- |
| Original 36 controls, normal Python | 36 passed |
| Original 36 controls, `-O` | 35 passed; unchanged descendant-custody control failed |
| Corrected real postflight and retention deadlines | Both passed normally and under `-O` |
| New behavioral/integrity contracts, normal Python | 11 passed |
| New behavioral/integrity contracts, `-O` | 11 passed |
| Historical input audit | All 163 bound files unchanged |
| Proposed workflow patch | `git apply --check` passed; not applied |

The final optimized run created a new custody hold for its own PID/PGID **23663**. The frozen runner reported `PermissionError: [Errno 1] Operation not permitted`, `child_returned: true`, `owned_group_killed: true`, `owned_group_gone: false`, and `custody_hold: true`. No later probe, signal or retry of that group was performed. Do not infer group disappearance from the child-returned field or from the fixture child's finite sleep. Preserve `evidence/final-runner-optimized-4adh1b9d/scratch/mixer-cache-runner-controls-ndhkqvc5/` and its `logs/descendant-control/` and custody-hold receipt. Parent custody coordination remains required. Earlier development runs passed all 36 under `-O`; those receipts are retained, but they do not override this final failure. The final child-free optimized contract run passed after this hold.

Exact SHA-256 values for review:

| Artifact | SHA-256 |
| --- | --- |
| `sources.json` | `8f8f3880b023c62eaaa12bb53911ce2dccb5ee85817a9371f006978f52b3dd59` |
| Shipping member tree | `be46b1c87d1971505d58622a8e189e29f0b5895e15bbd325065e4f24fa2cacb7` |
| `runner-controls.py` | `1ec5eeb5a80d257aaebd22544f715abdaa0765daa24a45f077554422ff770ab2` |
| `deadline_control.py` | `1efb2177c9159d84962979b2f06fbc75c3eabe9f16caf4e4cc26e52317544283` |
| `workflow.diff` | `b5cba142d464b9fff8cb9a3d55e68c7f29b0c56a6ecf8dd9b4c21cbd77bf34e2` |
| Proposed complete cache job | `fc47ba0f9201f0ccb88081cbbf0c010d9f60c7dec3b4ab37cb77cbc72699f129` |

`failure-provenance.json` independently confirms artifact 13596132427 from run 42427563693 attempt 1/job 128569025491: 551084 bytes, SHA-256 `27ef78c491b5311900e1b19369481ad7da1469e769443894a9a10b74bab28e9f`. This run passed 16 adoption, 9 materializer and 35 other runner controls, then stopped before the new compiler-selection control step and before the compiler fixture. Historical selection logs inside the archive are not evidence that the new step executed.

The fixture remains **103 commands**, **600 seconds active**, **60 seconds cleanup**, **60 seconds per child**, **8 MiB per output stream**. The exact prospective Rust 1.99.1 profile is unchanged, including compiler SHA-256 `1ba7bb8e273bd64125f4048d2ecce530e0a6470e565ab1b3aecf0b82b532f7b1`. Existing compiler qualification and baseline failures retain their historical scope; this task supplies no new compiler/native/GA qualification. All specified historical process, hosted-lane and phone holds remain intact. Concurrent parent changes listed in `final-source-audit.json` were not edited by this lane.

After independent review, the parent may adopt the 11 exact shipping files listed in `sources.json`, that manifest, the review evidence and the proposed workflow patch. The named next executable integration is a **fresh ordinary `.github/workflows/verify.yml` → `swift-cache-state-fixture` run on the new accepted commit**, including the existing selection controls and one unchanged 103-command fixture. Do not rerun failed attempt 1. Local partial success is not a substitute for that check. The proposed installed-job preflight deliberately refuses the currently unmodified canonical workflow.
