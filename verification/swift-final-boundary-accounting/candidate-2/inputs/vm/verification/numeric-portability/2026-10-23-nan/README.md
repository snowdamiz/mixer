# Arithmetic NaN portability repair

Linux x86_64 CI run [39890316915](https://github.com/snowdamiz/mixer/actions/runs/39890316915), based on `2fda7ab81f1b4520a962deca237e5e60d03dda44`, failed the existing explicit float oracle when `f32.ceil` returned signaling NaN `0x7f812345` unchanged. The VM had returned host floating-point result bits directly. The failing oracle is unchanged by this repair.

The implementation now chooses positive canonical NaN bits for every NaN result of arithmetic, rounding, square root, promotion, and demotion. This choice is allowed by the official [NaN propagation rules](https://webassembly.github.io/spec/core/exec/numerics.html#nan-propagation), including when all inputs are canonical or when an invalid operation has no NaN input. The [promotion](https://webassembly.github.io/spec/core/exec/numerics.html#op-promote) and [demotion](https://webassembly.github.io/spec/core/exec/numerics.html#op-demote) rules permit the same choice. Result classification uses integer bits and does not rely on the host quieting signaling inputs.

| Instructions | Result handling |
| --- | --- |
| f32/f64 ceil, floor, trunc, nearest, sqrt | Canonicalize NaN result bits |
| f32/f64 add, sub, mul, div | Canonicalize NaN result bits, including invalid operations without NaN inputs |
| f32/f64 min, max | Existing explicit NaN handling was canonical already; retained and covered by result normalization and both operand-order regressions |
| f32.demote_f64, f64.promote_f32 | Canonicalize NaN result bits after conversion |
| f32/f64 abs, neg, copysign, reinterpret | Retain exact payload bits and required sign manipulation |
| Float-to-integer conversion and comparison | Original trap, saturating, and comparison behavior retained; explicit signaling/quiet regression coverage |

The literal-bit regressions cover positive and negative minimal/maximal signaling payloads, canonical and other quiet payloads, unary and binary operations, invalid arithmetic, both conversion widths, and bitwise preservation. The pre-fix macOS negative control passed 12 tests and failed the two new canonical-policy tests. On this arm64 host the old implementation quieted signaling inputs while retaining payloads, which is allowed by Wasm; the negative control demonstrates the new policy tests are active. The nonconforming unquieted output was observed on Linux CI.

`receipt.json` records exact commands, versions, source manifest digest, output hashes, unchanged profile/oracle hashes, and limitations. `source-manifest.sha256` freezes the checked source and was verified unchanged after all commands. `before-fix-tests.patch` reconstructs the earlier 14-test negative-control source from the base revision; `before-fix-source-manifest.sha256` records its changed source hashes. The remaining source for that negative control is the base revision.

Observed macOS arm64 results:

- Default debug and release: 91 tests passed in each configuration.
- Experimental debug and release: 108 tests passed in each configuration.
- Explicit Node oracles: all nine functions passed in each configuration; the float arithmetic oracle matched 27,944 cases per configuration.
- Formatting and clippy with warnings denied: passed in default and experimental configurations.

Actual repaired Linux x86_64 debug/release execution awaits the root-controlled CI rerun. Physical iOS/Android checks remain pending while phones are disconnected. These results do not qualify signing, immutable package publication, FieldLog dogfood releases, OTA authorization, or GA gates.
