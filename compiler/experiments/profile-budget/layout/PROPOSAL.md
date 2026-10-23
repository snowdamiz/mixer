# Proposed full Swift resource and representation work

Status: **proposal awaiting root contract acceptance**. This document changes no production source, profile, C structure, package budget or admission rule. It recommends a staged implementation because the [host evidence](README.md) makes a simple increase of eager-interpreter ceilings impractical. It does not claim a working full Swift VM.

## Decision proposed

Keep integer-v1, numeric-v2, table-memory-v3 and their C layouts and acceptance frozen. Develop a separately named experimental profile only after an additive resource contract is reviewed. First implement bounded validation/representation experiments that can be exercised with existing legal modules, then qualify explicit new ceilings against the immutable FieldLog module. An inventory result must never become an execution authorization token.

Use complete structural/type validation followed by an immutable module representation containing function body spans and validation metadata, with a bounded decoded-function cache. Retain writable linear memory semantics. Consider immutable data backing or a derived initial-memory image only as a separately proven storage optimization. Count required Swift/ICU bytes in package and runtime totals even if reused between releases. No application substitution, Embedded Swift switch, broad WASI host allowance, native business-logic escape hatch or JIT is proposed.

The estimated current eager representation already needs at least 341,333,936 bytes for instruction/function lengths, active-data retention and initial memory for one actual corpus module. The existing legal synthetic sixteen-session case directly reaches about 275.31 MiB requested heap. Existing limits are still useful bounded profiles; those observations do not authorize changing them.

## Numeric contract inputs and unresolved budgets

The following are measured floors or existing ceilings, not approved full Swift limits. The candidate's unbounded Wasm memory declaration must be constrained by any future host profile.

| Resource | Frozen bounded profile ceiling | Actual smallest FieldLog candidate | Next contract decision |
| --- | ---: | ---: | --- |
| Raw module bytes | 4,194,304 | 52,008,982 | Explicit source/backing and decompressed-byte ceiling; compression must not bypass it |
| Defined functions | 2,048 total imported/defined function slots | 79,837 defined, plus 34 imports | Function metadata ceiling and measured bytes per entry |
| Static body instructions | 200,000 | 6,505,962 | Validation-work ceiling independent of retained decoded cache |
| Types | 512 | 493 | Retain ceiling unless evidence requires otherwise; also bound aggregate parameter/result storage |
| Globals | Decoder ceiling 1,024 | 5,271 | Explicit new global ceiling and total retained/runtime allocation accounting |
| Table entries | 65,536, v3 only | 46,700 | Retain ceiling; immutable element metadata and per-instance table copies still count |
| Initial linear memory | 64 pages / 4,194,304 bytes | 584 pages / 38,273,024 bytes | Separate admission and maximum-growth ceiling, without assuming final corpus pages are a peak |
| Observed memory after Node model corpus | No owned full Swift observation | 625 pages / 40,960,000 bytes | Owned execution and representative workload needed before choosing maximum |
| Largest function body wire bytes | Bounded by whole-module ceiling | 61,994 | Measure decoded entry including capacities and variable payloads; wire bytes alone cannot admit cache entries |
| Calls/locals/operand/control | 64 / 4,096 / 4,096 / 128 | Not established by this experiment | Preserve existing ceilings until actual validation/runtime evidence identifies a justified requirement |
| Instruction fuel / host calls | 1,000,000 / 1,024 per invoke | Not established by this experiment | Do not increase for compile success; separately measure execution/decode/import work and cancellation |
| Persistent sessions | 16 | One model command, no feature sessions | Add aggregate byte reservations before allowing large modules through this API |

A public resource descriptor should explicitly name source/backing bytes, validator work/scratch, static metadata bytes, decoded resident bytes, decoded pinned bytes, largest cache entry, per-instance memory/table/global/frame bytes, and process aggregate reservations. Each must have a hard ceiling and overflow-safe admission calculation. Units and whether counters cover payload length or allocated capacity must be specified. Existing 32-byte public `MixerVmLimits` must not silently acquire larger semantics or a new field; introduce a versioned additive structure/API if the approved contract needs these resources. Unknown profile versions remain rejected.

