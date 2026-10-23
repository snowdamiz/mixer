# Full Swift guest: next implementable slices

Status: original bounded host diagnostics and a proposed implementation sequence.
No runtime, contract, SDK dependency, FieldLog source, gate, or admission rule was
changed. No commit or push was made. Model selected for this delegated task:
`gpt-6.1-sol`, `xhigh`. Independent verification is pending.

Reproduce from the mixer root with a fresh name:

```sh
python3 -B compiler/experiments/swift-guest-next/run.py --name FRESH_NAME
```

The retained candidate, official Swift 6.3.3 SDK/toolchain and Node platform tool
must already exist at the paths in `run.py`. The script builds one original scalar
linker probe; it creates no package graph and downloads nothing. The local probe
binary is ignored. Commands, outputs, tool identities, source digest and scope are
in [the sealed diagnostic receipt](evidence/2026-10-23-callsites/receipt.json).
The earlier `2026-10-23-observed` receipt preserves the initial trace before
bounded callsite sampling was added.

## Recommendation

Advance **one coherent statically linked Swift reactor**, backed by the existing
complete streaming validator and a bounded decoded-function cache. Give the
actual FieldLog model a callable guest interface and qualify the exact linked
artifact. Implement a closed WASI environment with separately metered clocks,
secure randomness and bounded logging. Do not begin by creating a shared Swift
runtime dynamic linker or raising table-memory-v3 ceilings.

For transfer size, prototype content-addressed reconstruction against an exact
store-bundled base module. Reconstruct and hash one complete coherent module
before validation; this preserves the current static SDK linker model and
ADR-07. It is a separate transport optimization requiring a new explicit
contract. **Root has decided that section 20.2 continues to measure the complete
compressed artifact, including required runtime code. Base/delta reuse grants
no budget/gate credit and cannot solve that acceptance requirement alone.**
Required runtime bytes remain in the reconstructed artifact and all
installed/downloaded/reconstructed sizes must be reported.

## New observations

The exact retained full-Swift candidate remains 52,008,982 raw bytes, SHA-256
`19ac88f26f0daf34b64acb3c5b895fc79b52701368fc4c532ac8ede5844fee75`.
Wrapping Node's official WASI preview1 import functions preserves the complete
original model observation object: 1,000 tasks, 5,000 completion basis points,
Codable round trip, Unicode, reorder, commit/repeated-commit rejection, 1,503
pending changes, validation and report contents. This is the existing unchanged
model corpus, not the full feature/UI/effect graph or owned VM execution.

Only nine of the module's 34 imports ran in this observation:

| Import | Calls | Observed scope |
| --- | ---: | --- |
| `random_get` | 2,510 | 40,132 requested bytes; largest request 16 bytes |
| `clock_time_get` | 12 | Realtime ID 0; requested precision 1,000 and 1,000,000,000 ns |
| `args_get` | 2 | Fixed argv0 `fieldlog-corpus` |
| `args_sizes_get` | 2 | Same fixed arguments |
| `environ_sizes_get` | 1 | Empty environment |
| `clock_res_get` | 1 | Monotonic ID 1 |
| `fd_fdstat_get` | 1 | stdout descriptor 1 |
| `fd_prestat_get` | 1 | Descriptor 3 returned BADF 8; no preopened directory |
| `fd_write` | 1 | stdout; two iovecs; 257 requested bytes |

There were **2,531 calls** in total. `execute.rs::invoke_inner` resets its
`host_calls_used` counter for each invocation, for both legacy and capability
entrypoints. It is not a session-lifetime count. The current VM rejects WASI
imports outright. If a future WASI adapter uses that same meter and the whole
unchanged `_start` harness runs as one invocation, the frozen 1,024 host-call
ceiling would reject that invocation after other admission gaps were fixed.
This does **not** establish that normal per-event FieldLog reducer turns need
more than 1,024 calls or that the whole app is blocked by this count.

Ten sampled `random_get` stacks were attributed only after rechecking the exact
ordinal/size/file-offset relation for all 79,837 retained function bodies against
the link map. Calls 16, 512 and 1,024 include `UUID` -> `Workspace.enqueue` ->
`saveTask`; call 2,048 includes enqueue/toggleTask; call 2,509 includes
enqueue/commitDraft. The early eight-byte samples include `swift_stdlib_random`.
These are bounded samples, not all-call attribution. They explain why this
bulk corpus generates so many calls. Randomness must remain backed by the
platform CSPRNG; replacing UUID generation with predictable bytes is invalid.

The other 25 imports include every path operation, reads, polling, process exit,
descriptor mutation and `environ_get`. Their absence from this run is useful for
implementation priority, not permission to skip their validation, to grant a
filesystem, or to assume they can never execute.

