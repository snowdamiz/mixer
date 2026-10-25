# Independent bounded review of a rejected finite candidate

The review accepts the recorded rejection on retained evidence. It grants no
correctness, actual-target or release acceptance. See the
[review report](../../docs/swift-cost-retention-candidate-review.md).

`audit.py` is a standalone read-only Python standard-library executable. From
the repository root, run:

```sh
python3 verification/swift-cost-retention-candidate-review/audit.py
```

It checks the assigned packet seal, every sealed member, three complete source
archives, the current ordinary live 132-file closure, historical command/output
bindings, six raw trace pairs, method counts, generic stdout parity and scratch
absence/cleanup arithmetic. It emits JSON to stdout and does not write files,
extract archives, import packet code or execute any historical command. A changed
live closure makes the audit fail rather than silently accepting a newer tree.

`command.json`, `result.json`, `stdout.json` and `stderr` retain the successful
audit execution, exact command, tool hashes, all input hashes and output hashes.
The `attempt-1-*` files preserve the initial audit-check failure and original
audit source. Its only error was counting 67 child directories without the
separately recorded root; the corrected count is 68. No packet file was changed.

`seal.json` binds the review report and all review receipt files, excluding only
the seal and its sidecar. `seal.sha256` is the SHA-256 of the exact seal bytes.
