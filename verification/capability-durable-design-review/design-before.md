# Capability durable updater API proposal

Draft for root review, 2026-10-23. Design only: no implementation, authority,
contract revision or qualification is added. Authoring: gpt-6.1-sol, xhigh.

Use the frozen activation-v2, release-v3, runtime-identity-v2 and execution-v1
contracts. The execution contract remains SHA256
`898ea22b93a5b0dcd94c3b54f7cc97c41a259cd2285cbacd54bf0bd52ba48c97`,
wire `052ebe9fbdc20a41307332086767e7903680bc83ba273c696edf9187be6b6439`
and native header
`9213c34ebf0f14d14f3319172e83647f704f3a02a60d413b4de990884357b4a6`.
This proposal complements `capability-installed-factory-api-design.md` and the
approved validation/typed-failure design. Validation still returns Void; no new
transferable native validation proof, leaf product or constructor shortcut exists.

## Ownership and the smaller package seam

Keep the entire new updater actor, state models, selections and filesystem wrapper
**internal to the MixerCapabilityActivation target** in `capability-activation`.
Factory, coordinator and updater must be in that same module. The public
`InstalledCapabilityExecution` initializer remains material-only: no store open,
adapter constructor, session, scheduled work or executable selection. Its private
implementation retains one ReleaseVerifierV3 value; internal coordinator/store
initialization copies that value, preserving its reference-identity context.
Never reconstruct another verifier from otherwise equal roots/host DTOs.

The public execution façade accepts that installed value, never an independent
verifier, artifact, retained-evidence object, executable validator, adapter or
selection. Its proposed shape is:

```swift
public final class CapabilityColdStartRuntime: Sendable {
    public static func open(configuration: CapabilityRecoveryConfiguration,
                            execution: InstalledCapabilityExecution) async throws -> Self
    public func beginDownload(signedManifest: Data, signedAssignment: Data) async throws
    public func downloadOffset() async throws -> UInt64
    public func appendDownload(_ bytes: Data, atOffset: UInt64) async throws
    public func finishDownload() async throws
    public func cancelDownload() async throws
    public func start() async throws -> CapabilityActivationSnapshot
    public func reportMilestone(_ installedID: String) async throws
    public func recoverySnapshot() async -> CapabilityRecoverySnapshot
    public func close() async
}
```

A thin nonisolated façade owns bounded ingress/cancellation gates and a private
actor. It rejects busy/closed/oversize input before owned copies or internal Task/
actor-queue captures. The public methods create no unbounded detached jobs. Only
one download/startup mutating operation is admitted per coordinator; diagnostics
and close do not wait for a native validator. Caller-created task/input memory is
not engine-owned queued memory. Native validation retains its existing independent
process limit of two prepared/queued/running/draining operations, and construction
retains its existing sixteen-owner limit.

### Process reservation before any filesystem or adapter owner

Add one process-wide, fixed sixteen-entry coordinator/whole-attempt pool. Acquire
its reservation synchronously in the outer `open` path, before capturing/queuing
configuration or allocating a private store owner. Busy rejects without directory
I/O or adapters. The async `open` then creates an I/O-free private actor and awaits
its isolated `openDirectory` operation. All directory reads/writes/fsync/cleanup
run synchronously on that non-MainActor private actor, never in a synchronous UI
initializer or inherited UI task. There are at most sixteen admitted store actors,
each with one in-flight I/O/mutating operation; no per-call detached I/O fanout.
Constructor failure/cancellation keeps its reservation until opened descriptors
actually close on that actor. A hung filesystem operation retains its reservation.

The same reservation spans idle/download/startup/live/closing and failed-initializer
cleanup. It is acquired **before concrete adapters are initialized** and is owned
by one reference-backed `AttemptOwner`, not by a temporary start Task or façade.
It transfers to a counted closing owner when the façade disappears. It cannot be
released because close was requested, a native constructor returned busy, or a
callback was delivered. Release requires updater I/O/fds closed, concrete adapter
close completed, and any created native owner actually drained. Poison/uncertain
native ownership pins it. A candidate and fallback reuse the same reservation
sequentially; old adapter/native ownership must be fully retired before the next
adapter group is initialized. No overlapping second attempt is hidden in one slot.

