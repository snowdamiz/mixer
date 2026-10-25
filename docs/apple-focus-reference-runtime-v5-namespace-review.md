# Independent host review of the V5 namespace correction

The correction is **accepted at source and host-packaging scope** for V5-001.
There is no actionable defect in the three prefix changes or the new immutable
product staging wrapper. Root must separately make any fresh native selection;
this review does not authorize or execute it.

The reviewed producer handoff is
`bfc528c7786e681f964e93e9f022bae13dc9dd0ebd8b9f343f44f1834004d631`.
All 36 named members, their modes, sizes and SHA-256 values, and the member-tree
digest were independently verified before the controls and compared again
afterward. The reviewed correction packet is
`6c57bc5552a4f7e0e21ff1fdd589b270aa98b483f366f78bd88de2e26c0fd7dc`;
the corrected selected runtime archive is
`a526e25ebe8c5ce382a86376afb6076e984c7f92d77c05ae82e7ced54b5f32ad`.

Independent byte comparison found the same 31 selected runtime files as the
original V5 archive. Only `join_support.py` differs: one ASCII `4` becomes `5`
in its workspace-prefix check. The other 30 files, including the importer, are
exact. The packet-local adapter has that same single substitution and remains
the exact suffix of the selected `join_support.py`. The actual retained
`_dispatch` function body matches original V5 `dispatch` exactly except for the
one `native-run-v4-` to `native-run-v5-` output expression. The selection template
is unchanged. Oracle code, selected native product bytes, action sequence,
native command construction, timing contracts, windows and budgets consequently
retain their frozen identities. No broad arithmetic tests were rerun.

The new wrapper was read at its archive verification, product staging, dispatch
and cleanup boundaries. It verifies the correction packet and 13 directly bound
original references; it obtains only `product-manifest.json` and `products.tar.gz`
from the bound 18,648,051-byte V5 input archive. Each extracted data member is
checked against that archive's immutable binding. The nested product archive
then undergoes exact inventory, type, mode, byte and digest checks before its 55
files are materialized. Corrected source files come from the bound selected
archive. The wrapper has no live product fallback or compiler invocation, and it
resets its temporary `V1` binding in `finally`. The retained dispatcher and its
selected composition continue to check exact source origins and product bytes.

The independent [review program](../verification/apple-focus-reference-runtime-v5-namespace-review/review.py)
passed **37 focused checks** under Python 3.14.8 in approximately 1.64 seconds,
within its 60-second bound. Its
[receipt](../verification/apple-focus-reference-runtime-v5-namespace-review/receipt.json)
records command, Python executable/version, inherited compile-revision label,
exact source/tree hashes, each assertion, selector/dispatch observations and
cleanup. The executable implementation was loaded from the frozen producer;
only its data/output base was moved to an exact review-owned artifact mirror.
No producer file was written.

Four direct probes called the actual configured selector: selected archive and
packet-local adapter, each with V5 and V4 paths. V5 calls the substituted original
selector once; V4 rejects before that recorder. The actual wrapper and retained
dispatcher staged the unchanged 55 products and corrected sources, imported the
actual selected composition under its byte/origin guards, and reached a recorder
substituted for `h.run`. That recorder called the actual configured selected
adapter. Both dispatch and adapter selected the same `native-run-v5-<UUID>` path,
with the same supplied root selection and selection seal.

Negative controls rejected a changed reviewed packet before staging, a changed
out-of-band selection digest, a changed root packet binding, a changed source
manifest, and a repeated run UUID before composition. The actual selected
verifier rejected a changed source file and a changed native product file;
both review-owned mutations were restored before exact cleanup. The actual
immutable-input guard rejected a changed review-owned input-archive copy.

The producer's existing attempt 2 remains separate evidence: 13/13 controls,
including five retained exact methods, 12 selection attempts and one composition
recorder run. This review did not replay those methods. Attempt 1 remains
preserved with its 20 subtest/method errors, cleanup exception and later bounded
cleanup receipt; its audit-path failure is not erased or counted as a pass.
The original 4,673-member and prior independent 33-member closure checks remain
the root's earlier evidence, referenced by its existing decision; they were not
repeated here.

The [cleanup record](../verification/apple-focus-reference-runtime-v5-namespace-review/dispatch-cleanup.json)
confirms four product-input workspaces and the dispatched product/source scratch
were verified before removal. All independent scratch, including the synthetic
run output, was removed. The producer's 36-member closure and handoff remained
unchanged. Only small synthetic root-selection and observation records remain.
An audit hook confined file reads and writes and denied subprocess/native launch
and socket operations before producer imports. No such operation was attempted.

The compact [handoff](../verification/apple-focus-reference-runtime-v5-namespace-review/handoff.json)
binds this document and the review evidence. Its source/packaging acceptance is
limited to this concrete namespace defect. No native runner, compiler, UI,
screenshot, simulator/device query, service, network/provider action, credential
operation, Git operation, dependency or shared-tracker edit occurred. Excluded
hosted catalog/authority and interrupted outbound-worker implementations were
not read, imported or executed. Physical phones remain disconnected and
deferred. Fresh native evidence, keyboard/carrier completion, immutable published
FieldLog dogfood packages, signing, store, operational qualification and GA
acceptance remain uncredited.

The recorded host-review command was:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-runtime-v5-namespace-review/review.py
```

Verify the frozen review without dispatch or control replay:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-runtime-v5-namespace-review/freeze.py verify
```
