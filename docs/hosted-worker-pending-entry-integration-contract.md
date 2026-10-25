# Pending registry entry integration contract

This coordinates the next isolated entry integration after the Engine correction
has independent acceptance. It does not accept the current Engine candidate,
select deployment, install a schedule or enable a clock/provider. Root must bind
the final accepted Engine and component hashes before assigning implementation.
The original registry, completion-retention and stop-terminal contracts remain
binding; this document does not change their public payloads or limits.

Use the existing `PendingEnv` configuration and fixed registry/audit names.
Extend the operation environment with that same configuration and bindings, and
export the existing registry/audit Durable Object classes from the Worker entry.
Missing or malformed configuration is unavailable. No generated generation,
alternate namespace, unbounded name enumeration or implicit storage recreation.

Preserve the exact HTTP route, ingress authentication, eight application headers,
wire bytes, nonce echo and four-second outer handler bound. Following successful
ingress, derive the full pending identity from the validated request and pinned
generation. Validate its exact canonical bytes and computed operation key/shard.
Register it through the fixed shard with the existing 250 ms wait **before**
calling `OPERATIONS.idFromName` or `get`. Reject capacity, conflict, malformed
receipt, timeout or unavailable registration before operation allocation. Check
the outer elapsed/abort state after every awaited boundary; a late registration
acknowledgement does not authorize a late operation call.

Keep the existing authenticated operation fetch boundary. The operation derives
the same identity again, verifies its own Durable Object ID equals the configured
operation namespace's exact key, and may idempotently register through the same
shard to obtain a receipt for `Engine.commandRegistered`. This extra registration
uses the existing per-call bound and outer budget; it adds no public receipt
header, caller-selected shard, public recovery route or credential. Both sides
validate the complete receipt against the identity, not only a digest or UUID.

Maintain one Ledger and at most one Engine/context per live operation object.
Do not construct a new Engine for every request, which would reset its in-flight
guard. Context initialization must serialize concurrent first calls, validate the
full identity/receipt and operation ID, and never replace an already selected
identity. On restart derive context only from exact retained registration data;
do not synthesize missing authority. Malformed or conflicting retained data stays
unavailable/fenced. Existing migrated rows remain quarantined until an explicitly
validated enrollment path; enrollment cannot clear quarantine or create a row.

Expose only the already specified private `recoverKnown(identity, receipt,
ticket)` and `enrollExisting(identity)` methods. Validate their closed payloads,
generation and exact target ID before Engine dispatch. Recovery receives no
WireRequest, guard, provider URL or command, and never calls `command` or `claim`.
An empty known identity may produce its specified orphan/fence disposition but
cannot create an executable operation. Alarm/restart handling uses the same
retained Engine/context and never invents context from a schedule or wall clock.

The Worker `scheduled` handler addresses only the configured, fixed audit
coordinator and awaits its bounded `runScheduled()` call. Customer fetches and
operation alarms do not substitute for the independent schedule trigger. Preserve
the 16 shard/16 page/512 examined/8 wake/24 second limits and one unresolved
recovery slot. Actual provider schedule installation/delivery remains pending.

Production entry continues to construct the unavailable provider, clock and
object verifier. Tests may compose the already reviewed Engine with finite fake
providers/clocks in owned fixtures; do not add a production configuration switch
that enables synthetic authority. Entry tests must distinguish real production
unavailable behavior from fixture effects and deployed operation.

Integrate the accepted schema-3 Ledger/Engine/registry-context and direct local
imports in one isolated candidate. Frozen Engine packets use `./vendor/` imports;
changing those to live `./` modules requires fresh build and source/compiled
closure verification. Do not claim the old compiled closure is identical after
rewiring. Retain the prior original-controller assertions when adapting fixture
admission to explicit registration; an old empty-ledger direct `command` bypass
is not part of the new contract.

Required actual-workerd controls include pre-allocation registration ordering;
configuration/generation/namespace/ID mismatch; capacity/conflict/timeouts and
late acknowledgements; exact duplicate registration; concurrent first calls and
one in-flight Engine; restart from retained identity; missing/malformed/migrated
rows; private recovery identity-only behavior; audit delivery with no customer
traffic or operation alarm; stale/duplicate wake and ACK; permanent terminal and
MAX fences; command/claim/report rejection; and original positive stop-cleanup
behavior. Run original controller, accepted Engine and registry/audit regressions
with actual SQLite, exact process ownership and cleanup. Preserve all failures,
source hashes, command output and explicit limitations before independent review.
