# Accepted first stage: complete owned Swift reactor validation

Root accepted this bounded implementation stage on 2026-10-23 after the proposal
in `swift-reactor-owned-profile-design.md` and independent review in
`verification/swift-profile-design-review/review.md`. Only this validation stage
is approved for implementation now. Cache, executor, WASI dispatch, native ABI,
signed runtime, published profiles and full target execution remain unchanged.
The full product plan remains binding.

## Authority and public boundary

Expose a nondefault `experimental-swift-reactor` Rust feature depending on
`experimental-stream-validation` and `experimental-swift-wasi`. It exposes a
fixed-policy complete validator, an opaque `ValidatedSwiftReactor`, narrowing
`SwiftValidationBudget`, allocation-free typed `SwiftValidationFailure`, and
copied usage/structural observations. Names may follow existing conventions.

The proof certifies complete validation under this distinct experimental policy
and exact structural ABI. It does not attest a SHA, implementation identity,
original Swift behavior, signature, package admission, readiness or execution.
No new proof can convert to legacy `ValidatedSpans`, `FunctionCache`, eager
`Module` or any executable owner. No Clone, mutable bytes, deserializer,
caller-supplied metadata or arbitrary import policy exists. Shared private
snapshot/policy parsing is allowed; public frozen Profile/Limits and existing
validation/cache/execution entry points must retain their exact policy.

The qualifying runner checks the actual immutable target size53,777,114 and
SHA25624d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994
before validation. It keeps the real input allocation alive through the copy,
records its actual length/capacity and overlap, then drops it. A borrowed slice
cannot report all external caller allocations: distinguish internal reservations,
input visible bytes and measured runner allocation. Never claim RSS from these.
Small original fixtures may use the same complete fixed structural ABI with
simple bodies. They can earn the same policy proof but cannot earn exact-target
qualification. There is no private relaxed policy that can mint a public proof.

## Fixed policy and stage budgets

Use the existing scalar, floating, table, bulk-memory instruction grammar;
unsupported instructions/forms/capabilities remain rejected. Fixed maxima are:
64MiB source;80,000 total functions;512 types;8,192 aggregate type parameters;
128 parameters per signature;256 parameters-plus-locals per defined function;
8,000,000 instructions;128 operand values per function;512 controls including
the function;8,192 globals;4,096 exports/data segments/element segments and name
bytes;65,536 table elements;768 memory pages. Distinguish every dimension rather
than repurposing legacy Limits.locals for parameters and globals.

Defaults/maxima for validation are16MiB metadata,1MiB scratch,512,000,000 lifetime
work credits and120,000ms cooperative deadline. Public stage budgets may narrow
source, metadata, scratch, work and deadline independently; zero is real and
widening/overflow rejects before allocation. Keep checked/fallible reservations,
count growth overlap and fixed state, and reject unexpected allocator capacities.
The independent category maxima imply at most81MiB internal source+metadata+
scratch reservation; report actual simultaneous totals. Do not implement the
future256MiB runtime ledger or claim it has been verified in this stage.

Check shared cancellation and the deadline before allocation/work and throughout
bounded source copies, metadata/type/name scans and body validation. Cleanup
cannot allocate, consume work or depend on cancellation. Deadline is cooperative,
not preemption of a single platform operation. Public Swift-only failure kinds
must distinguish malformed, unsupported, semantic validation, exact-ABI shape,
resource, cancellation, deadline, invalid budget and allocation failures, with
absolute source/function location and partial usage. Keep existing public legacy
error enums and route behavior unchanged. No partial proof escapes any failure.

## Structural ABI and complete validation

Require the exact34 ordered Preview1 imports and complete signatures retained in
`compiler/experiments/fieldlog-reactor/evidence/2026-10-23-qualified/descriptors.json`;
use the closed existing adapter resolver and reject duplicates, extras, omissions,
wrong namespaces or signatures. No imported memory/table/global or legacy host
checkpoint/abort route is admitted. There is no start function.

Require one memory minimum584 with no declared maximum, one fixed table
minimum/maximum46,713, and exactly three exports: memory0; `_initialize` function35
with ()->(); `mixer_fieldlog_corpus_v1` function62 with ()->i32. Inspect/preserve
optional-maximum flags before normalization; declared max768 cannot masquerade as
absent. A distinct policy identity must never be represented as published v3.

Validate every body, including uncalled/unreachable instructions, through the
owned operand-type/control validator before sealing. Enforce all section/index,
UTF8/name, signature, local/global, initializer, branch/call/indirect, memory/table
and numeric rules. Add Swift-only active segment destination+count checks against
initial memory/table using checked unsigned arithmetic before sealing; preserve
legacy validation-versus-instantiation behavior. Ordered segment observations
remain immutable. The six previously rejected deep bodies must actually pass
the full type validator; raw diagnostics cannot substitute.

## Ownership and evidence

The implementation lane may change only coordinated validator internals:
`vm/src/experimental/{mod,account,metadata,reader,validate,descriptors}.rs`, new
private policy/snapshot helpers below that directory, new
`vm/src/experimental_swift_reactor/**`, `vm/tests/swift_reactor_validation*.rs`
and `verification/swift-reactor-validation/**`. Root owns Cargo/lib wiring,
this contract, status/gates and integration. Do not edit cache/execution, existing
WASI files, allocator-observer tests or other active lanes. Request coordination
if a necessary common seam cannot preserve these boundaries.

Required evidence: complete exact-target validation with count/work/peak/source
and deadline observations; same-policy original valid fixtures; exact/negative
import/export/memory/table shapes; all-body invalid uncalled code; each static
ceiling and narrowing budget; malformed/unsupported types/forms; unsigned range
and segment-fit cases; allocation-failure ordinals; cancellation/deadline during
stages and allocation-free failure cleanup; compile-fail proof authority; default,
stream/cache/execution and all-feature Debug/Release regression plus focused lint.
Stop at a measured failing ceiling and report it for specific root review; do
not silently raise it or start target execution. Pin source/tool/output/artifact
hashes. Phones remain disconnected and must not be queried.