The instantiated linear memory grew from 38,273,024 to 40,960,000 bytes. Of the
initial extent, 15 distinct 64 KiB pages had final byte differences. The complete
33,976,096-byte ICU extent at address 1,814,864 had **zero final byte differences**.
This observation does not see temporary writes later restored, interim growth,
peak memory, physical residency or RSS. Every byte must remain writable under
Wasm semantics. It motivates an experiment with a private writable COW initial
image; it cannot authorize read-only ICU memory or claim lower application RSS.

The exact byte partition compresses as follows with gzip9/mtime0:

| Diagnostic partition | Raw bytes | Compressed bytes |
| --- | ---: | ---: |
| Full original valid module | 52,008,982 | 18,852,048 |
| ICU packaged data span | 33,976,096 | 13,316,652 |
| All remaining bytes concatenated | 18,032,886 | 5,538,214 |

The last row is **not a valid Wasm module** and was never run. The script verifies
the known ICU hash and the earlier owned binary reader's segment/file relation,
then compresses a diagnostic partition without modifying the actual artifact.
Reusing/removing ICU alone cannot get this artifact below 3,145,728 bytes. Broad
runtime code/data reuse or a separately qualified supported SDK/library reduction
is also necessary. Simple import spelling changes are not established as safe:
the retained linker extraction graph has direct references from the actual
`Workspace.swift.o` to Foundation `CharacterSet.whitespacesAndNewlines` and
`ISO8601DateFormatter.init`. The current model needs those semantics.

## The supported linker path is a reactor, not a shared-runtime module

`ReactorProbe.swift` is an original scalar `@_cdecl` export. With the unmodified
full Swift SDK, the recorded build uses:

```text
swiftc -target wasm32-unknown-wasip1 -sdk <WASI.sdk>
  -resource-dir <swift_static>
  -Xclang-linker -resource-dir -Xclang-linker <swift_static/clang>
  -static-stdlib -parse-as-library -Osize -gnone
  -Xclang-linker -mexec-model=reactor
  -Xlinker --export=mixer_linker_probe_add -Xlinker --strip-all
  ReactorProbe.swift -o reactor.wasm
```

The actual official Clang/wasm-ld invocation selects `crt1-reactor.o`,
`--entry _initialize`, the normal static Swift archives and matching WASI
compiler-rt builtins. Node initialization followed by two calls returned 42 and
the specified wrapping result -2,147,483,648; `_start` is absent. This establishes
the linker model only. It is not a substitute FieldLog app or a Swift runtime
language test. The probe is 5,508,625 raw / 1,589,092 gzip bytes, and its 14 WASI
imports demonstrate that even a scalar Swift export is not an import-free
integer-v1 module.

The observed SDK `usr/lib` contains no `.so`, `.dylib` or `.wasm` runtime module.
The installed lld exposes `--shared`, `--experimental-pic`, imported memory/table
and dynamic export flags, but those flags do not prove the distributed Swift
archives can be turned into an independently versioned runtime module. Shared
linear-memory/table layout, relocation, static initialization, Swift metadata,
generics/witness tables, allocator ownership and symbol ABI would all need a
supported linkage contract and qualification. Independent Wasm instances cannot
exchange Swift heap pointers or function-table slots by assumption. A separately
instantiated Swift runtime would also introduce the dynamic linker explicitly
avoided by ADR-07. Do not choose it based only on an available lld flag.

One coherent reactor per target avoids that additional problem. The full Swift
runtime stays interpreted inside the same guest; no app logic moves into a native
runtime merely to improve size or timing. A store-bundled **base artifact used as
verified reconstruction input** is different from a callable shared runtime.

## Prioritized bounded implementation sequence

The coordinator has started the actual FieldLog reactor slice below. Runtime
execution remains the critical path; transport reconstruction is independent and
cannot establish either guest execution or complete-artifact budget compliance.

### 1. W07: build a real model reactor with exact semantic parity

Freeze a test-only scalar status/export interface before dependent edits. Build
the actual frozen FieldLog model source against the same full SDK, using the
reactor driver flags above. The first wrapper may put the established corpus
body inside an exported Swift function and preserve every model assertion and
observation; it must catch Swift errors at the C-compatible entry boundary.
Invoke it twice after exactly one `_initialize`, compare the complete observation
object with frozen native/command results, and identify all exports, signatures,
initialization effects, imports, resource counts and source/debug information.
Keep the original app code and corpus identity separate from the new wrapper.

This produces the **actual artifact the VM must support**, replacing speculation
that the command executable is already a feature module. It does not by itself
prove persistent feature state, UI/effects or actor behavior. Follow it with a
versioned byte/value feature boundary consuming `MixerGuest` and actual
FieldLog state transitions; never count the current native UI codec alone as a
compiled guest. No native function may compute the model observations for Wasm.

