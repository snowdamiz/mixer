# Swift cache deadline campaign v2

The selected experiment immediately tests the full 53,777,114-byte Swift reactor
at 256 decoded residents, 64M cumulative cache-work credits and a 60-second
cumulative runtime/WASI deadline. One conditional second full attempt uses 128M
cache-work credits with those same residents, deadline and original 100M fuel.
It is selected only if the first attempt actually exhausts CacheWork and preserves
its original cause, valid telemetry, zero resources/tickets and absent owned
process group. Fuel, deadline, invariant or any other failure does not select it.
There are at most two full attempts, counted before spawning, without retry,
resume or replay of the four v1 primary attempts. GitHub reruns are rejected.

The named milestone is **both original corpus calls matching all 11 native fields
on one initialized owner, followed by consuming cleanup**. The 60 seconds cover
initialization and both calls cumulatively, with the unchanged harness passing
one original `started` Instant to runtime and WASI. Validation retains its separate
120-second deadline. No counters or deadline origins reset between calls.

## Evidence and competing explanations

The sealed v1 review is
`verification/github-delivery-blocker-campaign/cache-campaign-review/seal.json`,
SHA-256 `4dcf3f8bf9533d0234a5966d111b1d3373299cbfb816ab871d0764c0a1024cec`,
from run 40740382537 at commit `cc350d3303ca71c5d57e87846f6a61304b658fa7`.
All four attempts failed Corpus 1. Its 256/64M attempt reached 66,569,302 guest
instructions at 30 seconds with 16,422,253 cache credits left. Retention reduced
repeated decoding, while free-pin search and full-chain validation consumed
91.96% of used cache work. The 128-resident candidate is retired from this path;
the reserved v1 fifth 256/128M/30s attempt remains unselected.

This trial distinguishes an insufficient diagnostic deadline from a remaining
fuel/work/algorithm limit. Its conditional trial distinguishes cache-work budget
from those other limits only if the new evidence supports that question. If this
second campaign fails the milestone, product-plan 24.4 requires an Astra
architecture comparison of algorithm change, resource-policy change and a
different implementation approach. Another accounting-only preparation chain
is not the selected next action.

## Minimal source change and retained safeguards

`campaign.py` imports the hash-bound v1 builder, classifier and owned-child
runner. It reuses v1's existing compressed source, complete WASM, original harness,
native observation, attribution observer and finite controls in place. No large
artifact is copied into this packet and no loader/authority system is added.
The candidate's difference from the reviewed 256-resident source is two default
deadline fields, plus one cache-work field only for the conditional profile.
`source-check/*/delta-from-reviewed-256.patch` shows the complete small delta.

All actual emitted budget fields and grants must exactly match the retained
historical fields except the selected resident/work/deadline values. Runtime
source remains independent Mixer code. It retains original validation/capability
checks, index geometry/accounting, 16 MiB cache, 8 MiB entry, 64 active pins, 48 MiB
guest memory, 256 MiB combined reservation, 100M fuel, 1B execution work, 64 frames,
host guards and consuming cleanup. The unchanged original harness preserves
first failures; `cleanup_empty=false` is expected for a failed workload while the
separate resource-emptiness event and final zero counts establish consumption.
No canonical VM source, installed profile or release authority is edited.

## Finite CI execution

Root integrates the candidate `workflow.yml` into `.github/workflows/`, commits
the complete bound inputs/review files, and dispatches once. The decisive command:

```sh
python3 -B verification/swift-cache-deadline-campaign-v2/campaign.py run \
  --output "$RUNNER_TEMP/swift-cache-deadline-campaign-v2"
```

Only a first-attempt GitHub-hosted Linux runner is accepted. Compilation uses
the same Rust 1.99.0, offline Cargo and two build jobs. Each selected profile
first runs the four v1 actual-cache controls and original harness control.
Each compile is limited to 180 seconds, each finite command to 90 seconds and
each full target to 200 seconds. The full allowance covers up to 120 seconds of
validation plus 60 seconds of cumulative runtime and 20 seconds of normal target
overhead. The existing runner retains separate five-second TERM and KILL windows.

The driver has a 540-second aggregate deadline and will not start a command unless
its full allowance plus 20 seconds for cleanup/receipts fits. This is deliberately
an admission bound, not a promise to spend every per-command maximum: slow setup
can decline the conditional attempt rather than exceed the selected campaign.
The 15-minute workflow budgets 1 minute checkout, 2 toolchain install, 1 pure
checks, 10 driver and 1 upload. The driver step therefore has one minute beyond
the aggregate deadline for final evidence and cleanup. Upload is always attempted
even on failure; hard runner/job termination cannot establish successful cleanup.

New remote groups alone are checked/signalled. Failure to verify a group absent
blocks further reuse and scratch removal. Final owned scratch removal and actual
commands, tool versions, source manifests, binary hashes, complete observations,
all effective bounds, first failures and resource cleanup are recorded. The
unmodified helper's raw wait4 RSS value is retained but marked unavailable for
VM/per-profile comparison: v1 showed a common launcher high-water floor. Logical
reservations remain separate. Unequal executed prefixes and single observations
do not establish equal-workload CPU/latency improvement.

## Local checks and limitations

```sh
python3 -B verification/swift-cache-deadline-campaign-v2/test_campaign.py
python3 -B verification/swift-cache-deadline-campaign-v2/campaign.py check \
  --output verification/swift-cache-deadline-campaign-v2/source-check
```

These are pure source/data and mocked decisions only; they launch no compiler,
guest, custody probe, native instance or UI/capture process. Actual compilation,
finite runtime controls and both-corpus feasibility remain pending remote CI.
Phones stay disconnected; computer use/capture/native remain paused; Android
stopped-v5, local custody groups, FieldLog local Swift-fetch cleanup, UnitA and
broad local hosted harness holds remain. No local PID or global inventory probe
is selected. Public SDK integration, immutable published FieldLog packages from a
separate repository, signed OTA, supported devices and GA require their separate
specified evidence. A diagnostic host success does not select production limits.
