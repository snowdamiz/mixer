# Actual FieldLog per-function diagnostics

## Pinned reactor extension, 2026-10-23

The original diagnostic now has an explicit `--input reactor` mode for the exact
unchanged full-Swift reactor, while an omitted `--input` still selects the same
original command artifact, bytes, hash and linker map as before. `--artifact PATH`
only relocates the selected immutable bytes; it never changes the selected pin.
An optional `--artifact-sha256` must equal that selected built-in pin. A wrong
hash, missing/directory path, changed length/content or changed map fails before
a compiler or body diagnostic starts. Neither mode authorizes a module.

```sh
python3 -B compiler/experiments/profile-budget/functions/run.py --name FRESH_COMMAND_LABEL
python3 -B compiler/experiments/profile-budget/functions/run.py --input reactor \
  --artifact-sha256 24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994 \
  --name FRESH_REACTOR_LABEL
```

The [final reactor receipt](../../../../verification/swift-reactor-function-diagnostics/2026-10-23-reactor-final-v2/receipt.json)
and [statistics](../../../../verification/swift-reactor-function-diagnostics/2026-10-23-reactor-final-v2/statistics.json)
bind 53,777,114 bytes at that SHA-256 to reactor linker map SHA-256
`4a0b71f0b462798fef168824952d2a74d2a3956425e5380667eb9e85bde48746`.
The [command compatibility replay](evidence/2026-10-23-command-compatibility-v2/receipt.json)
uses the original default without a new input flag. Each run records current
mixer revision/dirty paths, the frozen VM revision, source/tree digests, exact
commands and outputs, tool/binary identities and source/archive preservation.
Builds use only the original no-dependency frozen diagnostic crate, offline,
with one reused diagnostic target directory. Each exact executable is copied to
its run's retained `local/functions-*/tools/` before target reuse, so its receipt
does not depend on a subsequently overwritten Cargo output. There are no guest rebuilds,
downloads, new dependencies, devices, publication or changed executable limits.

| Exact reactor static observation | Value |
| --- | ---: |
| Defined bodies inventoried / decoded under existing body ceilings | 79,832 / 79,826 |
| Raw instructions / function-body wire bytes | 6,505,659 / 15,635,455 |
| Maximum explicit control nesting / including function | 378 / 379 |
| Maximum declared locals / parameters plus locals | 176 / 181 |
| Maximum signature parameters | 69 |
| Maximum static abstract operand slots per function | 67 |
| Locals/operand inventories above existing 4,096 ceiling | 0 / 0 |
| Memory minimum pages / declared maximum | 584 / absent |
| Table minimum / maximum | 46,713 / 46,713 |

Exactly six bodies retain `limit: control nesting exceeds profile`; all unobserved
decoded shapes remain blank. Function IDs include the 34 imports:

| Function | Explicit controls | Including function | Static operand slots | Exact map attribution |
| --- | ---: | ---: | ---: | --- |
| 24,208 | 353 | 354 | 10 | Swift Demangle NodePrinter `print` |
| 24,280 | 378 | 379 | 7 | Swift Demangle Remangler `mangle` |
| 33,106 | 182 | 183 | 3 | Unicode RegexParser `Script.rawValue` |
| 33,107 | 343 | 344 | 3 | Unicode RegexParser `Block.rawValue` |
| 53,196 | 205 | 206 | 9 | Foundation Gregorian calendar `_ordinality` |
| 68,133 | 155 | 156 | 6 | Foundation ICU calendar `_locked_ordinality` |

Map attribution checks ordinal, exact body plus length-prefix size and the same
five-byte offset relation for **every** reactor body. The maximum operand height
occurs in Swift `UInt8.SIMD64Storage` helpers, even though the emitted Wasm remains
scalar instructions; names do not imply a Wasm SIMD instruction requirement.
Full symbols and archive paths are retained in function-attribution JSON. Nothing
here justifies removing any of those language/library functions.

The new third, independently authored pass inventories scalar arity, structured
control labels/results and polymorphic unreachable stack heights directly from
each original body. It includes values retained below the current control frame
and uses signature parameter/result counts for direct/indirect calls. Its fixed
1,024-control diagnostic array and scalar 1,048,576-height ceiling are inventory
limits, not executable ceilings. It neither stores operand types nor compares
their types. A deliberately wrong f64/i32 body can pass arity inventory while
the frozen type validator rejects it. Thus 67 is an exact observation of this
abstract per-body height pass, not a type-validation receipt, dynamic call depth,
whole-call-chain stack size, runtime frame allocation or admission authority.

The existing constant-space instruction/control pass and unchanged frozen
one-body decoder remain separate. The new pass works on the six rejected bodies
without decoding or admitting them. It allocates no heap on a successful body;
its fixed stack scratch is outside the existing requested-heap counters. Existing
allocation observations remain labeled as allocator requests, not RSS bounds.

