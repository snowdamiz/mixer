# Independent browser relation contract review

The corrected source contract passes independent bounded development review,
with no remaining source-contract finding. Its original freeze was rejected
because the sole incoming membership foreign key omitted the customer
idempotency principal reference. The final corrected producer receipt is
`a19d7dcf6f4eff96276f88735d2de04e2f89370fcde6dac7218497613db48432`,
with input tree
`a32bd876f88de0bea58020afe8ff8bc08ec95884dcb8b0cbd7c6e8ac03be0ec6`.
This review covers documentation and source transcription only. It does not
accept PostgreSQL admission, an owner/Store join, browser readiness or a GA gate.

The review owns this document and
`verification/hosted-browser-relation-admission-contract-review/`. It reads the
ordinary nine migrations, their approved browser/customer schema delegates,
ordinary authorization Session, AGENTS, PLAN and the lifecycle runtime contract.
It neither imports producer expectations/checkers nor reads or runs frozen
catalog-inspector, authority-driver, rejected Worker V2 or a broad hosted harness.
The [migration source closure](../verification/hosted-browser-relation-admission-contract-review/reviewed-migration-source-closure.json)
records the exact inspected paths and digests. Build migrations introduce only
build relation targets. The installed Oban 2.24.2 PostgreSQL migration dispatch
and all fourteen version files were inspected statically; they introduce no
Mixer identity FK target. No Ecto/Oban library was loaded or executed.

The review's separate inert `Ecto.Migration.execute/1` stub evaluates only the
approved ordinary schema source and migrations 00003–00007. It loads no Ecto
application, Repo or Postgrex. The source-derived structure is produced before
comparison with the frozen exported matrix. Its SQL token comparison preserves
parentheses, casts, qualifiers, aliases, literal bytes and duplicate occurrences;
it changes only static-source token whitespace/unquoted case. This is a
transcription check, never a live expression authorization strategy. The
[derived baseline](../verification/hosted-browser-relation-admission-contract-review/independent-derived-baseline.json)
records its independent result.

The source confirms these complete exact-nine counts:

| Surface | Count |
| --- | ---: |
| Ordered columns | 124 |
| CHECK expressions | 80 |
| Primary keys | 9 |
| Additional unique constraints | 4 |
| Outgoing foreign keys | 10 |
| Indexes, including the partial unique attempt index | 14 |
| User triggers | 5 |
| Policies | 32: 10 ordinary PUBLIC plus 22 writer |

All ordered names/types/nullability and three defaults match the ordinary
source: attempts.ciphertext_version is integer DEFAULT 1;
profiles.state_revision and bindings.revision are bigint DEFAULT 1. The compound
session/vault/attempt/event CHECKs are compared in full as multisets. All five
ordinary identity predicates remain their original permissive PUBLIC policies,
with distinct NULL/false/true behavior. The workspace-directory migration alters
only memberships/organizations/projects; it adds no policy to the exact nine.
The browser and authz table/column writer grants match the explicit provisioning
source. Table SELECT/INSERT is distinguished from column UPDATE and raw/effective
privileges remain separate requirements. Ordinary Session supplies the existing
SELECT/no-mutation topology requirement; PostgreSQL 17 MAINTAIN denial is an
explicit proposed admission expectation, not an already executed runtime check.

The blocking omission was found by following ordinary migration 00005 into
[CustomerArtifacts.Schema](../hosted/lib/mixer_hosted/customer_artifacts/schema.ex).
Line 67 declares
`mixer_customer_idempotency(principal_id) REFERENCES mixer_authz_principals(id)`.
Together with `mixer_authz_memberships(principal_id)`, this yields **two** incoming
boundary FKs. Each references principals(id) with the ordinary nondeferrable
MATCH SIMPLE / NO ACTION defaults. Both endpoints' catalog linkage must be
checked without claiming full admission of memberships or customer idempotency.
There are twelve FK groups total, requiring a proposed 48 internal RI triggers
and 53 total triggers, including five user triggers. The nine relations have 107
constraint rows including four user constraint-trigger rows; both incoming FKs
make the boundary extraction 109, with sentinel 110. Trigger extraction needs
sentinel 54. These generated-catalog counts still require actual PG16/17 fixtures.

The [retained failing regression](../verification/hosted-browser-relation-admission-contract-review/incoming-fk-regression.stderr)
shows the expanded source dependency check rejecting the original packet:
eleven methods pass and two fail on its missing incoming FK and incomplete RI
counts. Its original receipt and matrix remain in the review evidence. A
permanent negative control rejects that original packet. The initial passing
checks against the narrower dependency set did not establish full migration
closure and are superseded by this correction.

Two earlier wording findings were also corrected: immutable/authz linkage UPDATE
denial now respects the exact mutable browser linkage columns, and RI trigger
expectations explicitly pair check_ins/check_upd with the referencing endpoint's
AFTER INSERT/UPDATE and noaction_del/noaction_upd with the referenced endpoint's
AFTER DELETE/UPDATE. All four must join to the exact FK constraint, opposite
endpoint and referenced key index, with exact function identity and enforcement
flags. User triggers separately join to the exact admitted no-argument function
OIDs; their four source byte hashes and lengths match independently compiled
ordinary StorageSchema bodies. Automatic constraint/index/RI names and numeric
OIDs are diagnostic rather than cross-installation oracles. Exact semantic
multisets plus endpoint/backlink checks preserve duplicate/extra denial.

The additive interface remains
`RelationCatalog.check_relation_surface!(repo, expected_roles, original_monotonic_deadline_ms)`
returning only `:relation_surface_verified`. Its result cannot prove Store/Repo
provenance or readiness. The trusted future Store must call both function/type
and relation checks on the same owned transaction/checkout under the original
deadline, and propagate any failure into rollback. The contract expressly keeps
this owner composition separate.

Actual PG16/17 catalogs, deparsed CHECK/policy/default/index forms, fast-default
representations, collation/opclass/locale/provider metadata, internal RI linkage
and operational index health remain unqualified. A source-only review cannot
verify those representations or a bounded catalog query implementation. The
future producer still needs both-major clean fixtures, mutation/adversity tests,
raw/effective ACL and role escape closure, original deadline/cancellation,
redaction/rollback and trusted owner/Store integration. Provider, HTTP, console,
Neon, operator, customer, immutable external FieldLog and all GA requirements
remain pending.

The final [sixteen independent methods](../verification/hosted-browser-relation-admission-contract-review/review-tests.stderr)
pass, including ten shape, six policy and five grant transcription mutations,
the original missing-delegate regression, source closure and frozen byte bindings.
All forty-eight actual runtime adversity cases remain pending. These results are
source/structural evidence only. The
[review receipt](../verification/hosted-browser-relation-admission-contract-review/receipt.json)
binds the final reviewed freeze, commands, tool versions, source revision,
tree digests, outputs, exact scope and cleanup. This lane started no database,
native runtime, phone, capture or UI process and performed no process discovery.
Two owned Python syntax-check cache files were removed; no owned scratch or
disposable process remains. No product source, dependency, migration, grant,
credential, PLAN/STATUS/gate, commit or push was changed by this review lane.
