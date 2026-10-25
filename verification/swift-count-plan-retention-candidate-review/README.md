# Independent audit of the recorded count-plan rejection

Disposition: accept the sealed finite rejection as accurately recorded. Candidate
correctness, live integration and full-target execution remain unaccepted.

`audit.py` is independent Python/stdlib code. It reads the sealed producer packet,
keeps tar source members in memory, independently reconstructs the exact diffs,
checks every seal member and receipt, derives raw trace/generic/hit/inventory
results, checks failure/oracle source assertions, enumerates finite model input
states, and rehashes the live 132-file closure. It never executes producer code,
Rust or the archived sources. No new dependency is introduced.

Run from the repository root:

```sh
python3 -B verification/swift-count-plan-retention-candidate-review/run-audit.py
```

The wrapper records argv, time, tool executable/hash/version, revision, audit
source hash and exact source snapshot, stdout/stderr and output hashes, producer
seal and before/after live closure. It preserves each invocation separately.
`commands/audit-01` retains the initial 22-pass/one-fail audit: a diagnostic-string
assumption missed rustc's source-line abbreviation. `commands/audit-02` is the
final **23-pass, zero-failure/error** audit. The producer was unchanged.

`audit-results.json` derives the final independent results. Its finite sequence
enumeration hashes describe Python model states, not freshly executed VM states.
The actual Rust oracle, work/cancellation/allocation failures and zero-ledger
controls are reviewed from raw producer output and exact source assertions.

`receipt.json` binds the result-only disposition, input seal, source closure,
exact final audit command and limitations. `seal.json` seals this document, the
review document and all owned artifacts except itself and `seal.sha256`.
Every filename beginning `root-` is excluded so root can add a separate audit
without changing the sealed review. `finalize.py` checks immutable inputs,
receipt/source/output bindings, syntax and whitespace, writes the receipt, then
seals and verifies every member. Do not overwrite this packet during later work.

No native/UI/capture/full-target, frozen hosted harness, publication, credential
or process-discovery action was performed. Native/physical/final gates remain
pending. See the [review](../../docs/swift-count-plan-retention-candidate-review.md).
