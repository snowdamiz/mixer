# Replay the pinned WebAssembly Core assertions

Run from the Mixer checkout on arm64 macOS with Xcode command-line tools,
Python 3.11 or later, and a local Rust toolchain. Use the Rust toolchain's
`bin` directory that contains both `cargo` and `rustc`.

```sh
python3 vm/verification/standards-replay/replay.py \
  --rust-bin "$HOME/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin" \
  --receipt verification/receipts/l03-standards-replay-local.json
```

The script resolves `HEAD` to a commit once, exports its entire `vm` tree into a
private directory under the local account's home, and verifies the archived files
against the committed Git blob IDs. It builds offline against that export with a
fresh Cargo home and `/` as Cargo's working directory. It refuses Cargo config
files in those lookup locations and workspace manifests above the export. Cargo
metadata must resolve the exported package and every target, including examples,
inside the verified tree. The script stages the release archive and exported public
headers in the experimental capability install layout, then snapshots and hashes
the C client from the replay runner's directory and links it against that archive.
It downloads the pinned WABT release and sixteen WebAssembly Core WAST files
over HTTPS and checks their SHA-256 hashes. [WABT release](https://github.com/WebAssembly/wabt/releases/tag/1.0.37) ·
[WebAssembly test sources](https://github.com/WebAssembly/spec/tree/05ca4182176763112561ae20153975c12bd689e4/test/core)

The script translates each WAST file and uses the resulting Wasm bytes directly.
Stock WABT, the Rust CLI, and the installed archive's `mixer_vm_session_*_v1`
C ABI start fresh for each case in the main selector. The Mixer runners use
`mixer-table-memory-v3`. The script checks the three outcomes against the
upstream expected bits or trap. For `assert_invalid` the script checks the WABT
diagnostic and both Mixer validators' refusal codes. Mixer uses its default VM
and capability limits throughout.

The five consecutive successful assertions on lines 19–23 of
`memory_grow.wast` run in one installed C session and in WABT's
`spectest-interp`. They check growth from zero pages, a zero-initialized load,
and a load that observes the previous store. Both runners instantiate the same
module again and replay the first growth assertion, which returns the previous
page count of zero. The WAST bytes, translated module, and selected assertion
rows stay intact. The full upstream growth block hits a bounds trap on line 15. Mixer
then reports `session_terminal` on line 16.

The separate block on lines 55–62 has a declared ten-page maximum.
Both runners grow to ten pages, check the current size with zero growth,
and return `-1` for two requests that exceed the declared maximum.
A fresh instance again reports zero pages.

For `memory_copy.wast`, WABT line 258 identifies the module. Line 267 invokes
`test` with no result, and lines 269–298 assert 30 byte reads. The module copies
seven bytes from address 12 to address 10 over two overlapping ranges. The
replay uses the earlier of the two smallest translated modules with overlapping
copies over nonzero data segments. Both runners read address 12 before the
copy, during the upstream assertions, and in a fresh instance. The three reads
return `i32:7`, `i32:2`, and `i32:7`. The initial and fresh-instance reads
reuse the action from line 281 with a separate expected value. The upstream
assertion and translated Wasm bytes stay intact.

The next `memory_copy.wast` module starts on line 300 and copies seven bytes
from address 10 to address 12. Line 309 invokes `test`. The 30 assertions on
lines 311–340 check both overwritten and untouched bytes in that instance.
Both runners also read address 12 before the copy and in a fresh instance.
The reads before, after, and in the fresh instance return `i32:7`, `i32:0`,
and `i32:7`. The replay uses the original translated module and assertion rows.
[Pinned higher-address copy](https://github.com/WebAssembly/spec/blob/05ca4182176763112561ae20153975c12bd689e4/test/core/memory_copy.wast#L300-L340)

In `memory_fill.wast`, line 145 defines the module and line 162 invokes
two overlapping fills. Five upstream assertions check every byte of the page
after the two fills, including both untouched ranges and the four overwritten
bytes. Both runners check that same four-byte range before the fill and again
after creating a fresh instance. The calls stay within the default session
fuel limit. [Pinned fill sequence](https://github.com/WebAssembly/spec/blob/05ca4182176763112561ae20153975c12bd689e4/test/core/memory_fill.wast#L145-L173)

`replay.py` lists the exact case selectors by WABT JSON line. For binary
`assert_invalid` commands, WABT can report the nested module's source line.
The selection covers integer wraparound, division and rotate, initialized
memory, sign and zero extension, exact f64 bits, the `meet-bottom` trap,
and invalid branch targets, stack types and memory bounds.

Two original scalar modules cover `f32.nearest`. Lines 2499, 2500, 2505 and
2506 of `f32.wast` preserve signed zero and round ±0.5 to the corresponding
signed zero. Lines 667–669 of `float_misc.wast` round 4.5, −4.5 and −3.5
to 4.0, −4.0 and −4.0. Each runner instantiates the original module for each
assertion and compares all 32 result bits. The CLI receives decimal arguments
that preserve the selected binary32 values. The installed C ABI receives
their raw bits.
[Pinned signed-zero cases](https://github.com/WebAssembly/spec/blob/05ca4182176763112561ae20153975c12bd689e4/test/core/f32.wast#L2499-L2506) ·
[Pinned nonzero ties](https://github.com/WebAssembly/spec/blob/05ca4182176763112561ae20153975c12bd689e4/test/core/float_misc.wast#L665-L669)

Four assertions from the original 196-byte module in `f64.wast` check both
argument orders for opposite-sign zeros. Lines 1620–1621 require `f64.min` to
return `0x8000000000000000`. Lines 2020–2021 require `f64.max` to return
`0x0000000000000000`. Each runner starts a fresh instance for each assertion
and checks all 64 bits. The four assertions use 14 replay commands.
[Pinned min cases](https://github.com/WebAssembly/spec/blob/05ca4182176763112561ae20153975c12bd689e4/test/core/f64.wast#L1620-L1621) ·
[Pinned max cases](https://github.com/WebAssembly/spec/blob/05ca4182176763112561ae20153975c12bd689e4/test/core/f64.wast#L2020-L2021)

Seven assertions in `conversions.wast` check `i64.trunc_f64_s` and
`i64.trunc_f64_u`. The signed cases cover a negative subnormal, a negative
fraction, and both signed limits. The unsigned cases cover a fraction below
zero and two results with the high bit set. Each runner uses a fresh instance
and compares all 64 result bits. The seven assertions add 14 commands, for
a replay cap of 284 commands.
[Pinned truncation cases](https://github.com/WebAssembly/spec/blob/05ca4182176763112561ae20153975c12bd689e4/test/core/conversions.wast#L210-L246)

Eight assertions from the original module in `conversions.wast` check every
result bit of `f32.convert_i64_s` and `f32.convert_i64_u`. The signed cases
cover positive and negative ties around 2²⁴ and a value just above a rounding
midpoint above 2⁵³. The unsigned cases cover 2⁶³, the largest unsigned
i64 rounding to 2⁶⁴, and a value one integer above the first rounding midpoint
above 2⁶³. Each runner instantiates the original module for every assertion.
[Pinned signed conversions](https://github.com/WebAssembly/spec/blob/05ca4182176763112561ae20153975c12bd689e4/test/core/conversions.wast#L465-L474) ·
[Pinned unsigned conversions](https://github.com/WebAssembly/spec/blob/05ca4182176763112561ae20153975c12bd689e4/test/core/conversions.wast#L513-L523)

Six assertions from `i64.wast` cover `i64.clz`, `i64.ctz`, and `i64.popcnt`
on zero and inputs with the high bit set. The runner verifies the selected
assertions and original module by SHA-256. Each runner starts a fresh
instance and compares the exact `i64` result.
[Pinned bit count assertions](https://github.com/WebAssembly/spec/blob/05ca4182176763112561ae20153975c12bd689e4/test/core/i64.wast#L246-L265)

Ten assertions in the same original `i64.wast` module cover `i64.shl`,
`i64.shr_s`, and `i64.shr_u`. They compare the exact 64-bit results for
shift counts 63, 64, 65, and −1 and for a right shift of the high bit.
Counts use their low six bits. Arithmetic right shift propagates the sign
and logical right shift fills with zeros. The added assertions reuse the
pinned module and run in fresh instances. They add 20 commands, raising
the replay cap to 304.
[Pinned shift assertions](https://github.com/WebAssembly/spec/blob/05ca4182176763112561ae20153975c12bd689e4/test/core/i64.wast#L176-L213)

Eight assertions in the same original module compare zero and
`0x8000000000000000` in both operand orders and check equality at both values.
WABT manifest lines 334, 337, 342 and 343 cover `i64.lt_s` and expect
`i32` results 0, 0, 1 and 0, respectively. Lines 349, 352, 357 and 358 cover
`i64.lt_u` and expect 0, 0, 0 and 1. Each assertion runs in a fresh instance
of the pinned module. The assertions add 16 commands, raising the replay
cap to 320.
[Pinned comparison assertions](https://github.com/WebAssembly/spec/blob/05ca4182176763112561ae20153975c12bd689e4/test/core/i64.wast#L334-L358)

Six assertions in the same pinned `i64.wast` module check `i64.div_u` on
lines 91, 93, and 94 and `i64.rem_u` on lines 129, 131, and 132. Each
dividend has its high bit set. The divisors are 2⁶⁴ − 1, 2³² + 1, and 1,000.
WABT, the CLI, and the installed C client check all 64 result bits in a fresh
instance per assertion. Each assertion uses separate CLI and C client
processes, adding 12 commands and raising the replay cap to 332.
[Pinned division and remainder assertions](https://github.com/WebAssembly/spec/blob/05ca4182176763112561ae20153975c12bd689e4/test/core/i64.wast#L91-L132)

For `br_table.wast`, stock WABT admits the original module at line 3 and
passes the ten `multiple-value` assertions. The Mixer V3 CLI and installed C
validator refuse that module with `unsupported` because it uses a value type
outside the profile. The runner copies the scalar function (lines 86–105)
and assertions (lines 1305–1314) verbatim from the SHA-256-checked fixture
into a separate module. Blank lines preserve the source line numbers, and
the runner checks that WABT translates the assertion rows identically in
both contexts. The standalone module exercises indices 0–3, the first
default at 4, and out-of-range selectors including `-1` and `0xffffffff`.
WABT, the CLI, and the installed V3 session C ABI execute the excerpt.
[Pinned branch-table fixture](https://github.com/WebAssembly/spec/blob/05ca4182176763112561ae20153975c12bd689e4/test/core/br_table.wast#L86-L105)

Six assertions from `elem.wast` exercise indirect calls in three modules.
Two initialized slots dispatch to different functions, a later active
segment replaces an earlier entry at the same index, and an untouched
slot in a named module traps with `indirect_call_null`. Each runner
instantiates the pinned module again before each assertion.

The original `call_indirect.wast` module at line 623 declares three tables.
Stock WABT validates it and passes the three selected `call-3` assertions.
The Mixer V3 CLI and installed C validator refuse the original module with
`limit`. V3 allows one table. The excerpt retains the original `$t3`
table, active element segments, referenced functions, and `call-3` export.
Blank lines preserve source line numbers. The runner checks that WABT
translates the assertions identically for the original module and excerpt.
Each runner instantiates the excerpt for every assertion. Line 659 calls
slot 0 and returns `i32:-1`. Line 662 calls slot 3 and traps with
`indirect_call_type_mismatch`. Line 663 uses index 4, which is the first index
outside the table, and traps with `table_out_of_bounds`.
[Pinned indirect-call fixture](https://github.com/WebAssembly/spec/blob/05ca4182176763112561ae20153975c12bd689e4/test/core/call_indirect.wast#L623-L663)

From `global.wast`, WABT runs six selected assertions in the original module.
The Mixer V3 CLI and installed C validators refuse that module with
`unsupported`. The digest-pinned excerpt preserves the source lines for the
two integer globals, their accessors, and all six assertions. The runner
checks that WABT translates the selected assertions identically. In one
installed C session, `get-x` and
`get-y` first return `i32:-12` and `i64:-15`. After `set-x` and `set-y`, they
return `i32:6` and `i64:7`. WABT and Mixer repeat the first `get-x` assertion
in a fresh instance and observe `i32:-12`.
[Pinned scalar-global sequence](https://github.com/WebAssembly/spec/blob/05ca4182176763112561ae20153975c12bd689e4/test/core/global.wast#L200-L217)

The same archive's `mixer_vm_capability_guest_ui_validate_v1` entry point checks
the independent cases, the excerpts, and the copy and fill modules.
The valid V3 modules lack the required Mixer exports or defined memory.
Guest UI V1 refuses them. Execution evidence covers the shared V3
instruction profile through the V3 session ABI.
The selected invalid `load.wast` module declares memory and reaches the Guest
UI V1 body type check. This replay covers a fixed subset on the macOS host.
Guest UI V1 application execution and W08/L03 gate
qualification are outside its evidence.

The JSON receipt records the source revision, VM tree, Cargo targets, exact
fixture and module hashes, commands, assertion outcomes, and process custody.
The runner removes scratch after terminal custody and durable receipt
publication. A destination collision or publication error exits 74 and retains
scratch, including the command logs and a fallback receipt when it can be
written. Unknown process custody exits 74 and retains scratch and its
`HOLD.json` when the filesystem accepts the write. The runner prints the
retained path in either case.

Run the inert controls without downloading fixtures or compiling the VM.

```sh
python3 vm/verification/standards-replay/test_replay.py -v
```
