# Browser lifecycle storage integration

Implementation resumed on October 25 under the existing native-runtime and
capture pause. This slice installs the inert durable browser lifecycle schema,
tightens trusted browser configuration metadata, and disables JIT locally inside
ordinary authorization transactions. No login route, provider exchange,
authenticated browser session, production provisioning or GA gate is enabled.

The SQL review reproduced four defects through five adversarial methods: NULL
scope elements could bypass the required workspace scope, bootstrap and begin
could cross exclusive expiry while waiting on unique insertions, and activation
could cross expiry during a later unique cookie update. Corrections require a
positively true scope match and recheck time after those waits. The final local
PostgreSQL 17.11 fixture passes 23 methods. Original failed attempts and source
bindings remain available in the [SQL review](hosted-browser-session-storage-review.md).
Separate correction review passes six additional methods, including observed
unique-lock waits, exact nine-table rollback and before-expiry success. The
final formatted fixture also passes all 23 methods on PostgreSQL 16.15 Linux
arm64. See [correction review](hosted-browser-session-storage-correction-review.md)
and [PG16 compatibility](../verification/hosted-browser-storage-pg16/review.json).

Nine ordinary migrations pass apply/idempotence, latest-six rollback/reapply
while preserving existing build data, and complete rollback/reapply under a
non-superuser schema owner. Independent review also verifies 116 denied runtime
SQL operations across four phases, deliberate privilege/RLS drift detection,
complete object teardown and unchanged roles. The five ordinary CI fixture
expectations now include migration `20261025000007`; the aggregate fixture
rolls back six migrations. The selected storage and migration specs remain
outside automatic ExUnit discovery and have their own PostgreSQL 16 CI step.
See [migration review](../verification/hosted-browser-migration-review/review.md).
This is local integration evidence, not deployed Neon/operator qualification.

The browser Config constructor rejects NUL in `profile_id`, `client_id` and
`api_audience` before matching trusted identity metadata. Existing UTF-8 byte
limits, exact identity matching and valid configuration serialization remain
unchanged. The selected producer suite passes 26 methods; separate review passes
32 methods including those 26, plus six independent Python serialization/hash
comparisons. See [text admission](hosted-browser-config-text-admission.md) and
[review](../verification/hosted-browser-config-text-review/review.md).

Ordinary workspace/artifact authorization now requires an owner transaction,
sets `SET LOCAL jit = off`, and verifies the setting before RLS-expanded queries.
Existing five-second transaction/statement/checkout and 500-ms lock limits are
unchanged. Eight new real restricted-role controls plus existing workspace,
transaction, artifact read and storage regressions pass 86 selected methods on
PostgreSQL 16.15 Linux arm64. They include restoration after commit and rollback.
See [the policy and measurements](hosted-workspace-jit-policy.md). Separate
[JIT review](hosted-workspace-jit-review.md) passes six independently authored
PostgreSQL 16 methods without importing the producer fixture. Exact-push Ubuntu
CI remains pending at this writing. The measured
local improvement does not prove the earlier CI timeout's root cause.

The previous pushed checkpoint `1257cbf8` failed Phoenix CI with 608/609 methods
passing and two skips: the first 121-project workspace read reached its existing
transaction deadline. Its output is retained with the
[resume receipt](../verification/implementation-resume-2026-10-25/receipt.json).
No failed attempt is relabeled as passing. Counts above overlap and must not be
summed as unique coverage. Broad hosted tests were not run locally.

Next, join the reviewed SQL lifecycle to a separately admitted runtime pool,
trusted key custody, process-owned one-use claims, bounded provider exchange,
qualified OIDC validation and the current default access-token verifier. Only
then connect the same-origin HTTP/console session flow. Unknown identity binding
still requires onboarding; storage creates no tenant, membership or first owner.
Commit ambiguity, real provider/Neon operation, key rotation, retention scheduling,
browser/native checks, physical phones, FieldLog and customer/GA acceptance
remain pending. Owned test databases, containers and scratch are removed in each
completed receipt; unrelated processes/data and unfinished files are preserved.
