# MixerVM execution profiles

This is independently authored Rust engine code based on the official [WebAssembly binary specification](https://webassembly.github.io/spec/core/binary/index.html), [validation rules](https://webassembly.github.io/spec/core/valid/instructions.html), and [execution semantics](https://webassembly.github.io/spec/core/exec/instructions.html). There are no external Rust crates, copied engine code, imported fixtures, or third-party production engines. Node's built-in WebAssembly API is used only in explicitly invoked development differential tests.

The default integer-v1 profile executes bounded i32/i64 model logic. Explicit numeric-v2 and table-memory-v3 profiles add floating-point operations and selected table/bulk-memory operations. **They do not execute the full Swift Wasm runtime and are not GA-qualified interpreters.** The binding product plan's W08 and D3 gates remain open. The frozen default executable contract is [vm-profile-v1.json](../contracts/vm-profile-v1.json).

## Build and execute

```sh
PATH=/opt/homebrew/opt/rustup/bin:$PATH cargo build --release --manifest-path vm/Cargo.toml
vm/target/release/mixer-vm validate feature.wasm
vm/target/release/mixer-vm inventory feature.wasm
vm/target/release/mixer-vm invoke feature.wasm exportedFunction i32:42 i64:-1
vm/target/release/mixer-vm invoke feature.wasm exportedFunction --fuel 1000 --memory-pages 4 --call-depth 8 --stack 128 --host-calls 10
```

Commands emit exactly one JSON object to stdout. Exit 0 means the requested operation succeeded within the executable profile; exit 2 means rejection, trap, invalid arguments, or I/O failure. `inventory` still emits useful data on exit 2. All errors contain a stable `code`, message, nullable function index, and absolute module byte offset (0 when unavailable). i64 result values use decimal JSON strings to avoid JavaScript precision loss; i32 values are JSON numbers. Success from `validate` means structural/type validation within this profile; active data and v3 element bounds are checked when instantiating. Validation is not authorization for an OTA release.

`validate`/`invoke` enforce a 4MiB source ceiling. `inventory` is a separate non-authorizing bounded inspector accepting up to 128MiB and 16 million instruction occurrences. It recognizes additional immediate encodings, including floats, indirect calls, and selected reference/bulk-memory instructions, to inventory a real Swift artifact without executing it. `valid` always comes from strict executable-profile validation. `inventory_complete` describes whether the inspector reached the end of all function bodies with known immediate shapes. `inventory_error` records a partial inspection; `error` records executable-profile rejection. Inventory completion does not assert module validity or semantic conformance. Opcode counts cover function-body instructions; constant expressions in globals/data are not counted. Prefix instructions appear in `opcodes`, with their subopcodes in `extended_opcodes`. Unknown immediate shapes stop inspection rather than interpreting immediate bytes as opcodes.

## Executable semantics and resource controls

This section describes the default integer-v1 profile.

Decode and type validation finish before instantiation/execution. Structured control is predecoded with matching ends/else targets. The runtime maintains explicit call frames, so guest recursion does not recurse on the Rust call stack. Supported features include direct calls, locals, mutable/immutable integer globals, single-result block/if/function types, loops, `br`, `br_if`, `br_table`, return, drop/select, integer comparisons/arithmetic/bitwise operations/conversions/sign extensions, one bounded linear memory, narrow/unaligned integer loads/stores, memory size/grow, and active constant-offset data segments.

Integer addition/subtraction/multiplication wrap to the operand width. Division by zero and signed minimum/-1 division produce distinct traps; minimum%-1 returns zero. Effective addresses add the unsigned i32 address and memory immediate without wrapping at 32 bits. Failed memory growth returns -1 without changing memory. Branches preserve the label result and discard intermediate stack values.

Each dispatched instruction consumes one fuel unit, including control delimiters. Branches that bypass instructions do not consume fuel for those instructions. Fuel and host-call counts reset per public invocation. Cancellation is checked before every instruction and import; `Instance::cancellation()` exposes a thread-safe cooperative flag. Cancellation remains set for that instance. Static limits bound module bytes, type/function/local/instruction counts, operand stack, and structured nesting. Runtime limits bound call depth, memory pages, host calls, and fuel. Limits may only narrow published ceilings. Re-instantiating an already validated module with narrower limits revalidates it. `memory.grow` cannot exceed the declared and instance maxima. The instance's memory and globals persist across Rust invocations; the original C invocation entry points instantiate fresh state. The additive persistent-session C API retains it across calls.

The only accepted imports are `mixer.checkpoint: () -> ()` and `mixer.abort: (i32) -> ()`. Checkpoint is a metered, non-blocking cancellation point; abort returns a structured `host_abort` trap. There are no arbitrary host callbacks, filesystem, sockets, process APIs, clocks, randomness, or WASI adapters. These two imports do not implement the full product capability bridge. Future blocking host functions require their own deadlines/cancellation and capability checks.

## C boundary

`include/mixer_vm.h` declares ABI v1 and status/value layouts. The library builds as rlib/staticlib/cdylib. `mixer_vm_validate` validates; `mixer_vm_invoke` validates, instantiates, and invokes a named export. A fixed report carries the result, fuel/host-call counts, code, function index, and byte offset. Every exported operation contains Rust panics with `catch_unwind`; release uses unwind internally so containment remains effective. The caller must supply valid buffers; Rust cannot validate arbitrary dangling pointers from foreign code. Unsafe code is confined to documented pointer/slice/struct transfers and the numeric-v2 platform control-state inspection described below. Inputs are borrowed for the duration of a call, and no pointer is retained. Null/length, struct ABI/version, size ceilings, value type/range, and reserved fields are checked before dispatch. C/Swift exceptions must not cross a future host callback boundary.

## Verification and open gates

```sh
PATH=/opt/homebrew/opt/rustup/bin:$PATH cargo test --manifest-path vm/Cargo.toml
PATH=/opt/homebrew/opt/rustup/bin:$PATH cargo test --manifest-path vm/Cargo.toml --test differential -- --ignored --nocapture
PATH=/opt/homebrew/opt/rustup/bin:$PATH cargo clippy --manifest-path vm/Cargo.toml --all-targets -- -D warnings
PATH=/opt/homebrew/opt/rustup/bin:$PATH cargo build --release --manifest-path vm/Cargo.toml
clang -std=c11 -Wall -Wextra -Werror -I vm/include vm/tests/ffi_smoke.c vm/target/release/libmixer_vm.a -o vm/target/ffi-smoke
vm/target/ffi-smoke
```

All binary test fixtures are built by the owned test builder. The explicit Node differential tests exercise every supported numeric opcode over integer edge cases, structured loops, memory load/store widths, and boundary traps. Mutation smoke tests cover all truncations and single-bit mutations of small fixtures plus deterministic hostile byte streams. These smoke tests are not continuous coverage-guided fuzzing, a standards suite, or an independent security audit.

Open requirements include full pinned Swift SDK feature/import qualification; extended-profile standards/device qualification; remaining table/reference/bulk-memory forms as actually needed; exceptions as actually emitted; multi-value/block type indices; allocator/Unicode/Swift runtime and actor/executor integration; host capability codecs; original Swift source maps/stack traces/debugger; standards suites; continuous fuzzing; performance/memory pressure measurements; C ABI sanitizers/independent extended-profile review; and full physical iOS/Android embedding/QA. Unsupported executable features and imports fail before any guest execution. There is no JIT, native code generation, signing, release eligibility decision, or publication path in this crate.

The actual full Swift Foundation/Codable/Unicode probe supplied by the compiler lane is recorded separately in `swift-probe-inventory.json`; its rejection is expected. Inspection recorded 34 WASI imports, 166 primary opcodes and 6,465,732 function-body instruction occurrences, with float, indirect-call and bulk-memory requirements beyond this profile. The source artifact is 60,112,045 bytes; the 4MiB source and 200,000 instruction ceilings also require qualification/tuning against real SDK output. Its identity and command are in `verification/2026-10-22/receipt.json`. Its size/import/opcode inventory is evidence of remaining integration work, not a FieldLog benchmark or full Swift execution claim.

Reproducible local verification commands, tool versions, outputs, source SHA-256 manifest and probe identity are recorded in [the VM receipt](verification/2026-10-22/receipt.json). These are macOS host receipts, not physical device execution evidence or independent verification.

## Opt-in numeric profile v2

`mixer-integer-v1` remains the default for Rust `Limits`, CLI commands and the original C symbols. Set `Limits { profile: Profile::NumericV2, ..Limits::default() }`, pass `--profile mixer-numeric-v2` to the CLI, or call the explicitly named numeric-v2 C entry points to select the extended profile. A decoded module records its selected profile; an instance cannot silently switch it. The frozen integer-v1 contract is unchanged. The additional machine-readable contract is [profiles/numeric-v2.json](profiles/numeric-v2.json).

```sh
vm/target/release/mixer-vm --profile mixer-numeric-v2 validate numeric.wasm
vm/target/release/mixer-vm --profile mixer-numeric-v2 invoke numeric.wasm calculate f32:1.5 f64:-0
PATH=/opt/homebrew/opt/rustup/bin:$PATH cargo test --manifest-path vm/Cargo.toml --test float_differential -- --ignored --nocapture
clang -std=c11 -Wall -Wextra -Werror -I vm/include vm/tests/ffi_numeric_smoke.c vm/target/release/libmixer_vm.a -o vm/target/ffi-numeric-smoke
vm/target/ffi-numeric-smoke
```

Numeric-v2 adds f32/f64 constants, function/block/local/global types, loads/stores, comparisons, arithmetic, sqrt, ceil/floor/trunc/nearest, min/max/copysign, trapping and saturating float-to-integer conversions, integer-to-float conversion, promotion/demotion and reinterpretation. It has 176 unprefixed executable opcodes plus the eight `0xfc:0`–`0xfc:7` conversion subopcodes. Prefix conversions cost one dispatch/fuel unit. Other `0xfc` operations still reject.

Float values are held as raw IEEE bits, including through locals, globals, calls, control results and memory. Bitwise abs/neg/copysign and reinterpret preserve the specified payload bits. Arithmetic uses platform IEEE operations; NaN results follow the specification's permitted canonical/arithmetic NaN classes. Min/max explicitly choose the correct signed zero. Nearest rounds ties to even and preserves negative zero. Trapping float-to-int conversion checks the truncated mathematical range before conversion: NaN traps as `invalid_conversion_to_integer`, while infinities and out-of-range values trap as `integer_overflow`. Saturating conversion uses defined clamp behavior, with NaN becoming zero.

Before a numeric-v2 invocation, the runtime reads the calling thread's rounding mode and CPU FP controls, then runs gradual-underflow probes only after confirming hardware exceptions are masked. Non-nearest rounding, enabled hardware traps, flush modes and unknown control settings reject as `unsupported_float_environment`. Host control settings are never changed; arithmetic can set normal sticky exception flags. The platform `fegetround` call and read-only CPU control inspection are additional audited unsafe boundaries. The observed platform header defines its nearest constant as zero. The current receipt qualifies these tests only on macOS arm64, not every CPU/platform configuration.

Numeric-v2 CLI results include an authoritative hexadecimal `bits` string and a display `value` string, so NaNs/infinities/signed zero remain valid JSON without precision loss. C ABI structures remain unchanged; the new symbols accept/return value type3 with f32 bits in low32 bits of `value`, or type4 with f64 bits in all64 bits. The old symbols continue rejecting those argument types. The C smoke test checks exact signaling-NaN transfer, backward rejection, f64 return bits, and changed host-rounding, flush-to-zero and supported hardware-trap rejection/restoration.

The numeric differential oracle builds original binary fixtures from raw constants, then reinterprets float results **inside Wasm** before Node sees them. This avoids JavaScript's number conversion obscuring NaN payloads. Finite values, signed zeros and bitwise operations compare exact bits; arithmetic NaNs compare the specification's permitted quiet/canonical classes. Edge and deterministic random cases cover every added numeric opcode, conversion boundaries, saturation, memory bounds, calls and mutable globals. These tests are development evidence, not standards conformance or a security review.

The actual FieldLog model corpus supplied by the integration lane is now the prioritization source: 60,505,739 bytes, 34 WASI imports, 166 primary opcodes and 6,510,037 body instructions. Numeric-v2 covers its measured floating-point and saturating-conversion instruction families. Numeric-v2 still rejects its table/indirect and bulk-memory operations as well as the full artifact, beginning with the 4MiB source ceiling. No full Swift, FieldLog owned-VM execution or OTA coverage claim follows from an opcode inventory. Its exact artifact identity and the historical v2 rejection/inventory command are recorded in [verification/numeric-v2/receipt.json](verification/numeric-v2/receipt.json).

## Opt-in table and bulk-memory profile v3

Select `Profile::TableMemoryV3` in Rust, `--profile mixer-table-memory-v3` in the CLI, or the new `mixer_vm_validate_table_memory_v3` / `mixer_vm_invoke_table_memory_v3` C symbols. The [v3 contract](profiles/table-memory-v3.json) inherits numeric-v2 and adds `call_indirect`, `memory.copy` and `memory.fill`. The integer-v1 and numeric-v2 contracts and entry-point acceptance are frozen; both still reject these additions. The legacy C structures and ABI version stay unchanged. C v3 uses a fixed 65,536-entry ceiling; Rust callers may narrow `Limits.table_elements`. No existing source, function, global, instruction, stack, memory or fuel ceiling increases.

V3 permits one defined nullable funcref table, initially null, with active function-index element segments (binary flags 0 or 2), constant i32 offsets and table index 0. Initialization checks complete unsigned offset/length bounds, including zero-length segments, before exposing an instance. Segments apply in declaration order; later overlapping entries replace earlier entries. Function indices and the indirect expected signature validate before execution. An indirect call checks the unsigned selector, null entry and structural parameter/result signature at runtime; equivalent duplicate type declarations match. Failures report `table_out_of_bounds`, `indirect_call_null` or `indirect_call_type_mismatch` with the calling function and instruction offset. Defined and approved imported callees use the existing call frames, fuel, host-call, stack, depth and cancellation limits.

Bulk operations use only memory 0. Copy checks both complete ranges before changing bytes and implements overlapping memmove behavior. Fill uses the low eight bits of its value. Addresses and length are unsigned i32 values; zero length still requires each address to be no greater than the memory byte length. Each operation consumes its normal dispatch unit plus `ceil(length/64)` fuel, charged before mutation. Insufficient byte fuel leaves memory unchanged and traps as `fuel_exhausted`. Cancellation is checked at dispatch and immediately before mutation. A native copy/fill spans at most the existing 4MiB memory ceiling; it is not interrupted mid-operation. These controls do not provide a hard wall-clock deadline.

Imported/multiple/typed/reference-valued/table64/shared tables, passive/declarative/expression elements, table mutation instructions, guest references, data-count/passive data, memory.init/data.drop, multi-memory, memory64 and all unknown instructions/forms fail closed. The import allowlist is unchanged; no WASI or filesystem adapter was added. Table export metadata is accepted; the invocation API still requires a function export.

```sh
vm/target/release/mixer-vm --profile mixer-table-memory-v3 validate table-model.wasm
vm/target/release/mixer-vm --profile mixer-table-memory-v3 invoke table-model.wasm run i32:0
PATH=/opt/homebrew/opt/rustup/bin:$PATH cargo test --manifest-path vm/Cargo.toml --test table_memory_differential -- --ignored --nocapture
python3 vm/verify-table-memory.py
```

The owned table/bulk fixtures cover static operand types, element bounds and ordering, null/mismatched callees, equivalent signatures, integer/float argument transfer, recursion, host-call metering, memory overlap, zero/negative/oversized ranges, unchanged bytes on bounds/fuel failure, cancellation, unsupported forms, and bounded binary mutations. Development Node comparisons observe memory after traps as well as results. The C smoke test proves explicit profile selection and unchanged v1 layout sizes. These are host tests and development differential evidence, not an independent v3 review or physical device qualification.

The actual FieldLog binary has one table with min=max 46,700 and one active element segment containing 42,604 function indices starting at 4096; measured body counts include 4,237 memory.copy and 761 memory.fill operations. This motivated the bounded new table resource class. V3 covers these selected forms, but still rejects the full artifact at 4MiB. Its 79,823 defined functions, 5,271 globals and 6,510,037 instructions exceed unchanged ceilings; its 584 initial memory pages and 37,712,880 active data bytes also exceed the existing memory budget. All 34 WASI imports remain unsupported. No FieldLog/full Swift execution is claimed. [The v3 receipt](verification/table-memory-v3/receipt.json) records the artifact hash, structural measurements, complete inventory, exact commands/tool versions and source digest. Historical receipts remain tied to their original source manifests.

## Persistent native sessions

The additive `mixer_vm_session_*_v1` symbols expose retained state to native hosts.
[The session contract](../contracts/vm-session-v1.json) fixes profile IDs, handle
ownership, concurrency and failure behavior. Create validates and instantiates
before publishing a process-local generation-checked handle. Module buffers can
then be freed. Invoke retains globals/memory and resets the original narrowed
fuel/host-call budgets for each call. Read/write copy at most 1MiB with complete
unsigned bounds checks; no guest pointer escapes.

The 16-session ceiling includes reserved creations and closed instances still
held by in-flight operations. Generation overflow permanently retires a slot.
Invoke/read/write serialize with a nonblocking try-lock; overlapping operations
return `session_busy`. Cancel is permanent and cooperative. Close invalidates
immediately and keeps storage alive until admitted calls finish; it does not
wait for guest execution. Already admitted work can mutate before observing
cancellation, so cancellation does not roll back state. Every interpreter error,
including unknown exports or signature mismatch, makes the session terminal.
Malformed API buffers and transfer-bound errors leave it usable. Contained panics
poison the instance and prevent reuse. Hosts must close handles explicitly.

No old struct, instruction profile, quota, symbol behavior or import allowlist
changes. This interface does not yet connect the typed capabilities, Swift async
runtime, updater lifecycle or published mobile SDK. Full Swift execution and W08
remain open. Host session tests cover retention, transfer bounds, stale handles,
capacity, generation retirement, panic cleanup, concurrency and terminal state.
