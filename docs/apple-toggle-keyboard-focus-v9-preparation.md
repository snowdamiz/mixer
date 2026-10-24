# V9 Settings keyboard diagnostic commit point repair

V9 implements the root-selected host-only persistence repair in
`verification/apple-toggle-keyboard-focus-v8-root-review/v9-commit-point-selection.json`
(SHA-256 `cb3fe08781f93cae77c143676544c25c178e751146c8f45043d21875309da795`). The selected
V8 producer seal is `46e2c5a61fcce4137595da36af6d120ef476b2fb5889a1bd8cfb38d70f7a9b0f`;
the failing independent review seal is
`ed10da1e0da527a1771b76b857047044a72db98bb24765ffa6c2a2840589eca4`. Their complete packets,
source and failures remain unchanged and bound by V9's 1,066 input hashes.

The reproduced V8 failure removed the guard, hit `lstat` EIO, entered rollback,
and then hit journal-unlink EIO. The rejected request returned HTTP 400 with live
cursor 19 while the unguarded durable journal replayed cursor 20 and a fresh store
opened. V9 runs that same real loopback HTTP/filesystem sequence with the rollback
unlink EIO armed. It now returns ACK 200 with live cursor 20, exact journal record
20 and offline replay cursor 20. The rollback path never runs, so its armed fault
does not fire. The live store reports retirement uncertainty and refuses valid
new work. A fresh store can open once guard absence is established.

The irrevocable commit point is successful completion of all payload/journal file
fsyncs, exact published-byte and hardlink-identity checks, and the publication
**directory fsync call returning successfully**. The rollback-capable `try` ends
there. A fault raised by the publication-directory call, including an injected
error after its real underlying fsync, remains a failed precommit operation and
retains guarded rollback behavior. The packet does not infer success from intended
bytes or from an operation that reports failure.

Before this boundary, V9 retains the guarded fresh-file transaction: stage and
fsync, publish without overwrite, remove only verified owned publications on
failure, sync rollback, then clear the guard. Successful rollback returns HTTP
400 with unchanged cursor, upload state and journal prefix; the same sequence can
retry. Failed rollback remains terminal, preserves the guard when available,
rejects new work and startup/replay, and supplies no setup credit. The postcommit
retirement API cannot clear a terminal precommit guard. Guard checks recognize
only ENOENT as absence; partial, malformed, empty and dangling-link guards reject
replay.

After the boundary, guard unlink, guard-stat, guard-directory fsync and reporting
errors never remove committed evidence or escape into Session. Session advances
its accepted cursor and the actual inherited HTTP handler returns ACK 200. Guard
retirement runs separately. A present guard, an uncertain stat, or a failed
retirement directory sync sets live `persistenceUncertain` and
`persistenceRetirementPending`, records warnings, prevents valid new transactions,
and disqualifies setup completion even when all Settings evidence is complete.
`resolve_retirement()` positively checks absence and syncs the directory before
clearing those live blocking flags. Previous warnings remain visible.

A present guard still rejects both startup and offline replay, regardless of
complete journal bytes. If guard removal actually happened, later offline replay
may accept the already-ACKed commit once absence is established. The two live
retirement flags can consequently differ from offline replay during unresolved
retirement; tests compare every other protocol/evidence summary field exactly.
The supplementary attempt receipt may record a warning when storage permits,
but it is not a replay poison marker. V9 makes no promise that transient live
retirement uncertainty without a present guard survives restart. It makes no
claim about actual power loss or arbitrary failed-media recovery. The synthetic
guard-resurrection control remains a conservative replay refusal test.

Attempt-outcome and summary/ancillary receipt errors remain visible warnings.
They cannot reject a committed request, replace ACK 200, roll back its journal,
or stop its cursor advance. Reporting-wrapper errors are also contained after
commit. Receipt failures alone do not represent unresolved guard retirement and
do not invent a new durable guard. The live runtime summary exposes retirement
detail, persistence warnings and ancillary failures.

