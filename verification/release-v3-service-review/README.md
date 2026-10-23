# Independent explicit service-v3 review

No actionable production finding. Review binds the owner's final candidate2,
53-input manifest
`e37325fc0c158a3b41f399f2cee80d372eb3527cc321698d0c5262b724bd3b4b`
and receipt
`974478bb7f9c50173ca0dfd3defac5828ade0d4aa16ebbb106780c338b2cad0b`.
Candidate1's missing old test contract export is preserved in owner evidence;
candidate2 production is unchanged and its corrected fixture export is qualified.

The independent review inspected the complete additive diff of server.go,
storage.go, store.go and versioned.go against c5bf3fee, alongside the frozen
protocol, local durability and PostgreSQL code. Version3 is explicitly selected;
there is no verifier fallback. HTTP envelopes and nested signed objects remain
closed and bounded. Authentication and publisher/editor roles precede mutation;
idempotency binds exact versioned method/path/body and authenticated tenant.
Only successful transactions advance the local container schema, with max rather
than assignment so later old writes cannot downgrade it. Reopen allows older
variants in a newer container and rejects newer variants in an older one.

Four original external public-only tests pass under Go race detection and vet.
They import only public release/protocol APIs, with original TEST ONLY keys and
metadata payloads; no internal/testutil or private storage method is used. Cases
cover nested alias/duplicate/numeric/null malformation leaving durable state and
schema unchanged; current signature/RBAC denial; unpublished filtering; exact
v1/v2 artifact/offer/audit preservation through schema3, old writes and reopen;
greater rollback sequence; strict route filtering; concurrent same-key replay,
exact-body and cross-version conflicts; and closed failure-atomic public stored
Record/Channel decoders and mixed variant rejection.

The owner full Go race suite/vet, real isolated PostgreSQL17 tests and old-binary
container probe are reused, rather than rebuilding or creating another cluster.
`audit.py` checks every frozen source pin and command stream hash, PG source
agreement/no skips, removal of the disposable directory, retained old/new binary
hashes and exact reviewed protocol bytes. PostgreSQL migration001 and postgres.go
are byte-identical to c5bf3fee. Typed stored-schema3 dispatch uses existing opaque
signed-byte columns; no SQL migration is inferred merely from a model change.
RLS, role guards, capacity, immutable rows, transactional sequence/idempotency and
pre/post commit restart behavior remain covered by the bound real PG receipts.

Old v1/v2 service and protocol tests are preserved except two explicit
unsupported-version probes in v2_test.go, which move3 to4 because3 is now
supported. The driver verifies those exact two substitutions. The initial review
preflight was overbroad about that test file and stopped before any Go run;
`2026-10-23-preflight/note.txt` records the correction. No owner production source
or test was edited by this review.

`run.py` runs the bounded original public tests against the immutable owner
export. `audit.py` seals exact receipts and evidence. Root owns a separate actual
TCP Go-service-to-Swift verification/reopen sidecar and integration approval.
This review executes only local httptest APIs and does not claim TCP delivery,
native executable validation, activation, production deployment, customer access,
credential/trust changes, devices, signing/publication or GA readiness.
