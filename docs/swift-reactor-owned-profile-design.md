# Proposed owned full-Swift reactor experiment

This is a proposal for root approval, dated 2026-10-23. It authorizes no profile
implementation, admission, reactor execution, publication, or GA credit. The
binding product scope remains `mixer-product-plan.md`. The accepted predecessor
contracts are `docs/span-execution-design.md` and
`docs/swift-wasi-adapter-design.md`; `docs/swift-guest-execution-next.md` supplies
the original full-Swift objective. The standalone span engine and WASI adapter
are now implemented, while their composition and the target's complete owned
validation/execution remain unimplemented. Phones remain disconnected.

## Target and evidence boundary

Qualify the unchanged retained artifact:

`compiler/experiments/fieldlog-reactor/local/2026-10-23-qualified/wasm/fieldlog-reactor.wasm`

It is 53,777,114 bytes, SHA-256
`24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994`.
Preserve the original Swift model, Foundation/Codable/Unicode behavior, throwing
boundary, and complete 11-field observation object. The complete existing native
and Node observations remain development reference evidence. No stub, rewritten
business model, Embedded Swift substitution, unvalidated body, or supplied JSON
inventory can replace owned execution of these bytes.

The final bound diagnostic is
`verification/swift-reactor-function-diagnostics/2026-10-23-reactor-final-v2/receipt.json`,
with its complete CSV, statistics and read-only binding audit. Its important
observations are:

| Dimension | Observed target fact | Scope |
| --- | ---: | --- |
| Defined / total functions | 79,832 / 79,866 | 34 imports included only in total |
| Types / concatenated type parameters | 493 / 4,105 | Maximum parameters per signature 69 |
| Globals / exports | 5,273 / 3 | Exports are memory, `_initialize`, corpus |
| Data / element segments | 20 / 1 | Active ordered segments |
| Instructions | 6,505,659 | Raw grammar inventory of every body |
| Maximum nested blocks | 378 | Function-inclusive control floor 379 |
| Maximum abstract operand height | 67 | Scalar-arity/control inventory; no operand type comparison |
| Maximum parameters plus locals | 181 | Static diagnostic, not aggregate live frames |
| Memory minimum | 584 pages / 38,273,024 bytes | No declared maximum |
| Table minimum / maximum | 46,713 / 46,713 | Absolute function indices |
| Successfully decoded legacy bodies | 79,826 | Six reject the unchanged 128-control ceiling |

The six rejected absolute functions are 24,208, 24,280, 33,106, 33,107, 53,196 and
68,133. Their raw nested depths are 353, 378, 182, 343, 205 and 155. The older
command artifact's evidence must not stand in for this reactor. The diagnostic
still records `valid=false`, `authorization=false`: neither raw scalar arity nor
successful per-body legacy decoding is complete module type validation. The
largest measured eager legacy payload is 1,310,728 bytes; the rejected-body
1,327,752-byte conditional payload estimate is a different diagnostic quantity.
Neither gives the future span decoder's exact entry size or aggregate cache peak.

Node's reference phases used 7, 2,522 and 2,513 WASI calls; secure random demand
was 20, 40,112 and 40,112 bytes. The two corpus writes were each 257 bytes.
Memory ended at 625 then 626 pages. These are reference observations, not owned
VM budgets or dynamic owned execution measurements. The bounded sink's fdstat
differs intentionally from Node's pipe, so identical host-call counts must not be
assumed before running the owned composition.

## Separate native selection and sealed ownership

Add one nondefault Rust-only feature `experimental-swift-reactor`, depending on
`experimental-span-execution` and `experimental-swift-wasi`. Keep every existing
`Profile` variant/name, `Limits` default/check, public validation/cache/execution
constructor, serialized fingerprint, native ABI, capability route and published
identity unchanged. A Cargo feature exposes the experimental API; it does not
select an import policy for an existing validator or authorize a package.

