# Durable capability architecture review

Independent read-only design review by capability_exit (gpt-6.1-sol, xhigh),
2026-10-23. Root then explicitly authorized one correction to the draft. No
production implementation, tests, contracts or previously sealed material evidence
were edited. This is architectural review, not executable qualification.

The initial draft was
`9d4bcd887c67a115f774220e52dd250ac41a9a3ece1e6a52f7e9c9be7722e205`.
The corrected draft is
`f5a8c7bf2ae7f597da56061870a926181ae3a8ecfe877d70033bb0787d37f08b`.
`design-before.md` and `design-after.md` preserve both exact versions. Removing
only the approved terminal-observation addition reproduces the initial hash.

One actionable gap was found and corrected: final retirement does not notify
terminal failure soon enough. The current bridge records failures from wake,
post/ack and cleanup internally and exposes diagnostic status. Its final drain
can remain pending indefinitely while actual exits hang or quarantine pins the
native owner. A coordinator notified only at drain could remain provisional or
healthy after such a failure. This violates activation-v2's recoveryRequired
transition and can allow a health publication without observing terminal state.

The added design requires a fixed non-authority observer registered before the
pump or any worker can run. It synchronously stops admission and latches immutable
checked first-failure facts for the exact attempt generation, then sends one
coalesced counted actor notification. No caller evidence or description-based
classification enters authority. Every await, enable/publication and health
commit-entry boundary checks that latch. If synchronous health I/O already entered,
its actual or uncertain durable outcome cannot be rolled back; observed terminal
failure must prevent a healthy return and retain failure/recovery linkage. The
observer cannot release any owner; retirement still requires updater descriptors,
concrete storage close and exact native drain. The new tests required by the draft
cover delayed didExit after an asynchronous wake failure following earned health,
commit/enable race points and continued seventeenth-owner rejection.

With that correction, the architecture is approved for separately scoped
implementation and qualification:

- Retained healthy evidence is a distinct opaque SPI type. It retains the same
  private verifier context and exact signed/payload/channel/installation bindings,
  waives only documented root time windows after private durable-health checks,
  and cannot convert to an ordinary current-authority artifact. Known keys,
  signatures, role/scope, explicit revocation, schema/resources/grants and payload
  integrity remain required. There is no public coordinator evidence ingress.
  SPI itself is not claimed to attest a healthy filesystem record.
- Candidate identity includes both exact signed documents and sequence, separate
  from canonical artifact identity. Failure/quarantine history remains keyed by
  canonical artifact digest, so greater reassignment cannot reset bad content.
  Healthy records and assignments cannot silently be overwritten by deduplication.
- High-water commits before chunks and never decreases. Async validation retains
  its own generation/cancellation lease; every completion rechecks current state,
  deadline and authority. Commit-entry ordering permits truthful durable/uncertain
  outcomes and rejects claims that cancellation undid synchronous I/O. Generation
  exhaustion is terminal. Cancellation is the explicit control path described by
  the latch rules, not a second ordinary operation queued behind validation.
- The outer process pool counts at most sixteen coordinator/store/attempt owners
  before filesystem or adapters, independent of validator, bridge and Rust quotas.
  Failed init, busy construction, cancellation, deinit and poisoned/hung ownership
  retain that reservation until actual cleanup; sequential fallback cannot overlap
  another adapter group inside one outer slot.
- Concrete adapter ownership transfers exclusively to the bridge cleanup owner.
  The existing host-close Task must also await the actual KV actor close; current
  host.close alone does not close its directory. HTTP request leases remain tied
  to actual URLSession invalidation. One host-close Task and one native-close job
  remain distinct, and the fixed retirement observer is tied to final drain.
- Store opening and synchronous fd operations are isolated off MainActor. New
  state and a narrow private I/O duplicate preserve exact old source/state behavior.
  Full immutable payload admission precedes adapters. Startup is disabled and
  one-shot per selection, effects intent is durable before enable, and real
  process-local milestone/observation evidence alone can earn health.
- The four checked execution resource outcomes map to the frozen deterministic
  codes; native allocation, validation rejection, capacity, API errors, malformed
  reports, cancellation, deadlines, panic/poison and unknown failures do not.
  Any failure after effects intent/open requires recovery, including after health.

Metadata SPI implementation can proceed independently of the later bridge and
coordinator work. Current exports do not yet implement the proposed ownership or
observer integration. New SPI acceptance/preservation, storage fault/reopen,
generation/cancellation/commit, cleanup handoff and signed real-Wasm lifecycle
tests are mandatory before claiming implementation correctness. No device, build,
VM execution, actual health, publication, graph attestation or GA gate is passed by
this review. Root owns subsequent implementation approval, commits and pushes.
