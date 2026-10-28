# Proposed capacity comparison inside the existing runtime window

Root may select **`capacity-window-v1`**, after independent source review, for
one new remote campaign. This packet contains the source generator, runner,
workflow template and controls needed to execute it. Nothing is installed or
dispatched. The old `paired-128-v1` campaign is closed and must not be replayed.

The decision unlocked is whether the original two-corpus FieldLog guest can
finish correctly within the existing 600-second host window, and whether
retaining 512 rather than 256 decoded functions materially helps that task.
This is host feasibility work. It does not accept production defaults,
native/mobile behavior, public immutable FieldLog distribution, OTA or GA.

## Evidence and competing explanations

The actual baseline is run `40779075333`, attempt 1, commit
`295f3f18a53459449f22253687bd2d0b2c09a0ed`, tree
`294faafd3be568208a366ea66f85c5538a376ffa`. Its two full attempts and eleven
command groups are closed; both arms retain their CacheWork failure and zero
authoritative final live/reservation currents. The exact sanitized summary is
copied as `baseline-summary.json`, SHA256
`49daa97d05b25a1d74496ea97d0f9d1e14f75501545b7d4d1083808e13a58d8d`.
The local complete review seal is
`3161abdae5f7ee09a0bd67062d3ae393af17bdb99a5859b20efb3ef404affbb8`.

The bounded raw-archive read adds a useful diagnosis. At their different
failure endpoints, control completed 98,173 decodes, of which 96,890 repeated
earlier functions; dense completed 100,664, of which 99,381 repeated earlier
functions. Both had decoded 1,283 distinct functions. Yet IR build debits were
only 9.63% and 9.87% of the 768M cache debits. These are source-defined work
credits, not CPU measurements. Dense miss/insertion/removal audit loops and
shared replacement walks still visit actual resident slots. Increasing
retention can remove churn, but also makes those walks longer. Their debit
amounts, rejection checks and atomic publication paths remain unchanged.

The competing explanations are:

1. The cumulative diagnostic counters stop an otherwise feasible workload
   before its existing time bound. The 256-resident arm tests a larger finite
   observation window without changing the executed dense algorithm.
2. A 256-resident working set causes substantial churn. The 512-resident arm
   tests one capacity change under the same scalar allowances and byte ceilings.
3. Real execution time, another resource, or a correctness issue dominates.
   Neither more work allowance nor retention is then a completion result.

## Exact candidate

| Bound | Dense 256 | Dense 512 |
| --- | ---: | ---: |
| Decoded residents | 256 | 512 |
| Reservation ticket maximum | 278 | 534 |
| Frames / active pins | 128 / 128 | 128 / 128 |
| Cache work | 4,000,000,000 | 4,000,000,000 |
| Instruction fuel | 2,000,000,000 | 2,000,000,000 |
| Execution work | 16,000,000,000 | 16,000,000,000 |
| Cumulative Runtime and WASI duration | 600,000 ms | 600,000 ms |
| Combined logical reservation ceiling | 268,435,456 bytes | 268,435,456 bytes |
| Cache / single entry / guest linear memory | 16 MiB / 8 MiB / 48 MiB | same |

All other validation, source, metadata, state, value/control, host, WASI and
capability/grant bounds are byte-for-byte equivalent. The same dense map is
160,000 bytes and its pin bitmap remains two u64 words. The resident slot and
shared planning arrays expand through their original size-derived reservation
formulas; cycle bookkeeping expands through `RESIDENT_LINKS`. The ticket cap
remains `residents + 22`. No uncharged table, allocation or scan is introduced.
Every actual slot walk is retained and charged. No counter is reset or refilled.
The original 53,777,114-byte Wasm, complete validator, native oracle, harness,
two calls on one initialized owner, consuming cleanup and sticky first failure
remain identical.

The shared counter expansion is deliberate. Linearly projecting the dense
baseline's measured 332.845-second prefix to the existing 600 seconds gives
about 1.435B fuel and 9.512B execution credits. Merely raising cache work would
predictably encounter the inherited 1B fuel and then 8B execution guard.
The candidate tests the existing time window in one campaign instead. The
chosen 2B/16B/4B ceilings add finite headroom, including for larger resident
walks. These projections are hypotheses, not throughput guarantees or proof
that any counter cannot exhaust first. Reaching any limit remains a failed
workload. `attribution-summary.json` retains the exact arithmetic and source
member hashes; its unequal endpoints support no paired speedup claim.

