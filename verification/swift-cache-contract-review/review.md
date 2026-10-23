# Independent Swift cache contract review

Decision: refine the cache/control contract before freezing dependent cache work.
The bounded descriptor prerequisite may proceed. This is review of a proposal
against current source; no Swift cache implementation or target execution is
accepted. Source hashes, commands, tools and complete bounded outputs are in
`receipt.json`. Only this review directory was written by this lane.

## Required refinements

### R1: consuming cleanup must preserve a rejected owner

The proposal requires checking the cache/control pair before any drop or refund
(`docs/swift-cache-stage-contract.md:279`) and requires that the original owner
can still drain a foreign pairing (`acceptance.json`,
`foreign_stale_nonce_and_control_ownership`). It then specifies
`cleanup(self, &mut CacheControl)` without an owned rejection result at line 286.
Returning a plain `Err(SwiftRunFailure)` from that consuming function implicitly
drops `self`; the correct control cannot subsequently drain its allocations or
original proof tickets. This is the same ownership issue already resolved for
`CacheConstructionFailure.rejected_adopted` at lines 183-192.

Freeze a private unboxed result with ownership returned only for a rejected
preflight:

```rust,ignore
struct CacheCleanupFailure {
    failure: SwiftRunFailure,
    rejected_cache: Option<SwiftFunctionCache>,
}

fn cleanup(
    self,
    control: &mut RuntimeControl,
    wasi: Option<&AccountedWasi>,
) -> Result<(), CacheCleanupFailure>;
```

This direct-borrow spelling avoids requiring ordinary operation-phase
preparation under cancellation/exhausted work. A private cleanup wrapper is also
acceptable if it can be constructed from these borrows without admission,
cancellation/deadline checks or work, using the pre-reserved cleanup envelope
in R3. The cache header must be checked while the whole cache is intact, before
destructuring it. On invalid WASI pairing or invalid cache/control pairing,
return `Some(self)` with zero vector drops, pin changes, refunds or allocations.
After successful preflight, consume/drain all storage even if a later refund or
live-count invariant fails; then return `rejected_cache: None`.

Extend the existing ownership test: call consuming cleanup with a foreign
control, recover the exact owner from the failure, verify both ledgers and
allocations were unchanged, then drain successfully through the original
control. Cover a foreign optional WASI context as well.

### R2: a borrowed actual WASI context must belong to this control

`CacheControl { control, wasi }` at lines 259-277 prevents simultaneous dispatch,
and resamples an actual context. It does not itself prove that the context was
constructed against the supplied control. A cache for control A can otherwise
sample context B and latch B's counters into A's first failure. Checking only
the cache header or the two adopted-proof tickets does not prove WASI pairing.

Add a narrow helper beside the sealed header, not a copied-counter constructor:

```rust,ignore
impl AccountedWasi {
    fn checked_usage(
        &self,
        control: &mut RuntimeControl,
        cursor: Cursor,
    ) -> Result<WasiUsage, SwiftRunFailure>;
}
```

It borrows the actual `AccountedWasi.header` ticket and validates it against the
same control before accepting its usage. It allocates nothing, spends no work
and checks neither cancellation nor deadline, so cleanup may use it.

Refine observation provenance within this helper: a foreign/missing header has
no trusted pairing, so use `None` for that invariant snapshot. A same-owner
ledger underflow must retain the actual context observation. For example, a
private pure `RuntimeControl::reservation_owner_matches(&ReservationTicket)
-> bool` can test nonzero exact identity; only when true may the helper obtain
`Some(context.usage())` and pass it into the existing full
`check_reservation_owner`. Full owner/accounting validation remains required.
Calling `check_reservation_owner(..., None)` unconditionally would lose the
actual observation on a same-owner accounting invariant. This helper returns
diagnostics, never reservation authority.

Freeze preparation order:

1. Validate the optional WASI header/control pairing; accept no foreign counters.
2. Check both actual adopted-proof tickets (construction preparation and the
   later supplied owned proof), or check the actual cache header (operations
   and cleanup), using the trusted current observation when present.
3. For allocating/work operations only, check sticky terminal/cancellation/
   deadline, calculate/enlarge the existing construction ticket, then construct
   `CacheControl`/phase/parts/meter/reader wrappers.
4. Keep immutable WASI and exclusive control borrows for the complete operation;
   sample `wasi.map(AccountedWasi::usage)` anew at each later boundary. Store no
   observation or observation authority between operations.

For consuming construction/cleanup rejection, return the supplied owner intact
as specified in R1 and the existing construction failure wrapper. For release,
return the owned pin on failed pairing. Test a foreign context with deliberately
different real dispatch counters, zero preflight effects, foreign failure
`wasi=None`, same-owner header-accounting first invariant with actual usage, and
unchanged already-latched first cause.

### R3: reserve cleanup temporaries before cleanup becomes necessary

The exact exclusive header formula at lines 214-220 covers stored fields.
Construction/pin phases additionally cover transient wrapper moves/readers and
restore their previous bound after returning (lines 222-236). Cleanup later
creates its own consuming owner/result, optional rejected-owner, vector/ticket,
parts and failure/observation transfer temporaries. The proposal does not name
where this additional cleanup envelope remains reserved after those phases end.

