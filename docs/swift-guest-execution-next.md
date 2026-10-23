# Next owned execution boundary for the real Swift reactor

Proposal for root review, observed against mixer HEAD
`5a0367d6c56bb288ddd45dccc44ddfe20f533781` on 2026-10-23. This is not an
accepted execution contract or a gate approval. The binding scope remains
`mixer-product-plan.md` W07/W08 and sections 10, 20.2 and 24. No existing product,
VM, profile, import contract, tests, dependency graph, native archive or gate was
edited by this investigation. Phones remain disconnected.

The smallest useful implementation is a **Rust-only span/cache execution
bridge**, followed by exact full-Swift import/resource admission on that same
bridge. Another scalar/stub Swift module, converting the 53 MB reactor into the
old eager `Module`, or a larger integer ceiling without the missing architecture
does not advance the required full-Swift execution boundary.

## Exact target and newly replayed evidence

Use the retained full reactor at
`compiler/experiments/fieldlog-reactor/local/2026-10-23-qualified/wasm/fieldlog-reactor.wasm`,
SHA-256 `24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994`.
The existing immutable source/native/command/reactor receipts remain the source
of model parity. The original Swift model, Foundation/Codable/Unicode behavior,
throwing boundary and full 11-field observation object must remain intact.

The new read-only collector is
`verification/swift-guest-next-execution/collect.py`; its final receipt records
exact commands, existing executable/tool hashes, versions, current revision,
source manifest digest and complete stdout/stderr. It uses the existing owned
executable and Node 22.23.3; it does not rebuild or assert current-HEAD provenance
for that preexisting executable. A failed initial collector preflight is retained
separately; it failed on absent `rustc` in PATH before running guest diagnostics.
The corrected collector does not require a compiler because it performs no build.

The exact reactor again rejects under the owned strict byte limit. Diagnostic
table-memory-v3 inventory traverses all 6,505,659 instructions and all 34 imports,
but returns `valid=false` and retains the byte-limit rejection. Every inventoried
opcode family fits the current v3 grammar: scalar integer/float, saturating
conversions, indirect calls, active tables and memory copy/fill. This is not
complete structural/type validation or proof of acceptable control/operand depth.

Node initialized the unchanged reactor exactly once and both exported calls
returned zero with complete native-equal observations. New bounded reference
measurements are:

| Phase | WASI calls | Secure random demand | Other observed behavior |
| --- | ---: | --- | --- |
| Initialization | 7 | 3 requests / 20 bytes, maximum 8 bytes | argv size/get, empty environment size, monotonic clock resolution |
| Invocation 1 | 2,522 | 2,507 requests / 40,112 bytes, maximum 16 bytes | 12 realtime reads, `fd_prestat_get(3) -> BADF(8)`, stdout fdstat, one 257-byte write through two iovecs |
| Invocation 2 | 2,513 | 2,507 requests / 40,112 bytes, maximum 16 bytes | 5 realtime reads, one 257-byte write through two iovecs |

The oracle's stdout is a process pipe. Its fdstat file type/rights are an
environment observation, not the contract for the product's bounded log sink.
ABI padding is not a semantic field and must not be copied as a required value.
The official installed WASI preview1 header is hashed in the receipt and supplies
the exact signatures, layouts, clock IDs and errno values. No new external tool,
runtime, library, fixture or dependency was downloaded.

## Concrete source blockers beyond the public 4 MiB rejection

