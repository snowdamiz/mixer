# Independent bridge review preparation

Historical preparation notes. Final results and current case counts are in
`README.md`; `preparation.json` intentionally preserves the pre-execution state.
Statements below about pending/unqualified work describe that earlier stage.

This is review preparation, not a bridge qualification receipt. Production and
the accepted design are read-only in this lane. The implementation owners must
supply an immutable Swift source candidate and source-bound single native archive
before final compilation/execution. No early commit, device operation, credential
or trust change, production publication or push is authorized in this lane.

Inspection used the accepted `docs/experimental-capability-bridge-design.md`, the
committed native C header/API and shared registry, current SDK host/installed
adapter/lease implementation, generated guest transport codec, concrete store and
legacy wrapper. No blocking safety/liveness contradiction is currently identified
in the design. The following implementation obligations are concrete review
targets; passing earlier C/SDK tests cannot establish them for Swift composition.

| Boundary | Required observation and adversarial case |
| --- | --- |
| Before submit returns | Register entry before await; stage both callbacks as tentative facts until submit returns accepted. A throw accepts no observer. Exercise concrete policy denial, where delivery and exit are synchronous inside host acceptance, plus labelled derived scheduling hooks. |
| Result versus exit | Process result/post decision before actual-exit acknowledgement. Inject exit-first and simultaneous events in review-derived copies; normal concrete storage flow remains primary. An absent result reaches C expiry before acknowledgement. |
| Close and deinit | Independently retained exit owner preserves immutable handle/generation. Latch close synchronously before late take registration; late never-submitted work acknowledges only its explicit no-I/O exit. Retain accepted observers after public owner disappears. |
| Issued unused ID | Store reservation before another await, dispose on every nonaccepted path, and keep its worker until cleanup returns. Strict envelope encode failure after valid arguments stops the whole attempt after cleanup. |
| Accepted cancellation | A stale cancellation after observed exit/host slot release does not undo acceptance or permit a no-I/O relabel. Unexplained cancellation failure closes admission while retaining observer ownership. |
| Host release lag | C reuse after exit can precede host actor slot release. One reservation attempt fails unavailable without spin/retry. Accepted host actor release is not exposed as a synchronous cleanup-complete fact. |
| Data/tasks/queues | Fixed eight mappings, one ordinary/memory command, at most one worker per entry and one close task. Callbacks copy bounded bytes/set fields/signal only. Phase changes release old payloads; measure transient conversion overlap separately. |
| Deadlines | Sample Swift before each C remaining query, carry the minimum absolute instant through host actor admission, and do not renew decoded HTTP timeout or round zero up. Delayed C query, decode, actor queue and resume are separate cases. |
| Wake fairness | Four-turn/8ms shared scheduling budget includes ordinary turns and conversions. Keep round-robin cursor and one ready hint; didInvoke0 parks only after authoritative None/no pending decision. Busy yields, and a nonconsuming ready guest cannot spin or starve another session. |
| Registry/link | Native archive is built from pinned dependency and linked exactly once under distinct static name. Audit actual link command/symbol/archive/header bindings; do not co-link MixerRuntime/default archive. Preserve legacy independent receipts. |
| Construction permit | Synchronous prepare acquires one of sixteen permits before queuing/capturing a module for off-UI create. Pending/live/draining share the bound. Abandonment releases only unused ownership; one-shot/double-create must not release a transferred permit. Cancel before start dispatches nothing; cancel racing C creation retains the worker and late native handle through close/cleanup before permit release. |

The original fixture builder produces eight real Wasm probes, including a storage sequence. Startup
attempts a put while disabled and polls the unavailable wrapper into guest memory.
After explicit development enable, `run` enqueues put(binary), get, delete,
get(missing), put(empty), get(empty), delete. The fixed wake polls and records each
exact wrapper and advances the next step. Public test code checks stage/memory and
the concrete private store; it never handles a token or injects a completion.
`enqueueThenTrap` and `enqueueThenSpin` must leave their concrete key absent.
Separate malformed-object and never-consumed-ready fixtures cover local rejection
and scheduler behavior. `manifest.json` generated with the fixture bytes defines
the fixed memory locations; a Node validation run only proves Wasm syntax.

`Package.swift` now defines a public consumer test target with seven original
XCTest cases in `PublicHarness/PublicBridgeReviewTests.swift` and an exact copied
fixture resource set. It imports public SDK/bridge products only, with no
MixerRuntime or internal C target dependency. The cases cover the concrete
seven-stage binary/missing/empty/delete flow, disabled startup, policy denial with
callbacks synchronous inside actual host acceptance, four malformed argument
objects, seventeen concurrent synchronous prepare calls, unused abandonment,
cancel-before-create/idempotence, repeated create preserving its returned session,
and unsuccessful trap/spin originating turns. This source is authored but remains
uncompiled/unqualified until the immutable candidate is supplied. Host test runs
must remain sequential within one process so the deliberately global capacity
oracle is not contaminated by unrelated parallel suites.

Additional pending public cases: two independent stores with equal guest token
bits; stop/deinit and retained native capacity; one command slot; monotonic timeout;
ready fairness/parking. Deterministic internal timing,
malformed native metadata, injected post allocation failure and adapter exit
ordering use labelled derived copies/hooks only, with source hashes and a
separate result category. They do not replace concrete storage/network evidence.

An early read-only prototype pass found three concrete implementation issues:
callbacks prematurely established acceptance and could permit old-worker reuse;
new calls published by wake could park after didInvoke0 without a drain hint;
native-close failure could release the construction permit with a counted
quarantined slot. The implementer reports staging callbacks, gating acknowledgement
on worker completion, retaining a drain hint until take None and retaining failed
close/quarantine ownership. Root independently observed the same defects. These
are not yet execution-verified corrections. Root also required cutoff checks
between each transfer/codec/turn phase; the implementation is staging phases.
The worker-tail review requires payload-owning inner async functions to return
before a tiny outer tail publishes completion, with only coalesced signal after
that boundary and later cancellation performed by the pump. This is a logical
worker/payload ownership transition, not Swift runtime Task destruction.

The follow-up one-time admission latch and close-before-worker-input ownership
gaps were also sent to the owner and are reported corrected. Root identified
closed cleanup parking when the budget expired before never-started work could
be classified; a dedicated eight-take/two-exhausted-scan case is authored. Root's
metadata failure finding is covered by separate local report fault cases.
The new envelope waiter is tested with close both before its publication and
before its resumption. All remain unqualified until frozen-candidate execution.

`InternalHarness/README.md` documents ten labelled derived scheduling cases and
one separately filtered metadata-fault case. `make-derived-review.py` refuses
production paths, copies only exact manifest-checked frozen SDK/bridge inputs and
records changed source/test bytes. Main public tests never use these controls.

The strong-retention internal scheduling test is distinct from all public cases:
pause the real concrete storage path with the existing SDK-only afterInvocation
gate, close/drop the public session, retain fifteen unused constructions, and
verify no seventeenth admission until the gate releases and actual exit/ack drains.
It may use SDK @testable scheduling hooks in a separate labelled review target;
it must never replace the concrete adapter or count injected completion as a
primary successful storage flow. Dispatch/pump ownership must retain the exit
owner after the final host observer removes itself.

Successful normal-trust HTTPS remains dependent on an explicitly provisioned
fixture. This lane will neither change trust stores nor add a production bypass.
Bounded stress/TSan, requested allocations and cross-builds will retain their exact
scope; no hard real-time I/O prevention, rollback, global process resource cap,
OS destruction, recoverable OOM, physical mobile or release/GA proof is inferred.
