# Fixture-envelope evidence transport

The original producer archive is preserved evidence of the first reviewed runner.
Independent review found acceptance blockers in duplicate compiler identity fields
and API diagnostic span binding. Its local passing run does not imply runner
acceptance; a separate correction and review are required before CI integration.

The CI runtime reads ordinary files from `verification/swift-envelope-ci-pack/`
and executes `scripts/ci/check-analyzer-envelope.py`. It does not open these
evidence archives. The pack retains all 60 selected originals, two selected
test-only augmentations, fixed inventories and small provenance records.

`producer-evidence.tar.gz` transports all 1,027 sealed implementation members
plus the seal and its hash sidecar: 1,029 files, 216,199,132 uncompressed bytes.
The archive is 1,985,011 bytes. Its SHA-256 is
`5caf356946f47919af51b5867cc341af07d50ec83ec65081eef3e391411b48f7`.
`producer-evidence-manifest.json` names every member and its byte count and hash.
This includes failed and superseded attempts, final raw command streams,
complete source snapshots, retained test inputs/reports, and pre/postflight and
cleanup receipts. Original local files are preserved.

`independent-round-1.tar.gz` preserves the rejected review round, its clean
host run and distinct interposed false-pass evidence. It contains 3,073 files
including seal and sidecar, totaling 389,911,074 uncompressed bytes, in a
7,267,598-byte archive. Its SHA-256 is
`b46b38498826759c69b2b1150e80f7235ea1d15ef94a3c1548dc3b98042b52e5`.
The matching manifest and verification receipt bind every byte, including the
complete recoverable sparse fixture from the deliberate retention interruption.
This archive records rejection, not runner acceptance. Use the same verifier
with `independent-round-1.tar.gz` and `independent-round-1-manifest.json`.

`correction-producer.tar.gz` preserves the corrected producer packet, its six
external source/contract bindings, original seal and sidecar, and the explicit
transport selection. All 377 members, 72,633,504 uncompressed bytes, were verified
against the 820,306-byte archive. Its SHA-256 is
`960457ad3bbcfe9643b3212a782ffdca9d0b4500dcc908ec1e79e981035365d4`.
`correction-producer-selection.json` converts the original packet-relative
member paths into repository-relative archive paths without changing any bytes.
The corrected producer passes 32 controls in normal and optimized Python and
one complete actual Rust 1.99.0 host invocation. Independent correction review is now accepted by root in
`verification/swift-envelope-ci-root-review/corrected-runner-acceptance.json`.
Actual Rust 1.98.1 CI qualification remains pending; this archive alone does not
grant that qualification. Use its matching `correction-producer-manifest.json`.

The final independent correction review is split across
`correction-independent-part-1.tar.gz`, `-part-2.tar.gz` and `-part-3.tar.gz`.
`correction-independent-parts.json` binds all three archive identities and
manifests and proves that their selections cover every one of the 10,789 sealed
review members, plus the original seal and sidecar, exactly once. Including
three selection records, the archives contain 10,794 files, 833,306,408
uncompressed bytes, in 24,569,034 compressed bytes. Each part remains below the
verifier's 4,096-file and 512-MiB bounds. Every member of every archive was
independently rehashed during transport verification. All 80 synthetic attempts
remain preserved, including the 40 invalid first-attempt fixtures excluded from
acceptance; clean actual and distinct refusal runs remain separate.

Verify each part with its matching `-manifest.json`. To inspect recovered bytes,
use a different new `--out` directory for each part. The central index identifies
which part contains an original repository-relative path; reconstruction is
for evidence inspection and does not authorize running historical fixtures.
The original 52-obligation map retains partial/deferred cases, not a 52-test
pass claim. Final review summaries and the map are also ordinary selected files.

`accepted-source-closure.json` separately selects the six accepted fixture source,
accounting and behavior-review packets for ordinary-file delivery: 417 distinct
files including their seals and acceptance receipt, totaling 10,339,825 bytes.
Every selected byte was reverified. This closure establishes the underlying
fixture scope; it does not grant acceptance to a CI runner.

Paths within a transport manifest are **archive member names and original
repository-relative evidence paths**. They do not assert that every historical
path exists as an ordinary file in a fresh checkout. Archive extraction recovers
those paths under a separate destination. Historical paths referenced inside
receipts remain provenance, not CI runtime dependencies. Older rejected evidence
outside the explicitly transported member list is not claimed to be published.

Verify every archive member without extraction or execution (Python 3.11+):

```sh
python3 -B verification/swift-envelope-ci-delivery/evidence_transport.py \
  --archive verification/swift-envelope-ci-delivery/producer-evidence.tar.gz \
  --manifest verification/swift-envelope-ci-delivery/producer-evidence-manifest.json
```

To recover the evidence, add `--out /absolute/path/to/new-directory`. Its parent
must already exist, the destination must be new, and no ancestor may be a symlink.
The verifier checks the archive identity, exact ordered member list, regular
file type, size and SHA-256; it never uses `extractall`, restores executable
permissions or executes recovered files. Inventories are bounded to 4,096 files
and 512 MiB. A failed recovery preserves its partial destination for inspection.
Recovery requires roughly the listed uncompressed size in free space.

Root's `transport-checks.json` records an actual fresh recovery of all producer
members, eight invalid path refusals, refusal to overwrite a destination and
refusal of a changed archive identity. The owned recovery directory was removed
after the child returned. These are evidence-transport checks, not additional
product, native, target, signing, semantic-replay or GA qualification.
