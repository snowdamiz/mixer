# Independent installed capability exit review

Scoped independent review passed for committed source
`3d4b88dd2eea3e26ce7ea87b3f78cb11631b410a`. No concrete issue remains unresolved
in the additive installed-adapter cleanup/host-slot lifecycle reviewed here.
No production implementation or earlier Android-review file was modified.

The reviewer exported `sdk/`, `capabilities/` and the approved proposal directly
from Git before execution. `freeze.json` and `frozen-source.sha256` pin all 105
exported files. The 49 qualified source entries and canonical digest
`24e6c520347a54fd31e74fdc6db185da6982f412e6068d078e9a64686da4dcc7`
match the committed implementation evidence. All frozen file hashes still match
after execution.

| Independently executed check | Result |
| --- | --- |
| Existing capability suite, debug | 37 passed |
| Existing capability suite, release | 37 passed |
| Existing HTTP/exit suites, ThreadSanitizer | 24 passed |
| Original independent suite, debug/release/ThreadSanitizer | 6 passed in each configuration |
| Public adapter-substitution compilation | Rejected arbitrary HTTP and storage conformers for the intended concrete-type errors |
| Owned native-identity generator | `--check` passed |
| Immutable evidence audit | 49 source files and 12 recorded command-log hashes match; schema/codec/dispatch bytes unchanged |

The independent tests exercise reentrant exit callbacks and 4,096 concurrent
fact reports in each join ordering, legacy observed-API rejection without consuming
a reservation, host deallocation before invocation, cancellation/close after a
storage write has committed, ordinary and observed HTTP submission while native
invalidation is held, and host deallocation after adapter cleanup but before
invocation returns. They assert one exit, separate terminal delivery, retained
host capacity until the join, zero native counter before the observer, and continued
shared-store usability. The negative compile is intentional; its complete compiler
output is retained. There were no accidental failing harness attempts.

Static review confirms that the installed value stores only concrete owned
`URLSessionHTTPTransport` and `AppPrivateKeyValueStore` instances. Native HTTP
observation cannot be supplied through the public legacy closure/service surface.
The private lease records both facts under one short lock, removes its observer
before calling it, and invokes callbacks after unlocking. The worker/exchange
retains that lease independently of a weak host relay; request identity plus private
lease identity guard slot reuse. Storage reports only after its synchronous actor
method has completed operation-local cleanup. HTTP reports only on preflight with
no session or after actual delegate invalidation releases its native counter.

`receipt.json` records exact commands, host tool versions, output hashes and scope.
`evidence-audit.json` audits the original iOS/Android/WASI compile and Swift/Java
codec receipts rather than repeating those cross-builds. `IndependentExitProbe.swift`
and `ProbePackage.swift` are the handwritten test sources. To reproduce, run
`python3 verification/capability-exit-review/freeze.py` in a fresh checkout, copy
those two files to `.local/probe/Tests/IndependentExitProbe/IndependentExitProbe.swift`
and `.local/probe/Package.swift` respectively, and run the commands recorded in
`receipt.json`. The negative package similarly uses `NegativePackage.swift` and
`UntrustedInjection.swift`. Run `audit.py` to check committed evidence.

URLProtocol fixtures control native ordering and bypass real TLS/network parsing.
ThreadSanitizer instruments owned code; system frameworks remain opaque. This is
an adapter cleanup boundary and per-host capacity proof, not a process-wide cap,
proof of kernel socket destruction/RSS reclamation, Swift stack unwinding, durable
mutation rollback, guest/C/mailbox integration, activation, or OTA qualification.
The installed value alone does not bind release identity/configuration/grants.
Physical iOS/Android lifecycle/trust/packaging, immutable published-package FieldLog
use, signing, stores and accountable GA gates remain pending. Phones stayed
disconnected and no device query, install, signing, customer message, publication,
credential change or new dependency was attempted. Root owns any push.