Acceptance: exact immutable source/harness/wrapper/tool/SDK/artifact hashes;
initialization once and repeated exported invocation; complete parity; current
owned rejection retained. Any thrown error, missing API, changed Unicode/date
semantics or silent native fallback blocks that slice.

### 2. W08: execute the existing supported subset through spans/cache

The current `vm/src/experimental/` already completely validates supported v1/v2/v3
modules into immutable owned source/spans. It retains the frozen ceilings and has
no execution conversion. Do not duplicate that validator or convert its result
into authority without its ownership/resource contracts.

Add a bounded decoded-function cache and execution bridge under the existing
limits first. Charge resident/pinned decoded capacity, one-entry construction
overlap, locals and variable branch payloads before allocation. Bind the cache to
the immutable span owner/profile/limits/validator-decoder version. Decode work
needs its own budget/cancellation; instruction fuel cannot meter eviction churn.
Pinned callers/callees cannot be evicted. Validate all uncalled functions before
any start/export/import. Preserve frozen profile tests and C ABI behavior.

Acceptance: parity with existing legal integer/numeric/table-memory fixtures;
eviction with recursion/indirect calls; oversized single entries; all-pinned
exhaustion; cancellation during decode; invalid uncalled functions; snapshot
ownership; reservation and cleanup after traps/close. Only then consider a new
explicit Swift profile. This step materially removes the eager ~372 MB decoded
payload arithmetic observed for the real corpus without claiming it already runs.

### 3. W08: exact WASI environment and a separately reviewed Swift profile

Implement only exact preview1 names/signatures in a nondefault profile. All nine
observed signatures return errno i32: args, environ sizes, resolution, fdstat,
prestat and randomness take `(i32,i32)`; clock time takes `(i32,i64,i32)`;
fd_write takes four i32 arguments. Validate against full decoded type signatures,
not only names/type indices. Specify the other imports too: explicit bounded
denials using official errno semantics for unsupported descriptors/capabilities,
or rejection of modules requiring an unimplemented semantic contract. Uncalled
imports are still declared imports and cannot be ignored by validation.

The minimal environment has fixed/empty bounded argv/env, no preopens, no sockets,
no subprocesses or general filesystem, stdout/stderr only as byte-bounded logs,
OS-backed secure random and explicitly granted clock behavior. BADF on preopen
enumeration is an observed required denial. `proc_exit` must become a structured
terminal guest outcome, never host process termination. Unsupported polling or
file operations must not block a host thread. No capability grant is implied by
the Node oracle.

Each adapter must check every guest pointer/output buffer/iovec with unsigned
checked arithmetic before host effects, define partial-output/error semantics,
and charge call count plus transferred bytes/work and cancellation. Secure random
errors fail explicitly; clock output is little-endian u64 ns and precision is not
permission to fabricate time. Logging has a sink/backpressure/deadline policy;
random/clock host calls need bounded native work too. Catch all foreign failures.

Design host-service injection as a typed owned runtime interface, not arbitrary
callback access to unvalidated memory. Native iOS/Android adapters use their
documented secure random/clock facilities. Tests may inject deterministic service
responses, but real corpus qualification uses the actual secure service. New
import-policy hash/schema and resource profile must be part of exact runtime
identity; no widened old fingerprint or default profile is acceptable.

### 4. Validate the exact full reactor, then execute real observations

Choose new numeric resource values only after the above artifact and accounting
exist. The current command corpus establishes these minima/gaps, not approved
ceilings:

| Resource | Current bounded profile | Observed full command |
| --- | ---: | ---: |
| Source bytes | 4,194,304 | 52,008,982 |
| Function slots | 2,048 | 79,837 defined + 34 imports |
| Instructions | 200,000 | 6,505,962 |
| Globals | 1,024 | 5,271 |
| Initial memory pages | 64 | 584 |
| Final observed memory pages | <=64 | 625, not peak |
| Host calls per invocation | 1,024 | 2,531 |
| Control nesting | 128 | Maximum raw depth 378; six bodies refuse decoding |
| Types | 512 | 493 |
| Table entries | 65,536 | 46,714 |

The body opcode families are already v3 families: integers, numeric-v2 floats and
saturating conversions, `call_indirect`, `memory.copy`, `memory.fill`. This is an
inventory statement, not complete validation. Six actual bodies exceed the
unchanged control ceiling; no new exception/reference/multi-value family is
indicated by this particular binary. The new reactor must be inventoried afresh.
Keep types/table bounds unless its evidence changes. Do not increase all limits
uniformly or infer dynamic call depth/operand stack/fuel from static counts.

