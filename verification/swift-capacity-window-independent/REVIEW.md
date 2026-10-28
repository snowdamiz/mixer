# Independent capacity-window source review

**Source accept** for root to select the exact frozen `capacity-window-v1`
campaign. No actionable source blocker was found. This review authorizes no
dispatch, runtime acceptance, production default, native behavior, OTA release,
published FieldLog qualification or GA claim.

The reviewed candidate seal is
`dce182dba6c4e4bf38738b486276596c7b0cbc17c798e8780ebd19287bced0d0`:
all 29 members, totaling 483,719 bytes, matched before and after the checks.
The generated source closures independently reproduce:

- Dense 256: `8a3759c514cc342c37d89df8ced0525f4c3619f774f9cbbb9a7d3bdf856a331d`.
- Dense 512: `09ac825f108574f626838e0fc54628adb5ed70fa8d8871b527bc1bba4922c0ee`.
- Proposed workflow: `370b57185345a18670e315e74e823cb5596a1543c86dae64fea6763f9e694e99`.

## Hypothesis and bounded comparison

The new capacity hypothesis is coherent but unproved. The exact archived
baseline result members confirm 98,173/100,664 completed decodes, only 1,283
distinct decoded functions in each arm, and 96,890/99,381 repeated decodes.
Build credits were 9.63%/9.87% of their exhausted 768M CacheWork budgets.
Those observations motivate a retention experiment while leaving competing
cost explanations open: a larger resident set also enlarges charged audit and
replacement walks. The candidate does not remove, discount or reset those
debits. Its shared `[bool; MAX_ENTRIES]` planning storage and corresponding
charge grow together; the dense map remains 160,000 bytes.

The 4B CacheWork, 2B fuel and 16B execution ceilings are deliberate finite
observation allowances shared by both new arms. The dense baseline's
linear 600-second projections are correctly calculated (about 1.435B fuel and
9.512B execution work), so raising only CacheWork would leave predictable
competing scalar guards. Projection does not establish completion, sustained
throughput or freedom from another guard. The failed historical arms have
different endpoints and provide no endpoint speedup claim. Matched diagnostic
prefix counters/cursors also do not establish identical guest state or entropy.

## Preserved contracts

Independent byte comparisons show that after reversing the three shared scalar
defaults and extended observer thresholds, `control.rs` is identical to the
executed dense baseline (with only the 512 profile's resident/ticket constants
also reversed). Accounting, checked overflow, first-failure stickiness,
narrowing checks and earliest Runtime/WASI deadline propagation are unchanged.
Both Runtime and WASI remain cumulative at 600,000 ms; frames/pins remain
128/128. All category ceilings, complete validation, capability/grant code,
the 53,777,114-byte Wasm, the original harness, and both original eleven-field
corpus observations on one initialized owner remain unchanged.

Only resident capacity differs between the two new profiles, with its original
size-derived storage/ticket consequences. Both have twelve selected finite
methods plus the original harness control. The new finite tests exercise the
selected resident boundary, above-capacity corruption/profile rejection,
exact scalar maxima, across-phase accumulation, all seventeen narrowing
dimensions, zero limits, checked overflow and sticky work failure.

The actual Rust geometry producer still sums the category ceilings once, then
adds the separate WASI/shared/foundation and maximum phase-temporary terms.
Frame/pin payloads already inside their categories are not added again.
The 512-entry compiled conservative sum is **unmeasured**. Both actual sums
must be at most 268,435,456 bytes, and both builds, twelve-test finite runs and
harness controls must close before either full attempt. There is no single-arm
fallback if 512 preparation fails.

The runner persists each full attempt before spawn and retains the original
two-full/eleven-command/2,700-second envelope. It requires first-attempt
GitHub-hosted Linux, explicit root selection, fresh output, source/binary/input
rechecks and command custody closure. Unexpected capacity, ticket/owner,
invariant, unsupported behavior, oracle, timeout/cancellation, telemetry or
cleanup failure stops comparison. Ordinary resource exhaustion permits the
second already-prepared arm only with preserved original failure, authoritative
zero-resource consuming cleanup and closed child/group custody.

## Executed review evidence and remaining work

`python3 -B verification/swift-capacity-window-independent/review.py` passed
**56 methods: 43 producer pure controls and 13 independent controls**, using
Python 3.14.8 in about 2.7 seconds under a 60-second review bound. Explicit
guards and audit rules denied child/socket/signal/wait effects and outside-lane
writes. Six guard-negative calls were rejected before any effect.

Independent negatives cover the extended late prefixes at each scalar maximum
and maximum plus one; exact 256 MiB admission and plus-one rejection;
double-counted geometry terms; real geometry-parser failure of the second arm
through mocked orchestration before either full; source/budget/oracle closure;
and replaced failures or nonzero/lost cleanup. Raw attribution was checked
against the 164,027-byte, 67-member closed-run archive and the two exact result
member hashes, without extracting or executing its contents.

The first review run passed all then-existing 55 methods but the reviewer
incorrectly expected 56. That reporting assertion was corrected and retained
in `initial-run-note.json`; a subsequent raw-attribution method brings the final
suite to 56. This was a reviewer bookkeeping error, not a candidate failure.

Actual Rust type checking, twelve finite tests per arm, both compiled geometry
receipts, both harness controls and the complete two-corpus workloads remain
pending. This packet performed no Rust/Swift/Elixir compilation, guest/runtime,
native/UI/capture, Git, process inventory, held-group probes, push or dispatch.
Review scratch was removed. Groups 20745, 20770, 20780, 20817, 20842, 20851,
20866, unknown FieldLog fetch, Unit A and broad hosted holds were untouched.

Root's next executable decision is to select this exact paired campaign once,
or decline it for a different implementation hypothesis. No further local
preparation or broader hardening is needed for this source decision.
