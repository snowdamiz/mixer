# Independent guest transport codec review

No actionable codec defect was found in immutable commit
`c8bb3bcb37076e6c05a4de6cafe342b57018b59e` within this review's scope.
This lane authored external public-API tests and review evidence only. It changed
no implementation, schema, VM/import, native bridge, C, activation or release code.

`review.py` exports exact Git bytes into a private temporary directory, checks all
implementation-receipt source entries against the committed blobs, and compiles
`PublicCodecReviewTests.swift` as a separate package importing `MixerCapabilities`
without `@testable`. The mutable working checkout's SDK is never a test dependency.
The exported source remained unchanged; temporary source/build directories were
removed after the successful run to recover disk space.

## Observations

- Tags 1–4 map exactly to HTTP request, storage get, put and delete. Completion
  metadata fixes capability, schema hash and operation. Each successful result must
  match that context on encoding and decoding; cross-operation results reject.
  Get/delete argument objects intentionally share a shape and receive their binding
  from the caller's enum tag. Payload shape alone is not operation authorization.
- New decoding entry points normalize JSON guard/Foundation errors to the fixed
  `CapabilityWireError.invalid("guest transport JSON")` while preserving existing
  `CapabilityWireError` values. Duplicate escaped keys, malformed UTF-8/surrogates,
  invalid JSON and parser resource failures cannot leak raw parser errors through
  these entry points. Legacy `Wire.swift` is byte-for-byte unchanged.
- Wrappers, outcomes and result objects reject missing/unknown fields, foreign
  capability/hash/operation, caller-supplied identity/session/token fields, unknown
  outcomes, and mixing the separate capability-failure/rejection vocabularies.
- Lightweight public DTO constructors do not bypass boundary validation: argument
  and success-result encoders revalidate generated types, header/identifier/URL/
  method restrictions, numeric bounds and canonical decoded-byte base64 limits.
- Frozen value semantics are preserved: HTTP 3xx remains a value that the native
  policy may reject separately; `found=false` with nonempty bytes is retained;
  `committed=false` remains a valid value. The codec adds no rollback, grant or
  request/session-routing authority.
- Generator output is installed before native source hashing. An independently
  reproduced first generation, with the new transport file and both native identity
  outputs absent, matches the committed outputs. Repeat generation and `--check`
  preserve every byte. Omitting the new transport file yields the prior native hash,
  proving it is covered on the first run as well as later runs.

## Recorded proof

Ten independent public-import tests passed in both debug and release, with warnings
as errors. They cover fixed tags/bindings, all failure values, closed shape/type
confusion, wrong result contexts, arbitrary DTO validation, normalized parser
errors, escaped ASCII and Unicode restrictions, canonical numeric grammar,
identifier/URL/header limits, decoded byte/base64 limits, wire/depth/value/string/
key resource limits, snapshot ownership, and deliberate frozen value semantics.
These are bounded deterministic tests, not exhaustive fuzzing or allocation proof.

The original 90-case debug and 90-case release fixture execution was reused and
independently audited. For all 180 records, the review checked fixture/input bytes,
exact stdout/stderr reconstruction and hashes, expected exits, output bounds, and
accepted semantic comparisons. It also checked every original command/tool log
hash and success status, including the existing iOS, Android and WASI compilation
receipts. Those cross-builds were audited rather than repeated.

The exact implementation source digest is
`d144534e28ac463b5cb500fc5a64b9bda6109cfa422a200d99191e917ed993b3`.
`implementation-source-manifest.json` records all corresponding path/size/hash
entries; each matches the reviewed Git commit. The original implementation receipt
names its precommit baseline `e8012c5a923397729974dab6b297eab2f6e7cf0b`; this review
links its tested files to the later immutable commit through the complete digest,
not through that baseline revision alone.

The fixed contract from `3ba601332dab7c2aba98d7a50d7f0e893b1ea776` retains SHA-256
`052ebe9fbdc20a41307332086767e7903680bc83ba273c696edf9187be6b6439`.
The contract, case manifest, schema-v1 source, old generated Swift models/host/guest
adapters, old Swift probe and Java models/codecs/probe match that commit exactly.
The new public probe is separate. Native source identity is
`9a89c437d78df58eb809765c945ba05239f491c85b4e72f1ffba22c640e7759e`;
omitting the new file produces
`9e66695878568cbb0859d13cc6505ffd45b1471365af4d236fb9601efc0f6ed2`.

`receipt.json` records review commands/log hashes, tool versions, immutable commit/
tree, source freeze, generator reproduction, audited fixture/compile provenance,
findings and limitations. Reproduce with:

```sh
python3 verification/guest-transport-codec-review/review.py
```

This qualifies only the independently reviewed standalone value codec on macOS and
supports the audited cross-compilation scope. Native bridge/session-token binding,
VM import admission/execution, C layouts/unwind handling, activation, identity-v2/
release-v3 migration, full Swift async execution, immutable package FieldLog use,
signing, stores and GA qualification remain outside this review. Phones remain
disconnected; no device commands, production changes or publication occurred.
