# R30 independent source/host review of R24

PASS for the app-private Activity context/reply correction in the frozen R24 packet. No concrete reachable source blocker found. This accepts the reviewed source change and retained host routing controls; Android runtime qualification remains root-owned.

Frozen unsigned APK: `ea9e1bce035a761106fbb7d704b31b77f68fbe667bba611972d46021426bf117`. Review inputs are R24 `REPORT.md`, `minimal.patch`, the three Java afterimages, `ActivityMailbox.swift`, `FieldLogAndroid.swift`, `fieldlog_jni.c`, compilation input hashes, and exact mailbox/JNI control sources and retained outputs. R17 product4 and FieldLogNativeSurface remain outside this changed-source review; their preservation is recorded in R24 artifact controls.

## Findings and acceptance

- Activity identity is an increasing positive Int64 context, distinct from SDK owner UUID. JNISurface carries that context independently of the Activity pumping MainActor. JNI routes activation to the registered receiver; install/revoke additionally require the exact bound context and owner.
- Closing immediately cancels the context's ticket/reply. Serialized work checks cancellation before execution, open checks again after asynchronous setup, and completion checks the live ticket. A delayed close calls singleton teardown only if that context still owns it; releasing the old context cannot revoke the newer bound owner.
- Polling is scoped to both context and request. Wrong-context/request and insufficient-capacity reads preserve the matching reply; successful consumption clears the ticket. Closed-context late completions are discarded. Deferred frame delivery requires the same current context, same presentation object, and an open mailbox context.
- JNI allocation/global-reference registration failures balance the acquired resources. A receiver is retained through SDK revocation and asynchronous repository closure; op3 releases it only after the route is closed and no longer bound. Failed revocation retains ownership and prevents release. This review does not claim recovery from failed native teardown. Successful close removes both the JNI record and mailbox entry; no historical context/tombstone collection accumulates.
- The handoff instrumentation keeps acquired Activities in its try/finally cleanup and explicitly waits for context release on the successful regression path. Exceptional cleanup attempts to finish owned Activities; it is not counted as a successful terminal-cleanup receipt. Partial Swift setup remains associated with its context for ordered close, and teardown failure cannot silently release a bound JNI receiver.
- The complete original R20 onStart positive flow, including Unicode save, repository reopen, fresh Activity, native invalidation and terminal checks, is byte-exact after removing the added regression invocation and PASS prefix. The complete final owner/core/coordinator/renderer cleanup assertion section is byte-exact.

## Evidence and limits

`source_checks.py` directly verifies mapped afterimage hashes against compilation inputs, the frozen APK digest, exact retained R20 code, and both retained control exit/output receipts. Results and tool version are in `source-checks.json`; no compiler rebuild or new controller was used.

Retained `compile-2/mailbox-control.stdout` exercises the actual mailbox and passes isolation, cancellation, late completion, capacity, exactly-once consumption and release. Retained `compile-2/jni-route-control.stdout` exercises the actual adapter with a JNI function-table double and passes old-poller/new-context activation, failed/successful revoke retention, stale release isolation, rejected foreign/closed operations and complete successful-path reference release. These controls are reused evidence, not newly rerun tests or Android receipts.

No device, ADB, UI, signing, native build/run, Git, child, publication, canonical edit, or historical held-namespace access occurred. Writes are confined to this R30 directory. No physical-device, immutable-published-package or GA qualification is implied. Root's concurrent native execution and final adoption remain separate.
