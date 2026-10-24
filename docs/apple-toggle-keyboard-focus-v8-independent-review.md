# V8 Settings keyboard preparation: independent review

The sealed V8 preparation is **not accepted for native selection**. The three V7
failure modes pass their targeted V8 controls in isolation, but a new combined
filesystem failure reproduces the same rejected-request/replay divergence at the
new guard-removal boundary. This is synthetic macOS host evidence; no native,
UI, simulator, phone, container, build, or application case ran in this review.

The reviewed producer seal is
`46e2c5a61fcce4137595da36af6d120ef476b2fb5889a1bd8cfb38d70f7a9b0f`, selected by
`b607b64d146e88d743da05739e341de24d01d3228d53c949f9dc72419c411fa4`. An independent
byte inventory verifies all 110 producer-sealed files, all 913 bound inputs, all
43 immutable V7 copies, and all 69 existing runner product entries. The review
binds 1,024 deduplicated input files, including the canonical Python executable;
any tool symlinks are bound separately to their link text and resolved target.
Read-only producer preflight succeeds with the selected seal. No producer packet,
prior review, root state, shared tracker, or Git state was edited.

**P1 — PERSIST-GUARD-ABSENCE-ROLLBACK: terminal rollback uncertainty can lose its
guard and replay a rejected request.** In `durable_settings.py:148`, `_clear_guard`
actually removes the guard. Its following `unresolved`/`os.lstat` check raises EIO
before it can verify absence. The surrounding exception path then attempts to
roll back publications. The independent probe injects a second EIO before the
actual `rollback-journal` unlink at line 155. The handler returns HTTP 400 with
`PersistenceUncertain`; the live Session remains at sequence 19 and reports
`persistenceUncertain=true`. Its complete journal sequence 20 nevertheless remains,
the guard is absent, and `uncertainty.guardPresent` is false. Actual offline
replay accepts sequence 20, credits `switchAction="tap"`, and reports
`persistenceUncertain=false`. A fresh `TransactionStore` also opens successfully.
The live retry rejects terminally, while the durable/replayed state has already
advanced. The expected refusal is not enforced by an in-memory terminal flag.

`guard-absence-probe.json` retains exact request, before/after state, journal
hashes, error/ACK, replay summary, retry and startup outcomes. The probe uses the
actual unchanged inherited HTTP handler, actual V8 Bridge/Session and actual
replay. It performs a real successful guard unlink and leaves the real published
journal bytes present. It does not replace the persistence or replay algorithm
with a policy model. Two recorded runs reproduce the boundary; both synthetic
working trees and command/source snapshots are retained in the evidence archive.
The partial flow does not establish a setup pass or native qualification.

Six independent host test methods also pass seven bounded controls: complete
initial-off and initial-on synthetic flows; a real post-publication directory
fsync error with exact rollback and same-sequence HTTP 200 retry; an actual partial
journal write during final payload upload with no orphan and successful retry;
an actual ancillary summary file fsync failure that preserves the committed HTTP
200 and durable warning; ordinary failed rollback with its surviving guard,
terminal retry, startup refusal and replay refusal; and exact absence handling.
The absence control propagates EIO, EACCES and ENOTDIR instead of claiming absence,
and rejects a dangling guard link at startup and replay. Those local checks do
not repair the combined boundary above. Test success counts do not include or
outweigh that safety-contract failure.

The repair should define an irrevocable commit boundary before guard retirement.
Root's proposed successful payload/journal publication-directory fsync boundary
is coherent if later guard retirement, stat, summary and receipt failures always
preserve the committed cursor and HTTP 200. A surviving or currently uncertain
guard must remain visible and block further work/qualification until resolved.
If the guard was actually removed and its stat failed transiently, later replay
may accept the already-ACKed commit once absence is established; a live warning
alone cannot promise durable restart refusal. Root has explicitly accepted this
contract direction for a separate fresh repair. This review makes no producer
implementation changes and does not accept that future implementation.

The app/oracle/runner/transport remain exactly V7. App source closure is
`f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46` and archive is
`b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393`. Runner source digest
is `e0fbb631305e7ec73c52c1d40a950e8b5392da78e53edc046c6459a2e646eaa7`, product tree is
`004235a284df48a38a7d0a074237a44c603f4eb32bfc0bb063fb94b6e2385835`, and retained archive
is `d576682db91277803aa1728c0a8b13e6e66a5a5e278b46ee24e7be8abc60333b`. No runner rebuild
or new compiled/native control execution was needed for this failing review.

Commands ran with Python 3.14.8 on the host. Command arguments, versions, source
snapshots/tree digest, outputs and output hashes are retained under `commands/`.
The independent synthetic emitter derives from the prior independent V7 Flow,
with V8 module selection, owned scratch and real HTTP transport; producer fixture
or control scripts were not executed. An initial read-only source lookup's shell
glob error is disclosed in `exploration-notes.json`; it was corrected without
changing producer files. No failed artifact is silently counted as a pass.

All synthetic journal, staged, payload and failure bytes, including the dangling
guard link and both reproduction attempts, are archived in `host-evidence.tar.gz`
with a per-entry manifest. Archive byte/link verification precedes removal of the
exact owned `host-scratch` tree. Every loopback server/client/thread is closed and
joined by its request helper, including failure paths. No other project's process
or data was touched. Native keyboard qualification, carrier acceptance and GA
remain false. The six application keyboard cases remain unrun. Physical phones
remain disconnected and deferred.

Read-only review verification:

```sh
python3 -B verification/apple-toggle-keyboard-focus-v8-independent-review/seal_review.py check
```