Do not yet choose production numeric maxima from one model command. For a bounded host prototype, the reviewed contract may choose explicitly experimental ceilings above the measured floors, but that result cannot close the 30 MiB OTA/native steady-state or 3 MiB p95 patch gate. The next experiment must first measure maximum per-function decoded bytes and full streaming-validator metadata/scratch before proposing numeric code-cache and process aggregate ceilings. Capacity of one hot function and the largest simultaneously pinned call chain are distinct quantities.

## Validation before any execution

Validate the complete module before running a start function, export, data initialization with observable host effects, or imported function. Streaming means the validator can release scratch after each body; it must still visit every function, including unreachable/uncalled functions, every immediate and every instruction. Unknown features, imports and forms fail closed at their original function/offset. Section ordering, all cross references, type matching, control and operand stack rules, segment/memory/table bounds, and existing limits remain enforced.

Use explicit validation work accounting over bytes, instructions, control edges and variable immediates, plus bounded scratch, checked arithmetic and periodic cancellation checks. Validation should produce compact body-span/type/local/control metadata or a content-bound proof object; any metadata allocation also counts. The later decoder may reuse this information but must not assume attacker-supplied cached metadata is trusted. Long branch tables and many small functions need independent limits and adversarial coverage.

The immutable bytes used by validation must be exactly those used by later decoding, instantiation and execution. A pathname or a read-only file descriptor alone does not prove another writer cannot change the file. Own a copied immutable snapshot, or prove a platform-specific sealed snapshot lifetime. Bind cache identity to content hash, profile version, validator/decoder version and effective limits. Retain ownership through all active functions and instances. Reject tampering or hash/cache mismatches before execution. No mutable mmap or same-path replacement TOCTOU is acceptable.

## Decoded-function cache contract

Store validated function byte spans, signatures and bounded necessary local/control metadata instead of all `Instruction` vectors. Decode a function on demand only from the validated immutable snapshot. Admission must include `Instruction` vector capacity, branch-label vectors, locals, indices, cache bookkeeping and temporary decoder allocations, with reservations before allocation/growth. Actual wire length is insufficient: the host branch fixture has only 2,001 instructions but 8,192,000 branch-label bytes, and the dense fixture's vector capacity is 31 percent larger than its instruction length.

A function larger than the single-entry budget fails closed with a structured resource error. Prefer detecting this during complete validation using a safe decoded-size bound so an ordinary later call cannot reveal a preventable oversized-function failure. Exact decoder capacity policy must be deterministic or conservatively reserved. If an exact size cannot be known until decoding, decode within a reserved bounded scratch/entry arena; never decode unboundedly and reject afterwards. Report the function and wire offset.

Active functions and return targets pin the corresponding decoded entries. Do not evict active code or rely on dangling pointers into movable vectors. When all eligible cache entries are pinned and a call cannot be admitted, return a structured resource trap while preserving memory safety and terminal/session semantics. The total budget must cover pinned plus evictable code and any new-entry construction overlap; a nominal LRU capacity is not a maximum allocation guarantee. Recursive indirect calls retain the same call-depth, signature, cancellation and instruction-fuel rules as direct calls.

Charge decode work explicitly, independently of dispatched instruction fuel, or tightly bound one decode per function per invocation plus a bounded invocation work budget. Otherwise repeated cache eviction can turn a cheap call sequence into unmetered native work. Validation, instantiation, cache misses, long memory copies and native imports each need bounded work and cancellation. Cache hits must not alter guest results, trap semantics or execution instruction fuel. Resource/decode charges should be visible separately so diagnostics do not confuse a cache miss with guest instruction use.

Before choosing a cache size, record exact maximum live allocations for individual actual functions and representative active call sets in an instrumented host export. Compare compact offset/control encodings as another independently authored representation option. Do not claim an unimplemented compact layout's nominal structure size as a measured saving.

## Source, data and writable memory

The current copy model can retain caller source, a separate active-data vector and mutable linear memory simultaneously. The data probes observe these copies directly. A future validated module may store data spans into its own immutable backing to avoid a second anonymous payload allocation. Source/backing ownership still counts once per retained backing, including during verification, instantiation and activation overlap. An optimization must not rely on the current caller buffer outliving a public C call.

