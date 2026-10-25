# Independent workspace identity-session prerequisite review

**Disposition: no actionable finding in the reviewed prerequisite.** Independent
selected-source replay passed the original **20/20** authorization transaction
tests, followed by **6/6** new real PostgreSQL probes. This accepts the bounded
identity-session extraction and directory-mode isolation as a local development
prerequisite. It does not accept the workspace directory implementation or API.

## Exact review boundary

Root froze these three working sources for review:

| Source | Reviewed SHA-256 |
| --- | --- |
| `hosted/lib/mixer_hosted/authorization/postgres/session.ex` | `80e0b2e942aca1c93daf61f77962be44e0ea3769787fa518af2144c4f8bfeb33` |
| `hosted/lib/mixer_hosted/authorization/transaction/context.ex` | `36c10584932aca726e855891f8c7ef54e35a19625a922cc779fe0eb6238b0bfc` |
| `hosted/test/mixer_hosted/authorization/transaction_test.exs` | `414cc74e70ca8572919ae82d4f17b10b9deb2095d4310aa6856dd8179dbae6ad` |

The producer packet is
`verification/hosted-workspace-identity-session/run-1/receipt.json`, with source
tree digest `72545e34e2add2313945e6472ab193afc7b400a2536447b41f38135c978b2dcc`.
Its exact archived ordinary input bytes were replayed. The live three shared
files matched those bytes before and after independent execution. No unfinished
`CustomerWorkspace` module or workspace migration was read, imported or compiled.

The supplied revision `c0334a9958df1f1d973310bbbdfc1ac8ec8912f9` identifies the
original HEAD context; the per-file hashes bind the uncommitted extraction.
`source-comparison.json`, `shared-source-diff.patch`, and `original-head/` retain
a read-only comparison against those three original HEAD files. The earlier
workspace contract and its sealed source-only receipt were not modified.

## Source assessment

`Session.prepare!` now composes `prepare_identity_scope!` and then obtains its
organization and project heads. The extracted private body retains the previous
READ COMMITTED setup, five-second statement/idle bounds, 500 ms lock bound,
effective role/table/function topology checks, parameterized transaction-local
identity settings, and profile → principal → family → credential lock sequence.
Ordinary preparation therefore retains the full original order through the
organization and project heads. Scope settings are still present before the
identity lock sequence for ordinary callers.

`prepare_identity!` selects an empty organization/project/application/environment
scope. Both entry points explicitly reset `directory_mode` to the empty string.
Its only return data is `%{principal_id: ..., family_id: ...}`. It does not load
or validate current active/window policy, bind a transaction Context, choose a
tenant, expose an HTTP route, or execute a callback. It is an internal preparation
primitive whose caller must own a transaction and subsequently validate current
identity and action-specific authority. A revoked credential can therefore still
produce linkage; treating that linkage as an authorization decision would be a
caller defect. The independent writer-first test deliberately verifies this
boundary rather than expecting an invented helper-level permission check.

`Context.@settings` adds `directory_mode` to the complete connection comparison.
Changing it after artifact Context binding makes the current connection differ
and invokes the existing latched rollback path. No role ceiling, required artifact
scope, Context shape, target, snapshot projection or public customer route is
added by this prerequisite. The original human artifact/audit action tests retain
their previous six-role ceilings, including billing-manager denial.

The privilege boundary is unchanged: the application sets trusted GUCs; identity
and Context structs are application discipline, not a malicious-BEAM or hostile
SQL sandbox. This review adds no broader promise about a compromised API login.

## Independent PostgreSQL observations

The new test file is
`verification/hosted-workspace-identity-session-review/identity_session_review_test.exs`.
It uses an owned loopback PostgreSQL instance, separate nonlogin/non-bypass owner
and restricted runtime roles, and the selected ordinary transaction fixture.
The fixture's disposable SQL probe is not a product artifact operation.

1. An administrator holds both tenant authorization heads `FOR UPDATE` while the
   runtime helper prepares successfully. `pg_locks` shows RowShareLock on exactly
   the four identity tables and none on either tenant-head table. Independent
   `FOR UPDATE NOWAIT` attempts conflict on each exact profile, principal, family
   and credential row, proving tuple locking rather than merely observing table
   lock modes. The helper returns only the two expected linkage fields.
