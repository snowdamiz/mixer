# Observed Clippy correction source candidate

This packet prepares source for independent review and a future bounded hosted
format/lint plus full Debug/Release regression. It installs no canonical files,
changes no workflow or allowance, and selects no dispatch. The binding product
plan, current native/UI/capture pause, disconnected-phone status, custody holds,
numeric policy, OTA authority and GA gates remain in force.

## Exact source and evidence basis

The coordinator supplied current Mixer revision
`6d57e05e58e6d614e58a0a4dc0fad661264fb46f`; no Git command was run in this lane.
All 136 canonical VM members are independently hashed against baseline closure
`af0db424af7b08f013d2c6a8894f4d156f76bc5f493620c6f2c0b85d3bf4c48b`.
The reviewed bitmap plus SL13/SL14 source closure is
`674242606ec1f81e8bf53d6d10c0ae390c94c75e78d0a5c0e695bfb36b5eec20`.
The starting point here uses the exact four standard Rust1.99 formatted files
from actual run 40814738980, yielding closure
`ffbc544201cf3d6ddf303b49f952c0e4b839bdfaf42e18588074d6c4c169b971`.

`actual-bindings.json` binds the actual baseline/candidate Clippy JSON,
comparison, complete source manifest, all four before/after formatted inputs in
both arms, format receipts/diffs, and the independently frozen actual review.
The latter's result hash is
`0e30665d7a380ba1eb757fbf152b9ceed88886c4a9f7286e334b2fa7ef1011a5`;
its seal hash is
`27a5648252f940c34d41e15934da20b1dc5dac1a32ae094cbdd8c0ec2c87a2e4`.
Bindings contain paths and hashes. Raw logs and artifacts remain local.

Actual baseline Clippy failed 101 with 50 error observations; candidate Clippy
failed 101 with 46. Their code/message/path multiset shares 45, with five
baseline-only and one candidate-only observations. The union is 51 observations
across 13 paths and 16 lint categories. Both commands stopped before successful
build completion. This is a union of observed output, not an exhaustive lint
inventory, and the difference cannot be causally attributed to the bitmap.

## Narrow corrections

| Observed category | Union observations | Source correction |
| --- | ---: | --- |
| `result_large_err` | 18 | Three test helpers write complete Results into caller-owned output slots; 15 measured closures return unit and retain their complete Results outside the measurement return value. |
| `field_reassign_with_default` | 5 | Initialize the exact overridden Program field in its original default struct. Fixture values and subsequent mutation/assertions remain. |
| `drop_non_drop` | 4 | End the same borrowed phase/ticket scope lexically. Missing completion still retains the original charge. |
| `possible_missing_else` | 4 | Insert a newline between the original independent `if` statements. No `else` is added. |
| `clone_on_copy` | 3 | Copy the already-Copy `Operation` field directly. |
| `manual_range_contains` | 3 | Use the same inclusive or half-open integer intervals. |
| `assertions_on_constants` | 3 | Preserve the exact predicates as inline-const assertions. |
| `manual_range_patterns` | 2 | Replace the exact contiguous opcode union with `0x45..=0xc4`. |
| `dropping_copy_types` | 2 | Discard the same Copy completion value with `let _ = completed`. |
| `precedence` | 1 | Parenthesize the existing division operand of XOR. |
| `int_plus_one` | 1 | Replace `allowed >= 1 + growthwork` with `allowed > growthwork` for the fixed, source-derived finite growthwork. |
| `err_expect` | 1 | Use `expect_err` in the cfg(test) malformed-scan inspection helper; success type Counts already derives Debug. |
| `chunks_exact_to_as_chunks` | 1 | Iterate the same complete 32-byte rows; the remainder remains ignored. |
| `needless_range_loop` | 1 | Enumerate the original 64-word array and compare the same words and expected values. |
| `let_and_return` | 1 | Return the existing WASI-boundary match directly. |
| `manual_dangling_ptr` | 1 | Express the original exact address 1 through the exposed-provenance API, retaining the integer-cast contract. |

There are 15 thin overlay files: the original four formatted candidate files,
the ten other files with observed diagnostics, and the one directly dependent
`value_operation_tests.rs` callsite. The coordinator explicitly authorized that
mechanical compatibility edit because it imports `construct_owned`. Its exact
canonical preimage is recorded in the manifest. Every other lint-changed path
has its own observed diagnostic.

### Results and allocation measurements

The original test helpers returned large complete errors deliberately. Boxing
would add allocations inside tests that require zero allocation or exercise a
precise failing allocation ordinal. The corrected helper signatures use
`&mut Option<Result<...>>` and return unit. No Result alias, wrapper, generic
signature disguise, lint allow/expect, dependency or heap allocation is added.
Ordinary callsites take the same Result from a stack slot and keep their
original `unwrap`, `unwrap_err`, matching and assertion behavior.

