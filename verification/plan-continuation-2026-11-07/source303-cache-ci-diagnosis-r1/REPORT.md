# Current cache CI diagnosis

Run 42666503150, job 129331452787 (`swift-cache-state-fixture`), revision `63a76a4c34ff01f50b9b38a936bc81c87f462c95`, tree `750807bc714063c2d1bcacd5a10d8b2e819ec60f`.

## Actual failure

The hosted Shared fixture runner, materializer and adoption focused controls step passed all 16 adoption and 9 materializer controls. The original runner suite stopped after test 29/36 at `test_owned_descendant_group_is_stopped`; the remaining seven controls and later shell commands did not execute. The test's assertion at `verification/plan-continuation-2026-11-07/cache-deadline-control-fix/runner-controls.py:102` requires `owned_group_gone` to be true. The executed source is materialized under the r8 directory; its original source is the deadline-control file above.

The retained command reports timeout, successful group-kill attempt, returned direct child, `owned_group_gone=false`, missing stdout/stderr EOF, and PermissionError errno 1 (`Operation not permitted`). The direct child return does not prove group absence. `verification/plan-continuation-2026-11-07/cache-refusal-cleanup-r8/commands.py:49` performs the post-wait `gone` check; `gone` at line 16 calls `os.killpg(pid, 0)` and lines 18–20 preserve UNKNOWN on errors other than ProcessLookupError. This sequence is consistent with the hosted state and reproduced with pure fakes. The hosted error does not include a traceback naming its precise syscall, so the actual syscall attribution remains an inference from the source and state, not a newly observed host syscall trace. The underlying OS reason for EPERM remains unproven.

The hosted evidence contains no TemporaryDirectory/symlink assertion failure. This failure is a process-custody denial, unlike the earlier fixture path canonicalization issue. No path normalization change is supported by this evidence.

## Bounded executable results

Exactly two material test executions: normal Python and optimized Python, each 3/3 PASS. `test_focused.py` loads only the r8 Commands class with a scripted process, clock and killpg implementation. It reproduces the post-kill EPERM state, verifies that positive ESRCH completes cleanup, and verifies no further process operation after UNKNOWN. No real child, compiler, native/device run, process census or denied-child experiment was performed. These results validate the reproduced state transition and fail-closed behavior; they do not establish the hosted OS cause or a green CI run.

Commands:

```
python3 -B verification/plan-continuation-2026-11-07/source303-cache-ci-diagnosis-r1/test_focused.py
python3 -B -O verification/plan-continuation-2026-11-07/source303-cache-ci-diagnosis-r1/test_focused.py
```

Each command's stdout/stderr is retained as `focused-{normal,optimized}.{stdout,stderr}`. Python/version/platform and source hash are in `source-metadata.json`. Normal and optimized executions both exited 0.

## Disposition

No patch delivered: no incorrect source behavior was reproduced. Treating EPERM as absence, weakening the descendant assertion, skipping the control, or proceeding after UNKNOWN would violate the required custody safeguard. Canonical source, source113 runtime/caller bindings, PLAN, STATUS and graph were not edited. No commit, push or delegation was performed. CI remains failing; this diagnosis is not a fix or qualification claim.

The next discriminating evidence, if root selects a separate authorized hosted experiment, is the exact syscall and traceback producing EPERM in a fresh owned descendant control. This delegated scope expressly prohibits a real denied-child attempt, so none was made. The existing hosted UNKNOWN command and every historical hold remain preserved; no retry or process observation is authorized by this report.

## Artifact and resource scope

Artifact 13697762123 was downloaded with `gh api repos/snowdamiz/mixer/actions/artifacts/13697762123/zip`. ZIP SHA256 was verified as `fd355f0b4fbc4b704573e2c96de0223ae093933523b9ad85e258ca7a0ec0fb84`. Only the six explicit new hosted focused-control stdout/stderr members in `artifact-metadata.json` were read/extracted. No scratch or held member contents were extracted or inspected. The ZIP central directory was initially filtered for log names, which also returned historical log member names; those historical entries were not opened and the retained metadata was narrowed to the six explicit focused logs. No held local filesystem tree was intentionally read for diagnosis. All newly written files are in this directory. No temporary device, process group or external scratch was created by the controls; no resource cleanup was needed.
