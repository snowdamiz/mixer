# Private Swift memory growth integration

The reviewed private memory-growth operation is integrated into the live VM.
This accepts a bounded host development slice. Full Swift execution, imported
host calls, complete dispatch, Ready/public invocation, native integration and
all FieldLog/physical/release/GA requirements remain open. G08's existing
absent-cursor cleanup diagnostic also remains open.

The implementation uses the actual frame phase, memory ticket, State arenas and
control/WASI owners. It reserves full replacement memory while old storage is
still live, checks bounded zero/copy work, and commits the original ticket only
after preparation succeeds. Cancellation before commit drops the new allocation
before refund; failures after commit retain the grown memory. Unreconciled debt
retains its original authority and frame envelope for explicit cleanup.

The raw 127-file reviewed closure is
`56e47ffa2c74ea243c9ead371a5ebfdeb59e85c0f05555419d51c84483afabe3`.
The live integrated closure is
`a0bbe77aca3021e48f1fb76dc97cfbc0406c24e5ba7eacdd33d5dabe8f998d9b`.
Their sole difference is one trailing ASCII space removed from
`experimental/execution/borrowed.rs` line 529. Both archives, manifests and the
exact normalization patch are retained. Nine live files change from the accepted
125-file bulk-memory baseline; no dependency or public route changes.

The independent review found no reproducible correctness or accounting defect.
It executed 20 exact-source growth tests and 14 adversarial selections, replayed
four fresh MIR inventories, audited all sixteen layouts and executed four fresh
representative layouts. All 39 Frozen methods and sixteen checked owner
declarations remain unchanged. Its complete packet, including every nested
command receipt and excluded failed harness attempt, is sealed.

Root replayed producer/reviewer evidence, checked the actual source delta and
executed the normalized live source in three separate empty build contexts:
98 focused all-feature Release tests, 16 Frozen Release tests and Swift-only
Clippy with warnings denied. Cargo artifact identities, exact compressed test
executables, full test lists, output, tools and source digests are retained.
Whitespace checks pass. All owned command groups exited and the 52-file,
95,738,146-byte test scratch was removed after an empty holder check. No native
instance or physical device was used by this integration.

The 10,356 added positive accounting positions preserve all 4,800 memory and
4,324 bulk positions. Logical production/unit headers are 2,074,592/3,212,368
bytes; frame envelopes are 4,452,888/8,115,000 bytes. State remains 128 MiB,
Combined 256 MiB and the ticket maximum 86. These are logical object bounds,
not RSS, stack or mobile performance measurements.

Evidence: [root acceptance](../verification/swift-memory-growth-root-integration/acceptance.json),
[independent review](swift-memory-growth-review.md). Recheck the saved proof with
`python3 -B verification/swift-memory-growth-root-integration/verify.py`; add
`--live` to require the current VM to match this exact checkpoint.
