# Private Apple keyboard full-case preparation V3

V3 repairs the workspace-allocation gap found in V2's independent review. It is
source-only preparation for review, with no native compile/run selection. All six
application keyboard cases remain unrun; native acceptance is pending, and carrier
and GA acceptance remain false. Physical phones remain disconnected.

V2 producer seal
`3a17071cc13bada8e47c48d2b739289ac9210ecacb90935e016a1ea4ce5a14d4` and its review
addendum seal
`f574fb107be4bdb79d0a10b433864dcbc3fc005f2c69f63cf06f94826c2e6a60` remain unchanged.
The addendum's 125-file map is the selected current V2 review evidence; it also
retains original review seal
`000fff844e224e9b52c5d042fe19aa29ce86775924a9d13e42bd9cc35c585137`.
`historical-review-selection.json` records that distinction. V1, V2, all failed
observations, and prior review evidence are preserved and bound.

The defect occurred after `mkdtemp` returned but before chmod/stat completed.
There was no full workspace identity in the lifecycle, so the old removal helper
returned early and its cleanup row falsely passed despite the directory remaining.
V3 records the allocator's exact returned path and fixed canonical temporary
parent before resolve, chmod, stat, or receipt writing. The identity remains
explicitly incomplete until the original preparation checks succeed. Cleanup is
registered from successful allocation return, independently of full identity.

`workspace_ownership.py` handles that boundary. Before identity completion it can
only remove the exact allocated empty directory, through its fixed parent's open
directory descriptor and the exact basename. It uses no-follow metadata checks
and `rmdir`; it has no recursive removal, child deletion, or file/symlink unlink
authority. Nonempty directories, regular files, and symlinks are preserved and
produce a failed cleanup row. No inode identity is inferred from allocation.

After full identity completion, the reviewed identity/mode-aware workspace
removal is retained. Both paths then require a positive no-follow ENOENT check
before cleanup can pass. A no-op removal, unavailable absence check, or removal
error cannot produce a passing row. Cleanup uncertainty leaves the absence flag
false; actual absence is not inferred from an intended or apparently successful
operation. The first allocation/reporting exception is retained, all other owned
cleanup operations are attempted, and run success remains false after the primary
failure even when all resources are successfully removed.

`v3-runtime.delta.diff` shows the small orchestration change. The explicit new
helper is also selected by the transitive origin guard. The prior reporting and
import repairs remain intact. All 57 prior host controls are retained; the full
seven-method runner, original six app method/helper block, actual Settings path
and measured JSON requirement, V9 Session/persistence, strict oracle, request/
upload/deadline budgets, native command arguments and ownership checks, and app
archives remain unchanged. The runner source-tree digest remains
`946ab559edadd5352912d5747629256a6287d9ca892d5aad0fbd0a7ce4d81e2c`.
No app or platform engine source was changed or rebuilt.

The final host matrix passed **69 methods**: the previous 57 plus 12 new actual
composed allocation controls. New controls reproduce the exact review chmod
fault, stat and resolve faults, identity-report failure, failed/no-op narrow
removal, unavailable post-removal absence proof, a no-op verified removal,
nonempty/file/symlink replacements, and an already-absent allocation. They preserve
the first exception object, check all five cleanup outcomes, prove real server/
thread and workspace absence where cleanup succeeds, and record failed cleanup
before narrowly recovering owned synthetic fixtures. Protected fixture contents
and modes remain intact. No unverified allocated path is recursively removed.

The first allocation test attempt passed ten controls and failed two assertions:
a test's intended one-shot identity-report fault also affected the later simulator
receipt. Those cleanup failures were correctly reported. The test was narrowed
to the intended first receipt; existing persistent-reporting controls remain.
Its raw failure output is retained. All tests use synthetic host data, real local
loopback/thread cleanup, and mocked native/process boundaries; they provide no
native input or device pass.

The final nine HTTP scenarios make 233 real synthetic loopback requests. The
closed runtime selection contains 22 source files and three case tables; actual
normal/duplicate loading binds 21 loaded sources plus four data reads (the three
case tables and selection manifest). The preserved replay helper is selected but
not loaded by normal composition. Per-request validation remains limited to this
closed runtime selection. All 2,537 input bindings, tool/Python hashes, commands,
source digest, elapsed times, output hashes, and exit statuses are recorded.
Only the inherited revision label is reused as metadata; no Git query occurred.
Owned synthetic scratch was archived with byte/mode verification and removed.
No compiler, simulator query/boot, UI, physical phone, or other project's data or
process was addressed.

Bounded review entrypoints are `private-contract.json`, `v3-runtime.delta.diff`,
`workspace_ownership.py`, `orchestration.py`, `test_v3.py`, `runtime-selection.json`,
`host-controls.json`, `runtime-import-bindings.json`, `provenance.json`, and the
archive manifest. Complete sealed verification remains read-only:

```sh
python3 -B verification/apple-toggle-keyboard-full-case-preparation-v3/run.py verify
python3 -B verification/apple-toggle-keyboard-full-case-preparation-v3/verify_isolated.py
```

The second command forbids process creation and execution of every selected
runtime source. `compile-proposal.json` and `run-proposal.json` remain separate,
unselected proposals. A future generic runner build and independently/root
reviewed post-build execution adapter must bind fresh runner/tool/product
receipts before native execution. The current CLI exposes verification only.
