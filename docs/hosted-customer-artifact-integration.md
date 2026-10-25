# Protected customer artifact integration

The local customer artifact composition is accepted after independent review and
a current-source PostgreSQL integration run. It implements the artifact
transaction contract's upload, staged private read, upload audit and
principal-bound idempotency through `MixerHosted.CustomerArtifacts`. It does not
enable customer HTTP routes or configure a deployed service.

The application facade obtains its Repo, host policy and public roots from
trusted application configuration. Upload checks the signed bytes and route,
then performs current authorization, immutable artifact/event/idempotency writes
and the project-head transition in one owned transaction. Read derives the real
application/environment from restricted signed metadata before exact permission
evaluation and private-byte admission. Audit pages validate canonical records
and predecessor edges. Every public success waits for commit. Independent tests
force actual PostgreSQL commit failures for all three operations and verify that
no receipt, bytes or audit result escapes as success.

Evidence is deliberately scoped and counts overlap:

| Component | Producer scope | Independent scope |
| --- | --- | --- |
| Pure v2 codec | 39 methods including unchanged v1/CBOR regressions | 49 combined methods; malformed module-identity callback defect repaired |
| Staged metadata authorization | 63 methods including 48 existing regressions | 80 combined methods; frozen dependency snapshot |
| Restricted PostgreSQL storage | 19 methods, including 4 MiB payload and rollback/reapply | 22 independent methods on the final source; SQL type/codec defects repaired |
| Application facade | 15 methods using actual signed uploads and stored reads | 12 independent methods, including upload/read/audit commit failures |
| Current-source CI fixture | 97 selected methods | Root verifies saved and current source bindings; standard hosted CI is separate |

The final focused CI attempt applies all seven ordinary migrations, reruns them
idempotently, rolls back the latest four and reapplies them. Its first attempt
exposed migration 005's policy dependency during rollback; the migration now
drops its exact new policies before tables without `CASCADE`. The second attempt
applied/rolled back successfully but exposed a missing legacy Repository module
in the standalone test collector. The third attempt passes all 97 methods with
empty test stderr. Both original failures remain retained.

Other repaired findings remain visible in their original packets: malformed
identity atom dispatch in the pure codec, SQL coercion of a string audit schema
and decimal-integral CBOR values, an extra artifact piggybacking a creating event,
future-principal metadata/RLS admission, and wildcard matching of reserved role
or temporary-schema prefixes. The final reviews verify the corrected behavior.

[Root acceptance](../verification/hosted-customer-artifact-root-acceptance/attempt-2/acceptance.json)
binds 428 retained files and 45 current CI inputs, plus the unchanged 132-file VM
and 40 console source bindings. All owned PostgreSQL instances and scratch were
removed. A first root evidence audit mistakenly treated the expected `pg_ctl
status` exit 3 as a failed cleanup; that recorder failure is retained, and the
corrected audit requires both the exact stopped-server output and cleanup flag.

This is local PostgreSQL 17.11 / Elixir 1.20.4 / OTP 29 evidence. The shared CI
harness now provisions separate synthetic storage, metadata and facade databases
and discovers the tests normally. A future standard hosted CI result must be
reported against its exact pushed revision and actual PostgreSQL version.

Remaining product work includes protected HTTP transport, live console data,
multi-tenant trust selection and coordinated lifecycle/trust writers, service/CI
principals, real identity-provider setup, Neon/Cloudflare/R2/CDN and operational
qualification, publication, native/physical comparison and independently
published separate-repository FieldLog dogfooding. The single captured
server-configured host/trust snapshot does not establish those capabilities.
No GA gate is marked verified by these component results.
