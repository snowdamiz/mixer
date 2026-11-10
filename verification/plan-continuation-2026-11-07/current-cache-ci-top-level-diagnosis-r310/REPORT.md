# NEW cache CI top-level diagnosis R310

Observed run **42883750881**, cache job **130066539843**, revision `1a56d6d0f28298c8805dfd6c1e5738819dcf9a7d`. [Job](https://github.com/snowdamiz/mixer/actions/runs/42883750881/job/130066539843).

The first failed control is **`test_owned_descendant_group_is_stopped`**, class `deadline_controls_original_normal.RunnerControls`. The uploaded `runner-controls.stderr` reports:

```text
File "/Users/runner/work/mixer/mixer/verification/plan-continuation-2026-11-07/cache-refusal-cleanup-r8/runner-controls.py", line 102, in test_owned_descendant_group_is_stopped
AssertionError: False is not true
exception: PermissionError; errno: 1; message: [Errno 1] Operation not permitted
errors[0].phase: active
pid: 1143; pgid: 1143
custody_hold: true; unknown_custody: true; owned_group_gone: false
child_returned: true; owned_group_killed: true; timed_out: true
stdout_eof: false; stderr_eof: false; exit: null
child_resource_usage.terminal_facts_verified: false
child_resource_usage.aggregate_delta: null
```

The full assertion detail is preserved verbatim in the copied stderr; the summary does not show the assertion's source expression or the original PermissionError stack. Its exact EPERM-producing syscall and the reason for EPERM remain **unproven**. Do not infer a new platform policy or identify it as an old held command.

## Observed execution

The workflow uses `set -euo pipefail` and sequential controls. Adoption's 16 controls passed; materializer's 9 controls passed. The normal runner reported 29 tests, one failure (28 preceding `ok` entries). Inspection stopped at this first failure: optimized runner, contracts, selection, and fixture logs were not opened. Live GitHub step summaries confirm descriptor/adoption success, focused-controls failure, complete fixture skipped, and adoption postflight success.

The failing hosted command's top-level summary already reports PID/PGID **1143**, cwd `/Users/runner/work/mixer/mixer/verification/plan-continuation-2026-11-07/cache-refusal-cleanup-r8/evidence/original-normal-vhtwnju_/scratch/mixer-cache-runner-controls-gzbtbyuz`, and retained scratch `/Users/runner/work/mixer/mixer/verification/plan-continuation-2026-11-07/cache-refusal-cleanup-r8/evidence/original-normal-vhtwnju_/scratch/mixer-cache-runner-controls-gzbtbyuz/out/scratch`. These were copied from the permitted summary, never recovered from scratch or journals. The summary also embeds hashes for descendant outputs; those members were not opened.

## Fail-closed assessment and limits

**The observed runner path remains fail closed:** it records custody/unknown, withholds a successful exit and CPU delta, reports unverified terminal facts, and fails the control rather than declaring cleanup success. That is the correct response to unproven group absence. This is evidence for this refusal path, not production qualification or a successful descendant-cleanup test. The complete real fixture was skipped. Child return and `owned_group_killed=true` do not prove group absence.

The top-level evidence is sufficient to scope the new hold reference to run **42883750881**, job **130066539843**, PGID **1143**, and its recorded retained scratch. See `HOLD-reference.json`; root owns any shared-metadata addition. No tests, reruns, process probes/signals/waits, cleanup, device actions, signing, root Git, messages, remote mutations, or canonical edits occurred. Historical holds remain untouched; this does not block independent Android/iOS development.

If root needs the underlying cause, the minimal next discriminator is **source-only**: inspect pinned `cache-refusal-cleanup-r8/runner-controls.py:102` and the exact active-phase runner branches that emit the copied PermissionError; determine whether the top-level exception distinguishes signal delivery from group-absence observation. Do not inspect journals or retry this hosted command. No generalized controller is proposed.

## Raw evidence

Artifact **13793584510**, `swift-cache-state-fixture-1a56d6d0f28298c8805dfd6c1e5738819dcf9a7d-42883750881-1`, is **1,345,020 bytes**, SHA-256 `2530a4cc4149fd9430578cdf03e2afac3f78fbab59b84328f8781b68cd0c1855`, matching the supplied exact ID/size/digest. Raw ZIP retained at `freshowneddownload/artifact-13793584510.zip`; member names were not listed and no broad extraction occurred. Only the six explicit stdout/stderr members below were opened.

| Copied raw summary path | Bytes | SHA-256 |
| --- | ---: | --- |
| freshowneddownload/shared-fixture-clock-controls-correction/logs/adoption-controls.stdout | 391 | `3b7f6bfe1dd434f3265476a151a7e06a9b307c6ab359c146d324c11eeddda237` |
| freshowneddownload/shared-fixture-clock-controls-correction/logs/adoption-controls.stderr | 2331 | `f3febf989f0f0288c4cedb39ef649e76d9feff72deef58f1c5f55e05fcccf0ac` |
| freshowneddownload/cache-fixture-shared-input-candidate-v2/logs/materializer-controls.stdout | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| freshowneddownload/cache-fixture-shared-input-candidate-v2/logs/materializer-controls.stderr | 1451 | `56a34d92b3101503e0af231df3a8f3dbe398b3efacb95e08d8f1a34ac3222973` |
| freshowneddownload/cache-fixture-shared-input-candidate-v2/logs/runner-controls.stdout | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| freshowneddownload/cache-fixture-shared-input-candidate-v2/logs/runner-controls.stderr | 8581 | `dc8abfd006083c61256c34fae2b2294c32161b586f0b246affa1987a0fc32960` |

`receipt.json` records source revision, platform/tool versions, commands/API reads, scope, and hashes. `github-job-steps.json` and `workflow-focused-step.txt` preserve the read-only API evidence. No acceptance, GA, release, or physical-device result is claimed.