This outer sixteen is a stricter resource-owner admission boundary, **not** an
extension or replacement of the bridge's sixteen construction/session permits or
the Rust shared sixteen-family registry. Legacy/development owners can make native
construction busy after the outer slot was acquired. On prepare/create busy or
ordinary constructor failure, the existing AttemptOwner retains all partially
initialized adapters and performs one coalesced cleanup; callers cannot retry by
allocating another uncounted adapter group. A retained/quarantined construction
failure never reports the outer slot free. All sixteen outer entries may remain
unavailable indefinitely. Validator's two process permits stay independent.

A small reviewed lifecycle integration is required rather than assuming current
`session.close()` proves adapter cleanup. Current bridge `NativeExitOwner` already
has the correct final `status.drained` predicate: native close succeeded, host
close completed, no command, every actual ticket acknowledged and no worker. Its
host-close Task currently closes CapabilityHost; that does **not** close the
factory's AppPrivateKeyValueStore directory. Proposed private/SPI ownership handoff:
an owned concrete adapter group (only the fixed HTTP transport and optional KV
actor, no arbitrary service/validator closure) transfers from AttemptOwner to the
bridge close owner upon construction. Its one existing host-close Task first
closes the host and then awaits the concrete storage actor's close. HTTP exchanges
remain owned through their existing actual invalidation/didExit leases. Native
close remains the one separate native-close dispatch job.

One fixed non-authority retirement signal, registered before ownership transfer,
releases the AttemptOwner only after `status.drained` and the store's own close.
It performs an O(1) latch/pool update and schedules no Task. This must be hooked to
the existing final drain transition, not terminal delivery or close0. Before a
bridge owner exists, AttemptOwner uses the same single host-cleanup Task to close
its adapter group; there is no native-close job unless a handle was actually
created. The handoff is exclusive, preventing two host-close Tasks for one group.
A registration/constructor unwind cannot lose the group or reservation. This is a
proposed separately reviewed bridge lifecycle addition, not an existing API or a
transferable execution proof. If actual retirement cannot be observed, retain the
reservation; do not poll/retry busy in a loop or invent a successful drain.

No nested cleanup task is added around the bridge's existing host-close Task.
Tests must gate failed init after KV open, bridge-busy, create cancellation/native
failure, host close, KV close, last didExit/ack, native close and quarantine, proving
that the seventeenth outer owner is rejected until real retirement. Validate that
one host-close Task and one native-close job remain the per-owner maxima.

`CapabilityRecoveryConfiguration` contains trusted native directory/channel/
installation, failure threshold1..10, nonempty installed milestone IDs<=16,
observation1..3600 seconds and disk reserve. It has no validator callback or guest-
selected policy. Use production wall/monotonic clocks sampled internally; controlled
clocks/faults and worker gates are internal test injection. Health truth remains a
trusted embedding responsibility; guest bytes and capability completions cannot
report milestones. This API is not proof that real UI/FieldLog milestones exist.

Duplicate the small independently owned DurableDirectory implementation and flock
C shim narrowly into this new package, with a distinct C symbol such as
`mixer_capability_update_flock`. Preserve its fd-relative nofollow regular-file/
hardlink checks, bounded reads/appends, lock ownership, fsync/rename/directory-sync
order, exclusive state temporaries and bounded owned-file pruning. Do not export
raw descriptors or a public filesystem backend. Do not alter old
`ColdStartUpdater.swift`, `ColdStartModels.swift`, `DurableDirectory.swift`, C shim,
old products or state encoding in this slice. Duplication here deliberately avoids
an unqualified shared-I/O refactor; a later common primitive requires separate
preservation evidence. This introduces no third-party runtime dependency.

Only two narrow metadata operations need additions inside MixerUpdates. Propose
an implementation SPI imported solely by the private updater:

