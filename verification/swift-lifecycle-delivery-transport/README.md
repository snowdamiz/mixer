# Lossless lifecycle evidence delivery

The immutable accounting packet includes four large JSON files, one above
GitHub's ordinary file limit. These files remain unchanged locally and retain
their original sealed SHA256 identities. Deliver this directory and all other
packet files, excluding only the four raw paths below. Their deterministic gzip
payloads restore the exact bytes; no JSON normalization or seal rewrite occurs.

| Raw path excluded from Git delivery | Raw bytes | Gzip bytes |
| --- | ---: | ---: |
| `verification/swift-reactor-lifecycle-accounting/paired-layouts.json` | 105906299 | 3578131 |
| `verification/swift-reactor-lifecycle-accounting/inventory-final.json` | 56074963 | 1260753 |
| `verification/swift-reactor-lifecycle-accounting/inventory.json` | 56073803 | 1260524 |
| `verification/swift-reactor-lifecycle-accounting/discovery-final-preinstall/inventory.json` | 56073803 | 1260524 |

The fixed manifest SHA256 is
`b5580b593d27f36d2acc5ad3e9a7dc1660a0b1a163c7ac11cbe57b6edf3a9922`.
Its original accounting seal is
`02b53f531a4cb4852cc7e99104d13bb09e969f9d6b018c4d5d8fd6cd0d3dbbdd`.
The restore helper inherits the previously tested exact-byte transport, with
only the four fixed identities and authority join changed. It rejects traversal,
symlink ancestors and payloads, drift, conflicts, truncated/excess data and
concurrent publication. Existing identical files are no-ops; existing differing
files are never overwritten. Temporary outputs are removed on failure.

From a fresh checkout, run:

```sh
python3 -B verification/swift-lifecycle-delivery-transport/restore.py --check-payloads
python3 -B verification/swift-lifecycle-delivery-transport/restore.py --repo /absolute/canonical/path/to/mixer
python3 -B verification/swift-reactor-lifecycle-accounting/verify.py
```

All 28 inherited negative controls pass, as do positive artificial restoration,
exact no-op, actual bounded payload decompression and the current-checkout four
exact no-ops. These checks preserve original evidence; they confer no compiler,
runtime, native or product qualification. The full matrix gaps remain unchanged.
