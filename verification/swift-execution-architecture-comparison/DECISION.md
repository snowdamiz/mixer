# Swift execution architecture comparison

Root selected a guarded dense resident index and free-pin bitmap, keeping 256
resident functions, compared with the existing algorithm under one identical
finite whole-owner calibration profile. The source candidate and two-arm driver
are prepared inside this directory. Compilation, finite controls and the two
full attempts remain pending; root has not selected a runtime dispatch.

The trigger is product-plan 24.4: two executed campaigns failed the same complete
milestone. Both campaigns are closed. The first campaign's optional fifth attempt
and the second campaign's two spent attempts are not reusable authority.

## Evidence that changes the decision

The actual first campaign is sealed by `4dcf3f8bf9533d0234a5966d111b1d3373299cbfb816ab871d0764c0a1024cec`.
The actual second campaign is sealed by `c6bde1201697149bfa84d2f31b112d14d8c1e35ac005fc908a16433941f23df8`.
Both seal paths and exact source/result hashes are in `findings.json`.

1. All six full attempts failed Corpus 1; Corpus 2 never started. The second
   campaign's 256/64M/60s arm stopped at CacheWork 64,000,001 after 41.736968s.
   Its 256/128M/60s arm stopped at InstructionFuel 100,000,001 after 44.335205s,
   with 99,059,182 guest instructions. Both returned to zero logical resources,
   and all eleven second-campaign commands have closed-process evidence.
2. The host already uses `cargo test --release`, with optimized output, retained
   overflow checks, and no recorded RUSTFLAGS override. The exact guest build
   used `-Osize -gnone -whole-module-optimization`. Recommending release builds
   or treating the 53.8MB artifact as an unoptimized guest would be unsupported.
3. `RuntimeControl::instruction_with_wasi` charges one fuel unit before every
   original guest instruction; bulk work charges additional fuel. At the second
   failure, 940,818 units are the difference between fuel and instruction count.
   Neither cache lookup nor an alternative dispatch representation can remove
   those original guest instruction obligations while preserving this policy.
   Repeating a cache/deadline-only increase cannot complete the same prefix under
   the original 100M allowance.
4. At that fuel stop, 39,668,442 chain-validation credits plus 26,461,390 pin-search
   credits are 93.29% of 70,883,119 cache credits. Completed decode count remains
   1,006, including 521 repeats, and cache hits reach 2,729,999. Increasing
   residency beyond 256 is not the best-supported next hypothesis.
5. These are implementation work counters, not CPU samples. The accepted test
   build updates `Hooks` TLS at each cache checkpoint and `CurrentAttribution`
   through a RefCell at each cache debit. Every `work_with_wasi` checks the clock;
   frame agreement obtains an entire `usage()` snapshot, including another clock
   read, just to compare live counters. Source inspection establishes these paths
   exist; no retained measurement attributes elapsed time to them or establishes
   which copies LLVM eliminates. VM-attributable RSS is also unavailable.

`analyze.py` independently joins the sealed result files, source archive members,
release-build receipts, original guest build receipt and eleven-field oracle.
Its successful offline output is retained in `offline-check.json`. The initial
1MB source-member guard rejected the 9.25MB explicit dispatcher inventory; the
corrected guard is 16MiB, still restricted to nine named members of the hashed
archive. This was source inspection only, with no compiler or guest attempt.

## Alternatives and choice

| Alternative | What it can resolve | Main cost or limitation | Decision |
| --- | --- | --- | --- |
| Dense validated-function-to-slot map plus 64-bit free-pin map | Removes linked-chain traversal and first-free linear scanning from millions of successful calls, while retaining actual resident and token checks | New private metadata and mutation invariants need actual finite tests and conservative accounting | Select as next implementation hypothesis |
| Compact control/ownership interface | Reading live counters directly instead of building `SwiftRunUsage`, and returning a compact terminal marker while one owner retains the full failure, could reduce hot-path clock reads and large result transfers | CPU contribution is unmeasured; changing failure propagation touches more operations and must preserve exact first failure/custody | Keep separate; do not combine into the selected candidate |
| Explicit finite whole-owner calibration policy | Allows measurement beyond the proven insufficient 100M fuel ceiling, without resetting either corpus | A large allowance alone does not improve performance or define a safe sustained-app schedule | Necessary accompanying experimental policy; not a production default |
| Independently authored compact basic-block interpreter | A second Rust executor could lower validated Wasm into compact block/operand records, execute with a tight dispatch loop, and retain source PC/fuel mapping and capability imports | New execution semantics, IR accounting, traps, floating point, indirect calls, bulk operations and cleanup need differential coverage; it still owes original-instruction fuel | Retain as genuinely different fallback; not the smallest next experiment |

