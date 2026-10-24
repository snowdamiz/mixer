This separate transport preserves the exact immutable V5, V6 and V7 evidence. It changes no existing file, candidate, symlink or runtime selection. The selected root delivery closure has 7,483 unique regular paths and 298 shared evidence symlinks. Two regular files exceed the root delivery script's 95,000,000-byte bound:

| Omit raw file from Git delivery | Exact raw bytes | New transport bytes |
| --- | ---: | ---: |
| `verification/swift-calls-dispatch/v6-fixture-expectation/inventory-v5.json` | 227,613,407 | 4,810,158 |
| `verification/swift-calls-dispatch/v7-fixture-expectations/compiler-partitions-v5.json` | 100,825,425 | 8,050,047 |

Deliver this entire transport directory, including its two new `payloads/*.gz`, instead of those two raw Git blobs. Keep all other selected files and all 298 original symlink targets/modes unchanged. The source raw files remain present and untouched in the producer's active checkout. The original V6 `inventory-v5.json.gz` also remains separate evidence: its decompressed SHA is `559616143aeb03073366e6be1ec1ca06bbea9402ec797c0f47a13be1da947806`, which differs from the bound raw SHA `a7d2e7dc7ac5c9950aeaedc792c7db660088c66293d6e653219b51a4343655f4`. Both original files individually match the V7 history bindings. The existing gzip therefore cannot substitute for the raw file. No JSON or compiler identity normalization was applied.

`transport-manifest.json` has exactly two entries. It binds original relative paths, raw bytes/SHA/mode, new compressed bytes/SHA and the unchanged V7 review seal plus its bound V6 history manifest. The new gzip payloads use empty filename, mtime zero and compression level nine; the capture pins the actual Python/zlib versions. Independent decompression to discard reproduced each original sealed raw SHA and length.

In a fresh POSIX checkout that preserves the existing symlinks, run from the checkout root:

```sh
python3 -B verification/swift-calls-dispatch-delivery-transport/verify.py
python3 -B verification/swift-calls-dispatch-delivery-transport/restore.py --repo /absolute/canonical/path/to/mixer
python3 -B verification/swift-calls-dispatch/v7-fixture-expectations/read_only_verify.py
```

The first command verifies this separate transport seal and checks both actual payloads by bounded decompression to discard. The second command validates the original authority files in that exact checkout and restores only the two missing raw files. Its root argument must be the canonical absolute checkout path. It rejects traversal, symlink ancestors, symlink/nonregular payloads, conflicting existing files/directories/links, compressed drift, truncation and excess output. It uses directory descriptors and `O_NOFOLLOW`, hashes decompressed output before publication, and publishes a complete temporary file with atomic exclusive `link(2)` creation. It never overwrites an existing target. Existing byte-identical targets are no-ops. Failure removes only the helper's actually created temporary file; a preexisting temporary-name collision is preserved. No target parent directories are created.

The third command is the unchanged V7 verifier. Its `bound()` reads every original sealed raw path directly and has no transport fallback or materialization. The collector's separate `read_json()` gzip fallback does not satisfy those direct seal checks. Restoring before the unchanged verifier is therefore required. The restored raw files are local verification material and must continue to be excluded from Git delivery; no original seal is rewritten.

Pure artificial fixtures prove successful exact restoration and unchanged no-op behavior, as well as failure and cleanup controls. A concurrent target-creation control proves exclusive publication cannot overwrite another file. Actual payloads were checked to discard, then the helper was run against the current checkout and returned two exact no-ops. No active old packet was materialized or modified. No Git, compiler, product VM, Node or native runtime was invoked. These are delivery byte-transport receipts, not new accounting or runtime qualification.
