# V8 Settings keyboard diagnostic persistence preparation

V8 repairs the three V7 persistence blockers in a fresh diagnostic packet. Root
selected this source/host work with
`b607b64d146e88d743da05739e341de24d01d3228d53c949f9dc72419c411fa4`, against producer seal
`1332308b51182f2ead68a774f135bc3121e00b7385cbd0337395a90d53175579` and independent seal
`6aacb2434dddd1ab41eecd2bd8f3c54b074322fdf372886adf6d4464452e91f3`. Root accepted the
transaction design direction; implementation acceptance and native selection
still require independent/root review. No native execution is selected here.

The Session validates a private copy and collects one journal intent and any
completed payload in memory. Validation performs no persistence. The V8-only
transaction store creates and fsyncs a guard before publishing evidence, writes
and fsyncs each staged payload and journal, publishes fresh hardlinks without
overwriting files, checks exact file identity/bytes, and fsyncs the publication
directory. The single protocol commit point is verified guard absence after all
those evidence syncs succeed. Only then does the accepted Session cursor advance.
The inherited Bridge source is unchanged.

Any earlier IO failure removes only this attempt's verified owned publications
and fsyncs that removal before clearing the guard. Successful rollback rejects
HTTP 400, leaves the accepted cursor, upload parts and journal prefix unchanged,
and permits the exact same sequence to succeed on retry. Payload and journal are
one request transaction: a failed final-chunk journal cannot leave a payload that
blocks the retry. Staged bytes and attempt outcomes remain retained evidence;
they never authorize accepted replay records.

Failed rollback is terminal uncertainty. Its pre-existing guard remains visible,
the live summary reports `persistenceUncertain`, setup qualification is false,
the cursor stays unchanged, further requests reject with `PersistenceUncertain`,
and both startup and offline replay reject the uncleared guard. Even a complete
journal does not override that guard. Partial, empty, malformed and dangling-link
guards also fail closed. Only ENOENT establishes guard absence; other stat errors
do not become a claim that the guard is absent. There is no automatic recovery
of a terminal transaction and no qualification based on its intended bytes.

An error reported after actual guard unlink is resolved by verifying absence:
the journal and payload were already fsynced, so the committed ACK remains HTTP
200. The subsequent directory sync for guard retirement and attempt-outcome
receipt are ancillary. Their failures remain warnings and cannot reject the
committed request. If guard removal metadata reappears after a crash, replay
conservatively disqualifies the run; the packet does not promise uninterrupted
replay availability across power loss. The host guard-resurrection control is
synthetic, not power-loss testing. As with any local file protocol, permanently
failed/inaccessible storage cannot guarantee recording new failure details; the
existing guard is the fail-closed evidence for unresolved transactions.

The V8 setup-only Bridge owns its ACK after Session commit. A later inherited
`persist_summary` failure is recorded in live `ancillary_failures`, the Bridge's
failure list and a supplementary fsynced file when storage permits. It leaves
HTTP 200 and the committed protocol result intact. If that supplementary write
also fails, live warnings disclose its unavailability; a supplementary receipt
is never represented as durable when its write failed. Runtime summaries expose
transaction uncertainty, persistence warnings and ancillary failures separately.

Fresh final host commands pass 21 retained actual Session/Bridge/replay methods,
10 persistence methods with 49 concrete real loopback HTTP controls, the unchanged
compiled native resolver's 71 host-provider controls, and unchanged shared
transport binaries' 16 and 35 controls. The fault suite performs real short and
partial `os.write` operations, file fsync errors before/after actual fsync,
publication errors before/after actual hardlinks, directory fsync errors, guard
unlink errors before/after actual removal, failed journal/payload rollback,
terminal retries, malformed guards, and ancillary summary plus receipt IO errors.
Recoverable controls compare exact accepted state, journal bytes and replay before
retry; committed controls verify HTTP ACK, cursor, exact replay and warning
visibility. HTTP uses the unchanged inherited handler. All AX/PNG/input data is
synthetic macOS host evidence. Early failed attempts are retained and disclosed
in `attempt-notes.json`; they receive no passing credit.

All 43 reused app, strict oracle, native harness and build metadata files match
V7 byte-for-byte. The app source closure remains
`f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46`, app archive
`b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393`, runner source
`e0fbb631305e7ec73c52c1d40a950e8b5392da78e53edc046c6459a2e646eaa7`, runner product tree
`004235a284df48a38a7d0a074237a44c603f4eb32bfc0bb063fb94b6e2385835` and runner archive
`d576682db91277803aa1728c0a8b13e6e66a5a5e278b46ee24e7be8abc60333b`. Runner build provenance
retains source revision context `c628863f7dc3dc3b694d2949be6176a311cce04c`. Products and archive
are bound in their immutable V7 location; no runner build or product-tree copy was
needed. `input-bindings.json` binds 913 deduplicated selected/historical/tool files.

The unique public switch-child coordinate target, exact route metadata,
integer-only query counts, parent/leaf snapshot checks, geometry, action-to-capture
freshness, original three-second window and all request/event/upload bounds are
unchanged. The 29-second diagnostic, two-second HTTP request, 600-second session,
2,500 requests, 100 events, 32 uploads, 7,000,000 decoded bytes, 3,072-byte chunks,
40 polls, route limits and all-outcome cleanup remain intact. The frozen V6 failed
journal still replays exactly; corrected route credit does not create enabled
or setup evidence. No six application case ran.

All synthetic scratch files from failed and passing attempts are retained in
`host-evidence.tar.gz` with a per-entry manifest. Only the exact owned scratch tree
was removed after byte verification of that archive. No native instance, phone,
UI, screenshot, Settings input, application run, publication, credential change,
shared tracker or Git write occurred in this lane. Physical phones remain
disconnected and deferred. Native keyboard qualification, carrier acceptance and
GA remain false. The packet stops sealed for independent/root review.

Read-only host preflight:

```sh
python3 -B verification/apple-toggle-keyboard-focus-v8-preparation/run.py verify
```
