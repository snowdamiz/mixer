# Additive browser activation preparation SQL

This opt-in prerequisite implements the additive seam in
[the runtime contract](hosted-browser-lifecycle-runtime-contract.md). It installs
one composite and one read helper only. It creates no ordinary migration and has
no application caller, runtime readiness consumer, provider or HTTP route. Root
reserves migration `20261025000008` for later independently reviewed integration.
The accepted StorageSchema and version-1 Catalog stay unchanged.

`ActivationPreparationSchema.statements/0` creates
`public.mixer_browser_access_evidence(profile_id text,profile_version integer,
issuer text,subject text,client_id text,credential_ref text,issued_at bigint,
expires_at bigint,scopes text[])` and
`public.mixer_browser_prepare_activation(bytea,bytea,bytea,bytea,bigint,
public.mixer_browser_access_evidence) RETURNS jsonb`, then revokes PUBLIC
execution/type usage. Installation remains inert to the lifecycle login.
`signatures/0` and `public_signatures/0` contain that helper alone.

The helper uses exact cookie/state/claim/configuration/revision input, one
`SELECT INTO STRICT` with unique-key joins across browser, vault, claimed attempt,
profile, exact subject binding and principal, and inline `to_jsonb` projection.
`LIMIT 2` and STRICT deny excess rows. It does not invoke the existing multi-query
snapshot helper. There are no row locks, table writes, identity creation or email/
domain matching. Normal relation AccessShare locks for SELECT are still present.
A concurrent writer may commit after this snapshot; preparation never blocks that
writer or becomes a permission ticket. Database time is read before lookup,
after projection and immediately before returning. Deadline equality and clock
regression deny. The existing activate remains authoritative and performs its
unchanged revision CAS and canonical locking/revalidation.

A missing, foreign, mismatched or expired current claim yields
`browser session unavailable` before binding disclosure. Only a valid claim and
active matching human profile can produce `browser onboarding required` for a
missing exact subject binding. Inactive/mismatched binding or principal, profile
issuer/client/class drift, principal valid-after fence and token expiry deny.
Stored redirect is bounded and tied to the saved configuration digest; the given
SQL signature has no current redirect parameter or profile redirect column.
The future ClaimOwner **must compare the retained current Config redirect with
the complete returned attempt before use**. This SQL does not establish that
comparison or Config/verified-token provenance.

Token numeric dates permit zero and are bounded to `0..9007199254740991`, matching
`Identity.Encoding.numeric_date?/1`. Positive DB revisions use
`1..9007199254740991`. Issued-at permits at most 30 seconds of future skew and
human lifetime at most 900 seconds, matching current `AccessTokenVerifier`.
SQL scope cardinality retains the existing activate ceiling of 64. Inputs require
one dimension, lower bound 1, required workspace scope, no NULL/empty/duplicate
member, each member at most 1,024 bytes, the verifier's ASCII scope-word grammar,
and aggregate word bytes plus separators at most 1,024. This bounds the projection
input more tightly than baseline activate while admitting every current verified
normalized scope list. It does not freeze the verifier's four-value allowlist.
PostgreSQL UTF8 text rejects embedded NUL before the helper receives it.

The result has exactly `version`, `snapshot`, `principal_id`, `profile_revision`,
`binding_revision`, and `principal_revision`. Version is 1; snapshot preserves the
existing exact StoredSnapshot row format, claimed status and erased attempt
cipher. `ActivationPreparation.decode/1` validates shape only. The future owner
must compare all retained claim/current configuration/current fresh access
identity fields, discard mixed evidence, seal outside locks and call unchanged
activate. The revisions and principal ID are provisional metadata only.

`catalog_manifest/0` is explicitly `additive_only: true`, `version: 2`,
`baseline_version: 1`. It contains only this helper's exact source/signature/
argument names/result/security/settings/runtime EXECUTE, ordered evidence fields
and decoder module/source SHA-256. `@external_resource` makes the decoder a
build-time tracked dependency. This is not combined admission of 19 functions,
4 composites and 10 application EXECUTEs. Version-1 admission must reject the
added surface; the selected tests exercise that boundary without changing Catalog.
A complete version-2 owner/admission implementation remains pending.

`provisioning_statements(writer, lifecycle_login, relation_owner)/3` requires
three explicit distinct restricted names and existing isolated roles. Preflight
checks strict flags/membership isolation, existing baseline function ownership,
login EXECUTEs, browser relation owner/FORCE RLS, type owner/USAGE and absence of
login table privileges or pre-existing writer/login CREATE. The bounded operator
transaction changes ownership of the new helper to writer and new type to the
explicit relation owner; grants only new-type USAGE and new-helper EXECUTE.
A temporary schema CREATE needed for function ownership transfer is revoked in
that transaction. Every failed plan must be rolled back by the operator; no
partial plan may be continued or committed. This preflight does not replace
complete catalog admission. It never replays initial baseline provisioning,
changes a table/policy, creates a role or handles credentials.
`rollback_statements/0` drops only the new helper then new type.

Run `python3 verification/hosted-browser-activation-preparation-sql/run.py` for
one owned disposable PostgreSQL 17 instance, selected source files, approved
ordinary fixture/migrations and existing locked dependency beams. No broad hosted
compile/harness or frozen/rejected lane is loaded. Immutable attempt receipts
record source/dependency digests, revision, commands, versions, outputs and owned
cleanup. Native/UI/capture/physical checks remain paused. This component does not
qualify Neon, provider/OIDC, ClaimOwner, deployment, browser workflows, customer
FieldLog or any GA gate. Independent review remains required before acceptance.
