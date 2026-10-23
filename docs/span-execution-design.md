# Cache-backed owned execution boundary

Root accepted for implementation on 2026-10-23. This is an additive Rust-only
experiment for W08; full Swift execution remains the next acceptance target.
It does not change any published profile, native ABI, activation route, package
pin, release identity or gate. The complete product scope remains binding.

## Construction and ownership

The nondefault `experimental-span-execution` feature depends on
`experimental-function-cache`. `SpanInstance::new(FunctionCache,
ExecutionBudget, Cancellation)` consumes one sealed cache, including its exact
validated bytes, immutable limits/metadata and identity. No second eager
`Module`, full-code decode, source copy, bytes/hash constructor, caller-selected
imports or caller-supplied descriptor is allowed. The original streaming
validator still checks every body under its unchanged v1/v2/v3 limits and exact
`mixer.checkpoint/abort` admission. Full Swift/WASI policy is a separate additive
decision after precise diagnostics; neither feature flags nor this API widen it.

Root supplies crate-private borrowed signature/import/export/global/memory/table
descriptors in `experimental/descriptors.rs`. These are read-only views of the
same `ValidatedSpans`. Ordered data/element segment access already exists.
Execution owns new `experimental/execution/` only. No cache or validator mutation
is needed. Request coordinated changes if the implementation finds otherwise.

Each live defined frame retains exactly one opaque cache pin, including recursive
frames. Borrow the instruction and selected br_table target briefly, copy those
scalar values, end the view borrow, then mutate execution state or pin a callee.
No frame may retain a reference into the cache. All normal returns, failed frame
construction, traps, cancellation and resource failures release every acquired
pin. Cleanup cannot allocate, decode, check cancellation or spend work/fuel.
An instance does not expose its owned cache or issue pins to callers.

## Mutable state and limits

`ExecutionBudget` has public narrowing-only fields: `state_bytes` (default and
maximum 16 MiB), `live_values` (16,384), `live_controls` (4,096), and `work_credits`
(64,000,000). Existing validated limits separately bound each frame's locals,
operand stack, control depth, all live frames, memory/table size, instruction fuel
and host calls. Zero capacities are allowed when no operation requires them;
numeric widening or overflow rejects before allocation. State byte accounting
includes fixed instance state, frame storage, locals, operands, controls, table,
globals, memory, scratch and old/new overlap. Live value counts include locals
and operands together, not independent per-frame quotas. All capacities use
checked arithmetic and fallible exact reservations; reject unexpected allocator
capacity before using it. No infallible growing Vec, `args.to_vec`, `split_off`,
unmetered clone or per-instruction heap allocation is allowed.

Memory, table and globals initialize only from sealed metadata. Validate ordered
active segment bounds before copying them; preserve overlap order and zero-fill.
Initializers are the already validated scalar constant grammar. Table entries
contain absolute function indices; indirect calls compare complete structural
parameter/result signatures, not only type indices. A trap never rolls back
earlier guest writes. No host I/O other than exact legacy checkpoint/abort is
introduced in this slice.

Instruction fuel is charged before every instruction and directly exported
import. A call instruction already pays for its imported call; do not charge it
twice. Checkpoint/abort use the frozen interpreter's accounting and outcomes.
Execution
work also charges before initialization, copies, growth, operand/local/control
movement and descriptor scans. Cancellation is checked before dispatch and each
bounded bulk chunk. Charge both old/new allocation during memory growth and
zero-fill/copy work before mutating memory. Successful `memory.grow` follows
Wasm semantics; exceeding the declared/host page maximum returns -1. Budget,
allocator, cancellation and implementation-invariant failures are typed terminal
instance failures; do not disguise them as successful guest memory.grow denial.

Fuel, host-call and work budgets are lifetime cumulative, including repeated
invocations. Cache work remains its existing lifetime budget and is reported
separately. Nothing silently refills per invoke. Normal success retains guest
memory/table/globals for subsequent calls. The first failure is sticky; later
invocations return that failure without guest execution. This experimental
terminal-on-error policy is explicit even where the eager instance is reusable.

## Public Rust surface and observations

Export `SpanInstance`, `ExecutionBudget`, `ExecutionUsage`, `ExecutionFailure`
and a closed failure-kind enum from the new module. Provide `invoke(&mut self,
name: &str, args: &[Value]) -> Result<Option<Value>, ExecutionFailure>`, borrowed
read-only `memory()`, `usage()`, `cache_usage()`, and `cancellation()` (a cloned
existing cancellation token). No arbitrary host callbacks, function-index entry,
mutable memory escape, fuel setter or new FFI. Invocation validates exact export
kind and argument types before dispatch. Source function/offset are retained in
allocation-free failures, with static code, attempted/limit, execution counters
and cache failure details where applicable.

Usage reports current/peak state reservations, source/validation/cache costs
separately, cumulative instruction/host-call/work counts, current/peak frames,
live values and controls, and memory pages. Peaks are reservation accounting,
not RSS. After every terminal invocation, current frame/value/control/pin counts
must be zero; memory and instance storage remain counted until drop. Report
construction failures with the same accurate partial usage, without a live owner.

## Required executable evidence

Use independently authored project fixtures and new original probes for all
admitted v1/v2/v3 operation families: scalar integer/float and saturating numeric,
branch/if/loop/br_table, direct/recursive/indirect calls, arguments/results,
locals/globals, loads/stores, memory size/grow/copy/fill, ordered data/elements,
null/OOB/type-mismatched calls, trap/abort/checkpoint and repeated stateful calls.
Compare values, memory, traps and preserved source positions with the frozen
eager interpreter and a development Node oracle where appropriate. NaN handling
must honor the existing numeric profile; reuse owned numeric helpers only after
explicit capacity guarantees, with no unrelated helper changes.

Exercise cancellation before construction/dispatch and during long execution,
fuel/host/work limits, exact aggregate allocation limits, pin exhaustion and
decode-cache failure on a callee, all trap cleanup paths, and no pin leaks on
failed construction. Include allocator observations/fault injection where useful
to substantiate fallible bounded claims. Build default, stream/cache, execution
and combined feature configurations; test Debug/Release and run focused lint.
Record complete commands/tool versions/source digests/output/scope. No physical
phones. Full reactor execution, WASI, size, mobile, signed product integration,
immutable consumer distribution and GA requirements remain open.

Root owns Cargo/module wiring, descriptor access, numeric-helper visibility,
this contract, integration/status/gates, commits and pushes. The executor lane
owns its new module, `vm/tests/span_execution*.rs` and
`verification/span-execution/`. Other active lanes own Android design and the
exact-reactor diagnostic; never sweep their unfinished files into a commit.
