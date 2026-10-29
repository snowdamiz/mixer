# Single dense512 completion experiment

Prepared for independent root review, with no actual build or VM run in this
packet. Select `dense512-completion-v1` only after review. This is one bounded
host completion hypothesis, not a production latency policy, default winner,
causal capacity comparison or GA acceptance.

The closed capacity-window run `40788458735` at
`e5670519a0d02b74a95c00d35dbf5f837fca9850`, tree
`89a9344ecf974105b7ad7df30394485bade6e284`, completed corpus 1 in both arms and
entered corpus 2 before the cumulative 600-second Runtime deadline. The pair
has zero attempts remaining. Its eleven remote commands closed, both consuming
cleanups reached zero live resources and tickets, and owned scratch was removed.
The failed baseline is retained unchanged; this new namespace cannot resume it.

For the executed dense512 arm, initialization ended at 0.061846 seconds and
corpus 1 ended at 419.716175 seconds. Its cumulative corpus-1 usage was
1,037,318,901 instruction fuel, 6,069,131,856 execution work and 393,625,800 cache
work. `phase-evidence.json` binds those raw observations to the local reviewed
archive and keeps the exact source identities. `phase-review.json` records a
fresh offline join to that archive. Raw CI logs and the archive stay in their
existing local review directory.

The explicit planning hypothesis is initialization plus twice the measured
corpus-1 interval: 839.370504 seconds, 2,074,600,457 fuel, 12,061,904,582 execution
work and 786,733,715 cache work. It is not an estimate of a completed run: one
sample, entropy, changing retained guest state and second-call behavior limit
prediction. The 1,200-second cumulative window is 1.4 times that time hypothesis,
rounded upward to a whole minute. Four billion fuel clears the observed
two-corpus hypothesis; the old two-billion fuel ceiling did not. Existing
16-billion execution-work and four-billion cache-work ceilings already clear
the hypothesis by about 1.33 and 5.08 times, so they stay unchanged. No automatic
increase follows another failure.

Only the Runtime fuel/default deadline, WASI default deadline and their finite
test expectations change from the executed dense512 source. The existing scalar
finite method now exercises the selected fuel limit, all seventeen widening
denials, zero limits, cumulative initialization/repeated calls, overflow,
earliest absolute deadlines, sticky expiry and consuming cleanup. There remain
exactly twelve selected finite methods. The existing earliest-deadline method
uses its original bounded 12ms expiry check; no long wait is added.

The same initialized owner executes both complete original corpus calls. No
counter, clock or owner is reset between phases. Original input, eleven-field
oracle, harness, lifecycle target, cache algorithms, capability grants, denial
paths and validation limits remain unchanged. Frames/pins stay at 128 and cache
residents at 512. Source/metadata/cache/state caps stay 64/16/16/128 MiB within
the 256 MiB combined envelope. The previous measured conservative geometry was
266,806,334 bytes, leaving 1,629,122 bytes; it is historical evidence, not a new
compiled receipt. Fresh finite execution must recompute and admit geometry
before the one full attempt.

The manual workflow shares the existing execution-experiment concurrency group,
refuses cancellation of an active group and accepts only first-attempt
GitHub-hosted Linux. It records Python identity in process, then permits exactly
six child commands: pinned rustc identity (15s), cargo identity (15s), fresh build
(180s), twelve finite controls (90s), original harness control (90s), and the one
full target (1,350s). Its aggregate driver budget is 2,100s. Per-command bounds,
six 10s cleanup allowances and a 10s receipt allowance total 1,810s. The full
command allows unchanged 120s validation, 1,200s cumulative execution and 30s
remaining margin. The driver independently preserves its aggregate cleanup
reserve. Workflow step/job bounds are 36/44 minutes.

Admission requires five closed preparation commands, exact generated source,
unchanged original input, a freshly compiled binary hash, passing finite and
harness counts, and exact scalar/deadline/geometry markers. The full-attempt
reservation is persisted before spawning and is never refunded. Missing root
selection, reruns, reused output, source drift, changed binary, invalid geometry,
failed control or insufficient aggregate time stop before full admission.

Resource exhaustion remains diagnostic failure. Unexpected capacity,
owner/ticket failure, unsupported behavior, invalid telemetry, changed original
failure, nonzero consuming cleanup, external timeout/cancellation or unresolved
process custody stop the experiment. Unresolved command custody retains scratch
and forbids further commands. Closure requires child reaping and owned-group
absence; regular output files then close and receive hashes. The inherited
driver has no explicit pipe-EOF flag. Logical memory is not RSS, and the raw
wait4 high-water value does not support VM-attributable RSS comparisons.

Success requires both original complete eleven-field observations, the original
phase classification and consuming zero-resource cleanup. Even success proves
only this host diagnostic completion. Failure preserves its original cause for
root's next decision; there is no second arm, retry or automatic follow-on run.
Earlier matched prefixes end at 250M; later divergence supports no endpoint
speedup or causal capacity claim. Prefix instrumentation is unchanged and remains
diagnostic only.

Local checks are pure Python with child/socket/signal/wait operations denied and
writes restricted to this sibling. The first wrapper run had 35 passing methods
but mistakenly required 36; its original outputs and count mismatch are
preserved. A meaningful actual-evidence tampering rejection was added; the final
suite has 36 methods. Actual Rust type checking, twelve finite controls, harness,
fresh geometry, full two-corpus execution and consuming runtime cleanup are
pending. Native/UI/capture, disconnected-phone, custody groups
20745/20770/20780/20817/20842/20851/20866, UnitA, broad hosted and the old FieldLog
fetch remain held. No canonical files, Git state, remote state or held processes
were changed by this lane.
