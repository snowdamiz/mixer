# Hosted audit codec independent review

Review result: **one processing-bound correction required** before root selects
the frozen candidate for live integration. No typed-byte, retained-row or
adjacent-edge correctness discrepancy was found in the exercised cases. This is
a component review, not authorization, release or GA acceptance.

The candidate is the four-file overlay committed in
`e337ddd14236cc94ede4def750a9fde4c461ad3e`, with implementation SHA-256
`655eff236f72a0d226ef8c93fa62b1c854c05b8adf51a6634773ea6f8a4f294c`.
The producer checker independently passed all 101 bindings. The review copied
the exact 60 accepted hosted baseline files, four frozen overlay files and two
shared protocol fixtures into owned scratch; all source and dependency bytes
matched the producer's accepted manifests. The original artifact CBOR source
and every baseline file were preserved. No dependency was added or changed.

## Required correction: P2, bound closed-key checks before sorting

At candidate `upload_event.ex:35-37` and `:159-160`, closed row/display checks
sort `Map.keys(input)` before establishing that the names are in the fixed
allowlist. A ten- or sixteen-entry map can contain arbitrarily long binary keys
with a common prefix. Comparison during sorting then consumes work proportional
to those unvalidated key lengths. The field bounds do not protect this earlier
step. Inputs still return the fixed error; the defect is the claimed bound on
processing malformed inputs, not acceptance of malformed audit history.

The finite probe allocates input before timing, uses three repeats of twenty
calls, and limits each key to 4 MiB. Median elapsed microseconds were:

| Input | 1 KiB | 1 MiB | 4 MiB |
| --- | ---: | ---: | ---: |
| Unknown display keys | 26 | 6,221 | 26,565 |
| Unknown retained-row keys | 11 | 4,137 | 18,235 |
| Known display keys, oversized reason | 505 | 541 | 588 |
| Known row keys, oversized digest | 8 | 11 | 15 |

These are observations on this host, not timing thresholds. The source also
establishes the unbounded comparison path. The finding is separate from memory
already allocated by the caller, which the candidate correctly disclaims.

The narrow correction is exact map size plus lookup of each fixed allowlisted
key, without enumerating or sorting unknown keys. Both row and display checks
need the correction. Preserve strict missing/extra/replacement-key rejection and
add regression coverage for large common-prefix unknown keys. Root owns the
correction and integration decision; this review did not edit candidate source.

## Passing evidence

One complete replay of the exact original overlay passed **104 hosted tests
with two explicit Linux-only network-namespace skips**. Formatting,
warnings-as-errors application compilation, packaged release build,
missing-configuration rejection and all four production test-export exclusions
passed. The disposable loopback PostgreSQL fixture stopped and its scratch was
removed. This exercises existing hosted foundation SQL, not a fresh audit writer
or migration.

The original **11 focused audit tests** passed, including reconstruction of
185 captured PostgreSQL rows across six chains and the existing 80 coherent-hash
vectors. Captured rows were retained; no fresh audit SQL is claimed.

The independent suite passed **six tests**, including **107 new typed-first
specimens: 46 valid and 61 invalid displays**, and **eight edge cases** built
from separately valid rows. The new stdlib builder imports no producer encoder,
oracle or fixture. It constructs typed events first, projects display values,
and separately builds CBOR, domain-separated SHA-256 and expected PostgreSQL
display bytes. Literal golden encodings check all unsigned integer width
branches. Malformed spelling cases keep coherent typed bytes and hashes, so a
stale hash cannot mask schema validation failures.

The new cases cover CBOR integer-header transitions through maximum uint64,
safe-integer time bounds, exact authentication tolerances, completion after
recording, all six roles alongside an uploader, every decision revision maximum
and overflow, unique memberships at 1/64/65, multibyte and control-text byte
bounds, identifier lengths/domains, canonical and noncanonical IPs, numeric,
UUID and digest spellings, and initial-state versus decode-only validation.
Separate edge controls isolate missing/skipped/foreign predecessors, hash and
state mismatch while each constituent row validates. Semantically equal JSON
with escaped Unicode/slashes, alternative key order or trailing whitespace fails
exact retained-byte checks. Invalid input returns the fixed error with no
stdout, stderr or captured log output. The original artifact encoder continues
to reject null and audit byte-string tuples.

Source inspection confirms proper-list bounds before traversal, byte-size
limits before UTF-8 scanning or digest conversion, fixed nested schema and
field ordering, bounded generated CBOR, initial tenant state and immediate
same-tenant predecessor linkage. The three public functions confer no identity,
membership, signature or release authority. The required key-check correction
above is the identified exception to the processing bound.

## Attempts and limits

Review attempt 1 passed original focused and full hosted/release checks, then
five reviewer tests failed in the review fixture loader: it called
`String.to_existing_atom/1` before the candidate module loaded those atoms.
The sixth artifact-encoder check passed. The original failed test source,
archive, command output and receipt remain retained. The loader was corrected
to a fixed explicit atom-key list. Attempt 2 replayed focused tests in a new
owned copy and passed all six independent tests plus the finite key probe;
the successful full hosted/release replay was not repeated. Both owned copies
were removed. Producer attempts 1-5 and all prior packets remain unchanged.

The environment was macOS arm64, Python 3.14.8, Elixir 1.20.4, Erlang/OTP 29
(ERTS 17.1), PostgreSQL 17.11, and the unchanged 21 locked Hex packages.
Exact commands, source archives/manifests, dependency inventories and output
hashes are recorded in the
[receipt](../verification/hosted-audit-codec-review/receipt.json). The
[checker](../verification/hosted-audit-codec-review/check.py) verifies the frozen
packet without starting services:

```sh
python3 -B verification/hosted-audit-codec-review/check.py
```

No live source, authorization composition, catalog/migration, authoritative
writer/repository, authenticated HTTP, Neon/R2/Cloudflare, configured identity
provider, operational gate, native/device, published FieldLog package or GA
acceptance was performed. Physical phones remain deferred. This review does
not independently authorize root integration.
