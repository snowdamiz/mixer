# Audit key-work correction independent review

Review result: **pass for the bounded correction, with no blocking findings**.
The processing-bound finding in the original codec review is addressed in both
closed-map checks. Root owns the live integration decision. This is pure codec
component evidence and does not accept an authority, production or GA gate.

The frozen correction receipt SHA-256 is
`c04cae984dd88344dc3933ad58b5f8c01c07eecf33cf22cf9266c494555d7c53`;
the reviewed module SHA-256 is
`daff6c6084be7094bc1a2b97ae386d5fcd4390e245c99f6de77f09572c07f6ad`.
All three frozen packet checkers passed. Independent archive verification found
the same 60 baseline files, 66 overlay inputs and unchanged 21 locked dependency
packages. Versus the original candidate, only the module and added focused test
differ. The module delta is exactly the two requested membership expressions.
Artifact CBOR, shared fixtures, 185 captured rows, six chains and producer
vectors retain their original bytes. No live implementation was edited.

The ten row keys and sixteen display keys are distinct fixed constants. Exact
cardinality plus presence of each required key therefore proves the same closed
map as the original sort comparison. Numeric equality cannot broaden this
schema because required keys are atoms or binaries. The checks short-circuit
non-maps and incorrect cardinalities, then query only those fixed short terms;
there is no enumeration or sorting of supplied keys before field validation.
Long foreign binary keys and nested foreign terms cannot enter later rendering
through a successful shape check. The correction removes the identified
unbounded common-prefix sorting path. This reasoning concerns decoder work on
already allocated input, without a universal BEAM latency or memory guarantee.

A fresh owned archive copy passed warnings-as-errors compilation and:

- **12 focused tests**, including the original eleven and correction regression.
- **Six retained independent tests**, covering 107 coherent-hash specimens and
  eight adjacent-edge cases.
- **Two new independent tests**, covering 546 exact-cardinality single-key
  replacements across 21 foreign key forms, 26 missing-key maps, 546 extra-key
  checks, eleven foreign map cardinalities through 10,000 entries, and distinct
  integer/float key controls. Original/new predicates agree with an independent
  exact-key-set check in these finite cases.

The new parity test compared complete original/corrected results for all 80
producer vectors, 107 independent specimens, 185 captured rows across six chains
and eight independent edges. Accepted results preserve exact CBOR, domain hashes
and PostgreSQL display bytes; rejected results remain the fixed error. The
original module was renamed only in owned reviewer scratch for this comparison;
its preserved source and exact name substitution are bound in the review archive.

The retained finite probe was run freshly with input allocated before timing,
three repeats of twenty calls, and keys capped at 4 MiB. Median microseconds per
twenty rejection calls were:

| Input | 1 KiB | 1 MiB | 4 MiB |
| --- | ---: | ---: | ---: |
| Unknown display keys, fresh correction review | 5 | 32 | 39 |
| Unknown row keys, fresh correction review | 1 | 1 | 1 |
| Known display keys, oversized value | 520 | 519 | 535 |
| Known row keys, oversized value | 2 | 2 | 2 |
| Unknown display keys, original review | 26 | 6,221 | 26,565 |
| Unknown row keys, original review | 11 | 4,137 | 18,235 |

All 36 observations rejected input. These are finite host observations, with no
timing pass threshold or claim covering all sizes, runtimes or host conditions.

Full hosted/release checks were **reused from the correction's exact overlay**,
not rerun by this review. The reused receipt and all source archive members,
commands and output hashes match: **105 passed, two explicit Linux-only network
namespace skips**, formatting and compilation passed, packaged release built,
missing configuration failed as expected, and all four test exports were absent.
The reusable full-suite source digest is
`bc9f63837c57c4635899477851468b80a2a624232dff835c334c23a916b1705b`.

The environment was macOS arm64, Python 3.14.8, Elixir/Mix 1.20.4 and Erlang/OTP 29
(ERTS 17.1), with `ERL_FLAGS=+S 2:2`, offline locked dependencies and `MIX_ENV=test`.
The reviewer scratch was removed. This review started no database/listener or
native instance. Full-suite PostgreSQL cleanup is independently hash-bound
reused evidence. Commands, tool versions, inputs, output hashes, exact test
archive and cleanup are recorded in the
[receipt](../verification/hosted-audit-key-bound-review/receipt.json).
The frozen checker starts no services:

```sh
python3 -B verification/hosted-audit-key-bound-review/check.py
```

No fresh audit SQL, authority composition/writer, migration, authenticated HTTP,
provider, UI, native/physical phone, immutable FieldLog consumption, production
publication or GA acceptance was performed. Physical phones remain deferred.