| Boundary | Current implementation | Required next decision |
| --- | --- | --- |
| Execution representation | `Instance` owns eager `Module`; cache cannot execute | New feature-gated instance consumes the sealed `FunctionCache` directly |
| Complete validation source | `Limits::check`, experimental `valid_limits`, and `account::Meter::reserve(Source)` each enforce frozen limits; the last hardcodes 4 MiB | Explicit new experimental policy; changing one caller is insufficient |
| Function/global/instruction counts | 2,048 functions / hardcoded 1,024 globals / 200,000 instructions | Actual target needs 79,866 total functions / 5,273 globals / 6,505,659 instructions |
| Validation work | 64,000,000 credits, independently bounded | Source copy plus charged top-level section spans alone require 107,554,182 credits; metadata/body/data/type traversal is additional |
| Control depth | Existing validator limit 128; cache decoder also has a fixed `[Patch; 128]` | Parameterize and reserve scratch consistently; exact new-reactor maximum remains unmeasured |
| Imports | Streaming metadata permits only exact `mixer.checkpoint/abort` | Native-selected exact WASI descriptor policy and typed bounded services; Cargo exposure alone grants no permission |
| Guest memory | 64 pages, no aggregate process reservation | Target starts at 584 pages; reference ends at 625 / 626 pages; declaration has no maximum, so host supplies a hard maximum |
| Recursive frames | Legacy max 64; cache max 64 active pins | Meter/reserve frames, values, labels and pins together; dynamic required call depth remains unknown |
| Cache work | 64,000,000 cumulative lifetime credits | Preserve this meaning in the first bridge; do not reset it silently each invoke. Later sustained-use policy needs explicit review |

The source+section work number is an arithmetic lower bound from the inspected
implementation, not an attempted widened validation. The existing per-function
diagnostic pins a different 52,008,982-byte command artifact and cannot simply be
run against this reactor. Its six rejected bodies and 379-control floor are
evidence for that old artifact only. Reuse/parameterize that original tool with
exact artifact identity checks before choosing the new control ceiling; do not
label the reactor's nesting measured or infer a dynamic stack/fuel maximum.

Memory extents are 38,273,024 bytes before/after initialization, 40,960,000 after
call 1, and 41,025,536 after call 2. They are guest linear-memory observations;
they do not measure allocator overlap, temporary source/data copies, peak host
allocation or physical RSS. The 30 MiB added-memory target remains unqualified.

## Proposed contract to freeze before dependent implementation

Add a nondefault `experimental-span-execution` Rust feature. It has no C ABI,
session registry, activation, release or mobile route initially. A proposed
`SpanInstance` consumes one sealed `FunctionCache`; there is no path from raw
bytes, inventory JSON, caller-supplied spans or a hash directly to execution.
Immutable validated source/metadata/cache remain one owned identity. Do not
construct a second eager `Module` or copy all code/data into decoded vectors.

Expose only the crate-private descriptors needed by this instance: signatures,
exact import name/type, exports, memory/table limits, globals and ordered active
segments. Initialization reserves all mutable state before allocating; active
segments preserve order, overlap, bounds and zero-fill. Global constant values
remain the admitted scalar initializers. The table retains absolute function
indices and indirect calls compare complete structural signatures.

Frames retain opaque cache pins. For dispatch, borrow a view briefly, copy the
`Copy` decoded instruction (and selected branch target), end that borrow, then
mutate/pin the cache for a direct or indirect callee. A frame never stores a
reference into cache payload. Every normal return and terminal error releases
all pins without allocating or requiring remaining work/cancellation budget.
No trap/cancel/failed callee construction may orphan an active pin.

Use fallible exact-capacity frame/value/label storage with byte reservations,
not the legacy infallibly growing per-frame vectors or `args.to_vec/split_off`.
Bound live frames, total locals/operands/controls and construction overlap; a
per-frame maximum multiplied by a call-count maximum must not be an unreported
allocation. Preserve cancellation/instruction fuel before dispatch and byte work
before bulk mutations. Charge memory-growth initialization/copy work and old/new
allocation overlap. Exhaustion produces a typed, terminal instance failure and
complete usage counters rather than a partial success.

The first bridge executes already admitted v1/v2/v3 modules under unchanged
limits and exact existing `checkpoint/abort` semantics. Reuse independently
authored original fixtures and compare observable values/memory/traps with the
frozen eager interpreter and development Node. This is necessary architectural
verification, while full-Swift execution remains the next explicit acceptance
target rather than being replaced by the subset milestone.

For full Swift, factor a private resolved span policy covering grammar, all
counts, source/metadata/scratch/work, memory, imports and execution limits. Keep
the existing `validate_spans(Limits, ...)` route frozen by converting it into the
same old resolved policy. Add a separate native-selected experimental policy
identity, never a widened default `Limits`, numeric alias for v3, unchecked
caller-sized ceilings, or release fingerprint. Change the cache's bounded patch
storage in coordination with that policy. Keep all uncalled bodies validated.