Ten Python tests cover pins/default/path/content/map identity, complete selected
function/instruction/wire/source totals, missing rows, rejected-shape nullability,
raw-height integrity and exact all-body map attribution. Eleven Rust tests cover
the original decoder limits plus scalar/call/indirect/local/branch/table/loop/
return/control/unreachable height behavior, retained outer values, deep bodies,
type-versus-arity distinction and the exact 4,096/4,097 operand acceptance
boundary of the frozen validator. Receipts remain `authorization=false` and
`valid=false`; full module validation/execution, new resource values, native
services, device/RSS/performance, source debugging, immutable consumer delivery,
OTA and all GA gates stay open. Historical observations below retain their
original command-artifact identities and are not silently rewritten as reactor
results.

## Original command-artifact investigation

The pinned full Swift candidate has six functions that exceed the unchanged control-nesting ceiling. This experiment does not admit that module. It inventories every function, diagnostically decodes one body at a time under the existing body ceilings, releases that body, and measures its allocations. No complete Module decoding/type validation, instantiation, imports or execution occurs.

The final [receipt](evidence/2026-10-22-qualified/receipt.json), [statistics](evidence/2026-10-22-qualified/statistics.json), [all-function CSV](evidence/2026-10-22-qualified/functions.csv.gz) and [link-map attribution](evidence/2026-10-22-qualified/function-attribution.json) distinguish direct observations, arithmetic and conservative estimates. Frozen integer-v1/numeric-v2/table-memory-v3 acceptance and public C ABI remain unchanged. No code-cache size or larger resource profile is approved.

## Reproduction and identities

```sh
python3 -B compiler/experiments/profile-budget/functions/run.py --name UNIQUE_LABEL
```

Python 3.12+, installed Rust and Darwin `time -l` are required. The original candidate and matching official linker map must be present at the paths recorded in the prior compiler experiment; `--artifact PATH` accepts another location only for identical pinned bytes. Neither the 52 MB binary nor the 56 MB map is checked into Git. This experiment does not rebuild the candidate or imply that another build root reproduces its hash; prior same-path control and path-dependent Swift module-hash findings still apply.

| Input/tool identity | Observed value |
| --- | --- |
| Full candidate bytes | 52,008,982 |
| Candidate SHA-256 | `19ac88f26f0daf34b64acb3c5b895fc79b52701368fc4c532ac8ede5844fee75` |
| Original gzip9 bytes / SHA-256 | 18,852,048 / `a38f38bac0cccc866dbb8bbe5432c710d3c779dcab0e1afa9a74806b2f70218c` |
| Matching osize-compress map SHA-256 | `8eaa353aca7ed3549b04c1f89ba22a19f7a42a247a44ab7173b725f7e61e6cd5` |
| Frozen owned VM revision | `64123c509e861ddd522631b293eadebdaca11341` |
| VM/contracts export SHA-256 | `6547c3562bd8918650f7c3bea38817601724c53ab031261b0e48a879d7329280` |
| Measurement source manifest digest | `a46eee638d8290bd55477169e170f48ee5d94273d0b47de7f56a28f4d70c0f79` |
| Diagnostic release executable SHA-256 | `7045ca7ffc5a6fa00180d816ec950a405a010735de16119f0196ba3440cf877d` |
| Host | macOS 27.0.1 arm64, Rust/cargo 1.99.0 |
| Agent selection | `gpt-6.1-sol`, `xhigh` |

The runner makes an immutable VM export, appends only `cfg(test)` body-decoder and structure-size observers, adds the original diagnostic module, and verifies every original file against its export hash. It calls the existing private decoder with unchanged 4 MiB body-byte, 200,000 body-instruction, 4,096 local and 128 control ceilings. Each diagnostic resets the instruction total; their aggregate must never be interpreted as a module accepted under the 200,000 module instruction ceiling. The original full artifact remains larger than 4 MiB and has unsupported imports and other aggregate-limit gaps.

A separate constant-space raw instruction/immediate scanner measures all bodies without imposing executable control depth. That scanner cannot authorize code: it performs no operand/type validation, import approval, cross-reference checks or full segment semantics. Its measured depth is inventory only. Diagnostic descriptor inventory quotas (64 MiB source, 100,000 function declarations, 16,384 globals, bounded names/types/groups/sections) are separate from and do not change executable profile limits.

Nine recorded commands passed, including six independently authored Rust negative/semantic-boundary test functions and five Python evidence-integrity test functions. The Rust tests cover truncated/oversized sections, ordering/types, body counts, local sum overflow, unchanged body nesting/local ceilings, and the deliberate distinction between structural diagnosis and type validation. Python tests reject fake zero shapes, incomplete rows, inconsistent counts/spans/capacities and approximate/mismatched attribution. These tests do not replace standards, differential, fuzz or full Swift qualification.

