# Independent current-authority catalog correction review

**Correction required before final contract selection.** The frozen correction
closes the five previously reproduced catalog omissions under ordinary
PostgreSQL DDL and sessions, but its raw comparator still admits malformed
entries that the root selection explicitly requires it to reject. Finding
**ACR01** concerns raw-input validation; this review found no ordinary
PostgreSQL-runtime authorization bypass within the selected properties.

The [receipt](../verification/hosted-authority-catalog-review/receipt.json),
[read-only checker](../verification/hosted-authority-catalog-review/check.py),
[independent runtime probes](../verification/hosted-authority-catalog-review/adversarial.py),
[boundary probes](../verification/hosted-authority-catalog-review/domain-probes.py),
and [complete raw-field domain guidance](../verification/hosted-authority-catalog-review/raw-field-domains.json)
bind the review. The producer and predecessor packets were not edited.

The selected inputs are the [root correction direction](hosted-authority-schema-corrections.md)
and its frozen selection, plus the
[candidate](hosted-authority-catalog-correction.md). Candidate source digest is
`8448b889f9050f9f160b8982bc929e1eacb5ca0c522cd3c7358404b331c987a0`.
Its receipt SHA-256 is
`5bc49cf63736fdb9b0835323c4313cbab6931489fdebc33e6616cf46952b9715`;
artifact-manifest SHA-256 is
`ff5b1c497e4d79cabb5eb69da2d56fe0ad44e9966d90c301148ecdc5fd40285a`.
The independently selected expected manifest remains
`78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e`.
Neither replay nor review rewrites that selection.

## Observed results

The producer checker verifies 789 bindings. Both independent fresh replays, each
using 53 padding tables outside the protected schema, pass the original 128
cases, the prior review's 48 observations, and all 67 correction cases. Those
48 contain 43 expected-behavior controls and five historical reproductions of
the old catalog's omissions. The historical reproductions are not security
passes. The original schema, functions, types, roles, catalog, resolver, lock
order and 128 assertions remain unchanged.

The final independent runtime cluster uses 61 padding tables. Its real OIDs and
generated internal FK trigger names differ from the fresh candidate replay,
while its normalized safe baseline equals the separate frozen selection. The
19 actual runtime cases comprise 15 rejected deployment/session changes and
four expected safe behaviors. The observations preserve 25 safe comparisons,
including fresh controls after restoration. Two additional observation groups
exercise eight strict malformed-input rejections and reproduce ACR01 in ten
initial examples. Thus the final **21/21 observation executions** include a
successful finding reproduction; that total is not a security pass count.

The independent ordinary-DDL/session cases include:

- A renamed internal FK trigger and a dropped/recreated identical FK retain
  portable identity with enforcement intact. The renamed FK still rejects an
  actual invalid reference. Renaming a user lifecycle trigger rejects.
- An additional equivalent FK produces 90 constraints and 78 triggers,
  including four additional actual internal FK triggers, and rejects. No
  deduplication hides its multiplicity. Internal `ENABLE ALWAYS`, changed event
  bits, an extra deferred constraint trigger and changed FK deferrability reject.
- A replacement `WHEN(false)` lifecycle guard permits an actual immutable
  subject update in the administrator fixture; inspection rejects that state.
- `NULLS NOT DISTINCT` uniqueness semantics and `REPLICA IDENTITY USING INDEX`
  reject. The candidate separately retains ordinary failed concurrent rebuild
  evidence for invalid/unready flags on the same required index definition.
- A two-hop `SET ROLE` membership chain with a grant-option parameter privilege
  allows an actual runtime `SET session_replication_role=replica`; inspection
  rejects it. Effective subjects include the intermediate reachable role.
- `ALTER ROLE ALL IN DATABASE` and a role-in-database override of safe role and
  database defaults produce actual unsafe fresh-session values and reject.
  Defaults for an unrelated role and a different database remain outside the
  applicable selected scope and preserve admission.
- Three distinct fresh runtime backend PIDs bind the exact runtime login and
  effective role, database and Unix-socket connection. An administrator connection
  using `SET ROLE` cannot substitute for that session identity. Actual REPEATABLE
  READ isolation with a safe default, and a fresh read-only default, reject.

The final boundary matrix executes **126 model-input cases**: 87 rejections,
18 valid uint32 OID portability controls, and **21 malformed admissions**.
These model cases are separate from real PostgreSQL deployment/session tests.