The second executor would be owned Mixer code, not a third-party VM, JIT, native
app workaround, compiler output substitution, or Patch/Skip material. It must
consume the same validated bytes and same host ABI. Each original instruction
would still be charged before its effect; a block may not charge one fuel unit
for many original instructions. A third-party reference oracle may compare it,
but cannot become the production engine or satisfy this owned-VM milestone.

## Exact candidate contract to coordinate before implementation

Start from the sealed v1 source archive and the accepted 256-entry/60s
parameterization, not the concurrently edited canonical tree. Candidate edits
belong only in this directory or a separately assigned root-owned lane.

- Replace the 128-bucket linked resident index with an admitted `Vec<u16>` keyed
  by the validated absolute function ID. Zero means absent; values
  1..256 identify a resident slot. The same sealed validation proof provides the
  function bounds: metadata validation admits definitions only within
  `80,000 - imports.len()`. The fixed payload is 160,000 bytes. This workload has
  79,832 definitions and 34 imports. Imported functions remain unpinnable by this
  path. Index dimensions never come from an unchecked requested function.
- On a hit, check key bounds, encoded slot bounds, actual occupied slot, and the
  actual resident function identity. The map alone never authorizes execution.
  Check pin owner/slot/nonce and actual resident pin count at every view/release.
  Preserve immutable validated source, decode policy and signature checks.
- Audit all 256 actual slots on every miss and before structural mutation;
  verify each occupied slot's reverse map and reject orphan, duplicate, wrong-key
  or out-of-range associations. This prevents a corrupted absent-map cell from
  turning an existing function into a duplicate decode/publication. A corrupt
  cell that points at another key cannot authorize that other key's code. There
  is no linked topology whose unvisited tail must be trusted. Do not merely
  early-return from the old chain walk or discard its corruption checks.
- Add an 8-byte free-pin bitmap for the unchanged maximum 64 pins. Select the
  lowest set bit, then verify the actual PinRecord is free. All record/mask/live
  admission checks and charges precede infallible publication. Release validates
  the original token first and publishes the cleared record and available bit
  together. An exhausted mask is checked against the records before reporting
  exhaustion; an inconsistency is an invariant failure. Failed acquisition and
  cancellation leave record/mask agreement intact. No pin or frame limit grows.
- Use private Swift-mode hooks/defaults to leave the frozen generic mode and its
  original traces intact. Count actual new map/bitmap/audit work; do not discount
  the same performed work. Credit categories may identify new operations but
  must still sum to actual debits, including the rejected first debit separately.
- Admit payload, headers, tickets, copies and temporary borrow/operation storage
  before allocation. Reuse the index's lifetime where possible. Exact-capacity
  and consuming-drop order remain. The prior conservative envelope leaves only
  1,647,194 bytes; payload arithmetic suggests room but does not prove admission.
  The actual finite envelope must remain below 268,435,456 bytes. No heap growth,
  observer storage, or allocator/RSS claim can be hidden in this margin.

## Bounded executable campaign proposed for root selection

The named unlock is one validated owner initialized once, then both unchanged
`mixer_fieldlog_corpus_v1` calls returning status zero and each producing all
eleven original native fields, followed by consuming zero-resource cleanup.
The exact existing test is
`experimental_swift_reactor::execution::frame_operations::memory_growth_operations::lifecycle::tests::exact_diagnostic::exact_reactor_target_once`.
The driver retains the original target/harness bytes. Do not substitute a
synthetic corpus or a reconstructed Wasm module.

Proposed common profile: 256 residents; 1,000,000,000 lifetime fuel;
8,000,000,000 lifetime execution-work credits; 768,000,000 lifetime cache-work
credits; Runtime and WASI deadlines both 600,000ms from the original single
start instant. All validation, byte, memory, frame, pin, value, control, host-call,
WASI transfer/work/log and capability ceilings remain unchanged. No per-call
reset, replenishment, new owner, changed clock origin or public profile loader.

