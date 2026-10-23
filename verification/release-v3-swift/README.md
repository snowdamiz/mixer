# Explicit Swift release-v3 qualification

The first v3 verifier/proof slice passes scoped qualification. `ReleaseVerifierV3`
selects only protocol3/guestABI2/UI1 with frozen known capability schemas and
resource limits. Its public artifact, assignment and grant types have no public
constructor or decoder. Copies of one verifier share immutable private authority;
a separately initialized verifier must verify signed bytes again. Assignment
verification rechecks current artifact authority, and artifact revalidation binds
current authority plus exact supplied payload bytes. No durable updater, factory,
coordinator, Wasm admission, effect, hosted route or retained-health exception is
implemented by this slice.

The exact 69-input source manifest is
`2026-10-23-candidate-1/source-manifest.sha256`, SHA256
`534414332fd4ec0731f781dc43faef56cb99c8b98022db64ea1545b5105d0388`.
The uncommitted candidate was copied to
`updates/.build/qualification-release-v3-2026-10-23-candidate-1/source` before final
execution. Current and exported inputs were rehashed around every command. The
new verifier source SHA256 is
`96c8cb21dceb2fe50334f279d3b2656b3ed92efb101fd62f5765ffe4e83d8cd1`.
The old Verifier.swift stays byte-exact at
`3886a064552bdd0573362909f4f6fe0973ddf5a6982cb4369c5a92b328a52d60`;
all19 baseline production/test inputs match Git
`1ab4d4ee76a5d4ba206bd370cbeeeb73a7c6c636`. Existing canonical/signature vectors and
rejection tests run unchanged. No general-purpose dependency was added.

| Evidence | Actual result |
| --- | --- |
| Full original plus new updates tests | 55 passed in debug and55 in release:40 original,15 new |
| New v3 Swift/C-shim TSan | 15 passed, including32 concurrent immutable verifier copies; no reported race |
| Shared Go/Swift positive vector | Exact CBOR, domain-prefixed messages, signatures, artifact identity, cohort and unchanged grant descriptor |
| Frozen shared raw corpus | All154 manifest +36 assignment cases agree;39 origin +14 namespace grammar cases independently re-signed with the Swift public test key |
| External public client | Non-@testable compile/static link and actual signed-string-payload verification succeed |
| Public opacity | Positive import/typecheck succeeds; eight intentional negative compiles fail for the expected access/type/conformance reasons |
| Official iOS arm64 | Release library module/object compilation with warnings-as-errors; artifacts hashed |
| Official Swift6.3.3 Android API28 arm64 | Release library module/object compilation with warnings-as-errors; artifacts hashed |

The host receipt is `2026-10-23-candidate-1/receipt.json`, SHA256
`253bf3912fe52262b5e837f2c3a51ea656b13eafe32dd59f991ccf53748484ff`.
Its19 commands include tool versions, both full suites, public client link/run/
architecture, a positive external typecheck, eight expected negative compiles and
scoped TSan. Negative cases cover all four proof/grant constructors, artifact and
grants Decodable conformance, legacy artifact substitution and private evidence
access. They are expected exit1 results, not failed qualification commands.

Original Swift cases additionally cover same versus foreign verifier context,
expired artifact signing authority while an assignment key remains current,
substituted payload, a captured key surviving mutation of an external no-copy
buffer, closed nested shapes and global/installed bounds, canonical signature and
JSON failures, sorted family-specific grants, replay/channel/cohort and exact/
plus-one64KiB document and4MiB payload boundaries. A signed memory-byte value1 is
valid metadata; no rounding or execution admission occurs in this verifier.

Both shared fixture copies match root's frozen originals byte for byte:
`signed-release-v3.json` SHA256
`ee4935fedca51b728e78801cb05c5732e8547bda1e26f109330e6659a0a2f77a`;
`release-v3-cases.json` SHA256
`8f62ae6bc91e951c3c66ab16689dd20f9465c7b671b2f24ad44b5960923c2b44`.
Root owns `services/protocol/testdata/generate-v3.go` and both canonical files.
The payload is a public test string, not Wasm. Test keys must never become an
installed signing configuration.

The separate official SDK receipt is
`2026-10-23-candidate-1-cross/receipt.json`, SHA256
`08a62b5a808adb31befefea9e608833d7900cfaef963d7de6ecd7795d871777d`.
Its five commands bind official tool/SDK selection and actual two-target module/
object outputs to the same source freeze. This is not a mobile final link,
platform run or physical-device receipt. The parent/root independent release-linked
public-client review is separately owned under `verification/release-v3-root-review/`;
its evidence and integration decision are not fabricated by this owner receipt.

`run.py --label NEW-LABEL` exports and runs the host matrix, refuses prior output
paths, preserves old source/test bytes and binds shared fixtures. The cross helper
pins the specific existing candidate receipt and compiles that immutable export.
`finalize.py` checks receipts, raw logs, source/export, fixture and artifact bindings
without re-running tests; `final-receipt.json` and `evidence-manifest.sha256` seal
reviewable files while excluding generated .build/.swiftpm/__pycache__ components.
Development logs are preliminary and do not replace frozen-source receipts.

This is signature/metadata/payload proof qualification. Swift TSan does not
instrument system CryptoKit/frameworks. Synchronous callers still control their
scheduling; no global process-memory, OOM recovery, arbitrary native-caller,
wall-time, OS destruction or rollback guarantee is made. A future bounded validator,
material-bound factory, private v3 updater/coordinator, actual effects/health/data
reconciliation, hosted services, signed embedding, published external consumers,
physical mobile and GA require separate evidence. No device, trust, credential,
commit, push or production publication operation was performed in this lane.
