# Atomic storage correction contract

Root selects these corrections before the atomic writer can be accepted for
repository implementation. They supplement the frozen
[preflight contract](hosted-atomic-storage-preflight.md) and preserve its original
receipts. The original specimen proves useful transaction, rollback, privilege,
codec and lost-COMMIT-response mechanics; it does not satisfy the complete
validation contract. The independent review's successful reproduction of a gap
is evidence of that gap, not a passing security requirement.

The next candidate remains an isolated synthetic PostgreSQL specimen. It must
correct every item below and preserve all existing positive and fault cases.
No live migration, repository, authorization, HTTP route or provider deployment
is authorized by accepting this document. Root will review the corrected source
and fresh independent evidence before selecting the final implementation seam.

## AS01: preserve numeric input evidence

The product `writer_context_v1.token_expires_at` and
`authentication_completed_at` inputs are **unconstrained numeric**, replacing
the proposed `numeric(20,0)` input typmods. The artifact input's `payload_size`
is also unconstrained numeric. A scale-zero cast can round a fraction before a
function body examines it; checking `trunc(value) = value` afterwards cannot
recover the discarded input. Persisted columns may use a bounded integer
representation only after strict admission.

At routine entry, reject NULL, NaN, either infinity, fractions, negative times
and values outside each exact range. Both identity times are integers in
0..9007199254740991; payload size is an integer in 1..4194304. Keep exact
transaction-local setting equality. Validate the trusted application's integer
inputs too, but do not substitute that check for the database boundary.
Canonical numeric display fields use unsigned decimal strings with no sign,
leading zero except `0`, decimal point, exponent or whitespace. Inspect the
actual installed composite catalog types in tests, not just the DDL text.

## AS02: refresh time at the effect and replay boundaries

Retain fresh policy and time checks after all canonical authorization locks and
the tenant-head lock, before any idempotency lookup. In addition, perform a
fresh database-time and original-deadline check after every later potentially
blocking read and immediately before the first mutation. Construct decision and
recorded timestamps from that final decision clock. Immediately before returning
a cached result, repeat expiry, authentication-completion freshness and deadline
checks after its validation reads.

The predicate remains completion < expiry, DBnow < expiry, completion within
[DBnow-45, DBnow+30], and the original SQL/monotonic deadlines unextended. After
all mutations, validate fresh time and deadline before returning success so a
wait during DML cannot preserve effects after the operation becomes invalid;
failure rolls the entire transaction back. The outer application still checks
its original transaction context before completion. This does not promise that
an already-sent COMMIT cannot finish just after expiry or that disconnect proves
rollback. Preserve the real lost-COMMIT-response test and fresh authorized retry.

Tests must observe the actual database wait, advance the independent clock to
the exact expiry or completion-age boundary, release the wait and assert no
new committed artifact/event/idempotency/head change. Cover late reads, cached
replay validation, and DML where an applicable lock can be held. Retain an
unexpired success control. Synthetic fault/clock tables remain test-only.

## AS03: validate cached result and event linkage

A matching principal/action/target/request hash is necessary, but insufficient
to return a stored response. Require status 201 or 200, nonempty bounded exact
response bytes, an integral bounded event ID, and a same-tenant event that
matches the stored principal, action, target and request hash. Fully validate
that event's typed display, CBOR, hash and predecessor edge. A foreign key to
some existing event is not the required association.

For this version the exact response remains the current UTF-8 encoding:
`{"manifest_sha256":"<lowercase 64 hex>","event_id":"<canonical uint64>"}`.
Recompute these expected bytes from the validated target and event and compare
them with the retained response; do not silently repair or return regenerated
bytes on corruption. Establish status from the event's actual artifact creation
relationship: 201 corresponds to this artifact's creation event; an identical
artifact's later new-key upload is 200. Replays return the original stored bytes,
status and event only after all checks succeed. Mismatches fail closed without
disclosing cached material or creating a new event.

Exercise changed status, changed body, oversized/empty body, wrong existing event,
wrong tenant/actor/target/request and inconsistent response event/manifest fields.
Include a valid refreshed-credential replay by the same immutable principal.
The routine's single atomic insertion and immutable-row privileges establish
the original key association. These bounded checks detect inconsistent retained
material; they do not prove provenance against a privileged offline owner who
coherently rewrites a complete cached row to another otherwise equivalent
event. Such an adversary would require an independently retained commitment.

## AS04: validate immutable artifact creation linkage

An existing artifact must carry a valid same-tenant creation event reference.
That event must be a correctly typed successful upload for the exact artifact
target and must describe the actual insertion transition for its immutable
material. Recompute Change1 and the changed state using the creation event's
previous state; require its current state to match. Check the creation actor
when the product row adds that already-required field. No caller supplies a
creation event or actor. Require this linkage before accepting an unchanged
artifact, and before using it to validate a cached result.