## ACR01: malformed fields disappear before validation

Severity: medium; final prerequisite selection remains blocked by the selected
malformed-input contract. The source location is
`candidate/inspector.py:28–29,59–67` in the frozen candidate copy. `oid()` checks
only that a value is an integer greater than or equal to zero. `normalize()`
then deletes OID fields and deletes internal-trigger `name`/`definition` without
validating their raw domains.

| Input change to an otherwise selected raw observation | Observed result |
| --- | --- |
| Internal trigger `name` set to null, object, array, false, integer zero or empty text | All six admitted |
| Internal trigger `definition` set to the same six malformed values | All six admitted |
| Row `oid=4294967296` in relations, constraints, indexes or triggers | All four admitted |
| A selected nonzero internal trigger `relation_oid`, `function_oid`, `constraint_oid`, `referenced_relation_oid` or `constraint_index_oid` changed to `4294967296` | All five admitted |

The upper OID bound follows the installed PostgreSQL platform header's unsigned
`Oid` representation, not an invented JSON limit. Header copies and hashes are
included. The positive lower bound and `4294967295` are accepted portable OID
controls. Negative values, zero row/required association IDs, booleans, floats,
numeric strings, null and objects reject in the exercised OID positions.
Retained boolean fields reject integer 0/1 substitutions.

These malformed values were injected only into copied inspector inputs; the
review made no PostgreSQL catalog writes and demonstrated no server producing
these malformed values. They contradict the candidate's claim that all raw
entries are validated before transport fields are removed and the root's
explicit malformed-entry requirement. They do not establish an ordinary-DDL
enforcement bypass or justify changing resolver algorithms or role privileges.

The narrow correction should validate the complete raw shape and primitive
domains **before any lossy normalization**, retain exact semantic comparison
and entry multiplicity, and keep the existing selected expected bytes frozen.
The machine-readable field guidance covers all nine enforcement groups and
the actual nine fresh-session string fields, including required/nonempty text,
nullable identities/defaults/ACL arrays, nested object keys, empty argument and
column text, bool-versus-int distinctions, positive versus optional uint32 OIDs
and association consistency. It preserves valid generated internal names and
OID changes. Add boundary regressions rather than deleting portability behavior
or automatically regenerating expected state.

## Attempts, environment and limits

Observed HEAD was `f044e6db2bbf0d76d521d0741ce9545de91cadda`, committed tree
`21ab5ac3c94b960f9276e6271d757ce951a80f36`; copied source digests identify the
uncommitted candidate and reviewer files separately. Both review attempts bind
their exact executed driver and probes, inputs, commands, SQL results, outputs,
raw/normalized observations and source manifests. Python is 3.14.8;
PostgreSQL/psql/pg_ctl are Homebrew 17.11 on macOS 27.0.1 arm64.

The first attempt retained 20/21 observations: a reviewer setup error batched
`CREATE DATABASE` in one libpq multi-statement command and PostgreSQL correctly
rejected it with SQLSTATE `25001`. The reviewer split those commands; the second
attempt passed all 21 observations. Neither attempt changed producer code or
expected state. All four owned clusters, including both candidate replay
clusters and both reviewer clusters, were stopped and their unique scratch
roots removed. No TCP listener, other project's process, simulator, emulator or
phone was touched. Large SQL logs are losslessly compressed with original and
compressed hashes.

Inspection is a point-in-time prerequisite check, not protection against
subsequent concurrent privileged DDL. No product startup inspector, combined
authorization/domain schema, driver coordinator, HTTP/provider behavior,
Neon/TLS/pooling/Cloudflare/Oban/R2 operations, physical phones, FieldLog
published-package qualification or GA gate is implemented or accepted here.
The candidate's `index live=false` state remains catalog/model coverage only;
no runtime concurrent-drop liveness receipt is claimed. Those limitations are
preserved rather than converted into passes.

From the repository root, verify the frozen review without starting anything:

```sh
python3 -B verification/hosted-authority-catalog-review/check.py
```

For a new isolated review run, choose an unused numbered attempt. The driver
refuses to overwrite an attempt and cleans up its owned cluster after failure:

```sh
python3 -B verification/hosted-authority-catalog-review/run.py --attempt attempt-3
```
