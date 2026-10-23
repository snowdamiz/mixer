# Independent appearance foundation review

Verdict: **pass for the frozen pure foundation only; no blocking product findings**.
Authoritative execution: `candidate-2/receipt.json`.

Reviewed candidate source tree:
`2a72523ed49f8695ac321c1f0f256640f66cb445504fc893d53066d0c82f6185`
(59 producer inputs). All archived inputs and all five live product files were
hash-checked before and after independent execution. The public value declarations
match the accepted declaration contract after comments and blank lines are removed.
The concrete codec and math operations were compiled and exercised through public APIs.

The reviewer independently wrote `build_corpus.py` and `main.swift`. The generator
interprets the frozen schema directly and applies separately written prose graph
checks. It never imports the producer tests or preserved design Python validator.
The Swift runner is compiled with exactly four hash-checked copied product sources
in an isolated derived tree. It does not modify or execute the live SDK checkout.

Debug (`-Onone`) and Release (`-O`) each passed:

- 5,153 descriptor cases: 535 accepted and 4,618 rejected. Every accepted case
  validates and round-trips through byte-identical canonical output and equal Swift
  values. Cases cover every required field, unknown fields, nested wrong types,
  numeric/string limits and enums across shared, bundled-font and platform-specific
  graphs, plus deterministic byte mutations.
- Independent parser probes for decoded duplicate keys, numeric token spellings,
  UInt64 limits, ASCII/Unicode/escape failures, canonical endings, depth16/17,
  value4096/4097, arrays64/65, decoded strings512/513 and exact descriptor
  byte65536/65537 behavior.
- Raw constructor rejection at both `validate` and `canonicalData`, including
  multi-megabyte strings, 100,000-element arrays, catalog references, font variants,
  bounded numbers, both platform themes and geometry overflow attempts.
- 589,833 `scaled64` and 1,835,015 `pixels` comparisons against an independent
  quotient/remainder rounding reference. Every admitted metric is swept at selected
  boundary and near-boundary scale/density values.
- 59,520 text-scale/density normalization cases at each half-step and its adjacent
  representable values; 16,384 stack-spacing ties; invalid ranges and nonfinite
  inputs. Total: **2,507,093 assertions per build, zero failures**.
- The public built-in default emits the same **1,906 bytes** in both builds, SHA256
  `e94f6988744bde16b83001db8e5047aeac4f15f6b045f99a4660445e7e2062d2`.

Source inspection confirms input bytes are admitted before the parser's byte-array
copy; parser depth/value/array/string counts are bounded before child retention;
raw resource and face counts are checked before mapping; caller strings are walked
to bounded ASCII lengths before retention in a new graph; and canonical byte size
is measured before allocating output Data. Hostile raw constructor execution supports
these checks, but is not an allocator instrumentation proof. Caller-owned arrays and
strings necessarily already exist at entry.

## Addenda and preserved attempt

The sealed design Python oracle checks scale1/locale `und`/neutral direction only
for referenced fonts. The accepted prose, root clarification and production Swift
require it for **every fontSFNT resource**, including unreferenced entries. Independent
cases confirm the stronger invariant. Historical design artifacts remain unchanged.

The frozen `spacing64` contract explicitly specifies `floor(value*64+0.5)`. At the
representable value immediately below the first half-step, the addition rounds to
1 before `floor`. The production implementation matches that exact formula; the
independent runner records this detail. Cross-language implementations must preserve
the frozen formula or obtain an explicit contract change. This is not a finding
against the implementation.

`candidate-1` preserves a failed independent harness compilation: Swift6 correctly
rejected nonisolated helper functions mutating main-actor globals. The reviewer added
`@MainActor` to three harness helpers, then completed candidate2. No product source
was changed. Its original fixtures are also preserved compressed; local uncompressed
material and compiler caches/binaries are excluded from Git.

This pass establishes no installed or signed appearance authority, actual SFNT/PNG
validity, licensing, glyph support, widget consumption, native systemSans identity,
Apple baseline match, iOS/Android appearance parity, physical-device result, published
FieldLog dogfooding, release safety or GA gate. The four pure foundation sources
remain independent of native renderer and signed presentation mutation.

Reproduce from the same producer archive with a new unused result label:

```sh
python3 verification/ui-appearance-foundation-review/verify.py candidate-3
```

The corpus is stored as deterministic `independent-corpus.json.gz`; the verifier
materializes its uncompressed counterpart only under ignored `.build/`.