```swift
@_spi(CapabilityDurableV3) import MixerUpdates
// On the same ReleaseVerifierV3 value, implemented beside its private context:
// _authorizeOfferV3(exactManifest:exactAssignment:channel:installation:lastSequence:now:)
//     -> OfferEvidenceV3
// _verifyRetainedHealthySnapshotV3(exactManifest:exactAssignment:payload:
//     channel:installation:storedSequence:acceptedSequence:)
//     -> RetainedHealthyEvidenceV3
// _revalidateRetainedHealthyV3(_:payload:) -> RetainedHealthyEvidenceV3
```

Each method bounds input before taking owned snapshots. Offer evidence is distinct
from payload-verified artifacts: it exposes only header-bound digest, sequence,
length/hash and its private context. Retained evidence is another distinct opaque
SPI type, with no public initializer/decoder and **no conversion or getter returning
public VerifiedArtifactV3**. It privately binds the same context, exact signed
snapshots, payload hash/length, signed limits/grants, channel and installation.
Its read-only SPI metadata permits the installed private factory to derive policy
from the whole enclosing evidence. Ordinary verify/revalidateArtifact and
verifyAssignment remain current-authority strict and cannot accept this type.
Fresh selections use the existing VerifiedArtifactV3; retained selections use the
distinct evidence case. Neither evidence type means executable admission.

SPI name hiding is not security. Another app module can explicitly import SPI
and call it on its own verifier; it can already call development native APIs.
Safety here is the unexposed factory verifier/context, private record/selection
constructors, no external evidence ingress, and complete native validation under
the private coordinator. The retained SPI verifies signatures/metadata; it does
**not** prove that its caller actually read a committed healthy record. The only
OTA callsite is the private updater after its durable checks below. Document this
trusted implementation boundary rather than describing SPI evidence as a durable
or execution attestation. Do not expose a public `ignoreExpiry` option, relaxed
verifier constructor, roots-rewriting helper, accepting closure or native result
setter.

These additive helpers are currently missing. They can be implemented beside
VerifierV3's private/fileprivate types without making its context public or changing
old verifier behavior. Ordinary v3 API preservation tests are required. Private
factory construction must handle the fresh/retained sum type without laundering
retained evidence into a fresh artifact. If this SPI trust boundary is not accepted,
stop for a separately reviewed module reorganization; current exports alone cannot
implement retained-expiry semantics safely by passing now0 or rebuilding roots.

Alternatives considered: a public retained-record reader would duplicate native
store parsing in updates and add a second fd/snapshot/epoch ownership seam. A new
native-validation certificate/leaf product would change the approved Void API,
permit retention and authority surface. A validator closure or widened legacy
updater is prohibited. The private updater plus explicit metadata SPI is smaller.

## Durable state and exact identity

Use a new closed native-store layout, `kind:mixer-capability-cold-start-v1` and
`schemaVersion:3`, explicitly separate from the server's schema3. Fresh open may
initialize only a newly created private directory. An existing directory with
missing state, old schema, wrong complete InstalledRuntime/fingerprint, channel or
installation fails without deleting/reinitializing it. Per-runtime storage or an
independently reviewed migration is required. The directory is trusted app-private
storage, not a signed or adversarial same-user immutable filesystem.

Persist at most1MiB metadata, four retained candidate records plus one pending
download, and bounded256-entry failure/quarantine histories. Signed manifest and
assignment are each<=65536 bytes and payload<=4194304. Preserve exact signed input
bytes, not a normalized/re-encoded envelope. All downloaded/stored bytes remain
untrusted until verified. Payload reads produce bounded owned Data; a path never
becomes execution authority. Keep opaque verifier proofs only in memory and mint
fresh context-bound evidence from stored signed bytes on reopen.

Separate the content artifact digest from the **candidate record identity**. A
new greater assignment for an older artifact must not overwrite the exact signed
assignment attached to an existing healthy record. Define candidateID as SHA256
of a domain-separated deterministic-CBOR private record containing artifact digest,
sequence and the SHA256 hashes of both exact raw signed documents. The store's
host/channel/installation identity is additionally mandatory. Health/staged/attempt
pointers refer to candidateID, not just artifactSHA256. Payload files can deduplicate
by verified payload digest; independently rehash an existing destination before
reusing it, and never silently replace a healthy signed record. This is a private
storage identifier, not a change to release-v3's canonical manifest identity.