Earlier first/structural iterations are retained under ignored `local/functions-*/superseded-evidence/`; the committed qualified run is final. All rows retain original function/offset identity. Rejected decoded shapes are null/blank, rather than invented zero values. This also clarifies the original layout experiment's opaque-session zero sentinels; no current arithmetic uses those unobserved session shape fields.

## All-body structural observations and unchanged rejections

The independent raw scanner reports exactly 6,505,962 instructions and 13,869,023 function-body wire bytes, matching the prior pinned-artifact inventory. There are 50,134 explicit branch-table target entries in 6,419 tables, and 7,184,984 immediate wire bytes (local-declaration headers excluded). All 79,837 bodies are inventoried. Of them, 79,831 diagnostically decode under the existing body limits, totaling 6,466,748 instructions; six return `limit: control nesting exceeds profile`.

Function numbers below include 34 imported functions; the CSV also records the zero-based defined-function index. Raw nesting counts explicit blocks/loops/ifs. Validation needs one additional function control frame.

| Function | Wire bytes | Raw nested blocks | Including function | Official link-map input |
| --- | ---: | ---: | ---: | --- |
| 24,206 | 41,109 | 353 | 354 | Swift Demangle `NodePrinter::print`, `libswiftCore.a(NodePrinter.cpp.o)` |
| 24,278 | 10,105 | **378** | **379** | Swift Demangle `Remangler::mangle`, `libswiftCore.a(Remangler.cpp.o)` |
| 33,104 | 4,809 | 182 | 183 | Unicode RegexParser `Script.rawValue`, `libswift_RegexParser.a` |
| 33,105 | 9,028 | 343 | 344 | Unicode RegexParser `Block.rawValue`, `libswift_RegexParser.a` |
| 53,194 | 13,871 | 205 | 206 | Gregorian calendar `ordinality`, `libFoundationEssentials.a` |
| 68,131 | 10,529 | 155 | 156 | ICU calendar `ordinality`, `libFoundationInternationalization.a` |

Current body parsing permits at most 127 nested explicit blocks, for 128 controls including the function. Nothing here changes that. The deepest successfully decoded body has 116 explicit nested blocks. A future complete profile would need a justified control-depth decision covering at least the measured 379 controls, plus full type validation and tests; 379 is a measured input floor, not an approved ceiling.

Names are attributed only after checking all 79,837 CODE input rows against actual body order, body-plus-length-LEB size, and the constant five-byte linker-map file-offset bias. The complete exact symbols/source archive paths and map hash are retained. These findings do not justify deleting Swift demangling, regex, Unicode or calendar semantics.

## Per-body decoded capacities and direct allocations

These distributions cover only the 79,831 bodies that decoded successfully. Quantiles use nearest rank. Capacity bytes include initialized and spare vector capacity. One MiB is 1,048,576 bytes.

| Quantity | Median | p95 | p99 | Maximum |
| --- | ---: | ---: | ---: | ---: |
| Instructions | 14 | 345 | 1,000 | 26,005 |
| Instruction vector bytes | 640 | 20,480 | 40,960 | 1,310,720 |
| Branch-label vector bytes | 0 | 0 | 64 | 4,304 |
| Local-type vector bytes | 0 | 11 | 28 | 256 |
| Code + branch + local payload capacity bytes | 648 | 20,496 | 41,224 | **1,310,728** |
| Direct Rust requested allocation maximum above body baseline | 760 | 21,338 | 42,882 | **1,311,256** |
| Direct additional live allocation-count maximum | 2 | 8 | 11 | 78 |

The largest 61,994-wire-byte function (global index 33,698) has 26,005 decoded instructions, two explicit nested blocks, and 1,310,728 payload bytes. The 42,436-wire-byte function at 33,696 has 17,400 instructions but the same vector capacity. They are RegexParser `classifyBlockProperty` and `classifyScriptProperty` helpers. Wire size is therefore neither instruction count nor complete decoded size.

The payload figure excludes an inline `Function`/cache-entry header, indices, inventory maps, source and decoder scratch. Adding the measured 64-byte current Function header is an arithmetic estimate of 1,310,792 bytes, not a measured future cache entry. The allocator maximum includes body-local inventory and scratch allocations, but excludes allocator internal bookkeeping and transient native realloc copies. The allocation-count and byte maxima need not occur in the same function/instant.

Across all supported bodies, the sum of individually observed instruction capacities is 371,113,280 bytes; branch capacities sum to 268,656 and locals to 352,716, totaling **371,734,652 bytes**. This is arithmetic over sequential diagnostics, not a measured simultaneous allocation. It omits all six rejected decoded bodies. Adding all function headers at length, current active-data copy and initial linear memory gives 452,830,108 bytes under the current eager/copy model, still omitting source, rejected payloads, extra function-array capacity and other metadata/runtime allocations. No full-module heap or RSS measurement is claimed.