First run complete streaming type validation, with an explicit experimental
source/function/global/instruction/control/memory/import descriptor and measured
metadata/scratch/work reservations. Distinguish a nesting requirement from new
opcode support. If a revised compiler control lowering is considered instead of
a new explicit depth, qualify its actual emitted alternative and semantic parity;
never remove/refuse bodies silently. The artifact has no declared max memory, so
an effective hard maximum must be supplied and enforced by the host.

Then execute the unchanged complete model through the owned interpreter, including
normal Foundation/Codable/Unicode/error behavior and actual secure randomness.
Report dynamic fuel, call depth, stack, host-call/byte counts, cache peaks and all
traps, rather than deriving them from Node. If any dimension exhausts, retain the
failed receipt and revise only that dimension through the explicit profile review.

### 5. Writable initial-memory backing and physical measurements

After correctness, derive a content-bound initial image from validated active
segments, preserving declaration order, overlap, zero fill and bounds. Raw Wasm
payload file offsets are not aligned guest memory mappings. Test a private
writable/COW image and correct growth on each platform with explicit fallback.
The final unchanged ICU bytes make this experiment promising; they are not proof
of immutability or a 30 MiB memory pass.

Account separately for module backing, image backing, clean/dirty resident pages,
mutable per-instance memory/globals/table, cache, frames, host buffers and
activation overlap. Clean file-backed pages can still count in process RSS.
Avoid retaining an anonymous 52 MB source plus 37 MB data copy plus 38 MB initial
memory. An mmap or shared base does not exempt source/data from resource budgets.
Aggregate byte reservations must cover all sessions, creation and Closing/Reclaiming
lifetimes; a count limit of sixteen is insufficient for full Swift modules.

Phones remain disconnected; no device tool was invoked. Physical iOS/Android
startup, native-versus-OTA steady/peak RSS, UI latency, async/actor/suspension,
immutable published-package consumer delivery, source debugging, recovery,
independent security review and every GA gate stay pending.

### 6. Independent W07/W10 transport experiment: coherent artifact reconstruction, before packaging claims

Using a frozen store base from the same toolchain/runtime identity, produce an
original bounded copy/literal recipe for a **complete** target reactor. The
manifest must bind app/environment/target identity, exact base SHA-256, recipe
version/hash, target SHA-256, compressed/expanded byte counts and resource limits.
Initially require the immutable base installed in that store binary, rather than
a chain of previously downloaded updates. A missing or mismatched base rejects;
it must not choose a similar SDK or fetch arbitrary substitute runtime code.

Reconstruct into private bounded staging with checked source ranges, output
limits and bounded work; verify the complete target hash; validate exactly those
immutable target bytes; then follow normal activation. There is still one module
and one Swift heap/table. Reject overlapping/overflowing invalid recipe spans,
truncation, excess output, tampered bases/targets and cross-fingerprint recipes.
Reserve staging, decompression, old/new artifacts and validation overlap before
allocation. Authenticate the recipe and final bytes; standard hashes do not make
an unauthenticated recipe trustworthy.

Measure several **real source changes** including validation logic and UI/state
changes with native/guest parity. Changes to optimization/link layout can perturb
many bytes even with identical SDK inputs, so hash-equal ICU alone cannot predict
transfer size. Report full artifact gzip, required runtime bytes, reused base
bytes, compressed recipe/literals, assets and total transfer. An unchanged-app or
optimization-only reconstruction is an engineering control, not the change corpus.

**Budget boundary:** section 20.2 says p95 <=3 MiB compressed including required
guest runtime code. The present complete module fails. Root has explicitly
retained the complete compressed artifact metric. Base reuse can reduce
transmitted bytes without deleting runtime code, but it grants no budget/gate
credit and does not solve section 20.2. A separately qualified slimmer full-Swift
SDK/library configuration is required to satisfy that size gate under the current
model. There is no evidence here that such a configuration preserves this app's
Foundation behavior.

## Primary local inputs

- Binding scope: `mixer-product-plan.md` sections 7, 10, 11, 20, 24 and 25.
- Owned current implementation: `vm/src/{decode,validate,execute}.rs`,
  `vm/src/experimental/`, `vm/experimental-stream-validation.md`, and VM profiles.
- Existing measured function/layout evidence under `compiler/experiments/profile-budget/`.
- Official installed Swift 6.3.3 SDK: `WASI.sdk/include/wasm32-wasip1/wasi/api.h`
  (errno values, clock IDs, layouts and signatures), `crt1-reactor.o`,
  `static-executable-args.lnk`, and actual official driver/linker output retained
  in this receipt. No competitor implementation, generated material, tests,
  fixtures, libraries or dependency graph was used.

Three independently authored diagnostic tests cover byte/page-range accounting,
iovec bounds and request aggregation limits. This is deliberately small host
evidence with accurate limits; it is not W07/W08 completion.
