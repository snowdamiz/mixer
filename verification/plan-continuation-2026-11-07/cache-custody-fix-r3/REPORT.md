R3 verdict: NOT VALIDATED / DO NOT ADOPT. The two-command budget is consumed. Both permitted supervised normal/-O invocations failed at harness initialization before any unittest body, actual preflight, or original-control entrypoint ran. No third invocation, retry, alternate runtime, real descendant, original36 real-process suite, compiler, native, CI, commit, push or delegation was performed.

Owned directory: verification/plan-continuation-2026-11-07/cache-custody-fix-r3/ only.

The four requested source corrections are prepared:

1. commands.py gives the existing 5-second wait plus 5-second group-cleanup allowance one shared finite deadline, also used by post-stop EOF drain. The bound is capped by the unchanged overall active deadline plus cleanup allowance. A missing actual EOF at the finite deadline latches UNKNOWN before unwinding. Forced closure does not set EOF flags. stop_complete prevents repeated finalizer stop operations after successful process cleanup.
2. Every active poll/wait now passes through observe(), which catches any BaseException, latches UNKNOWN, and rethrows the original exception. Group and signal failures likewise latch UNKNOWN. Admission, stop, gone and observe reject afterward. Resource snapshots after UNKNOWN are omitted. Ordinary read failures, including PermissionError from read rather than a custody observation, still enter bounded process cleanup and preserve the original exception; incomplete EOF custody remains held and suppresses CPU deltas.
3. workflow-job.yml adds the exact native-custody-premise/cleanup_control.py to sparse checkout and artifact evidence. The prospective workflow.diff changes only the cache job against canonical 0f30624d bytes; another envelope lane must be coordinated by root. No workflow was installed, no git apply was run.
4. test_original.py restores local_support.HERE and sys.path in finally covering the write-guard/evidence workspace, install, suite and result-writing operations; final verify runs after restoration. The original control source and corrected deadline helper are untouched.

Premise decision, recorded before code in premise.md: retaining the Commands derivative is smaller than adapting the accepted native controller. The native controller has combined stdout/stderr and aggregate caps, buffer/receipt interfaces, and read-failure handling that differ from this fixture's per-stream cap, original receipts and ordinary-error policy. We transfer its finite cleanup deadline and sticky observation principles while retaining the exact accepted file as the OUTER supervisor. No performance comparison or historical EPERM explanation is established.

Prepared verification, not completed:

- combined_fakes.py reuses the R2 review's exact two failing methods against unchanged R2, then successor variants against the real Commands methods with fake Popen/poll/wait/killpg/selector/read/time/resource APIs.
- It includes the ten prior sealed fake controls, six other R2 review methods, additional nonpermission poll/wait/group failures, ordinary read PermissionError cleanup, and original method byte/inventory checks. All checks use unittest and remain enabled under -O.
- It builds source projections from the exact 311 tracked paths selected by the job, plus sealed candidate shipping files. It calls the actual adapter CLI main for preflight, then actual test_original.main with the real source/workspace/materialization setup and a fake 36-method suite. The module audit-hook registration is intercepted only to avoid installing an immortal imported global-dependent hook; the R3 outer audit blocks every inner process/group/network operation and all writes outside the assigned directory. Missing-controller and wrong-seal reproductions, restoration on setup failure, and successful successor pre/postflight are all planned assertions, NOT observed results.
- Source/data adapter controls retain the real fresh_output validator, verify refusal makes no writes, retain postflight on ordinary fixture failure, and reject retained-source tampering. These were not reached in R3.

Actual failure and preserved evidence:

The initial harness used Python str.replace without count=1 on the review source's sys.addaudithook(audit) text. That replaced both the real review registration and the nested string literal used by the review to disable the inherited test_fakes audit. The inherited R2 audit stayed installed. Importing the successor review then failed with RuntimeError: Mutation outside owned directory. Both runs have the same traceback; there were zero executed test methods. The process/network guard was never weakened to get around that failure.

executed-shipping/ retains every exact attempted shipping member and its seal. The corrected final harness uses count=1 so the nested disabling substitution remains intact. This correction has NOT been executed. sources.json binds final shipping bytes; it is distinct from the executed-shipping/sources.json seal. postflight.json reports equality during the failed execution window, not successful testing of final sources. direct-postflight.json records unchanged canonical workflow and the R2/history files read by this lane.

Execution record:

    python3 -B verification/plan-continuation-2026-11-07/cache-custody-fix-r3/supervise.py

The outer driver called the accepted native controller at SHA256 8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df. Exactly two owned child commands ran, each with timeout=120; normal and optimized each exited 1. supervision/commands.json records exact interpreter argv, cwd, logs, direct reap, stdout EOF, stderr EOF and positive owned-group absence. PIDs/PGIDs 45780 and 45781 both reached TERMINAL, without signals or cleanup errors; supervisor scratch was removed. There is no new UNKNOWN process hold. Empty fake evidence directories remain as failure evidence. No process enumeration occurred.

Tool/source identity: Python 3.14.8, Darwin 27 arm64; host.json records executable SHA256 e401ac7a95cda75dee34a0cfe1e4faf0a6df1a501cf67887f177fb78cd4eb60a, argv and suite/supervisor hashes. Direct filesystem reads of the worktree ref and decompressed Git commit object confirm revision 0f30624df2edcd50ee7f1b069afb96c0ae263791 and tree ad8066ea6ff9a8e97a162b357bd4cfcb3fee7d13. The observed input-tree digest is a8fc3f747f68f46299a5d85c9ae52710f03977a2761f9976d5f298658e6bc3a8.

Preservation / explicit limits:

The derivative installs only Commands into the frozen fixture globals. The original execute/cleanup functions, 36 method bodies, corrected deadline helper, 103-command fixture, 768 method inventory, 124 capture inventory, exact Rust 1.99.1 selection, 600 active / 60 cleanup / 60 child seconds, and 8 MiB per stream are unchanged sources and planned executable invariants. No execution counts, compiler qualification, deadline-control pass, original36 pass, source-closure pass, or first historical EPERM causality resolution are claimed. Source103 eda43c6bb96bfeb15ab31731858c7388a7ba52329c8ba8e48ed52505bfe86158 belongs to the separate accepted store/Java integration; this lane made no canonical edits and did not recompute or requalify that closure.

All named held PGIDs and retained scratch remain untouched: 40708, 40709, 40711, 23663, 20745, 20770, 20780, 20817, 20842, 20851, 20866; FieldLog 40802230894 PGID2424/PID2621, held v5, frozen hosted lanes and phones. Hosted 42442717964/PGID2331 remains remote historical evidence, never a local target.

Final source seal SHA256: 3b29ccffa865d26098c912bcb6ede69f9f8348ac7a0ad90875dac2290ff7e492
Final shipping tree: cba94ff92d9e3030beb426a36ac87a348ae691b61964e00ec08b606fb6794ead
Executed initial source seal SHA256: 0afba51ea1b7062b2a0594dea2c4d907199b3b5dde7772a8c0d563ad2dd59e9b

Next decision: preserve both failed runs and use a separately authorized fresh pure/fake successor to validate the corrected harness and candidate. Do not select the tiny real control yet. Once that prerequisite and independent review pass, followon-gate.txt proposes ONE exact executable tiny_real_control.py command for root selection, with a fresh leader/descendant pair only, no retries, exact accepted outer supervision and retained scratch on UNKNOWN. It is sealed but unexecuted and carries no authorization. The real 36-process suite, full fixture and CI remain pending.