Keep durable acceptedSequence, pending download, staged candidate, healthy and
previousHealthy exact records, active attempt and bounded diagnostics. Each attempt
has a unique launch ID, source, candidateID, sequence, phase, health-commit binding
and conservative `effectsMayHaveOpened` flag. Retained healthy attempts also get
new durable launch IDs; the old updater's nil-launch retained selection is not
reused. No process-local monotonic clock value proves health after reopening.

## Download and bounded asynchronous admission

1. `beginDownload` checks idle/open/not poisoned, bounded owned signed snapshots,
   strict v3 signatures/scope/host/cohort and sequence>durable acceptedSequence via
   the offer helper. Check deny-history capacity and disk reserve. Atomically
   commit pending exact documents and the new high-water before any payload byte
   is accepted. No await separates final checks from the commit-entry latch and
   synchronous actor I/O. Cancellation, invalid executable content, partial
   download and later failure never lower high-water.
2. Append accepts at most1MiB per admitted call, exact saved offset and signed
   remaining size, with bounded owned copies and preserved disk reserve. Reauthorize
   the pending offer at current time and require pending sequence==acceptedSequence.
   A chunk's storage write/sync failure has uncertain durability: poison this owner
   and require reopen rather than claiming no bytes were appended. Resume verifies
   actual regular-file length; it never resets replay state.
3. Finish reads/rechecks exact immutable payload and signed length/hash, artifact,
   assignment and reservation. Under the actor, allocate one nonwrapping operation
   generation and latch candidateID/sequence/identity/config. Prepare the concrete
   native validator **before** queuing/capturing the worker payload. Busy does not
   stage anything or release the durable sequence. Keep exactly one pending payload
   snapshot in this updater; do not detach additional payload-owning work.
4. Await `ExperimentalCapabilityValidation.validate()->Void` using installed exact
   startup, capability context and min signed/installed limits, including floor to
   exact0..64 memory pages. It performs full uncalled-body/import/wake/start/memory
   admission and no adapter/instance/export. The private code itself connects this
   call to its owned bytes; no transferable success marker or public validator
   argument exists. Construction later revalidates this same tuple.
5. After every await, check updater/coordinator owner identity and generation,
   current operation/candidate/sequence, open/poison and cancellation latch, and
   monotonic cutoff. Resample trusted wall time and reverify current authority for
   fresh staging. A stale worker cannot publish, clear a newer busy flag, or mutate
   durable state. No await lies between final checks and payload publication plus
   staged-state commit. Define an atomic commit-entry latch: cancellation/close
   winning before entry prevents writes; after entry, synchronous filesystem I/O
   cannot be preempted. A transaction may become durable even if cancellation or
   close is requested during it. Retain the operation through completion, report
   its actual/uncertain durable result, and prevent subsequent execution publication
   or enable. Never claim cancellation rolled back an in-flight commit. Charge
   validation and commit elapsed time to the bounded finish operation, using the
   minimum signed/installed startup interval; this is a cooperative discard
   deadline, not preemption or a guest-turn50ms guarantee.
6. Payload rename then metadata commit preserve the existing fsync ordering. Any
   ambiguous rename/state/cleanup error poisons the owner; no staged success is
   returned. Reopen may recover the verified destination using the reserved exact
   offer. A cancelled download commits cancellation first, then cleans up; failures
   require reopen, and acceptedSequence remains unchanged.

An operation lease owns the generation, cancellation latch and prepared validator.
Close/cancel retires the generation synchronously before awaiting cleanup, invokes
validator.cancel synchronously, and never creates a Task per cancellation. Queued/
running validation retains its native permit/input through dequeue/C return even
when retired. A hung worker is not forgotten or counted free. Its completion only
releases its own ownership and cannot reopen the store. The filesystem lock/fds
must not be released while any store I/O still owns them; native validation holds
only bytes, never descriptors. Close stops new operations immediately, then closes
fds once synchronous store operations are out of scope. Define generation exhaustion
as terminal, never wrap/reuse. Clocks moving backward, overflow and foreign errors
are conservative interruptions, not deterministic guest traps.