These upper bounds are explicitly a finite feasibility envelope, not a claim
that completion needs or fits these amounts. The recorded 100M/44.3s failure
proves a lower bound, not the total cost. The 10x fuel and approximately 11x
execution/cache headroom avoid spending the next attempt immediately on a
predictable neighboring cumulative limit. The 600s runtime ceiling remains an
independent stop. Nothing in this profile establishes mobile acceptability.

1. In fresh remote Linux CI only, build optimized Rust 1.99.0 with locked offline
   dependencies, retained overflow checks and the same test observer. No local
   compilation, guest/runtime, native, UI, capture, PostgreSQL, or held custody
   action is selected.
2. Run existing finite cache/harness controls and new actual-candidate controls:
   all 256 slots including encoded value 256; lowest/highest defined key and
   import rejection; forced miss/eviction and pinned victim; map/slot corruption
   and absent-map duplicate prevention; all 64 pins and rejected 65th; stale,
   foreign, reused and double-release tokens; nonce exhaustion; failure and
   cancellation at every new debit/publication prefix; allocation/exact-capacity
   failures; maximum simultaneous reservation envelope; and consuming cleanup
   after every success and injected failure. Frozen-mode controls stay unchanged.
3. Only after its finite and harness controls pass, spend each arm's full attempt
   once: the original 256-entry algorithm first, then the dense candidate.
   Retain the exact
   53,777,114-byte input hash
   `24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994`,
   original harness/source archive, host grants and oracle. A read-only bounded
   observer may record 25M, 50M and 100M guest-instruction checkpoints in addition
   to the existing lifecycle observations; at most three such records per owner,
   at most 8KiB total, no counter reset and no change to first-failure authority.
4. The second arm may proceed after an ordinary resource failure only when the
   first arm's source/input/bounds, first failure and complete cleanup are
   verified. Any invariant, oracle, telemetry or custody defect stops the
   campaign. The comparison changes the algorithm at identical finite limits;
   it is not a replay of the old profile. Original failures remain failed.

Maximum: two full attempts, each watchdog 750s (120s validation + 600s runtime +
bounded cleanup/receipt margin); each build 180s; each finite/control command
90s; driver 2,700s; command step 46 minutes; workflow 55 minutes. Eleven worst-case
commands plus individual cleanup/receipt margins total 2,485s. Pre-admit each command's worst-case time
plus cleanup before spawning. Reuse the accepted guarded-command/custody design:
count attempts before spawn, no retry/resume, record the pending command before
spawn, stop on unresolved custody, and signal only the owned remote group with
the existing TERM/KILL windows. Remove scratch only after every owned group is
proven absent. No change is proposed to local actor holds.

Stop immediately on source/input/profile drift, invalid telemetry, unexpected
capacity, failed finite controls, oracle mismatch, invariant, unresolved cleanup
or missing terminal command evidence. Resource exhaustion or deadline is a
failed full attempt, never a feasibility pass. Preserve the original failure in
`final_failure`; `cleanup_empty=false` on that failed owner is expected. Check
the separate final usage for all eight zero reservation currents, zero tickets,
all six zero live counters and no cleanup invariant. A success additionally
requires `cleanup_empty=true` and no first failure.

If the candidate completes and the control does not, report measured feasibility
and its specific limiting-resource difference. If both complete, compare actual
work/churn and complete-workload CPU/wall observations. One pair cannot establish
a variance-qualified speedup. If candidate work falls but time does not, the
clock/snapshot/test-hook hypothesis survives; the separate compact-control
candidate becomes the next small experiment. If candidate hits the 1B fuel cap,
do not authorize another automatic increase: reconsider the execution policy
and application path using the new exact prefix. The different block executor
is a next architectural option, not a way to evade original instruction metering.

Sustained application scheduling remains separate work: future yield/lease
authority must live outside untrusted guest code, preserve state at safe points,
bound aggregate CPU/time/host work, and meter restarts. Resetting counters per
corpus or silently reviving a terminal owner is rejected.

## Current boundary

This packet contains source/data inspection, the selected source candidate,
finite controls and remote driver. The candidate has not been compiled, no new
full attempt has run, and the required milestone remains unmet. Canonical source/status files and frozen
evidence packets were not edited. All native, phone, local compiler/runtime,
UnitA, database and custody holds remain. Public SDK/FieldLog release, mobile
performance, signed OTA and GA remain unqualified by this comparison.