Initially review static lower bounds from the exact reactor, then attempt full
streaming validation and record actual metadata/scratch/work peaks before cache
construction. Choose numeric experimental ceilings explicitly; no proposed
value is approved here. Dynamic call depth, operand stack, fuel, cache pressure,
host work and wall time must be measured by owned execution. If one resource
exhausts, retain that failure and review that dimension; do not uniformly raise
every ceiling or skip a body/import.

## Exact WASI adapter boundary

Freeze one descriptor containing all 34 actual preview1 names and complete
parameter/result signatures from the retained `descriptors.json`. Instantiation
accepts only that exact native-selected policy; declared-but-uninvoked imports
still need specified denial behavior. Unknown modules/names/signatures reject
before instantiation. Admitting a known syscall with a defined denied outcome
does not grant the capability that syscall would normally require.

Typed host services supply OS secure randomness, explicitly granted realtime/
monotonic clocks and a bounded logging sink. They receive bounded owned scratch
bytes and typed requests, never unrestricted mutable guest memory, arbitrary
callbacks or host pointers. Test services may be deterministic; qualification
must use the real secure service. Native work has byte/work/deadline/cancellation
limits independent of instruction fuel, and synchronous host reentry is denied.

Implement fixed bounded argv/empty environment, no filesystem preopens, no
sockets/processes and no unrestricted filesystem. `fd_write` supports stdout/
stderr only; fdstat must truthfully describe that sink and zero ABI padding.
Preopen enumeration returns `BADF`. Unsupported file/path/poll operations have
explicit errno or terminal outcomes and never successful no-op stubs. Polling
must not block a host thread. `proc_exit` becomes a terminal guest exit outcome,
never host process termination or a returning success.

Validate the complete unsigned checked guest ranges, output pointers, iovec
table and aggregate transfer before any host effect. Freeze alias/partial-write
semantics. Logging may have externally visible partial progress: report it
accurately; do not claim rollback. Random output is copied only after bounded
secure-service success; errors fail explicitly. Clock outputs use the specified
little-endian u64 nanoseconds; unknown/denied clocks fail explicitly. Denied
operations must not create filesystem/network effects or fabricate success.

## Implementation ownership proposal

After root accepts this boundary, split only these bounded lanes:

1. Root owns Cargo/lib feature wiring, the resolved policy and private descriptor
   access contract, shared status/gates, integration, commits and pushes. Root
   freezes the constructor/import/outcome/resource types before other edits.
2. Execution lane owns new `vm/src/experimental/execution/`, new focused
   `vm/tests/span_execution*.rs` and `verification/span-execution/`. It adds the
   cache-backed dispatch/frame/initial-state machinery and subset differential,
   trap/pin-cleanup, cancellation, memory and allocation evidence. It coordinates
   any accessor/cache change rather than editing another lane's files.
3. WASI lane owns new `vm/src/experimental_wasi/`, its new tests and
   `verification/swift-wasi/`, implementing the exact frozen descriptor and
   typed services without touching executor/cache/validator files.
4. Root or a separately assigned policy lane owns experimental validator/cache
   resource changes and exact-reactor function diagnostics. It binds the new
   policy identity, complete-validation and allocation evidence before root
   attempts `_initialize` once and the two actual corpus invocations.

Full owned acceptance requires native-equal complete observations from the exact
reactor, real secure randomness, retained failures, and dynamic instruction/
host-call/host-byte/work/depth/value/cache/memory counters. State persistence,
feature UI/effects, async/actor/suspension, debugger/source locations, immutable
published FieldLog consumer packages, physical platforms and all GA gates remain
the continuing product scope after this model execution slice.

## Separate size requirement

This artifact is 53,777,114 raw / 18,976,211 gzip9 bytes. The full compressed
artifact fails 3 MiB; one sample is not the required p95 change corpus. Keeping
one full Swift runtime in the interpreter is the execution decision. Delta/base
reuse, omitted runtime bytes, native business-logic replacement, Embedded Swift
or a stub cannot supply size-gate credit under the current product requirement.
Qualifying a smaller full-Swift/SDK/library configuration while preserving the
actual app behavior remains independent work. Successful execution does not
close that failure.