Fresh final verification passed 21 retained V8 Session/Bridge/replay methods and
20 persistence methods containing 68 concrete real loopback HTTP controls. The
original precommit short/partial write, file fsync, publication, directory fsync,
rollback, payload+journal retry, upload-state and terminal controls remain. The
retained suite also checks exact route metadata, integer query counts, switch
geometry/binding/freshness, original timing bounds, unchanged request/event/upload
limits, frozen V6 journal failure, and all six unrun application cases.

Two V8 guard-clear-before-unlink controls deliberately changed from rejected
HTTP 400 and retry to committed ACK 200 with a present guard, live retirement
block and replay/startup refusal. Guard clear now runs after the selected commit
point. They cover both an action journal and a completed upload transaction; the
accepted payload and journal remain intact. Postcommit directory-failure controls
now also require a live block until positive retirement. These stronger live
restrictions coexist with later guard-absent offline replay of the ACKed commit.
`expectation-changes.json` records these policy changes. No precommit expectation
was relaxed.

Additional focused cases cover the exact V8 double fault; guard unlink errors
before/after actual removal; postcommit stat EIO with guard present/absent and
with/without an unlink-reported error; precommit stat EIO; exact publication byte
and identity mismatches; retirement directory fsync errors before/after actual
sync; attempt outcome file/directory errors; summary and supplementary receipt
IO faults; complete-evidence setup disqualification; positive retirement; and
reporting wrappers. The new committed-boundary checks bind the exact journal record,
cursor and journal prefix, check that rollback never ran, and compare exact
protocol/evidence replay wherever guard absence permits replay. New-work probes
use a valid next request and require no accepted state/journal advance.

The first focused development run passed 19 of 20 methods. Its test incorrectly
resent the already accepted sequence while expecting the retirement-block error;
validation correctly rejected the duplicate as `Diagnostic sequence`. The V8
regression already produced ACK 200/live 20/replay 20 without rollback. The probe
was corrected to submit valid next work. Attempt 2 and the final source-bound host
command passed all 20 methods. Both early outputs and all scratch remain retained;
attempt 1 receives no passing credit. Early development source versions were not
separately frozen, so only the final command's exact execution-input hashes support
acceptance of this source tree.

All 43 reused app, oracle, runner/harness and build-metadata files remain exact
V7 copies. The unchanged compiled Swift resolver passed its 71 host-provider
controls, and unchanged compiled shared transports passed 16 and 35 controls.
Their bytes and tools are hash-bound; these executions are macOS host checks, not
native runtime results. The app source closure remains
`f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46`, app archive
`b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393`, runner source
`e0fbb631305e7ec73c52c1d40a950e8b5392da78e53edc046c6459a2e646eaa7`, runner product tree
`004235a284df48a38a7d0a074237a44c603f4eb32bfc0bb063fb94b6e2385835`, and runner archive
`d576682db91277803aa1728c0a8b13e6e66a5a5e278b46ee24e7be8abc60333b`. The runner remains
in its immutable V7 location; nothing was rebuilt.

The final executed source tree digest is
`405f115aba7754ba9b938629e9120a938e735f02a7fe016ab041e11dc74d6f07`, with source revision
context `67d6d0455c64ccb454c2e06e11edbdca2836a1cd`. The environment is Python 3.14.8
(Clang 21.0.0) on macOS 27.0.1 arm64. `host-controls.json` and
`commands/attempt-1/commands.json` record exact argv, working directory, version,
binary/source hashes, elapsed time, exit code, observed counts and stdout/stderr
hashes for every final group. Per-control receipts retain exact journal hashes
and accepted cursors. `command-receipts.json` records the surrounding packet
commands; the seal records its own command and version.

Only V9's owned synthetic scratch was archived, byte-verified and removed. The
archive manifest retains every synthetic attempt and each file's digest, size,
mode and deliberate symlink fixture. Every owned HTTP thread/socket closes in
`send_http`'s `finally` path. No native instance was created, queried or run. No
UI, screenshot, Settings input, physical phone, container, Git, shared tracker,
credential or publication mutation occurred. Physical phones remain disconnected
and deferred. Native keyboard qualification, carrier acceptance and GA remain
false. This packet stops sealed for independent/root review; it authorizes no
native execution.

The read-only sealed host check is:

```sh
python3 -B verification/apple-toggle-keyboard-focus-v9-preparation/run.py verify
```
