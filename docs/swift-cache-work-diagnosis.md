# Swift cache-work diagnosis

The next implementation choice should be to remove the two redundant 512-slot
patch-clearing loops from the private Swift cache. Keep the initialized,
reserved 512-slot arena and both complete decoder passes. This is a source-bound
recommendation, not an implemented optimization or a claim that FieldLog will
finish after the change.

This report uses the accepted 132-file VM closure
`f2682c6a2fd6f6e74bd00a2394ff32b704aa1e2ed3d2373ef95cdee29fa7eb2c`.
The live files matched all 132 hashes before and after the experiment. The prior
target packet and its raw observations are referenced by SHA-256 in
`verification/swift-cache-work-diagnosis/input-bindings.json`; they are not
recursively copied or modified. No further full target execution occurred.

The sole selected 53,777,114-byte FieldLog run passed complete validation and
Initialize, then failed Corpus 1 at `Cache / WorkExhausted / swift_run_work /
CacheWork`, absolute function 593, offset 344732: attempted 64,000,001 against
64,000,000. Corpus 2 did not execute. The terminal snapshot has 148,116 hits,
24,055 misses, 24,054 completed decodes and 23,990 evictions, with 64 resident
entries. Cache reservation peaked at 1,936,515 bytes against 16 MiB; terminal
resident payload was 534,184 bytes. These are prior observations, not new
measurements. The terminal snapshot follows failure completion/drain; it is not
an extra observation of the internal failure checkpoint.

`SwiftMode::scan` calls `reset` before the counting pass
(`vm/src/experimental_swift_reactor/cache.rs:1921`); `build_payload` repeats it
before the building pass (`:1990`). `reset` checks arena length, then performs
512 `meter.work(1)` calls and 512 `EMPTY_PATCH` writes (`:1876`). Each successful
decode therefore necessarily spends 1,024 credits on these writes. Metering
reaches the original `RuntimeControl::work_with_wasi`
(`vm/src/experimental_swift_reactor/control.rs:1397`), which checks the original
cumulative ceiling before accepting a credit. This is real performed work, not
a missing-budget or ignored-meter defect.

The clearing writes are unnecessary under the current decoder's control-stack
invariant:

- Both Swift pass adapters create fresh `depth = 0` and zero counts.
- Block/loop/if entry checks capacity, charges work and writes the complete
  `Patch { start, alternative: None, kind }` at `controls[depth]` before
  incrementing depth (`vm/src/experimental/cache/decode.rs:272`).
- `else` uses checked `depth - 1`; it never reads an inactive slot (`:296`).
- A nested `end` decrements depth before reading its patch; a function `end` at
  depth zero reads no patch (`:308`). Reusing a popped slot writes all fields
  again. Patch application only uses those initialized active records.

Thus old contents outside the current active prefix cannot affect a pass. This
argument does not allow uninitialized Rust memory: keep the constructor's
fallible exact allocation, 512 initialized elements and charged initialization
(`cache.rs:1665`). It also does not remove checks or charges for actual active
patch writes, `else` mutations or output patching.

A finite Release fixture used a source copy of the actual cache, original
complete-validation proof, original runtime control, original scan/build and
consuming cleanup. The only copied-source changes were a successful-credit
observation hook and one appended test. No production algorithm, amount,
ceiling, deadline, input proof or failure behavior was replaced. The hook records
credits under the existing `CacheStep`; its totals equal the authoritative
cache-work deltas. The exact command, tool versions, transformed source manifest,
hook, small source diff, stdout and stderr are retained in the diagnosis packet.

| Synthetic operation | Cache credits | Scan reset | Build reset |
| --- | ---: | ---: | ---: |
| Empty helper, cold pin | 1,229 | 512 | 512 |
| Nested block/loop/if/else helper, cold pin | 1,310 | 512 | 512 |
| Either helper, resident hit | 3 | 0 | 0 |
| 65 functions cycled twice | 164,008 | 66,560 | 66,560 |

The first two cases assert independent expected decoded control targets. The
65-function fixture records 130 misses/decodes, zero hits, 66 evictions and 2,600
resident bytes. It demonstrates the count-bound LRU behavior on that synthetic
access sequence; it does not establish the real target's working set or prove
which target functions were decoded repeatedly. One test passed, with 364 tests
filtered out. Existing compiler warnings remain in stderr. All three original
owners drained reservations and live pins/entries to zero. The disposable source,
build and temporary directories were removed after empty holder checks and an
exact process-group absence observation; no signals were sent.