Only resident capacity differs between the two new profiles. The older dense
run is the preserved lower-counter baseline, not a concurrent timing control.
No historical timing is compared as if it were a paired run. The same bounded
prefix observer in both new arms records 25M, 50M, 100M, 250M, 500M, 750M, 1B,
1.25B, 1.5B and 1.75B original instructions, at most ten records/8,192 bytes.
Fuel, execution work, host calls and cursor must match before any observed
prefix comparison. Equal counters still do not establish identical entropy
or complete guest state. Raw wait4 RSS retains the known launcher-floor limit.

## Admission and stop rules

The runner keeps the prior resource/custody protocol: GitHub-hosted Linux,
attempt 1 only, explicit `MIXER_CACHE_WINDOW_SELECTION=capacity-window-v1`, fresh
output, Rust 1.99.0, release/overflow checks, locked/offline dependencies, two
build jobs and no incremental compilation. The aggregate driver cap is 2,700
seconds. There are at most eleven commands and exactly two full attempts when
the campaign closes normally. Each full attempt is persisted before spawning,
with no refund, automatic retry, resume, third arm or re-dispatch authority.

Both builds, both sets of twelve finite tests, actual compiled geometry and
both original harness controls must finish before the first full attempt.
Each geometry receipt recomputes the conservative combined bound from actual
compiled inventory sizes and unchanged category ceilings. The 512-entry
conservative total is **unmeasured**. Exceeding 256 MiB rejects the entire
comparison before either full; no category or combined ceiling is widened to
rescue it. The earlier frame/pin payload deltas already sit inside their
category ceilings and must not be added a second time.

The two additional finite tests exercise the real selected resident boundary,
the highest u16 map slot, above-capacity corruption and profile rejection;
and exact scalar maxima, accumulation across phases, exhausted-limit stickiness,
all seventeen narrowing dimensions, zero limits and checked overflow. The ten
existing dense/frame/pin controls, full geometry and original shared frozen
controls remain. Actual Rust compilation and all twelve tests are still pending.

Build/finite/geometry/harness failure, source or binary drift, unsupported
behavior, invariant/exact-capacity/ticket/owner failure, malformed diagnostics,
oracle mismatch, timeout/cancellation or unresolved cleanup stops the campaign.
No second full starts after one of those failures. Ordinary resource exhaustion
permits the second already-prepared arm only after original failure preservation,
authoritative zero-resource consuming cleanup and child/group closure checks.
Unresolved command custody retains scratch and admits no further commands.

## One campaign, then decide

- If the 256 arm completes both original eleven-field observations with zero
  cleanup, it demonstrates host feasibility under this profile. Prefer its
  smaller resident count if both arms succeed; collect further representative
  evidence before any production/default claim.
- If only 512 completes, retain it as the feasible experimental capacity and
  use matched-prefix evidence to assess the retention explanation. This single
  sequential sample is not a production performance win.
- If only 256 completes, retire the larger-capacity candidate for this profile.
- If neither completes, record the first guard and actual phase/cursor in each.
  Both reaching the unchanged deadline means the next selection must address
  actual runtime cost (cache access/retention or executor architecture), rather
  than automatically increasing more counters. A remaining counter failure
  identifies an underestimated observation window and still proves no
  feasibility. Root must choose a new evidence-backed hypothesis explicitly.

Root's concrete options are to select this exact paired campaign, or decline
it and pursue a different cache/executor implementation. There is no selected
single-arm shortcut and no silent fallback from a failed 512 preparation.

## Current validation and delivery boundary

`python3 -B verification/swift-cachework-128-experiment/verify.py` passed 26
source checks and 43 pure runner methods under Python 3.14.8 with a sixty-second
internal bound. The audit and explicit guards deny children, sockets, signals,
waits and writes outside this lane. No Rust/Swift/Elixir compiler or guest,
native/UI/capture process, process inventory, held-group probe, Git mutation,
push or dispatch occurred. All local custody groups, Unit A, hosted and unknown
FieldLog fetch holds remain untouched.

The candidate is owned by the fresh `gpt-6-astra` / `xhigh` experiment lane.
Source closures and command/tool/read-set details are in `receipt.json` and
`source-check/`. `workflow.yml` is a proposal. Independent review and root
selection, actual compiled geometry, finite behavior and complete workload
results remain pending. Raw CI archive/log/review stay in the prior local
evidence directory; this proposal copies only its 4,336-byte sanitized summary.
