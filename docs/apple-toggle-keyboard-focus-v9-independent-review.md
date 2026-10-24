# V9 diagnostic persistence independent review

The selected V9 **host diagnostic persistence contract is accepted**. Independent
controls found no remaining commit/ACK/cursor/replay mismatch within the reviewed
scope. This accepts no native execution, keyboard qualification, application
case, carrier, or GA gate.

The exact producer seal is
`a9f7f3843bd8cfbd2f751f70d2a0b02e503166129ab98637d3602bba2eb4c0f5`.
The selecting root contract is
`cb3fe08781f93cae77c143676544c25c178e751146c8f45043d21875309da795`.
Every selected producer file and inherited input binding was independently
rehashed, the producer's read-only preflight passed, and all 43 immutable V7
app, oracle, harness, and build-metadata copies matched. The packet records
1,168 input bindings after adding review bindings for inherited imports.

The review executed 72 independent concrete controls through **1,546 real
loopback HTTP requests**, including synthetic setup requests. Its input generator
is adapted from the V8 independent review, with no producer fixtures or producer
test assertions used for these controls. The matrix first passed 60 controls;
12 focused additions then passed without rerunning the successful matrix.
Commands, exact source snapshots, Python executable hash/version, platform,
stdout/stderr hashes and exit codes are retained under the review's `commands/`.

The actual endpoint is the unchanged
`apple-toggle-pan-origin-correction/bridge.py::server_for` handler. It invokes
V9 `DiagnosticBridge.request`, then `Session.request`, then
`TransactionStore.commit`. Session only installs its validated draft after
commit returns. The handler serializes that result and emits HTTP 200.
`inventory.json` records actual method definitions, source hashes, and class MRO;
the tests run this wiring, rather than a simulated handler or persistence model.
The loaded producer-source map digest is
`c19ff5a9be1bc83fdd80a75f8c2d887600140e7eed12e33b1a2144c57f4945a7`.

The exact V8 fault was independently exercised: real guard unlink, one guard
`lstat` EIO, and an armed rollback-journal unlink EIO. V9 returned ACK 200,
advanced the live cursor from 19 to 20, preserved exact journal record 20 and its
prefix, and replayed cursor 20. The rollback trap never fired. Guard absence was
established after the transient error; a fresh store opened. The original live
store remained uncertain and refused valid next work until positive retirement.
After that retirement, the same valid next request succeeded. The compact
`old-v8-fault-result.json` retains those results and the exact operation trace.

Both action-only and payload-plus-journal transactions were tested against
postcommit guard unlink errors before and after actual removal, no-op unlink,
guard stat EIO with the guard present and absent, reported unlink error combined
with stat EIO, and retirement directory fsync errors before and after actual
fsync. They retained ACK 200, exact committed journals, cursor advancement, and
no rollback. Present guards refused replay and startup. Unresolved live
retirement blocked a valid next transaction without accepted state or journal
advance; positive absence and directory fsync resolved the block. Receipt
file/partial-write/fsync and directory-fsync failures, reporting-wrapper errors,
and summary plus supplementary-receipt failures could not reject the commit.
Additional controls faulted the actual inherited summary writer's file fsync,
replace, and directory fsync before and after the real operation.

Precommit real partial writes, file fsync errors, publication failures, and
publication-directory fsync failures retained HTTP 400, unchanged accepted state
and journal prefix, and same-sequence retry after recoverable rollback. A raised
error after the underlying publication-directory fsync remains precommit because
the call reported failure. Terminal rollback-journal failure retained the guard,
blocked replay/startup, and could not be cleared by the postcommit retirement
API. Exact publication-byte and hardlink-identity mismatches rejected and rolled
back before retry. Empty, partial, complete, and dangling-symlink guards all
refused replay/startup and valid new work.

Two fully populated synthetic Settings sessions proved that unresolved retirement
disqualifies live setup credit even when all expected evidence and completion
markers are present. When the guard is actually absent, later offline replay may
accept the already ACKed journal and recover setup credit. The review does not
claim a transient live warning survives restart without persistent evidence.
These are injected filesystem/HTTP controls, not power-loss or failed-media
recovery qualification.

There are two provenance limitations. Seven transitively imported inherited
source files and three import-time case-data files were outside the producer's
1,066 inherited input bindings. The review explicitly binds their observed bytes
in `review-inputs.json`, `inventory.json`, and
`runtime-import-data-bindings.json`; it does not relabel them producer-sealed.
No application case used those imported native oracles. Also, V9's seal reports
revision context `67d6d0455c64ccb454c2e06e11edbdca2836a1cd`, while its read-only
preflight reports the reused V7 context
`c628863f7dc3dc3b694d2949be6176a311cce04c`. Both are retained as metadata labels;
file hashes, rather than an inferred Git state, bind this review. No Git query
was performed.

Attempt 1 failed only the reviewer's initial inventory assertion that every
recursive import was already producer-bound; it stopped before HTTP tests and
gets no passing credit. Its exact sources and failure output remain retained.
Attempt 2 corrected inventory scope by adding explicit review bindings and
passed the first matrix. Attempt 3 ran only the 12 added controls. Attempt 4
traced data reads during a fresh import. `attempt-notes.json` records all changes;
there was no unchanged test retry.

Packaging attempt 1 caught a reviewer manifest-mode comparison error before any
scratch cleanup. Raw `gettarinfo` modes for hardlinked files included file-type
bits, whereas tar headers preserve permission bits. The failed archive,
manifest, source, and logs remain in `packaging-failures/attempt-1`. Packaging
was corrected to normalize permission bits; no HTTP tests were repeated.

The producer's sealed 21 Session methods, 20 persistence methods with 68 HTTP
controls, 71 Swift resolver controls, and 16/35 transport controls were verified
as retained evidence, not independently rerun. The app and runner were not
rebuilt. The environment was Python 3.14.8, Clang 21.0.0, macOS 27.0.1 arm64.
Only this lane's synthetic scratch was archived, byte/link verified, and removed.
Every HTTP request closed its client and server and joined its request thread
with a three-second bound. No native instances, UI, screenshots, phones,
containers, other projects' data/processes, Git state, shared trackers,
credentials, or production publication were touched. Physical phones remain
disconnected and deferred.

Verify the sealed review without executing HTTP/native tests:

```sh
python3 -B verification/apple-toggle-keyboard-focus-v9-independent-review/seal_review.py check
```