## Cold start, retained evidence and private one-shot selection

Start captures monotonic began **before** durable selection/read/validation.
The exact selected signed startup limit determines cutoff=began+min(signed,
installed); reject if selection has already consumed it. Record the durable attempt
before construction/startup. Full payload revalidation and native admission precede
selection publication. The private single-use `StartupSelection` contains exact
payload, fresh-or-retained evidence, effective config, store identity, candidateID,
attempt generation and launch ID. A reference-backed consumed latch makes copied
internal values unusable twice. It has no public initializer, Codable conformance,
path-only representation or ingress method; only this coordinator consumes it.

Fresh staged candidates require current root authority. Retained exception applies
only after reading the real committed healthy/previousHealthy record and matching
its candidateID, original signed documents, payload, complete host/channel/
installation, sequence<=acceptedSequence, health binding and nonquarantine status.
Then call the retained SPI on the same factory verifier. Reverify exact signatures,
known key/role/scope, host/resources/schema/grants, assignment binding/cohort and
payload integrity; skip only signing-key time-window checks for these exact stored
records. Do not waive explicit revoked configuration, wrong role/key/scope or
changed roots/identity. Do not apply this mode to a download, staged-but-never-
healthy record, changed assignment, same-artifact replacement record or caller data.
The SPI's retained subtype and private selection retain this provenance.

Recheck the durable record/epoch and deny status after the validator await and
before consumption. No reread of external paths can replace selected owned bytes.
At most one compatible retained-healthy startup is attempted after a candidate
fails before effects; a new fallback began is sampled **before** committing failure
and selecting/validating fallback. Native fallback is an explicit result for the
embedding's actual compiled implementation, never a fabricated healthy guest.
Cleanup that may retain locks/uncertain ownership can keep the coordinator stopping
rather than promise immediate conflicting fallback.

No generic new process can use a previous monotonic observation as current health.
A retained guest reruns disabled startup. After real new observation/milestones it
may reaffirm the exact already-committed health record under retained authority;
it cannot promote new signed bytes via that exception. Fresh candidate health
promotion still requires fresh-authority revalidation at commit.

## Effects, health and recovery

Startup remains effects-disabled. After successful startup, recheck current/open/
cancel/deadline state, publish that startup result privately and durably record
`effectsMayHaveOpened=true` **before** enqueueing enable. This conservative intent
closes the crash window between actual enable and durable recording; true does not
claim that I/O actually occurred. Its uncertain commit prevents enable. Set the
per-attempt in-memory effects latch before the enable call; cancellation/late
enable failure must never reopen a before-effects fallback path. Check the latch
again at the actual worker boundary. Once admission can win, no promise of effect
rollback or zero-I/O race is made. Startup-disabled requests stay unavailable and
non-drainable after enable.

Only the same attempt's successful enable starts its process-local monotonic
observation. The embedding reports actual installed milestones; guest startup,
completion, return value or a rendered test label is never sufficient. Bound names
and accumulation by the installed<=16-ID set. Commit health only after observation,
all required milestones, current generation/open/nonterminal checks and revalidation
of the exact candidate/evidence. The durable health transaction references the
exact signed record. A failed/uncertain transaction never returns healthy; poison,
stop execution and require reopen. Retain active-attempt linkage after earned
health so a later runtime failure cannot evade effects/recovery accounting.

