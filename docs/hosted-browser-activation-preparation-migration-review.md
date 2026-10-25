# Independent inert preparation migration review

The frozen preparation migration passes this bounded independent development
review. No blocking product finding was observed. Migration `20261025000008`
delegates only to the previously reviewed preparation schema's installation and
rollback statements. The existing nine migration files, preparation SQL and
decoder, StorageSchema and both function/type catalog versions retain their
accepted bytes. This accepts an inert additive migration and its local rollback
behavior; it does not accept browser readiness or a deployed operator workflow.

The reviewed producer [handoff](../verification/hosted-browser-activation-preparation-migration/handoff.json)
is SHA-256 `ef7383d9fac9a6675885237eb7bb5b6d3f1a8179c680d758cc3f51769f3ceefb`;
its [seal](../verification/hosted-browser-activation-preparation-migration/seal.json)
is `8ab16a016fed507234390a1a59a253bc3c379f7e4291bf3cf57eb059e293b63a`.
All 543 sealed members, eight owned sources, seven semantic source pins and
original nine migration hashes verified before and after the fresh passing run.
The source revision was `6b1dfd337ed95ed91ecc4c42b13c5baa67a9e84d`; the
selected source-tree digest is
`5fa7f0f578357971e1bf2c058bc56c5a92f2c77551c8dd974e69641024189d20`.

The [passing receipt](../verification/hosted-browser-activation-preparation-migration-review/attempts/20261025T191835.833795Z-706578d4/receipt.json)
records PostgreSQL **16.15**, Elixir/Mix **1.20.4**, OTP **29**, Python
**3.14.8** and the exact Docker image digest and server metadata. The two
suites remain separate:

| Suite | Methods | Failures | Skips/exclusions |
| --- | ---: | ---: | ---: |
| Original selected ten-migration integration, independently replayed | 1 | 0 | 0 / 0 |
| Independently authored migration/operator adversity | 11 | 0 | 0 / 0 |

The first suite executes the exact ordinary ten-migration spec on a fresh
database owned by restricted LOGIN `migration_owner`. It covers apply/no-op,
inert helper/type/table privileges, additive down/up with baseline preservation,
the seven-migration rollback boundary with existing build data, and complete
rollback/reapply. Source review confirms that the four ordinary test edits only
update the expected list/count and preserve the old aggregate rollback boundary
by increasing its step count from six to seven. Their broad ordinary execution
remains pending remote CI.

The independent suite uses a separate fresh database and actual Ecto migrations.
It reuses only the ordinary fixture utilities and initial baseline provisioning;
its adversarial tests and oracles were authored separately. It proves:

- A conflicting preexisting access-evidence type survives failed `up` with the
  same OID; no helper or migration record is left behind. An injected
  `CREATE FUNCTION` event-trigger fault rolls back both the preceding new type
  and the new helper, and removing the fault permits the ordinary retry.
- A dependent table forces `down` to fail after helper teardown begins. Ecto's
  transaction restores the exact helper/type catalog rows, ownership, ACLs,
  OIDs and migration record; V2 still accepts. Removing the dependency permits
  normal additive rollback.
- Disconnecting the dedicated operator connection after each of all twelve
  pre-COMMIT provisioning prefixes rolls back temporary schema CREATE,
  ownership and grants. A separate finish-time unexpected EXECUTE grant aborts
  the final ACL check and restores the original inert addition on rollback.
- A provisioned V1 baseline accepts only V1/legacy. Inert migration makes both
  fixed versions deny. The complete one-connection upgrade enables V2 only;
  noninteger, unknown and legacy versions deny. Repeated actual preparation
  against a retained claimed session returns its same snapshot without changing
  persisted state. Additive down restores V1, and reapply needs fresh explicit
  provisioning again.
- Actual lifecycle and ordinary runtime logins cannot acquire either owner role,
  complete provisioning, or drop the fixed helper/type. PostgreSQL's schema
  GRANT attempt returns warning `01007` with no privileges granted; the following
  ALTER OWNER fails with `insufficient_privilege`. The review asserts these
  actual results. Only the lifecycle login can enter the helper after upgrade;
  invalid evidence then fails inside its existing validation. The ordinary login
  remains denied execution.
- The restricted database/public-schema owner can perform post-provision down
  despite helper ownership having transferred to the writer. The review observes
  the actual current/session users and existing database/schema authority;
  no runtime membership or teardown grant is added. Bidirectional role edges,
  grant-option ACLs and repeated initial provisioning over V2 fail closed while
  preserving the original state.

Preservation comparisons include existing public function sources/catalog rows,
type rows, relation rows/OIDs/ACLs/RLS, policies, constraints, defaults, triggers,
role flags, memberships, namespace authority and every existing ordinary public
table's data. Only the additive helper/type and migration bookkeeping are omitted
from the baseline comparison. A real claimed browser session, authz profile,
principal/binding and build row supply nonempty state. These comparisons establish
that this migration does not alter the baseline; they do not establish full
relation admission or production correctness.

The runner copies explicitly named ordinary sources and exactly eight existing
locked dependency beam directories, including Oban and application files.
Selected `elixirc --warnings-as-errors` and actual projectless `mix format
--check-formatted` pass. It loads no hosted application or broad discovery
harness, RelationCatalog/RelationManifest, frozen catalog-inspector or
authority-driver, or rejected Worker V2 lane. Each suite must report its exact
method count with zero failures, skips, exclusions and invalid cases. Both passing
suite stderr streams are empty. The source and dependency hashes remain stable.

All four independent attempts are retained. The first stopped before PostgreSQL
startup because the new review test used the repository formatter instead of
projectless formatting. The second passed the migration replay but failed to
compile the review's reserved `@type` attribute. The third passed the migration
replay and ten of eleven independent methods; its remaining oracle incorrectly
expected schema GRANT to error instead of returning PostgreSQL's no-op warning.
Only review files changed to correct these harness issues. No failed attempt is
counted as accepted product evidence. Every attempt records removal of its owned
container and selected compiler products; no external scratch was created.

The producer document currently links older successful operator receipt
`b5b7c1ed`, while its frozen handoff selects the
[final successful operator receipt `d888cda9`](../verification/hosted-browser-activation-preparation-migration/operator-attempts/20261025T191111.336251Z-d888cda9/receipt.json).
The [binding comparison](../verification/hosted-browser-activation-preparation-migration-review/producer-receipt-comparison.json)
proves that both bind identical product and test bytes and pass six operator
methods. Only their documentation snapshot differs. The historical producer link
therefore identifies an equivalent earlier passing run and misses no control.
The producer document and seal remain immutable; current metadata can link this
review for the selected final receipt. This review does not modify producer files.

Reproduce from the repository root:

```sh
python3 verification/hosted-browser-activation-preparation-migration-review/run.py
```

Broad ordinary hosted CI after delivery, all full relation admission controls,
trusted Store transaction/deadline ownership, runtime pool/custody/current
identity/OIDC/provider/HTTP/console composition, Neon and actual operator
authority, customer/FieldLog and GA qualification remain pending. The catalog's
result remains only `:function_surface_verified`. Computer use, screen capture,
native simulator/emulator tests and the final physical-phone matrix remain paused
and were not attempted. No production migration, publication, credential change,
customer message, commit, push or other project's process operation occurred.
