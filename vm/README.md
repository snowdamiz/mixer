# MixerVM execution profiles

This is independently authored Rust engine code based on the official [WebAssembly binary specification](https://webassembly.github.io/spec/core/binary/index.html), [validation rules](https://webassembly.github.io/spec/core/valid/instructions.html), and [execution semantics](https://webassembly.github.io/spec/core/exec/instructions.html). There are no external Rust crates, copied engine code, imported fixtures, or third-party production engines. Node's built-in WebAssembly API is used only in explicitly invoked development differential tests.

The default integer-v1 profile executes bounded i32/i64 model logic. An explicitly selected numeric-v2 extension adds floating-point operations as described below. **It does not execute the full Swift Wasm runtime and is not a GA-qualified interpreter.** The binding product plan's W08 and D3 gates remain open. The machine-readable executable contract is [vm-profile-v1.json](../contracts/vm-profile-v1.json).

## Build and execute

```sh
PATH=/opt/homebrew/opt/rustup/bin:$PATH cargo build --release --manifest-path vm/Cargo.toml
vm/target/release/mixer-vm validate feature.wasm
vm/target/release/mixer-vm inventory feature.wasm
vm/target/release/mixer-vm invoke feature.wasm exportedFunction i32:42 i64:-1
vm/target/release/mixer-vm invoke feature.wasm exportedFunction --fuel 1000 --memory-pages 4 --call-depth 8 --stack 128 --host-calls 10
```

Commands emit exactly one JSON object to stdout. Exit 0 means the requested operation succeeded within the executable profile; exit 2 means rejection, trap, invalid arguments, or I/O failure. `inventory` still emits useful data on exit 2. All errors contain a stable `code`, message, nullable function index, and absolute module byte offset (0 when unavailable). i64 result values use decimal JSON strings to avoid JavaScript precision loss; i32 values are JSON numbers. Success from `validate` means structural/type validation within this profile; active data bounds are checked when instantiating. Validation is not authorization for an OTA release.

`validate`/`invoke` enforce a 4MiB source ceiling. `inventory` is a separate non-authorizing bounded inspector accepting up to 128MiB and 16 million instruction occurrences. It recognizes additional immediate encodings, including floats, indirect calls, and selected reference/bulk-memory instructions, to inventory a real Swift artifact without executing it. `valid` always comes from strict executable-profile validation. `inventory_complete` describes whether the inspector reached the end of all function bodies with known immediate shapes. `inventory_error` records a partial inspection; `error` records executable-profile rejection. Inventory completion does not assert module validity or semantic conformance. Opcode counts cover function-body instructions; constant expressions in globals/data are not counted. Prefix instructions appear in `opcodes`, with their subopcodes in `extended_opcodes`. Unknown immediate shapes stop inspection rather than interpreting immediate bytes as opcodes.

## Executable semantics and resource controls

This section describes the default integer-v1 profile.

Decode and type validation finish before instantiation/execution. Structured control is predecoded with matching ends/else targets. The runtime maintains explicit call frames, so guest recursion does not recurse on the Rust call stack. Supported features include direct calls, locals, mutable/immutable integer globals, single-result block/if/function types, loops, `br`, `br_if`, `br_table`, return, drop/select, integer comparisons/arithmetic/bitwise operations/conversions/sign extensions, one bounded linear memory, narrow/unaligned integer loads/stores, memory size/grow, and active constant-offset data segments.

Integer addition/subtraction/multiplication wrap to the operand width. Division by zero and signed minimum/-1 division produce distinct traps; minimum%-1 returns zero. Effective addresses add the unsigned i32 address and memory immediate without wrapping at 32 bits. Failed memory growth returns -1 without changing memory. Branches preserve the label result and discard intermediate stack values.

Each dispatched instruction consumes one fuel unit, including control delimiters. Branches that bypass instructions do not consume fuel for those instructions. Fuel and host-call counts reset per public invocation. Cancellation is checked before every instruction and import; `Instance::cancellation()` exposes a thread-safe cooperative flag. Cancellation remains set for that instance. Static limits bound module bytes, type/function/local/instruction counts, operand stack, and structured nesting. Runtime limits bound call depth, memory pages, host calls, and fuel. Limits may only narrow published ceilings. Re-instantiating an already validated module with narrower limits revalidates it. `memory.grow` cannot exceed the declared and instance maxima. The instance's memory and globals persist across Rust invocations; C invocations instantiate fresh state.

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

Open requirements include full pinned Swift SDK feature/import qualification; tables/indirect calls; numeric-v2 standards/device qualification; bulk memory; references/exceptions as actually emitted; multi-value/block type indices; allocator/Unicode/Swift runtime and actor/executor integration; host capability codecs; original Swift source maps/stack traces/debugger; standards suites; continuous fuzzing; performance/memory pressure measurements; C ABI sanitizers/independent review; and physical iOS/Android embedding/QA. Unsupported executable features and imports fail before any guest execution. There is no JIT, native code generation, signing, release eligibility decision, or publication path in this crate.

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

The actual FieldLog model corpus supplied by the integration lane is now the prioritization source: 60,505,739 bytes, 34 WASI imports, 166 primary opcodes and 6,510,037 body instructions. Numeric-v2 covers its measured floating-point and saturating-conversion instruction families. It still rejects the full artifact, beginning with the 4MiB source ceiling. Tables/indirect calls, `memory.copy`/`memory.fill`, bounded WASI/runtime adapters and corpus-scale resource qualification remain required. No full Swift, FieldLog owned-VM execution or OTA coverage claim follows from an opcode inventory. Its exact artifact identity and full rejection/inventory command are recorded in [verification/numeric-v2/receipt.json](verification/numeric-v2/receipt.json).
