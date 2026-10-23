# Metadata-only release-v3 durable SPI

Frozen candidate1, independently authored with gpt-6.1-sol / xhigh. This is a
metadata dependency for the proposed private capability updater. It creates no
Wasm admission, durable selection, healthy-record provenance or execution authority.
Independent review and integration remain pending; no commit/push was made here.

The production source is only `updates/Sources/MixerUpdates/VerifierV3.swift`:
SHA256 `474e8d3223430225a06743ccb6d29043980b1ad4b57f69a44308182260c9a3ac`.
The14 original new test functions are in `VerifierV3DurableSPITests.swift`:
`ec18e5455229b78e1db18d5983f53882526caa6172738a02c9fae32b79d58dd5`.

`@_spi(CapabilityDurableV3)` exposes opaque `OfferEvidenceV3` and
`RetainedHealthyEvidenceV3` with fileprivate constructors and no Codable or
`VerifiedArtifactV3` conversion. The offer checks both signed headers, greater
sequence and cohort without requiring payload. Retained verification requires the
exact stored sequence<=accepted high-water, both signed snapshots and matching
payload. Its only authority exception omits root notBefore/notAfter checks; it
still checks revoked/key/role/scope, signatures, closed shape, installed host,
resources, grants, payload and cohort. Revalidation rejects an identical-but-new
verifier context; ordinary verifier copies retain their original private context.

SPI is not a security barrier. A different caller can invoke these metadata
helpers on its own verifier. The future private updater must establish actual
committed-health provenance and keep its factory/verifier and selections private.
No method returns a durable receipt or executable proof. Existing ordinary public
current-time methods remain strict and cannot consume retained evidence.

Every variable-size input is preflighted before owned copies: both documents
<=65536bytes, payload<=installed<=4194304, and channel/installation at most128ASCII
identifier bytes. The new string gate examines at most129UTF8 bytes before using
the unchanged identifier helper. Exact signed Data is independently copied before
parsing, including external no-copy backing. Copies returned to callers use Data
value semantics. No process-wide verification concurrency/RSS bound or recoverable
OOM claim is made.

## Qualified evidence

Run from a checkout containing this candidate:

```sh
python3 verification/release-v3-durable-spi/run.py --label fresh-review-label
```

The driver requires a fresh output/work directory and exports all71 recorded
inputs before compilation. It checks live/export hashes before/after every
command. Dependencies remain the unchanged pinned updates Package/lockfile; the
new SPI has no capability SDK/bridge or native VM dependency. No mutable SDK source
is consumed.

- Receipt: `2026-10-23-candidate-1/receipt.json`, SHA256
  `7c96522e85e95c1f485c3d141bed09f864e1a2d4b32e5811604dbd33a967bd53`.
-71-input manifest:
  `67c44a3e6dd956165ad001ab569edd0d2b5d52ebd54a47ca6079f5234486a2f9`.
-31 exact command logs:69 functions each debug/release (55 unchanged+14 new),
  14 new functions under TSan including32 concurrent immutable verification calls,
  external non-testable SPI and unchanged public clients linked/run,12 intentional
  public/SPI compile rejections with checked diagnostics and a positive control.
- Official iOS arm64, simulator arm64 and Android arm64 release module/object
  builds passed; tools/SDKs/commands and actual output hashes are in the receipt.
  This is compile evidence, not final app link, device/signing or platform execution.
-40 prior updates paths match Git baseline
  `61f34bf3834a81d47b6e3a9b191ede5a5743ea9e` exactly. Removing only the three
  explicitly marked additive blocks restores the entire prior VerifierV3 source,
  SHA256 `96c8cb21dceb2fe50334f279d3b2656b3ed92efb101fd62f5765ffe4e83d8cd1`.
  Old verifier/updater/models/I/O, tests, fixtures and package outputs are untouched.

New tests include separate artifact/assignment time windows, revoked/wrong-role/
scope/key/domain signatures, replay and UInt64 boundaries, exact/+1 document and
4MiB payload limits, malformed later-input preflight ordering, >1MiB bridged Unicode
and ASCII-suffix rejection, metadata/grant/resource mutations, raw JSON ambiguity,
cohort rejection, external-buffer mutation and same/foreign-context revalidation.
The original suites retain their frozen cross-language vector corpus.

`development/initial-test-compile/` preserves the initial missing-try test harness
failure, exact failing test and command log. `development-qualification-1/` is the
complete passing12-test preliminary qualification before the bounded-prefix
improvement/two additional tests; its source/log pins are historical and are not
the final candidate. The fixed final source is qualified separately above.

The ignored work paths recorded in receipts hold actual exported sources,
consumer binaries and cross modules/objects. Host debug products are subsequently
rebuilt for TSan; the pre-TSan host library archive is not separately retained or
claimed bit-reproducible. Exact consumer binaries and cross outputs are retained
and hashed. Swift/C-shim TSan does not instrument system CryptoKit/framework code.
No files from other active lanes were edited or cleaned up. Phones remain unused.
