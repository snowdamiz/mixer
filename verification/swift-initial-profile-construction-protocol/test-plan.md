# Finite next implementation verification

These are required future tests; none is marked passed by the data-only probe.
Use Rust1.99 macOS arm64 host Debug and optimized modes only. Run exact named
methods, record each command and source closure, and keep existing limits and
deadlines. Full suite/full target, native/simulator/emulator/device/UI/capture
tests remain outside this selection. No physical-device reconnect request.

The selected input is the exact complete record under
`inputs/root/selected-host-budget.json`, never `Default`. Proposed negative and
boundary records under `test-budget-records.json` each carry all 17 values;
their altered budget is not the selected record. Tests must paste all values
explicitly into the named Rust test source, compare that source to this roster,
and never admit a hidden partial override/default. Zero unrelated budgets are
not universally invalid; narrowing a limit can independently exhaust construction.

1. **Successful fresh route:** actual official supported reactor bytes through
   unchanged safe validation/adoption, optional None and actual same-control
   AccountedWasi. Cache slot starts None. Verify exact original constructor and
   phase completion, guard-before-acquisition call order, full budget comparison,
   actual cache fields/lengths/capacities/tickets, header bytes and physical retained
   row File bytes from that cache proof. The finite fixture size/source budget is
   explicit; it must not silently replay the historical 80k-function target.
2. **Closed outcome matrix:** exercise tags 1–8 and both nested phase-completion
   results for tag 4, both row results for tag 8. The empty-slot occupancy refusal
   returns its consumed adopted proof; another live cache's owner, nonce, shape,
   ledger and File remain unchanged. Verify construction/header/row not-attempted
   states by actual call counters in test-only fixed instrumentation, not just tags.
3. **Original failures/cleanup:** prepare owner/deadline/capacity rejection retains
   adopted; pre-partial construct failure returns Some(rejected_adopted); partial
   failure returns None with actual cleanup/quarantine observations. Preserve
   exact first-failure cursor/kind/code/resource/attempted/limit and usage. Inject
   a separately source-reviewed phase-completion boundary fault, retain both
   failures and restore only the actual replaced authority before cleanup. No
   invented phase marker, repaired ledger, refund or diagnostic reclassification.
   Successful cache survives completion/header/row failure in the caller slot;
   original CacheCleanupTail and its returned storage are consumed exactly once.
4. **All 17 budget fields:** one-field drift each refuses before prepare even
   where `min(entries,defined)` hides a scalar difference. Test each actual
   canonical ceiling and explicit exhaustion independently. Entry limit zero and
   entry limit above cache capacity remain acceptable header cases when actual
   construction and B<=capacity succeed. Zero slots/pins may construct under the
   VM but header returns unsupported; no clamp to 1. No global all-zero rule.
5. **Authentic owners and exact state:** foreign adopted/header/buffer/WASI tickets,
   missing header, wrong category/bytes/owner, all slot/pin/index/plan/patch lengths
   and capacities, nonce and every usage/live field, including peaks and own
   active_pins. Defensive faults restore replaced actual storage before cleanup.
   Same-control optional WASI succeeds without historical-instance claims;
   None remains supported. An unrelated positive Cache reservation refuses B
   equality; an authentic preexisting zero-byte Cache ticket is permitted and
   separately cleaned by its original owner. Other state/WASI owners are allowed.
6. **Chronology and borrow privacy:** actual postconstruction imported-index failed
   acquisition reproduces the independent chronology counterexample, yet cannot
   call a guard constructor. Compile-negative cases attempt guard literal from a
   sibling, returned guard/proof borrow, cache move/mutable acquisition/control
   mutation while guard lives, independent snapshot injection into the row bridge,
   closure/reentry substitution and selected-record construction from external
   caller. Inspect exact source closure for the sole private literal/call path;
   compile cases support privacy/lifetime facts and do not alone prove semantics.
7. **Header and local structure:** encode all named fields at exact offsets,
   little endian, magic MIXPRF01, 24 reserved scalar zero bytes, eight distinct
   opaque 32-byte claims and trailing 128 zero bytes. Check overflow/narrowing,
   policy/count/type/defined-body boundaries, all slot/pin pairs 1..64, checked
   H/B and actual cache capacity. One independently changed expected size,
   alignment, type ID/count, schema/endianness/width/formula value must refuse
   local error 6; changed source/tool with identical shape supplies no internal
   build refusal or authority claim. Literal selected data must be reviewed and
   distinct from fresh actual measurement values. Record every complete
   Result/Option/guard/caller/error/return/move place in the actual implementation.
8. **Rows:** bridge takes only guard+File and derives retained cache.proof internally.
   Actual output admissions and write faults preserve the accepted adapter's exact
   code/stage/offset/output_bytes/output_attempts, including metadata/position
   errors where safely injectable, interrupted writes, zero, short/error writes,
   per-block exhaustion and late failure. Header is retained when rows fail. File
   size/offset/acknowledged progress establishes no rollback/fsync/durability.
   Source-bound fixed fault injection must not become a public callback seam.
9. **Whole new bounds and cleanup:** independently review all sources, generated
   compile-case inputs, caller/refund/tail boundaries and complete byte/align
   measurements. Join actual new places/lifetimes with original constructor,
   row writer, original owner, File/Metadata/write transfers, heap extents,
   source loops, requested I/O and phase restore/drop order. Keep original
   reservations/caps/deadlines unchanged. No 11,912/13,904 row allowance or source
   action bound is inherited as combined capacity or VM debit. If the proof cannot
   close under those unchanged limits, stop at that exact failure for root review.
   Record owned children reaped, owned TMP/scratch/native instance cleanup (no
   native instance is started), and preserve unrelated projects' processes/data.

The future dedicated host runner must impose finite command/output/time bounds,
retain raw failed as well as successful output, use owned scratch, remove compiler
products, hash exact source/tool/target/cfg/optimization/executable evidence, and
avoid native or process inventories. Final accountable root and independent review
remain necessary for component acceptance; CI/compiler/OS expansion, canonical
integration, real digest/preimage/source/build/custody binding, retained-descriptor
composition, original typed result/final15-ledger context, replay, semantic metrics,
FieldLog published package, physical/store/operational and GA gates stay pending.
