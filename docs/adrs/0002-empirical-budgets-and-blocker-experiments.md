# ADR 0002: Empirical budgets and decisive blocker experiments

Status: accepted execution policy, October 28, 2026, following the user's direct
request to revise the plan, experiment aggressively on blockers, and escalate to
Astra 6 Extra High agents. This decision changes planning and delegation policy;
it does not execute a VM experiment, alter a production limit or pass a gate.

## Decision

Apply product-plan sections 20.3 and 24.4. Treat provisional numeric ceilings as
testable hypotheses. Keep security, validation, capability, signature and lifetime
invariants enforced. Preserve original failures and compare bounded alternatives
using actual workload results. Use fresh `gpt-6-astra` / `xhigh` agents for stalled
blocker diagnosis, competing approaches and independent evaluation; ordinary
implementation stays on `gpt-6.1-sol` / `xhigh`. The controller remains user-selected.

Repeated review and accounting preparation must unlock a named executable test
or integration. At the plan's escalation trigger, the coordinator selects a small
experiment campaign and decides from its result. Existing per-run source freezes
preserve evidence; they do not permanently freeze experimental design decisions.
Current explicit security denials and native, local-custody and UnitA holds remain
in effect. No prohibited action is retried through a different model or harness.

## First VM campaign: cache capacity versus work allowance

The exact retained reactor baseline fails CacheWork at 64,000,001 / 64,000,000.
Its measured scan/build attribution and cache-pressure evidence motivate a
comparison; they do not prove a larger cache will succeed. Bind each figure to
its original source/run seal rather than merging historical observations.

| Variant | Decoded resident limit | Cumulative cache-work credits | Question |
| --- | ---: | ---: | --- |
| Baseline | 64 | 64,000,000 | Reproduce or reuse the exact comparable preserved failure. |
| Work only | 64 | 128,000,000 | Does additional bounded work permit correct completion? |
| Capacity A | 128 | 64,000,000 | Does retention outweigh larger tables and planning scans? |
| Capacity B | 256 | 64,000,000 | Does further retention reduce rebuild work? |
| Combined, only if justified | Best observed capacity | 128,000,000 | Does combining the measured changes permit completion? |

Reuse the original bounded baseline harness and loading path where permitted.
Prefer a small cache/profile experiment over designing another loader, release
authority or provenance subsystem solely to collect a performance comparison;
an actual defect or explicit hold still requires its concrete correction.
Comparability requires the same effective implementation/accounting semantics,
toolchain, inputs and harness. If parameterization or instrumentation materially
changes those, run a 64-entry/64M control on the candidate implementation and
preserve the historical failure separately. Do not compare historical timings
across changed environments as if they were a paired benchmark.
Run cheap finite checks before full comparisons. The first campaign has at most
five full-workload attempts including a fresh baseline if needed. A repeat must
have a stated purpose and finite count: comparability, independent reproduction,
variance measurement or a concrete correction. Count it within the campaign's
run bound rather than retrying an unchanged failure indefinitely. If those
variants cannot distinguish the hypotheses, select
another approach or report the specific missing measurement. Test 512 residents,
a different algorithm or another limit only in a new evidence-driven campaign.
Do not multiply every variant into an exhaustive Cartesian product.

Initially retain the 16-MiB cache, 8-MiB entry, 64 active pins, 48-MiB guest linear
memory, 256-MiB combined reservation, guest instruction/execution limits and
existing deadlines. Resident entries and active pins are different resources.
The implementation currently has fixed-size structures and coupled ticket limits;
any parameterization must account for all changed tables, ticket slots, counters,
walks and overlapping lifetimes inside the retained byte ceilings. Do not change
one integer while leaving invalid indexing or uncharged allocations. Do not lower
accounting charges, reset cumulative counters, omit inputs, substitute an easier
workload or relax the output oracle to make a candidate finish.

Use the same full Swift artifact, native/reference observations and two corpus
calls on one initialized owner, preserving cumulative state/counters. Record the
actual source/tool/profile identities, phase outcomes, complete observations,
work/instructions, cache churn and decode counts, elapsed/CPU time, available
peak RSS, logical allocation/reservation peaks separately, first exhausted
resource, failure and final consuming cleanup. Unavailable metrics stay pending.
Keep a watchdog and bounded cleanup; unresolved cleanup blocks reuse of the
affected execution resources. No native/UI/capture or held local run is selected
by this document. Prepare the authorized isolated host/CI path and name the exact
hold-release condition when a run cannot currently proceed.

Classify results precisely:

- A longer prefix before another failure is diagnostic progress.
- Both corpus calls completing with correct observations, no invariant failure
  and successful consuming cleanup is host feasibility.
- A larger work allowance permitting completion is a profile feasibility result.
- Lower measured cost on the same completed workload is an optimization result;
  CPU/latency claims need comparable repetitions sufficient to address variance.
  A single timing is only an observation.
- Mobile, public SDK, signed OTA and GA acceptance require their own evidence.

At campaign close, select the smallest demonstrated adequate experimental
configuration with headroom and a concrete integration action, or select a
materially different hypothesis. Do not select a production default from one
host corpus. Calibrate it against real FieldLog workloads and supported devices,
including the product's separate startup, responsiveness, added-memory and patch
size targets. Design sustained-use fuel replenishment/yield semantics explicitly.

## Integration priority and reporting

Maintain a dependency-ready lane on public-SDK FieldLog native iOS/Android flows
while VM experiments advance; full-reactor completion is not a prerequisite for
native shared Swift implementation. During the native pause, continue source,
host and cross-build work and retain runtime acceptance as pending. Each campaign
report names the usable behavior advanced, the blocker removed or still present,
and the next decisive command. Commit/test/artifact counts are supporting evidence.

The binding scope remains W01-W18, D0-D8 and G01-G38. Existing independent engine
ownership, signing isolation, release authorization and all final acceptance
requirements remain intact.

Evidence anchors: [experimental envelope](../swift-reactor-owned-profile-design.md),
[exact baseline result](../swift-exact-reactor-after-plan-reuse-result.md),
[cache-pressure diagnosis](../swift-plan-cache-remaining-work-diagnosis.md), and
[scan/build attribution](../swift-current-attribution-runtime.md).