Introduce a crate-private `ResolvedSpanPolicy` covering grammar, all metadata
counts, source/spans, per-function and aggregate stacks, memory/table, imports,
validation, decode/cache, execution, and identity. Every old entry point resolves
to its exact frozen policy, including old hardcoded limits. The new entry point
selects a distinct internal `SwiftReactorExperimentV1` identity. It uses the
already supported scalar/table/bulk-memory grammar without claiming to be the
published `TableMemoryV3` profile. No caller can construct or deserialize this
policy, provide arbitrary ceilings, mutate its identity or supply an import
resolver/callback. Native budget arguments may only narrow its fixed maxima.

Refactor a private sealed snapshot payload shared by the implementation. Retain
the public legacy `ValidatedSpans` wrapper for frozen snapshots, and add an opaque
`ValidatedSwiftReactor` wrapper for the new policy. It has no public `Profile` or
widened `Limits` accessor, conversion to legacy `ValidatedSpans`, Clone, mutable
source, caller-supplied spans, or deserializer. Source ownership, complete
metadata, resolved imports, successful all-body proof, validator revision and
policy identity remain inseparable. Existing legacy `.profile()` and cache
`CacheIdentity.profile` must never report a Swift snapshot as v3.

The private cache engine can consume the shared payload; legacy `FunctionCache`
continues accepting only legacy `ValidatedSpans`. A Swift-only opaque cache owner
is constructed only inside the new reactor module after successful validation.
Factor the existing span execution machinery behind a private owned core rather
than exposing cache, pins, mutable memory or alternate imports publicly. The new
`SwiftReactorInstance` owns that core and exactly one `WasiContext`. The legacy
`SpanInstance::new(FunctionCache, ...)` remains structurally restricted to legacy
imports. No second eager `Module`, whole-code decode or second retained source
is permitted. All frames keep one opaque pin and copy scalar instructions before
cache mutation, as in the accepted span contract.

The qualifying native runner must hash the actual immutable input bytes with a
standard cryptographic implementation and require the target size/SHA-256 before
calling the new validator. It drops the caller input only after the owned proof
exists, and records both allocations' overlap. This is qualification artifact
binding, not a security claim that a hash authorizes execution: every body is
still validated and only the resulting opaque owner reaches execution. The
experimental validator may validate other bytes under the same fixed policy for
original negative/resource fixtures; those fixtures cannot acquire exact-reactor
qualification. A future production source allowlist/signature authority is a
separate reviewed boundary, not inferred from this experimental runner.

## Explicit proposed resource envelope

These are proposed experimental maxima, not measured requirements or approved
product budgets. There is no uniform widening of old public limits. Keep the
independent limits independent and retain the first exhaustion before reviewing
only its failing dimension.

| Resource | Proposed maximum | Reason and required measurement |
| --- | ---: | --- |
| Owned source | 64 MiB | Contains exact 53,777,114-byte reactor; checked span end uses resolved source extent |
| Total functions / types | 80,000 / 512 | Contains 79,866 / 493; all bodies still mandatory |
| Globals / exports | 8,192 / 4,096 | Replaces Swift-only 1,024-global blocker; exact target exports checked separately |
| Data / element segments | 4,096 / 4,096 | Preserve old count bounds; exact target has 20 / 1 |
| Aggregate type parameters / parameters per signature | 8,192 / 128 | Contains 4,105 / 69 with explicit aggregate accounting |
| Parameters plus locals per function | 256 | Contains diagnostic 181; type validator confirms |
| Total instructions | 8,000,000 | Contains inventory 6,505,659; count checked during complete validation |
| Operand slots per function | 128 | Diagnostic height 67 is only a sizing input; actual type validation remains required |
| Control depth including function | 512 | Contains static floor 379; decoder and validator use the same resolved interpretation |
| Table elements | 65,536 | Existing bound already contains 46,713 |
| Memory host maximum | 768 pages / 48 MiB | Above reference 626; reference does not prove sustained sufficiency |
| Validation metadata / scratch | 16 MiB / 1 MiB | Reservations, growth overlap and fixed state included; actual peaks unmeasured |
| Validation work | 512,000,000 credits | Current source-copy/top-section lower bound alone is 107,554,182; complete work must be measured |
| Decode cache capacity / entry | 16 MiB / 8 MiB | Preserve present byte bounds; eager diagnostic payloads are not span-entry receipts |
| Cache entries / active pins | 64 / 64 | Preserve current caps; dynamic pressure/recursion unknown |
| Cache work | 64,000,000 lifetime credits | Preserve current cumulative meaning; no per-invoke reset |
| Live defined frames | 64 | Preserve current bound until owned execution measures an actual need |
| Live values / controls across all frames | 16,384 / 4,096 | Preserve current aggregate arena bounds; not multiplied per-frame allowances |
| Mutable execution state | 128 MiB | Must cover actual old/new memory growth overlap plus all arenas/table/globals/fixed state |
| Instruction fuel / execution work | 100,000,000 / 1,000,000,000 lifetime credits | Bounded initial diagnostic attempts; actual execution demand remains unknown |
| Entered host calls | 32,768 lifetime | Required beyond frozen 1,024; also independently checked by WASI |
| WASI limits | Accepted `WasiBudget` maxima | 4 MiB cumulative transfer, 65,536-byte payloads/logs, 64 iovecs, 32,000,000 work, 30-second lifetime |
| Combined VM reservation | 256 MiB | Source + metadata + cache construction/scratch + state overlap + WASI; enforced before each allocation |
| Validation cooperative deadline | 120 seconds | Separate stage deadline; no proof on timeout |
| Cache/construction/initialize/invoke lifetime deadline | 30 seconds | Earliest outer/adapter deadline wins; cumulative across phases |

