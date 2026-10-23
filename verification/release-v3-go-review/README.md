# Independent Go release-v3 review

No actionable protocol defect was found in the frozen candidate. This is an
independent host review of public Go protocol primitives, not approval of v3
service routes, storage dispatch, native execution or release publication.
Authoring/review model: gpt-6.1-sol, xhigh.

The25 production/fixture inputs have sorted-map SHA-256
`6d6383875d27c3f786de7591f035c9310abb9866900d78e4c448795fa8bdb094`.
All exact file hashes are recorded in `2026-10-23-final/receipt.json`:

- `v3.go`: `ca2bac3c5c071429741211900aacc752a3477306b768765d77c5c88b8ad71fca`
- `v3_test.go`: `1717fcec5495212a962c61b58cd36cc93dfdb941adcc225918c2e9404ff7f8d3`
- `json_shape.go`: `da89f9e60f12a5c86c6195fd84ecf77c2c53089eb2e548fa499eea9df793e054`

Fourteen existing protocol source/test/fixture/generator files were byte-equal to
`aca686bfc72b8f18db727de5307977fb51790e0a`. Removing the exact two-line v3 type
case from the new `json_shape.go` yields the committed old bytes. The driver
exports21 baseline Go/SQL dependency files for the existing HTTP-shape test,
independently of mutable service lanes. Production inputs remained unchanged
throughout all final runs. No services source was edited by this review.

Final receipt SHA-256:
`882a70c8c823d11c6cd6ef5dfd9cd37eaf0f96a0dacc8d1b9092bac9242ed5ae`.
Final `seal.json` SHA-256:
`38c2617dc31ea205b85ff158fd0a0dc00e2eea2e19f6fde52c69969b178e0186`.
The original independent test is `review_test.go`, SHA-256
`bb21748d3dbc3b79001cf624e1e6f985a6bf5017c969c96771b9f6d964e4e29f`;
`run.py` SHA-256 is
`6c1f7df7a74c1d029967caea65a9a0fefc86ca217d8434a38d8fa97cce569629`.

Observed results:

- Existing protocol tests passed normally and with Go's race detector, including
  the six new v3 test functions and shared154 manifest/36 assignment raw cases.
- Seven original external-package public-API test functions passed normally and
  with the race detector. They use new deterministic TEST ONLY keys/models and
  do not reuse the fixture generator's keys or model constructor.
- Every signed scalar leaf was mutated with its primitive type preserved.
  Sixteen semantically valid header changes additionally rejected the original
  signature and accepted a fresh standard Ed25519 signature. Signature bytes,
  domains, root roles/scope/half-open time ranges, duplicate/128+1 root bounds,
  replay/high-water, invalid installations and artifact reauthorization reject
  as expected.
- Closed/missing/unknown/alternate-case/null/escaped-duplicate fields, numeric
  lexical violations, signature arrays/base64 padding/newlines and failed
  decoding into reused receivers were tested through both checked decoding and
  direct standard-library unmarshalling. Failed fixed-model decoding preserved
  the existing receiver.
- Signed resource limits, exact4MiB/+1 payloads, known capability/schema maps,
  installed ceilings and typed legacy/domain separation passed original probes.
- An independently authored Python restricted-CBOR encoder matched both fixture
  messages/domains, artifact identity and unchanged grant descriptor hash.
  Standard Go crypto independently verified signature behavior in the probes.
- `go vet ./protocol` passed. Regenerating the test-only v3 fixture/corpus inside
  the private export reproduced both files byte for byte.

One explicit API limitation was reproduced and agreed with root: Go's ordinary
`encoding/json.Unmarshal` strips outer whitespace before invoking custom
`UnmarshalJSON`, so direct DTO unmarshalling cannot enforce the byte length of
the original transport including that padding. `DecodeSignedManifestV3`,
`DecodeSignedAssignmentV3` and `protocol.DecodeJSON` enforce their original input
bounds; the independent exact65536/+1 test confirms this for the manifest.
Direct JSON decoding is closed raw-value parsing and never authority. Network
callers must use the checked entrypoints. This was not a checked-decoder bypass;
root documents it in the separate v3 API README.

The explicit v3 validators check their real schema/protocol3/ABI2 tuple before
using a temporary common-field validation view. Inspection confirmed that this
temporary view is never hashed, signed or returned as verified authority. The
actual v3 model and exact domains feed signature checks; assignment verification
rechecks artifact authority. Header-only APIs do not prove payload verification,
and this boundary is separately tested and documented.

Replay from the repository root with fresh output:

```sh
python3 verification/release-v3-go-review/run.py --output /absolute/private/fresh-go-v3-review
```

`development/first` and `development/final` retain two exporter failures: omitted
existing HTTP-test dependencies, then omitted embedded SQL migration files. These
were harness errors before protocol tests ran. Corrected export results are
retained under `development/final-v2`; the final run strengthens type-preserving
mutations and valid-field signature checks. Earlier test/driver versions are
retained beside the current files. No skipped test is reported as a pass.

No production network, credentials, devices, native capability I/O, Swift v3
parity, updater persistence, v3 HTTP/SQL rollout, actual installed identity,
Wasm admission, UI/FieldLog or GA gate was exercised. Existing HTTP-shape tests
use an in-process test server with baseline implementation. Timings in receipts
are development command elapsed times, not product performance measurements.
