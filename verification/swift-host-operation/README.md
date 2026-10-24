# Frozen private host-operation candidate

Read `../../docs/swift-host-operation-implementation.md` and `receipt.json`.
`candidate-source.tar.gz` is the canonical 128-file VM candidate;
`candidate-source-manifest.json` and `candidate.patch` bind its exact source.
The baseline is accepted normalized growth closure `a0bbe77…`; its own archive
and manifest are retained. Only root can integrate after independent review.

Run `python3 -B verification/swift-host-operation/verify.py` from the repository.
It checks every archived source, exact executable and Cargo artifact, command
output and nested command receipt, final accounting/layout/runtime prerequisites
and the seal. Only the exact root `seal.json` excludes itself. Add
`--live-baseline` only while live VM source is still that baseline.

Production/unit MIR, 16 final paired layouts, six complete library test contexts,
four additional host probes, four Frozen integration runs, negative compiler
probes and Clippy are retained. Earlier source overlays and nine failed command
attempts are historical and excluded from final qualification; the expected
parser-only failure and invalid-borrow compiler rejections are also retained.

This is private host development evidence. G08 absent-cursor diagnostics, full
calls/dispatch/Swift, Ready/public invocation, native joins, immutable published
separate-repository FieldLog, physical phones, release and GA remain pending.
No publication, release signing, customer communication or credential change
occurs. Scratch paths in exact artifact records are historical after cleanup;
their exact executables remain compressed under `artifacts/`.