It cannot be repaired by enlarging construction during cleanup:
`RuntimeControl::enlarge_construction` starts with `self.check(cursor)` at
`control.rs:858`, so terminal/cancelled/expired/exhausted operation cleanup must
not depend on it. Successful ordinary cleanup must also remain admission-free.

Freeze a checked conservative named-object cleanup envelope at construction,
admitted within the same exclusive-header ticket, for example:

```rust,ignore
cache_header_bytes = size_of::<SwiftFunctionCache>()
    .checked_sub(size_of::<ValidatedSwiftReactor>())?
    .checked_add(cache_cleanup_temporary_bytes()?)?;
```

Include the actual chosen cleanup rejection/Result owner shapes, simultaneous
cache moves, aggregate-entry/three-vector transfer owners, optional tickets,
borrowed parts/wrappers, and observed refund/fault/failure transfers. Do not copy
unsubstantiated counts from WASI. Alternatively, demonstrate and freeze a named
foundation allowance that covers these exact simultaneous objects without
double-using another live phase's allowance. The existing foundation function
only names proof/control/adopted/failure/usage/ticket objects, not Swift cache
owners (`control.rs:349`). Accounted WASI already makes a separate permanent
cleanup allowance in `accounted_header_bytes` (`accounted.rs:67-75`).

No new ticket is needed; the 86-ticket inventory remains unchanged. Record
target size/alignment and simultaneous named counts, then test cleanup and
intact rejection after earlier operation phase completion under cancellation,
expired deadline, exhausted work and a latched terminal failure. Assert no
admission/work/allocation, conservative current accounting until actual drop,
and zero remaining owned tickets after complete original-owner teardown.

## Descriptor prerequisite observations

No copying or stored layout change is needed for the proposed six immutable
views. Current metadata already retains the exact function type/body spans,
signature parameter spans, globals, ordered data/element spans and declared
memory/table maximum forms. Suitable assignment details:

- Signature lookup uses absolute indices for all 34 imports and all defined
  functions. Function-span lookup rejects imports and maps absolute index 34
  to defined ordinal 0; it must not call the current public `function_body`
  with the absolute index. Type lookup is separate.
- Function body begins at the local-group declaration, after the body size LEB.
  Element payload contains only encoded function-index LEBs after the count;
  data payload contains raw bytes after its length. Preserve empty ranges,
  overlapping segment order, exact offsets and original retained allocation.
- Explicitly choose `host_maximum` semantics. Current metadata tuples contain
  the resolved effective maximum: memory 768 and table 46,713 for this exact
  ABI. The independent policy ceilings are 768 and 65,536. The descriptor test
  should assert the chosen table value; the current fixture manifest asserts
  table minimum/declared maximum but omits table host maximum.
- Global initializer failure cursors need a documented O(1) checked absolute
  offset derivation from the retained source slice or a separate Swift-only
  offset accessor. Existing `GlobalView` has no offset field; preserving its
  legacy layout does not prevent such a separate accessor.
- Keep public `SegmentView`, proof/metadata layouts and legacy return values
  exact. Widen only private visibility. Accessors remain allocation-free borrows
  and do not themselves authorize execution or independently executable proof.

## Accepted directions, subject to implementation evidence

The single actual `AdoptedProof` move, rechecking both original sealed tickets,
outer one-shot construction/operation phases, exact previous-bound restoration,
static sealed mode adapters, one permanent 512-Patch Swift arena, unchanged
legacy 128-Patch stack state, aggregate entry ticket and pre-allocation admission
are consistent with the current source and accepted execution-stage design.

The legacy failure/work trace at lines 240-249 matches `FunctionCache::pin` and
`pin_inner`: scratch preflight precedes cancellation, initial work precedes
function lookup, nonce precedes pin/slot scans, misses change before scan,
eviction plan precharges before effects, build failure may retain committed
evictions, and no fallible operation follows legacy publication. Preserve the
same static error snapshots and reader/local-expansion/instruction/target/
patch credit schedule during generic extraction. Do not make generic adapter
bookkeeping inflate or silently consume the legacy scratch model.

Swift declared locals remain separate from sealed parameters in both passes;
128 parameters plus 128 declared locals is the 256 boundary, while decoded
payload capacity excludes parameters. The current complete-validator boundary
fixture confirms function-inclusive depth 512 accepts 511 nested blocks and
rejects 512 nested blocks. The permanent 512-element arena must be reset with
explicit work checks per slot in both passes and charged once as Cache.

## Reproduced bounded checks and limitations

The artifact checker reports 18 pending engine functions and does not claim
implementation acceptance. Its two artifact tests and eight negative mutations
pass. Existing legacy cache tests (3) and the existing complete-validator
parameter/local/control boundary test (1) pass in Debug and Release: 8 existing
engine-test executions total. The reviewed source hashes did not change while
these commands ran; full outputs and tool versions are retained in `receipt.json`.

These checks do not implement or verify R1-R3, cache transient counts, allocator
fault ordinals, the new generic extraction or a Swift cache. The future 18-test
cache suite, full regression commands, independent implementation acceptance,
bounded runner, exact 53,777,114-byte target execution, physical devices,
published consumer, performance and GA gates remain pending. No target
instantiation, device discovery/run, publication, commit or push occurred.