A 768-page memory growth can require almost 96 MiB of old/new memory live at once.
The state ceiling must charge that overlap before allocation and also all other
state; it cannot be described as a 48-MiB peak. The 256-MiB combined ceiling is an
additional bound, not the sum of separately observed peaks. A shared ledger
tracks each current category and their simultaneous peak. During validation the
native runner separately includes its borrowed input allocation; after sealing,
it must drop that input before cache/instance construction. A receipt must not
omit an externally retained input or present VM reservation accounting as RSS.
All this exceeds the unqualified product memory target; experimental execution
success would not resolve that gate.

Parameterize both `account::Meter::reserve(Source)` and metadata span end checks;
their existing 4-MiB constants independently block the reactor. Do not merely
bypass `Limits::check`. Parameterize the 1,024-global bound, complete validation
budget checks and all runtime/decode checks from the same resolved policy. The
existing 4,096 name/export/segment bounds remain explicit. Count aggregate type
parameters before expansion. Preserve checked u32 span/index arithmetic and
unsigned guest bounds; source sizes remain well below 4 GiB.

The cache's `[Patch; 128]` cannot accept the target. Use fallible policy-sized
reserved patch storage or an equivalent explicitly accounted bounded storage,
shared across its two passes. Charge initialization/scanning and temporary
storage overlap. Determine its actual `size_of`/capacity in the built decoder;
the legacy diagnostic's control size is not the cache decoder's layout. Frozen
routes still enforce 128 controls and their original admission. Retain exact
capacity checks, entry construction overlap, eviction/pin safety, cumulative
work and allocation-free cleanup. Cache identity carries a separate private
policy identity rather than an invented published Profile value.

## Complete admission and exact import composition

No proof exists until every section, function type, index, initializer, active
segment and every instruction in every defined body passes the owned structural
and operand type validator. Preserve section ordering, duplicate checks, start
handling, stack polymorphism, branch signatures, load/store/memory/table rules,
indirect complete-signature comparisons and numeric semantics. Unknown opcodes,
reference/SIMD/threads/GC instructions, unsupported capabilities or forms fail
closed. Raw opcode/height diagnostics cannot authorize this step. Failed or
cancelled validation drops all partial owner state with typed resource/source
diagnostics; no partial proof or fallback route escapes.

The exact target contract additionally requires no start function, one memory
with minimum 584 and no declared maximum (resolved host cap 768), and the one
46,713-entry fixed table. Require exactly the retained 34 function imports in
their retained order, with exact module/name bytes and complete signatures from
`descriptors.json`; no duplicates, omitted uninvoked imports or extra scalar
results. Resolve each to the adapter's `WasiFunction` during complete admission
and store its sealed enum by absolute import index. No imported memory/table,
global, unknown module or legacy checkpoint/abort is admitted by this policy.