Use typed row constraints and same-tenant foreign keys where possible, including
deferred linkage if insertion order requires it. The narrow routine must still
validate semantic linkage that a foreign key cannot prove. Exercise missing,
nonexistent, wrong-existing and wrong-target creation events and altered state
commitments, retaining the unchanged-artifact/new-key success control.

## AS05: close the entire audit display and row shape

Implement the full selected Event1/Actor1/Decision1/Target1 display decoder in
both independent codec paths. Require the exact 16 root keys, actual JSON types,
exact nested array lengths, all required values and explicit null only at the
selected optional positions. Counting keys does not establish a closed shape.
Require canonical UUIDs, lowercase exact-length byte encodings, canonical
integer strings and all field-specific ranges; schema is JSON integer 1.
Require ValidID targets, supported platform/action/identity class, bounded UTF-8
reason/profile text, canonical source IP or explicit null, and 1..64 unique
membership lifecycle IDs sorted by UUID bytes with valid roles and positive
revisions. Preserve the selected six-role vocabulary and upload role ceiling.

Validate tenant/target equality, event ID, actor and time relationships, explicit
byte lengths and the previous-hash empty/32-byte rule. Encode from validated
typed values and compare exact CBOR, standard hash, stored row projections and
immutable PostgreSQL display bytes. Enforce the selected 16KiB CBOR/32KiB display
bounds before accepting retained material. No arbitrary JSON-to-CBOR coercion
or accepted alternate spelling is allowed.
Time relationships use AS02's selected tolerance: authentication completion may
be up to 30 seconds after the database decision clock. Do not accidentally add
a completion <= decision/recorded requirement.

Tests must mutate every field class, missing/extra/null/type/length/range and
noncanonical spelling. Include the reproduced same-count missing `source_ip`
plus replacement key and leading-zero profile version. Keep independently
authored golden bytes unchanged for valid inputs; these checks confer no
signature or release authority.

## AS06: validate the predecessor edge without an unbounded scan

For event 1 require empty previous hash and the exact initial tenant state.
For event n > 1 require a same-tenant event n-1 and match its validated event hash
and current state against n's previous hash/state. Fully validate the immediate
predecessor's own typed representation and hash. Apply this bounded validation
to the terminal head, cached event and artifact creation event as needed; share
already validated rows within the fixed operation rather than scanning history.
The terminal event must also match the head's event ID/hash/current state.

Reject a coherently re-encoded wrong predecessor, missing predecessor, wrong
state edge and first-event nonempty predecessor. This is bounded adjacent-edge
verification under append-only privileges, not a proof against an offline
privileged owner coherently rewriting an entire historical chain.

## AS07: enumerate the real SQL surface

The corrected specimen must emit its actual complete catalog manifest: composite
field order/types, tables/constraints, function signatures/definitions/hashes,
owners, effective ACLs, RLS policies, role capabilities and memberships. Replace
conceptual helper aliases with the actual identities. The original eight pure
helpers are `u(numeric)`, `b(bytea)`, `t(text)`, `a(bytea[])`,
`hash_domain(text,bytea)`, `target(upload_input)`, `hx(text)` and
`event_from_display(jsonb)`. Necessary new typed-validation helpers may be
private and pure; enumerate them exactly. Keep a single public mutation entry,
no dynamic SQL or extra runtime EXECUTE surface. Private pure helpers remain
owned by the schema owner and callable only by the domain writer as needed;
authz helper ownership/grants remain separately explicit.

Use exact individual function grants rather than granting future helpers by
default. The deliberately granted foreign fixture caller must remain clearly
test-only. Product signatures use the names selected in the original contract;
the specimen names are not a product migration. Root must select and verify the
final product DDL/ACL/definition manifest before implementing its startup
inspector. No conceptual alias may be treated as an installed-object check.

## Verification and ownership

The next producer owns only its new correction documentation and verification
directory, copied specimen and uniquely owned disposable PostgreSQL resources.
Do not modify either frozen predecessor packet, live hosted sources, trackers,
dependencies or legacy Go schemas. Preserve original positive tests; change an
independent gap-reproduction oracle only in the new candidate's copy to demand
rejection, and retain the original test and evidence unchanged. Add direct
boundary, concurrency and corruption tests, keep all failed attempts, bind
commands/tool versions/source/output hashes, and clean up owned resources.

Acceptance requires root source review and a fresh independent reviewer. Full
authoritative membership/credential/profile locking, product migrations and
inspector, HTTP admission, real signed upload composition, Neon/R2/Cloudflare,
jobs and external qualification remain separate required work. No GA gate closes.