Checked deterministic guest traps increment bounded failure counters whether
before or after effects; the effects latch separately controls recovery behavior.
Unknown cancellation/deadline/panic/quarantine/API/interruption do not become
deterministic app failure. Explicitly map the four typed resource reasons
`.fuel`, `.hostCalls`, `.callDepth` and `.operandStack` to the frozen deterministic
codes `fuel_exhausted`, `host_call_limit`, `call_depth_exceeded` and
`operand_stack_exceeded` **when observed as checked startup/invocation/wake VM
outcomes for this active attempt**. The bridge labels these .resource but that
taxonomy does not change activation-v2. The other frozen deterministic guest
traps, including checked host_abort, also count in those execution operations.
Native allocation, capability payload allocation/identifier exhaustion, session/
validation/construction/command capacity, API errors, cancellation, turn deadline,
malformed reports, panic/poison and unknown outcomes never count. A validation
operation's configured-limit rejection is not a runtime deterministic trap.
Explicit local cancellation/deadline cause takes precedence over its resulting
VM cancelled outcome. Do not broadly classify every .resource or status2 value.
Use the checked typed classifier, not description, substring, status2 alone or
capability operation results. Persist failure/quarantine without dropping
high-water. Failure/quarantine keys remain the canonical artifact digest, so a
new assignment/candidateID cannot reset the same artifact's deny history. A
partial history write poisons rather than resetting.

After effects intent/open, **every terminal failure** stops admission/guest work
and yields recoveryRequired; no automatic live guest replacement or conflicting
native launch. Retain actual host/native exit owners, tickets and counted obligations
through shutdown. Timeout, cancellation, terminal delivery and close are not native
exit. One coalesced host-close Task plus one separate native-close job remain the
bounded cleanup work; hung/poisoned ownership can persist indefinitely. Public
close may stop the façade promptly but must not claim the underlying drain finished.

On next cold open, an incomplete attempt records unknownInterruption, never an
inferred deterministic trap. Preserve prior health, acceptedSequence and possible-
effects diagnostics. A new bounded cold attempt may choose compatible healthy or
native fallback under installed data compatibility rules; prior external effects
may persist. A greater signed sequence can roll back to older compatible content,
but must create a new candidate record, never lower high-water or silently mutate
the existing health record. No live reconcile/clear-recovery override is added in
the first implementation; the embedding must close and reconcile possible I/O
before starting a new process-session owner.

## Implementation order and required evidence

1. Approve this private ownership and the exact new SPI/subtypes. Current v3 exports
   are insufficient for pre-download header authorization and retained expiry; do
   not emulate these with forged artifact tokens or relaxed ordinary verifiers.
2. Qualify the approved bounded Void validator/typed-error/zero-page API; material
   factory stays separately reviewed and material-only until coordinator work.
3. Approve/qualify exclusive adapter-close/drain ownership handoff above, then add
   the two metadata SPI paths and distinct retained type with public compile
   negatives, same-context/foreign-context tests and unchanged ordinary v1/v2/v3
   acceptance. Do not expose context or a current-time artifact conversion.
4. Implement new private I/O/store/state plus façade and full async generation
   tests. Preserve old updater source, exact saved bytes/fixtures and all existing
   fault/recovery acceptance. Do not move old storage code or C products.
5. Compose concrete factory, disabled startup, durable effects intent, real health
   and conservative recovery. Then run signed local real-Wasm integration. Actual
   device/published-package/FieldLog/HTTPS/UI/GA gates remain separate and pending.

Required original tests cover every durability fault point and reopen outcome;
exact sequence reservation before chunks; cancelled/invalid/trapping downloads
retaining high-water; metadata/payload corruption, nofollow/hardlink/offset/disk
bounds; old/wrong identity store nondeletion; exact raw signed bytes and same-artifact
new-assignment record separation. Gate cancellation/close/timeout at each await,
queued/running C and commit boundary; late/foreign generations and wrapping reject;
busy admits no additional copied payload or validator work. Prove no callbacks can
accept unsupported Wasm and no validation result can retarget startup/limits/bytes.

Retained tests must reject expired never-healthy staged/download records, forged
or externally injected evidence, changed signed bytes/assignment, wrong context/
identity/channel/installation, quarantine and corrupt payload; allow only exact
committed compatible healthy records offline. Test constructor/public API negatives,
ordinary verifier expiry still rejecting, and identical DTOs producing foreign
contexts. Test startup cancellation/expiry before enable, kill at every effects-
intent/enable/health step, real installed milestone/monotonic gating, runtime failure
after health, no live fallback after intent, actual exit ownership through close,
and fallback's own selection/validation time budget. No synthetic milestone or
successful test label qualifies current FieldLog health.
