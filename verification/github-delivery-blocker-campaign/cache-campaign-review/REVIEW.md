# Observed cache-capacity campaign result

None of the four profiles completed Corpus 1; Corpus 2 was unrun in every case.
The experiment removed uncertainty about the cache-size hypothesis: 256 residents
substantially reduced repeated decoding, but the unchanged 30-second runtime
deadline became the first limit. No profile is host-feasible yet, and no
production/default/native/OTA/GA promotion is supported.

Independent reviewer: fresh `gpt-6-astra`, `xhigh`. The reviewed execution is
[GitHub run 40740382537](https://github.com/snowdamiz/mixer/actions/runs/40740382537),
attempt 1, exact commit `cc350d3303ca71c5d57e87846f6a61304b658fa7`. It ran from
17:56:06 to 17:59:55 UTC on October 28, 2026. The green job means the four bounded
comparisons and evidence upload completed; each full-target process exited 101
after preserving its actual failure.

## Observed outcomes

| Resident/work profile | First failure in Corpus 1 | Guest instructions at failure | Cache work used | Completed decodes / repeated | Evictions |
| --- | --- | ---: | ---: | ---: | ---: |
| 64 / 64M | CacheWork attempted 64,000,001 | 23,358,291 | 64,000,000 | 61,627 / 61,142 | 61,564 |
| 64 / 128M | Runtime deadline at 30.000 seconds | 56,427,609 | 122,155,136 | 111,856 / 111,371 | 111,792 |
| 128 / 64M | CacheWork attempted 64,000,001 | 21,624,153 | 64,000,000 | 50,876 / 50,391 | 50,748 |
| 256 / 64M | Runtime deadline at 30.000 seconds | 66,569,302 | 47,577,747 | 1,006 / 521 | 750 |

All profiles validated the exact full input, constructed the original owner and
completed initialization at 37,328 guest instructions. Each attempted the first
corpus once. None emitted a native-equality observation, returned the complete
first-corpus output, or started the second corpus. The original short-circuit
behavior and two-call oracle remain intact.

The fresh 64/64M control reproduced the historical failure's exact instruction
count and all final attribution counters, including the rejected debit. Its
widened index and Linux environment remain separately identified; historical
macOS elapsed/CPU timings are not paired benchmark observations.

## Competing hypotheses and decision

The 128-resident trial did not improve the work-limited stopping point. Its
empty-slot, victim and eviction-plan scans consumed 19,520,000 credits, versus
11,828,480 in the 64-entry control, despite a shorter executed prefix. Repeated
build work was lower, at 27,450,613 versus 34,500,496 credits, but that did not
offset the observed table costs enough to advance this trial. This supports the
warning that a larger linear planning table can make an intermediate capacity
worse. These unequal stopped prefixes are not an equal-workload speedup estimate.

At 256 residents the repeated-build total fell to 398,284 credits, with only
521 repeated completed decodes among the same 485 distinct decoded functions.
Empty/victim/plan scanning fell to 707,072 credits. Retention therefore addresses
the repeated-decoding problem in this observed execution, even though the larger
index and planning array are charged. The remaining cache-work distribution is
now dominated by free-pin search (17,659,948 credits) and full resident hash-chain
validation (26,091,142), together 91.96% of 47,577,747 credits. This identifies
algorithmic candidates for a next experiment; it does not establish their CPU
cost or justify removing validation.

The completed initialization offers one small common-work checkpoint: all four
execute 37,328 guest instructions and seven host calls. Cache work is 160,343
for both 64-entry profiles, 164,370 for 128 and 196,882 for 256. The two larger
profiles decode 126 functions without eviction during initialization, versus
135 decodes and 71 evictions at 64. This confirms the competing retention and
table-cost effects without comparing unequal corpus prefixes.

Close this four-attempt campaign. Retain 256 as the next diagnostic candidate;
retire 128 from this path under the current policy. No adequate production or
host-feasible configuration has been selected. Do not spend the reserved fifth
attempt on 256/128M: the 256/64M run still had 16,422,253 cache credits available
when the runtime deadline fired. It also had instruction-fuel headroom, using
67,150,429 of 100,000,000. Increasing cache work alone does not address that first
observed limit.

The next root-selected campaign should discriminate the cumulative runtime
deadline from execution cost while retaining the 256-resident candidate. A
bounded higher-deadline trial must keep Runtime/WASI deadlines coherent, preserve
the 100M instruction ceiling and all memory/capability/cleanup safeguards, and
record whichever limit comes next; a competing algorithm trial can target
guarded pin search and collision-chain work. Neither was implemented or run by
this review. The existing fifth attempt remains unselected. No original primary
attempt should be rerun without a new stated comparison purpose.

## Verification and source bindings

`committed-source-binding.json` verifies every independent-review candidate pin
against the exact committed tree and the installed workflow's byte identity.
`remote-metadata.json` binds run, job and artifact identity. Artifact 12838319537
was retained as a 246,419-byte ZIP with GitHub digest
`87aa945b9d78851e9674f1015bf9850220ed9e59a25fac6e8c50c54289ed4fd6`.
Safe extraction yielded 1,006,569 bytes, below the 64 MiB ZIP / 256 MiB expanded
bounds. Duplicate, traversing, absolute, encrypted or linked members were rejected
by the extraction path. No downloaded artifact code was executed. Signed redirect
URLs were neither printed nor persisted; all URLs in retained job logs were
redacted. The archive's complete file hashes are in `artifact-retention.json`.

`verified-results.json` is the machine-readable result of
`python3 -B verification/github-delivery-blocker-campaign/cache-campaign-review/verify_results.py`.
It verifies all four generated source manifests and patches, original input
bindings, selected effective budgets, raw-output hashes for all 19 command
receipts, compile-to-executable path bindings, raw classifier replay, exact
historical baseline attribution, phase outcomes and final consuming state.
The original 18,976,211-byte compressed Swift artifact remains bound to
`e22a8226908ef68170ac94267978b4b436c45764bc591451ef16161d6dbd52ac`;
its decompressed 53,777,114-byte SHA remains
`24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994`.

Remote evidence contains nine passing pure controls, four passing finite actual
cache controls for each profile (16 total), and one original harness control for
each profile (four total). The four full attempts follow those prerequisites;
there are no retries or fifth attempt. Finite controls actually exercise the
N-entry geometry, full collision chains and high links, pin bound, retention and
eviction, original failure/cancellation prefixes, allocation failures, conservative
combined envelope, and final owner consumption. They remain synthetic control
evidence, not corpus completion.

The compiler was Rust 1.99.0 (`b940084d7eb6a299eb4bfeb8e34901bc051e7ac4`),
`x86_64-unknown-linux-gnu`, LLVM 23.1.1; Cargo was 1.99.0 and runner Python 3.12.3.
The host reports Linux 7.0.0-1017-azure with glibc 2.39. Compilation used fresh
separate targets with offline Cargo. Binary hashes/sizes and matching executed
paths are retained; binaries themselves were removed remotely, so this review
cannot independently rehash their bytes locally.

## Cleanup and measurement limits

Every full attempt consumed its owner to zero live reservations, resource counts
and tickets, with no cleanup invariant. Every command receipt records an empty
owned process group, no external timeout and no signal intervention; owned
scratch was removed. The original harness correctly emits `cleanup_empty=false`
and preserves the original first failure in `final_failure`, with `after_cleanup`
attached. Its separate `cleanup_reservations_and_live_empty=true` proves resource
emptiness. Failure-free completion must not be inferred from that emptiness.
The review's initial overly strict assertion expecting `cleanup_empty=true` on
failed workloads is retained in `reviewer-assertion-correction.json`; the corrected
offline check verifies resource emptiness and exact preservation of the first
cause. It incurred no runtime attempt. Timeout/cancellation signal paths were not
exercised by these ordinary exits.

Reported combined logical reservation peaks were 176,325,243, 176,585,946,
176,711,990 and 178,523,906 bytes respectively, all under 268,435,456. Peak cache
reservation at 256 was 3,123,993 bytes, under 16 MiB. The finite conservative
simultaneous 256-entry envelope was 266,788,262 bytes, leaving only 1,647,194 bytes
under the same combined limit; observed corpus peaks do not erase that tighter
conservative margin.

Single full-command wall observations were 14.143, 31.052, 12.943 and 31.043
seconds respectively, including validation and cleanup. They are not equal
completed-workload timing comparisons or variance-qualified speedup evidence.
All full commands, synthetic controls and even version probes report the same
168,927,232-byte RSS value. This common launcher/process high-water floor prevents
isolating VM-attributable peak RSS from these receipts. Retain the raw values,
mark that measurement unavailable for per-profile memory comparison, and do not
substitute logical reservation figures for actual RSS.

This review ran source/data inspection and bounded artifact transport only.
It did not dispatch, retry, compile locally, execute a guest, probe local PIDs or
custody, use global process inventory, start native/UI/capture work, contact a
phone or edit canonical source/status metadata. All active holds remain in force.
Public SDK integration, immutable separate-repository FieldLog consumption,
signed OTA, physical devices and GA remain pending their specified evidence.