Require the exact three exports: memory index 0, `_initialize` function 35 with
`() -> ()`, and `mixer_fieldlog_corpus_v1` function 62 with `() -> i32`. These exact
indices describe the pinned target, not an assumption that name matching alone
proves its implementation. Original small Swift-policy fixture tests use a
private test policy with the same closed import machinery and bounded resources;
it cannot mint an exact-target proof or enter a public frozen route.

The private execution host environment is a closed enum with legacy and
Swift-WASI arms, constructed only after matching the sealed policy identity. It
is not a trait object or public callback. At a Swift imported call, borrow the
exact argument slice from the owned value arena and the disjoint mutable memory,
dispatch the sealed enum to the owned `WasiContext`, and copy only its scalar
outcome before modifying frames/values/cache. No service receives arena pointers,
unrestricted guest memory, raw fd/path, caller environment, or a synchronous
reentry hook. Runtime checks remain defensive even after exact admission.

Native construction takes explicit `WasiGrants`, a narrowing WASI budget and the
shared cancellation token; it constructs the context internally rather than
accepting an externally configured callback environment or a context with a
different cancellation owner. Default grants remain denied. The qualifying run
explicitly grants secure random, realtime, monotonic, stdout and stderr capture.
Denied file/path/poll behavior remains exactly the accepted adapter contract.

The core charges instruction fuel once for the call instruction, then checks
its host-call limit before entering the adapter. WASI independently charges
its own call/byte/work budgets; report both counters and identify an attempted
call rejected at either boundary. Never count native byte work as instruction
fuel or refill either component between calls. The four-byte errno result is a
Wasm i32 containing the official unsigned Preview1 errno value; ordinary errno
outcomes return normally and do not terminalize the instance. `proc_exit(code)`
is an allocation-free sticky terminal guest exit, including code zero: it never
pushes a success result, resumes the caller or terminates the native process.
Adapter cancellation/deadline/budget/invariant failure terminalizes the owned
instance with the exact typed adapter failure. Release every acquired pin/frame
without further work, allocation, service or cancellation checks. Preserve prior
guest writes/capture commits from earlier calls; only the adapter's current call
is atomic. No blanket rollback of the guest program is claimed.

## Initialization and corpus invocation

Expose a narrow Rust-only constructor such as
`SwiftReactorInstance::new(ValidatedSwiftReactor, SwiftRunBudget, WasiGrants,
WasiBudget, Cancellation)`. Names are proposed; the ownership rules are binding
if accepted. The new budget type independently narrows the fixed envelope and
does not accept `Limits` as a widening mechanism. Construction includes owned
cache/state/WASI creation and `_initialize` exactly once. Its private state
machine is `Constructing -> Initializing -> Ready`, or sticky `Exited/Failed`.
No owner is returned as Ready before initialization completes with the exact
empty result and all frame/value/control/pin counts zero. Construction failures
include partial reservations/work, and release all ownership. Initialization
failure never retries or creates a fresh context to hide consumed resources.

Ready exposes only the corpus entry (for example `invoke_corpus()`), copied
usage snapshots, source/policy identity, read-only memory and borrowed stdout/
stderr captures. It exposes no arbitrary export-name/function-index invocation,
public `_initialize`, mutable memory/cache, fuel setter or budget reset. The two
required corpus calls run on this same initialized owner and retain Swift
globals/heap/table/memory and all cumulative counters. A nonzero corpus i32 is
reported as an actual guest return for the harness to reject, not rewritten to
zero or confused with `proc_exit`. Any terminal failure/exit becomes sticky and
later calls perform no guest/native work. No automatic retry/new owner is part
of qualification.