Source-derived arithmetic gives a useful lower bound, distinct from measured
target attribution: `24,054 completed decodes × 1,024 = 24,631,296` compulsory
reset credits, or 38.4864% of the terminal 64,000,000 credits. Between Initialize
and Corpus 1 terminal, `23,919 × 1,024 = 24,493,056` compulsory reset credits are
implied. The incomplete final miss may contribute additional reset work; this
packet does not attribute it or identify the precise failing inner operation.
There is no target per-stage trace or CPU profile. These calculations do not
predict a new terminal count, runtime speedup, stdout parity or completion.

Other costs are visible but should remain separate. Shared `pin` linearly scans
up to 64 pin records and 64 resident slots, then scans/plans LRU eviction on a
miss (`vm/src/experimental/cache/borrowed.rs:672`, `:731`). A miss always counts
then builds the body; a later miss for an evicted function rebuilds it. The target
counters alone do not identify unique functions, reuse distances, scan lengths
or per-stage cost. Removing one decoder pass would disturb exact fallible
allocation, pre-eviction size checks and count/build agreement. Adding indexes or
changing residency policy needs more state/accounting and shared-algorithm
coordination. Neither is the smallest first change. No bound widening is
recommended.

The proposed patch should replace the clearing helper with an O(1) arena-length
check and an explicit ordinary meter check at each existing pass boundary. It
must delete the writes themselves, rather than execute them without charging.
Preserve descriptor/parameter checks, body bounds, every real byte/LEB/local/
instruction/branch/control operation's existing charges, both pass agreement,
allocation/admission and publication checks. Keep constructor work at 640 for
the 64-slot/64-pin fixture. Keep cache bytes, entry bytes, entries, pins, work,
deadlines and all other runtime budgets unchanged. Numeric Swift LRU timestamps
will differ because they use cumulative work; every successful pin still spends
positive work, so its ordering must remain identical for the same successful
pin/release sequence.

Before implementation, root should select an explicit additive amendment to
`docs/swift-cache-stage-contract.md:149`: that contract currently requires every
reset slot to be charged in both passes. The amendment must authorize eliminating
the redundant operations and define the replacement boundary checks. It must
leave the frozen legacy `[Patch; 128]` wrappers, public layouts, APIs, identities,
revision constants and exact legacy work/error traces unchanged. The likely
implementation ownership is private Swift `cache.rs`, its tests and the selected
contract/evidence files. The shared decoder needs tests/argument review, not an
algorithm edit. Any change to the named temporary inventories, helper borrows or
phase footprint map needs coordinated reassessment; keep reservations
conservative rather than claim savings from deleted local values.

The candidate needs these targeted failure and invariant controls:

- Poison all initialized patch fields through a test-only seam, then use actual
  cache misses for flat, sibling, nested block/loop/if/else and br_table shapes.
  Assert independent complete IR/targets, both-pass agreement and zero clearing
  writes; prefill again before the build pass so scan output cannot mask a bug.
- Exercise deep-to-shallow reuse, reused sibling slots and the valid inclusive
  depth-512 boundary. Retain rejection at depth 513 in complete validation.
- At a private borrowed-decoder seam, use hostile inactive patches with an
  empty-stack `else`, duplicate `else`, truncated/unclosed control and trailing
  bytes. Require typed failures without reading an inactive patch. A new direct
  pass may start at depth zero over leftover scratch; never retry a failed
  original runtime control, whose terminal failure must remain sticky.
- Enumerate every candidate work prefix and cancellation checkpoint, including
  both new pass boundaries, scan, allocation/build and publication. Require
  unchanged first-failure precedence, no uncharged mutation/publication, honest
  evictions and consuming zero cleanup. Retain deadline-origin/overshoot controls
  at the new boundaries. Preserve the old sealed baseline rather than rewrite
  its expected outputs.
- Retain count/build mismatch, exact capacity and all allocation-ordinal failure
  tests. Compare same-sequence pin/nonce/LRU/eviction results, retained-byte/live
  ledgers, three fixed buffers and zero-allocation hits/releases. Keep the
  frozen legacy feature-mode traces and public-surface checks exact.

This packet contains diagnosis and a baseline fixture only. Root selection,
candidate implementation and independent review precede any newly authorized
bounded full-reactor attempt. Full Swift parity, the second corpus, app/native
behavior, published FieldLog consumer packages and all final acceptance gates
remain pending. Phones stay disconnected; no device, UI, provider, network,
credential, service or publication work was performed.