Every Wasm linear-memory byte remains writable. Immutable Swift/ICU source data cannot be declared permanently read-only merely because this model workload did not modify it. Active segments must be applied in module order, including overlap and zero bytes; instantiation bounds errors must be detected before any execution. Memory growth preserves old bytes, zeroes newly exposed bytes, respects the profile maximum and returns the specified failure without partial change. Host transfers and guest accesses remain bounded and serialized under the same instance ownership rules.

A file-backed initial-memory image is only a possible second-stage experiment. Raw Wasm segment file offsets and guest addresses need not share page alignment, so directly mapping payload sections at guest addresses is not generally correct. A derived image would need content-bound generation after full validation, correct segment ordering and zero fill, a private writable/COW mapping, growth behavior, immutable backing ownership, and correct snapshot/session cleanup across cancellation and failure. Physical file-backed residency and dirty-page costs must be measured; reducing Rust allocator counters alone is not evidence of lower app RSS. Platforms without an equivalent safe mechanism need an explicit fallback with the same admission budget.

The compiler attribution shows 33,976,096 bytes of packaged ICU data retained by an actual SDK reference. It does not establish which locales are individually necessary or what can safely be removed. This proposal does not remove any SDK data or defer its cost out of package totals. Debugger/source-map loss from strip-all remains unresolved.

## Session and activation aggregate accounting

Resource reservations must cover creation before a public handle exists, live instances, active operations, closed in-flight instances, payload destruction, and old/new feature activation overlap. Preserve the repaired `Closing`/`Reclaiming` lifetime: releasing a handle does not release capacity while its payload still exists. Failed instantiation and cancellation must release reservations exactly once after destruction completes. Unknown handles, generation reuse and busy/terminal behavior retain the existing contract.

A shared immutable module/cache could amortize source and decoded code among sessions, but requires an explicit strong owner, content/profile/limit cache key, bounded retention and concurrency policy. Mutable memory, globals, tables, segment/drop state and application state remain per instance unless WebAssembly semantics explicitly permit sharing. Do not multiply a shared-module estimate by sixteen or divide independent-instance RSS by sixteen and call it a production saving. Measure both admitted aggregate maximums and actual live allocations.

Publish separate per-module, per-instance and per-process/host ceilings. The count limit of sixteen alone is insufficient. Native updater staging buffers, signed payload copies, verifier/decompressor scratch, old/new feature states and UI protocol buffers are part of activation peak and need a composed reservation or a separately measured bound. This experiment does not establish that composed maximum.

## Qualification sequence and stop conditions

1. Review a versioned resource descriptor, lifecycle ownership and structured error contract before modifying production files. Preserve all frozen profile positive/negative tests.
2. Build a complete streaming validator and compact representation under existing accepted module limits first. Differential/negative tests must reject unknown instructions in uncalled functions, invalid control/type paths and malformed variable immediates before any guest/import runs. Measure scratch and retained metadata directly.
3. Add bounded decoded caching with tests for oversized single functions, capacity growth, large branch payloads, pinned chains, recursion/indirect calls, eviction, deterministic resource errors, cancellation, decode-work exhaustion and maximum allocation reservations. Test immutable snapshot tampering/replacement and stale cache identities.
4. Separately prove data-span or COW-image semantics with overlapping segments, zero fill, arbitrary writes to formerly constant bytes, growth success/failure, host transfers, concurrent close/cancel, panic containment and cleanup. Compare allocator counters and process RSS.
5. Only after new resource ceilings are reviewed, validate the immutable actual FieldLog artifact. All 34 WASI imports remain rejected until individually specified and implemented as bounded capabilities. No filesystem/preopen grant follows from Node's development oracle. Imports that can block need their own deadline/work/cancellation behavior.
6. Execute the established complete model observation through the owned runtime when its feature/import contracts are supported; compare all fields to frozen native/Node observations. Extend ordinary Swift and adversarial coverage and standards/fuzzing evidence. A model command pass still does not prove guest UI/effect/feature activation.
7. With user-available phones, measure equivalent native and activated OTA app startup, steady/peak/total RSS, input latency and lifecycle/memory pressure on the required physical devices. Count all required runtime and immutable data bytes for the real-change patch corpus. Retain the plan's budget gates if unmet.

Any budget failure, unsupported import/feature, oversized pinned entry set, mutable snapshot, unbounded allocation/work path or incomplete validation blocks the relevant profile's execution. None is a reason to silently widen an existing profile. Parent/root acceptance is required before this proposal becomes an implementation task.
