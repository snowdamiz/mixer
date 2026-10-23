# Independent PostgreSQL review

Reviewed commit `b70a8774c13763ceced909d925a539e1f149381c`, repository tree
`0f62257a97af48e7d6211e29cf3761e8b09fd0c4`, services tree
`0f4172c77ecb6b758cfea9969f59e4a1fb178da4`. The original implementation receipt's
source digest `a6700d77c38a52bab5ddfe8f2c53cc62e6799fd2acc50476662425a676f453d5`
was independently recomputed from the frozen files and matched.

Reviewer: gpt-6.1-sol, xhigh. The initial review was read-only. Root subsequently
authorized the reviewer to fix `services/release/**`; fixed-source review by an
independent owner remains required. No production database, configured database,
physical device, credential, migration deployment or push was used.

## Findings and fixes

| ID | Severity | Reproduced behavior on original source | Resulting guard |
| --- | --- | --- | --- |
| PG-01 | P2 | Startup accepted a runtime schema owner. That role dropped the release schema and all contained immutable tables in a rollback-only test transaction. | Include release schema ownership in authority checks. |
| PG-02 | P2 | Startup accepted ownership of `monotonic_channel()`. Dropping that function removed its dependent trigger; the existing runtime UPDATE permission lowered the stored sequence from5 to1 in a rollback-only transaction. | Include installed release functions in authority checks. |
| PG-03 | P2 | After owner-side metadata drift to version2 with the version1 checksum, both startup and migration retry accepted the unknown version. | Read and require version1 separately from the checksum. |

Schema/function ownership was deliberately assigned by the isolated cluster's
migration owner. These are startup misconfiguration defenses; no authenticated
HTTP user was shown to gain database ownership, and this is not a DBA-resistant
security boundary. The original deployment uses separate owners correctly.

The corrected authority query distinguishes ownership inherited through `USAGE`
from authority reachable through `SET ROLE`. `MEMBER` alone is broader on
PostgreSQL16+. Six observed membership modes confirmed that inert membership
cannot self-enable, while direct, inherited or assumed `ADMIN OPTION` can grant
SET authority. The guard follows administrator-role chains, including nested
administration, and preserves inert membership without such a path.

The production regression has16 schema/function ownership subcases and12 role
attribute subcases. Ownership is rejected when direct, inherited, assumable or
administratively obtainable; inert non-administrable membership is preserved.
SUPERUSER/BYPASSRLS/CREATEROLE/CREATEDB attributes are rejected when assumable and
are not mistaken for ordinary inherited object privileges. Accepted non-assumable
attribute memberships were also checked against a populated unscoped RLS query.

Database ownership alone did not bypass installed FORCE RLS or permit alteration
of the release table/schema/function in the PostgreSQL17.11 probe. No blanket
database-owner rejection or broader database-administration safety claim follows.
Exploratory attempts to replace a policy helper without schema CREATE, set its
custom tenant options, or move it into a temporary schema were denied; those are
ruled-out paths, not additional findings. Their initial diagnostic logs remain in
`logs/`; the authoritative reproduced failures are the three named tests in
`evidence/original-postgres/real-postgres-tests.stdout`.

## Reproduce

Requires installed PostgreSQL tools and Go1.26.4. From the repository root:

```sh
python3 verification/pg-independent-review/verify.py \
  --output verification/pg-independent-review/.build/new-run
```

The output must not already exist. The runner exports the pinned source twice,
verifies the original source receipt, runs the baseline, and adds only the three
explicitly named release-file overlays plus the independent test files to the
fixed export. The selected source and every command/output are hashed. The
original private-cluster harness is reused with one test-selector replacement;
its data-directory marker, disabled TCP listener, cleanup and restart checks are
unchanged. Independently authored tests are copied into the frozen package so they
can exercise its private storage boundary; production sources are never edited
by the runner.

Baseline and fixed host commands are `GOTOOLCHAIN=go1.26.4 go test -race -count=1
-json ./...`, `go vet ./...`, and baseline `go mod verify`. Tagged database runs
use `go test -race -tags=postgres_integration ./release -run <recorded selector>
-count=1 -v`. The expected old-source test process exits1 with exactly PG-01,
PG-02 and PG-03 failing. The overall review runner succeeds only when those
failures reproduce, the fixed checks pass, source snapshots remain unchanged and
every private cluster is removed. An expected negative probe is not a passing
product test.

## Observed scope

The final fixed run passed19 real database test functions plus one selected
configuration function, with37 subtests. This includes the original seven real
database functions and actual immediate database crash/restart, plus independent
live lost-response retry, pooled tenant reset across all eight tables and adjacent
projects, cancellation during a locked tenant head, all five append-only families,
database-owner limits, membership semantics and the three reproduced guards.
Unit/race tests, vet and module verification also passed. Exact outputs, tool
hashes, commands, original/fixed manifests and cluster cleanup are in `evidence/`.

Only PostgreSQL17.11 on macOS arm64 was executed. PostgreSQL14/15/16/18 runtime
coverage, hosted authentication, TLS/SCRAM, backup/restore, failover, operational
RPO/RTO, outbox delivery, external audit and GA gates remain open. PostgreSQL14/15
role-assumption semantics follow the official specification but were not executed.
Concurrent signed schema2 work was excluded from the frozen fixed-source export;
its composition requires the separate owner/integration checks.

Primary semantic references: PostgreSQL17 [DROP SCHEMA](https://www.postgresql.org/docs/17/sql-dropschema.html),
[role membership](https://www.postgresql.org/docs/17/role-membership.html),
[privilege inquiry functions](https://www.postgresql.org/docs/17/functions-info.html),
and PostgreSQL14 [role membership](https://www.postgresql.org/docs/14/role-membership.html).