## Conservative estimates and validator scratch

The raw scanner also supports a conditional payload-capacity upper estimate for every body, including rejections. With the current push/extend policy: code capacity is the next power of two covering `max(instructions, 4)` times 40; branch payload is bounded by `8 × total target entries + 16 × branch tables`; local capacity is bounded by `max(8, 2 × declared locals)` when nonempty. These terms bound the selected IR's vector payload capacities if the body were supported and structurally decoded. They exclude inventory, cache bookkeeping, allocator internals/transient copies, source, full validation and runtime allocations, so they are not a total heap bound or an admission decision.

The largest such estimate is **1,327,752 bytes** for rejected function 24,206. Summed over all bodies, the estimate is 374,597,758 bytes. The runner verifies every observed successful payload fits its estimate. A future cache still must reject a single entry larger than its approved budget, reserve construction overlap, retain active pinned entries safely, and meter decode work; neither these numbers nor the prior proposal approves that budget.

There are 493 function signatures with 4,105 total parameter types, 49,120 local groups, a maximum 69 parameters in one signature, and maximum 181 parameters plus declared locals in one function. No function exceeds the existing 4,096 local ceiling by this count. This is not a measurement of operand-stack height or successful type validation.

Measured private layout: validator Control 16 bytes, Validator state 72 bytes, `Option<Type>` operand 1 byte, decoder control tuple 24 bytes. Under existing accepted per-function ceilings, conditional scratch-capacity estimates are 8,192 local bytes, 4,096 operand bytes, 2,048 validator-control bytes, plus 72 inline bytes. Decoder-control capacity has a separate 3,072-byte bound. Decoder and validator phases do not necessarily overlap, and these terms exclude code, global metadata, error formatting and allocator internals. Using only the actual maximum parameter/local count gives a 362-byte local-vector capacity upper estimate, without changing any admission rule.

If a future profile could admit the observed 379 controls using the current growth policy, a 512-slot vector would use 8,192 validator-control bytes or 12,288 decoder-control bytes. This is hypothetical arithmetic, not an implemented or approved resource change. A complete streaming validator's actual scratch and all uncalled-function type/control checks still need executable measurement under the unchanged accepted profiles.

## Diagnostic metadata/source retention and process maximums

The original diagnostic span index retains **2,519,168 requested bytes**, directly observed and equal to its measured vector capacities. Its descriptors borrow immutable source spans: 24-byte function indices, 12-byte signature indices, 8-byte local groups, 12-byte global initializer/type indices, 20-byte imports, 16-byte exports and 20-byte data/element descriptors, plus flat parameter types. It captures 5,271 globals, 21 data segments, one element segment and two exports. This is an independently authored diagnostic index, not a production validated representation or proof object. It omits retained proof/control/duplicate-name/capability state a future validator may need.

| Observed Rust requested allocation phase | Bytes above pre-source baseline |
| --- | ---: |
| Source vector | 52,008,982 |
| Source plus retained diagnostic index | 54,528,150 |
| Metadata construction maximum (includes temporary function-type vector) | 54,847,498 |
| Source/index/one-body maximum across all diagnostics | **55,839,406** |
| After index and source drop | 0 |

The absolute observed maximum is 55,910,263 requested bytes, including the 70,857-byte harness/output baseline. The maximum live allocation count is directly observed as 133. Every body returns exactly to its pre-body allocation baseline before the next body is decoded. Per-body counters are reset, so post-body phase peak fields describe the last counter interval; `maximum_observed_requested_bytes` separately retains the maximum across intervals.

Darwin process peak RSS is **60,276,736 bytes**, including source/index, harness, native libraries and output processing inside the Rust test process. Python CSV/map summarization runs separately and is not included. This is neither a full VM instance, guest linear-memory allocation, total app RSS, steady-state result nor OTA/native comparison. The test-only allocator excludes native allocator metadata, transient internal realloc copies and native-library allocations; capacity can cover pages that were never resident. No mobile performance inference follows.

The pinned candidate declares 584 initial pages (38,273,024 bytes), no memory maximum, and a fixed 46,714-entry table. The pristine baseline had 46,700 entries; the prior layout proposal's smallest-candidate table floor is corrected accordingly. Full Swift/ICU behavior remains intact. The package remains 18,852,048 gzip bytes, above the plan's 3 MiB diagnostic comparison; actual representative-patch p95 remains unqualified. Unsupported WASI imports, all module-level limits, full uncalled-body validation, execution, cache/pinned-set budgets, immutable production packaging, debug/source maps, app adoption and physical memory/performance gates remain open. No phone/device operation was attempted.
