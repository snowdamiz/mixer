# Bounded custody premise campaign

Started 2026-11-08 UTC (local November 7). Parent 96f03ab65966a6374e958e780fa09a3eed814c0b. Source101 a10a62cc79145bc80bfd780257589f437cc82e2f1ebaad6ccde39c134d56e0ca. Scope: only this directory. No native/compiler/ADB/UI actions, children agents, commits or pushes.

Shared premise, written BEFORE any repair: sending or probing an owned Darwin process group before reaping its direct child is a reliable presence/absence observation, including while that child exits.

Competing explanations and predictions:
1. Mock leakage: a synthetic PermissionError escapes a scoped patch. Prediction: fake context-unwind inspection reveals patched killpg outside the context. Counterfactual: restoring identity disproves that mechanism; genuine errno=1 with the old harness's unmocked failure cases supports another explanation.
2. Algorithm ordering plus Darwin semantics: killpg can find a group but skip its zombie members and return EPERM when no eligible member is found. Prediction: deterministic zombie-only fake fails old signal-before-reap order, while reap-first and group-observation-only-after-reap complete with positive ESRCH. Counterfactual: both variants fail under an independent persistent permission denial.
3. Wrapper/actual-host policy: the current execution wrapper rejects even a fresh owned live group, or post-reap absence observation. Source/fakes cannot decide this host condition. Only after fake discrimination, at most two single-child experiments may test it; no native work follows here.

Comparison required by product plan 24.4:
- Algorithm change: poll/reap BEFORE deciding to signal; after one successful signal, drain pipes and reap before checking group absence. Preserve four distinct custody facts and global stop-on-unknown. Preferred if the fake discriminates.
- Resource policy change: extend deadlines or add a sleep before group probing. Reject if it merely changes the chance of racing a zombie; no timing interval establishes absence.
- Different implementation: initial kernel PROC_PGRP_ONLY census, never fallback after EPERM. Potentially supports membership but needs a pinned ABI, error/zero-result and truncation semantics, and actual host evidence. Do not add this larger platform surface when reap ordering suffices for the observed direct-child failures. Canonical short Commands has the same signal-before-reap sequence; wholesale reuse would retain the defect. Keep the narrow existing shared selector needed to drain the three owned services concurrently.

Bounds: two fake-only suite commands, each <=120s; 4MiB combined per command and 32MiB aggregate; whole campaign <=15min. At most two new real children, each <=5s, one new owned group each, no descendants. Every real attempt needs explicit hypotheses/predictions/counterfactual before launch. First real UNKNOWN/EPERM stops the campaign: persist hold and no subsequent process actions, probes, signals, retries or launches. Retain scratch on unknown. All historical IDs and scratches untouched; no group enumeration.

Decision: fake discrimination must precede selected repair. Native remains pending independent review. R2 instrumentation, all 11 smoke checks, readiness and native timing budgets remain unchanged.

The first fake command passed both baseline discriminants. Scoped killpg patches restored the original function; both old failure shapes reproduced without OS process calls. Selected repair now reaps before the initial signal and suppresses group absence probes until direct-child reap is observed. No errno is reinterpreted.

Host admission uses the exact final optimized 26-test fake suite (the previous 23 controls plus ordering/helper-isolation controls), followed by two narrowly scoped real experiments. It does not replay the historical 23-case real-child campaign. One fake command remains. The updated native entrypoint requires that final suite's controller/lifecycle/tests/driver hashes and both new real custody receipts. This is a new admission profile, subject to independent review; it does not relabel either old failed pass.

Real experiment 1, conditional on final fake suite success: one Python child closes stdout, writes stderr after 40ms and exits. Wait 150ms while draining pipes; the repaired controller reaps before signalling. Prediction: direct-child reap and both EOFs, then positive ESRCH with terminal custody. Counterfactual: denial despite reaping identifies a wrapper/host condition; stop, retain, do not run experiment 2.

Real experiment 2, only after experiment 1 has positive terminal custody: one Python child writes readiness and sleeps at most 2s. Signal once while live, then drain/reap before the first group absence probe. Prediction: one successful SIGKILL and positive ESRCH after reap. Counterfactual: live signal or post-reap observation denied means the wrapper/host cannot support this custody protocol; stop with hold. Each uses one fresh group, separate pipes, 4.5s whole cleanup bound, no descendants, <=4MiB stream capture / <=32MiB aggregate. These discriminate the actual host policy, which source and fakes cannot establish. No old group is consulted.

Primary-source basis: Apple XNU kern_sig.c killpg1 (main, read 2026-11-08) filters SZOMB group members and returns EPERM when its eligible-member count is zero; ESRCH is returned when no group is found. This supports a mechanism, not proof of the installed xnu-13432.1.9 implementation or the old groups' current state.
https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_sig.c
Apple's libproc wrapper maps syscall failure to zero (errno must be checked); the kernel's PROC_PGRP_ONLY path checks security policy and scans allproc and zombproc under the list lock. A future census implementation must distinguish error, zero members and buffer truncation. No census was executed in this campaign.
https://github.com/apple-oss-distributions/xnu/blob/main/libsyscall/wrappers/libproc/libproc.c
https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/proc_info.c