2. With helper preparation first, a protocol-ordered credential revocation is
   observably blocked on the actual row lock. It completes only after the helper
   transaction releases. A subsequent ordinary artifact request rejects the
   revoked credential before reaching its callback.
3. With credential revocation first, helper preparation is observably blocked.
   After writer commit it reads the newly inactive credential under READ
   COMMITTED, returns linkage without a Context, and the next ordinary artifact
   request denies. No earlier stored active state becomes authority.
4. A reused single-connection runtime inherits all five tenant/directory settings.
   Ordinary artifact preparation restores the exact requested tenant and empty
   directory mode. Its properly checked local probe commits. The producer's
   replayed identity-only test separately confirms all five settings become empty
   and no organization or Context authority is established.
5. Changing directory mode to either directory collection causes an immediate
   artifact checkpoint failure. Catching its rollback throw and restoring the
   old mode cannot clear the latched failure: finalization rolls back the earlier
   local write. The producer's replay also covers changing mode immediately
   before finalization.
6. Returned linkage and a previously captured artifact Context both fail as
   effect authority inside a new identity-only transaction, even with directory
   mode explicitly set. Neither reaches the write callback.

These probes supplement, rather than replace, the original twenty transaction
tests for snapshots, role ceilings, invalid inputs, Context ownership/reuse,
callback/effect rollback, time windows, actual lock-wait expiry, deadline bounds,
topology and connection cleanup.

## Reproduction, provenance and cleanup

```sh
python3 verification/hosted-workspace-identity-session-review/run.py \
  --output verification/hosted-workspace-identity-session-review/run-N \
  --source-revision c0334a9958df1f1d973310bbbdfc1ac8ec8912f9
```

The collector uses a fixed ordinary source allowlist. It verifies replay inputs
against the producer receipt, checks that pinned dependency BEAM hashes match,
checks formatting, compiles selected sources with warnings as errors, and runs
the baseline and independent tests in separate Elixir processes. The independent
process excludes the twenty baseline tests after loading their ordinary fixture;
its six probes execute once. Only authorization migrations 003/004 are applied
by the baseline fixture. No application startup, shared main harness, recursive
product source discovery or new dependency installation occurs.

Passing **run-2** binds executed input tree
`73781f647c6980b249ba3f02f51a7941d4a187556ee7bd714c70ae0bdf948240` and dependency
manifest `c544378354d431a88740973b97517211c514bcad9a51616cb6188cf6ee502645`.
Environment: Darwin arm64, Elixir 1.20.4, OTP 29/ERTS 17.1, PostgreSQL 17.11,
Python 3.14.8, `ERL_FLAGS='+S 2:2'`. Every command, exit code, selected source
copy/hash, dependency hash and output is retained in its receipt and logs.
Both baseline and independent processes passed; the owned PostgreSQL cluster
stopped and scratch was removed.

**run-1 is preserved as a failed review-fixture attempt.** Its baseline passed
20/20 and independent probes passed 5/6. The lock-inspection query accidentally
included index relation locks; the expected four table names therefore did not
match. Restricting that review query to ordinary table relations corrected the
probe. This was reported to root before any producer fix; no producer change
was requested or made. Its owned cluster and scratch were also cleaned.

## Remaining limits

This is a selected-source replay of the shared prerequisite, not qualification
of the live workspace producer, nullable-name migration, directory RLS,
pagination, HTTP transport, console or new workspace action. Subsequent code must
actually validate identity after waits and perform its own bounded tenant-head
and commit-time checks; the helper does not do that work for it.

Full private artifact storage/HTTP integration, current workspace integration,
audited production provisioning/revocation, real issuer/SSO, deployed Neon and
Cloudflare topology, customer acceptance, FieldLog immutable published-package
consumption and G22/G24 acceptance remain separate evidence. No frozen catalog,
authority-driver or rejected Worker transport lane was read or run. No
production migration/publication, customer communication, credential change,
signing or store action occurred. Computer use, capture, simulator/emulator and
physical-phone tests remain paused/pending; none was started by this review.