Create the outer execution deadline before cache/state construction. Construct
WASI with the accepted 30-second maximum; check the earlier outer deadline before
and after each bounded import/service and throughout dispatch/copy/decode loops.
Validation has its own bounded stage deadline and shared cancellation. Each
platform call and bounded copy/rollback remains non-preemptible; no hard realtime
claim is made. If initialization plus both invocations exhaust the fixed
deadline, cache work, fuel, pins or another dimension, retain the exact failure
and request a specific policy review. Do not silently reuse the owner's proof
in a fresh unlimited instance, extend a deadline or reset between invocations.

## Required implementation order and review seams

1. Root accepts/revises this policy identity, numeric envelope, proof ownership,
   exact-target shape and outcome/lifecycle contract before implementation.
2. In one coordinated validator/cache lane, factor private policy/snapshot
   ownership, preserving all frozen wrappers; replace hidden source/global/decode
   blockers; implement the new proof and all-body validation/resource failures.
   Re-run frozen default/stream/cache/execution behavior and allocation receipts.
3. Measure complete validation of the exact artifact with all source/metadata/
   scratch/work/deadline peaks and allocation-failure ordinals. Confirm the six
   formerly rejected bodies actually type-validate; include all 79,832 bodies.
   Do not begin target execution from a diagnostic inventory or partial proof.
4. After the shared private contracts freeze, an execution composition lane owns
   the new wrapper, closed import branch and lifecycle/error/accounting changes.
   Coordinate modifications to `experimental/execution/` with its current owner;
   coordinate any adapter visibility change with the frozen adapter owner.
5. Root runs original small fixtures, external-consumer authority/failure probes,
   exact target initialization once and the two real corpus calls, retaining
   failure receipts. Independent review precedes coherent root commits/pushes.

The minimal coordinated source touch points are Cargo/lib feature wiring;
`experimental/mod.rs`, `account.rs`, `metadata.rs`, `reader.rs`, `validate.rs` for
the shared policy and sealed payload; `cache/mod.rs`/`decode.rs` for identity and
policy-sized patch/resource checks; `descriptors.rs` for private policy/import
views; `execution/mod.rs` for a shared owned core and closed import outcomes; and
new `experimental_swift_reactor/**`, original tests and verification collectors.
The adapter's public construction, grant/errno/terminal semantics and private OS
services need no behavioral change. No C ABI, native executor, public Limits or
Profile enum, published release/cache profile ID, capability mailbox, platform
transport or production router should change for this experiment.

Required evidence includes exact and malformed signatures/import order/shape,
all-body validation including unreachable uncalled failures, every static and
dynamic ceiling at/beyond boundary, cross-policy proof/cache rejection,
unsupported grammar, source/span overflow, type/indirect mismatch, initializer
and ordered segment bounds, every constructor/decode/growth allocation ordinal,
cancel/deadline during every stage, no leaked pins on import terminal outcomes,
native grant denials and real OS services, exact-once initialization, sticky
exit/failure and persistent successful calls. Test allocation behavior and shared
aggregate peaks, including input/snapshot overlap and old/new guest growth.
Include compile-fail authority tests and default/individual/combined feature
Debug/Release matrices plus focused lint. Deterministic services remain private
unit fault probes; they cannot qualify the real target.

The qualifying target receipt must bind exact original Swift/native/reactor/tool
sources, tool versions/binaries, VM policy/validator/decoder revisions, dirty-tree
source manifest, complete command output and artifact SHA-256. Retain all 11
observation fields and compare parsed values with the existing native reference,
including both complete corpus observations. Record phase deltas and lifetime
totals for instructions/fuel/host calls, WASI transfer/random/log/work, validation
and cache work/misses/decodes/evictions, frames/values/controls/pins, memory pages,
current/simultaneous-peak reservations, and actual elapsed time. Never record
secure random output bytes. Node remains an optional independent development
oracle, not the engine or source of admission.

Successful model execution would close only this owned full-reactor boundary.
The 18,976,211-byte gzip artifact still fails 3 MiB and is not the p95 change
corpus. Product memory/time/energy/startup, sustained use, UI/effect bridge,
async/actor/suspension, debugging/source locations, immutable separately published
FieldLog packages, physical iOS/Android, signing/store/customer/operational
reviewers and all applicable GA gates remain open. No phones should be queried
or requested to reconnect for this proposal or host-only implementation slice.