The constructor still completes the original construction/error scope before
publishing its result. If completion fails, its failure still takes precedence;
if preparation fails, the original proof is still explicitly dropped/refunded,
and a refund failure still takes precedence over the preparation failure. The
pin helper keeps the same prepare/pin/complete order. The owned instance helper
retains its complete ConstructionFailure, including any cleanup tail. Measured
closures place the full result in a caller-owned slot while allocation tracking
is active; only slot extraction occurs after the observer stops. No destructor
or cleanup operation is moved outside an existing measured region.

### Numeric and ownership boundaries

`growthwork` is `(584 + 585) * 65_536 = 76_611_584`, so `1 + growthwork` cannot
overflow either a 32-bit source multiplication or the resulting u64. At the
tested threshold, equality to growthwork is false in both predicates; exactly
one above is true in both. This replacement is not generalized to arbitrary
possibly-overflowing y+1 arithmetic. The opcode union covers every byte from
0x45 through 0xc4 exactly once as a set, with no new opcode admitted. All three
range replacements retain their exact endpoint inclusion. Parenthesizing the
division preserves Rust's existing multiplication/division-before-XOR parse.

The two borrowed cache phases and the WASI phase still leave scope without
completion in their omission tests. The intentional ReservationTicket loss
ends at the same effect boundary as its former explicit drop, preserving its
original owner/charge and all retained-charge assertions. The ticket stores
only owner/category/bytes and has no Drop implementation. Copy completion
discards have no destructor in either form.

The exact formatted `borrowed.rs` is unchanged here. In `cache.rs`, only the
observed cfg(test) inspection expression changes after the production source
prefix. Production limits, counters, credit formulas, bitmap behavior and
ownership code remain exact to the reviewed formatted bitmap candidate.
SL13/SL14 corrected method bodies remain exact. Tests, assertion counts and
error-code literal inventories are retained across every overlay.

### Pointer semantics and Rust version availability

The invalid-pointer test must keep address 1, u8 alignment, its oversized length,
the other maximum-address and misaligned-output fixtures, and every error and
storage assertion. The candidate uses
`ptr::with_exposed_provenance::<u8>(1)`. The official API documents it as fully
equivalent to `addr as *const T`; it preserves both the exact address and the
original exposed-provenance semantics. `ptr::dangling` guarantees non-null
alignment but its public contract does not guarantee that particular address.
`without_provenance` would change the original provenance contract. Neither is
used. See the [official exposed-provenance documentation](https://doc.rust-lang.org/std/ptr/fn.with_exposed_provenance.html).

`vm/Cargo.toml` declares edition 2021 and no `rust-version`. Root README says
Rust without a minimum; `vm/README.md`, the frozen default VM contract, profile
contracts and release toolchain candidate declare no lower Rust MSRV. No
declared MSRV is inferred from CI. The observed supported host compiler baseline
is 1.98.1 and the actual formatter/Clippy diagnostic used 1.99.0.
The new API high-water mark is 1.88.0 for safe
[`slice::as_chunks`](https://doc.rust-lang.org/std/primitive.slice.html#method.as_chunks);
the pointer API has been stable since 1.84.0. Inline const blocks have been
[stable since 1.79.0](https://blog.rust-lang.org/2024/06/13/Rust-1.79.0/).
These are availability checks against the observed host compilers, not a claim
that any lower Rust version is qualified.

## Guarded controls and pending execution

`test_controls.py` installs the process/session/group/signal/wait/socket deny
guard before importing the packet implementation. It checks exact full source
closures and raw-input hashes; replays every permitted source edit; verifies
test, assertion and diagnostic-literal inventories; checks opcode and arithmetic
boundaries, complete row/word observations, result precedence/identity and
absence of added boxing/suppression. It reproduces both exact diffs.
`canonical-to-candidate.diff` shows the whole candidate relative to the current
canonical VM. `formatted-to-candidate.diff` isolates these lint corrections from
the exact frozen formatted candidate. `manifest.json` supplies all 136 member
hashes and all materialization paths.

The controls are pure source/data evidence. Rust compilation, formatting,
all-target Clippy with unchanged `-D warnings`, full Debug/Release runtime
regressions, independent review and canonical integration remain pending. A
fresh hosted formatter may adjust the new source layout; its exact output must
be retained and re-bound before claiming formatted-source execution. The
existing source/evidence packets remain frozen. No local Rust/Cargo/rustfmt,
Clippy, Swift, Elixir, product runtime, Git/gh, UI/capture or native runtime was
invoked. No owned process/runtime scratch or test instance was created.
