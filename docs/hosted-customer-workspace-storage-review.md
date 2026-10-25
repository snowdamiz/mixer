# Independent customer workspace storage review

**Disposition: no open finding after the root-coordinated compiler-warning
correction.** Strict structured compilation is clean. Independent replay passed
the producer's **24/24** PostgreSQL tests; **9/9** new independent controls also
passed on the corrected source, with zero failures, skips or exclusions. This
accepts the selected local storage/RLS development slice as a prerequisite for
HTTP and console integration. It does not establish the complete hosted product
or any GA gate.

## Review boundary and source binding

The review followed `mixer-product-plan.md` §§17, 18 and 25, the frozen
[`hosted-customer-workspace-contract.md`](hosted-customer-workspace-contract.md),
and the root-approved
[`hosted-workspace-identity-session-review.md`](hosted-workspace-identity-session-review.md).
The producer confirmed source freeze directly before executable review. Its
passing packet is `verification/hosted-customer-workspace-storage/run-11/`,
source tree `842299dbe4f346d0342ec92b863d50735dd31184d2b0879d551b551a898ac738`.
The archived ordinary input bytes, including its test fixture, were checked
against that receipt. After sealing the original review packet, root corrected
only the unused argument at `storage.ex:207` from `repo` to `_repo`. The final
collector accepts only that exact one-line overlay with its supplied SHA-256;
all other producer inputs must still match the archive. Final live files matched
the copied inputs before and after execution.

| Selected source | Reviewed SHA-256 |
| --- | --- |
| `hosted/lib/mixer_hosted/customer_workspace.ex` | `ea897c99ee520bc57d9dfd086ff7e102b042d2750d91f404561bdc048ebcf8e6` |
| `hosted/lib/mixer_hosted/customer_workspace/input.ex` | `0ede3d8032b9703375f4d4bddd35567979ab8b454278eaaf4adfb8ca91c45fbc` |
| `hosted/lib/mixer_hosted/customer_workspace/storage.ex` (root corrected) | `3ca97ed522b3d088dd098829d27dbd9c81bfb52c399dcf4efd3e377d121c5e34` |
| `hosted/priv/repo/migrations/20261025000006_add_customer_workspace_discovery.exs` | `43140162ceaf87b58bcdcdf820a9b95b7ae465a873193ac61c7a725a18bde875` |
| `hosted/lib/mixer_hosted/authorization/postgres/session.ex` | `80e0b2e942aca1c93daf61f77962be44e0ea3769787fa518af2144c4f8bfeb33` |
| `hosted/lib/mixer_hosted/authorization/transaction/context.ex` | `36c10584932aca726e855891f8c7ef54e35a19625a922cc779fe0eb6238b0bfc` |

The shared Session/Context hashes equal the accepted identity-session prerequisite.
The parent-supplied and independently observed HEAD is
`6ed7df4f147b3a3254dab91dd3224b9513f586a8`; per-file hashes bind the uncommitted
workspace implementation. The complete executed source/dependency bindings,
commands, versions, exit codes and outputs are in
`verification/hosted-customer-workspace-storage-review/run-4/receipt.json`.
The review task was assigned as a bounded independent Sol 6.1 / xhigh lane;
the root controller retains integration and delivery ownership.

## Resolved compiler finding and review-gate correction

The original storage source had an unused `repo` argument in its empty witness
clause. Integration's strict cold compilation identified the diagnostic. The
reviewer's original collector passed `elixirc --warnings-as-errors` but trusted
its zero exit code; the compile log still contained this warning. The reviewer
missed that output on the first assessment. Runs 1/2 establish passing behavioral
controls, not a clean compiler gate.

Root changed only that argument to `_repo`, after the original review packet
was sealed. The exact original-to-corrected diff is retained in
`verification/hosted-customer-workspace-storage-review/storage-warning-correction.patch`.
Original storage hash:
`70ab23191691cfaa9282515012a119da44d5c2277b7782de0497132c7e2ac085`.
No policy, query, witness selection or other executable behavior changed.

The corrected collector now uses `Kernel.ParallelCompiler.compile_to_path` with
`return_diagnostics: true`, accepting only the structured result
`{:ok, _, %{compile_warnings: [], runtime_warnings: []}}`. It does not infer a
clean result from compiler exit status or output text. The independently recorded
`negative-warning-control/receipt.json` compiles the sealed original ordinary
source: the structured gate rejects its diagnostic with exit 1, before any
PostgreSQL startup, and removes its own scratch. Final run-4 accepts the exact
corrected source with both diagnostic lists empty, then passes all 33 behavioral
controls. This finding is resolved; `findings.json` retains its history.

## Source assessment

The facade admits only bounded human verified identities with exact
`mixer.workspace.read`, full existing Scope IDs, and the closed internal page
shape. Input validation does not treat token fields or cursors as membership
authority. Cursor decoding rejects noncanonical JSON/base64url, duplicate keys,
wrong collection/organization/version, invalid IDs and extra fields by validating
then requiring exact re-encoding. Stored nullable names retain their exact
bytes; invalid non-null printable/length/UTF-8 representations fail closed.

Migration 006 adds nullable organization/project names and three explicit
SELECT-only directory policies. It narrows the existing organization/project/
membership scoped policies to the empty ordinary directory mode, preserving
their previous predicates. Directory policies require exact human linkage,
current identity and membership windows, action, required scope, phase and
collection-specific empty/exact tenant settings. Organization membership
visibility does not recurse through tenant resources. Project visibility
requires an active organization, active project and an explicit all-project or
matching exact-project grant; organization-only grants remain descriptive
organization roles. There is no new definer resolver, read-all view, DML grant,
helper, identity bootstrap or artifact action added by this migration.

Each call owns a new bounded READ COMMITTED transaction. It prepares and locks
the exact profile/principal/family/credential chain, selects at most limit+1
resources, and selects at most one deterministic live witness per canonical
role. An organization without an organization-scoped witness uses one exact
project witness. It locks selected organization heads before project heads in
byte order, with deduplication, including the lookahead and any outside
organization-visibility witness. Temporary exact lock contexts restore the full
intended directory settings before directory reads continue.

After the last lock wait, new statements reload identity, selected resources,
names and the frozen witnesses. Lost, changed or expired selected witnesses
fail closed without replacement or retries. Final checks validate identity and
witness windows, reject backward wall time or an expired monotonic deadline,
and compare owner process, dynamic Repo, backend, transaction, role and every
bound GUC. No caller callback follows the checks. Ecto's actual owning commit
must succeed before a page can escape. Descriptive directory roles never become
an artifact Context or action grant.

These serialization conclusions depend on the contract's controlled-writer
protocol. The review did not implement or qualify lifecycle writers. Pagination
remains weakly consistent across requests; selected rows are revalidated, and
LIMIT bounds selected materialization and lock counts rather than all internal
PostgreSQL scan work.

## Independent executable observations

The new controls are in
`verification/hosted-customer-workspace-storage-review/storage_review_test.exs`.
They use real loopback PostgreSQL with a separate nonlogin/non-bypass owner and
restricted runtime login. The review evaluates only the four explicitly named
ordinary fixture modules from the producer test's AST; the producer's test case
is not registered in this second process. There is no recursive source discovery
or application startup.

1. A direct SELECT matrix individually corrupts profile, version, issuer, client,
   subject, principal, family, credential, identity class, token window, action,
   scope, phase, mode and tenant GUC fields. Organizations, projects and
   memberships disclose no rows. Correct project mode exposes only the exact
   actor's matching project/membership. A separately resolved actor sees its own
   organization. Directory mode exposes none of the ordinary artifact, audit,
   idempotency or artifact-head rows.
2. Catalog inspection observes exactly three SELECT directory policies, all
   twelve authorization tables with ENABLE/FORCE RLS, nonlogin/non-bypass
   owners, no PUBLIC table ACL, and runtime SELECT-only privileges. All six
   existing fixed lock helpers retain zero arguments, definer mode, fixed
   pg_catalog search path, safe owners and their exact runtime/PUBLIC EXECUTE
   topology. Runtime authorization INSERT/UPDATE/DELETE attempts are denied.
3. While a one-row organization page is paused just before finalization, actual
   `FOR UPDATE NOWAIT` tuple probes conflict on all four exact identity rows,
   both returned/lookahead organization heads and both selected exact-project
   witness heads. An unrelated foreign organization head remains lockable.
   The lookahead head becomes lockable after the owning reader commits.
4. A 106-membership project fixture with a 100-row page holds exactly the
   necessary 101 candidate project heads plus its outside organization-visibility
   witness head. Independent tuple probes conflict on all 102; the next
   unselected project head remains lockable. The page returns 100 sorted,
   properly scoped roles and a cursor without a global membership cap.
5. An organization name writer holds its selected head before a reader waits.
   After the writer commits, the reader's fresh locked reread returns the new
   exact Unicode/name bytes rather than its earlier candidate value.
6. A credential-family expiry crosses an actual selected project-head lock wait
   within the 500 ms lock bound. The fresh post-wait identity check denies with
   unauthenticated before any row is returned.
7. Revocation of the selected lookahead organization commits during its actual
   head wait. The entire page fails unavailable; no partial page or cursor is
   exposed. A subsequent fresh request returns the surviving row with no cursor.
8. Both directory facades reject an existing caller transaction. A test-only
   deferred unique constraint makes PostgreSQL reject actual COMMIT; the facade
   returns unavailable, no probe row survives, and transaction/process/Context
   state clears so the next ordinary directory call succeeds.
9. With migrations 003/004/005/006 applied in order, a signed ordinary artifact
   upload, exact idempotency replay, metadata/content read and audit query pass
   through the real CustomerArtifacts/Authorization/PostgresStorage path. The
   directory mode cannot see those stored rows. Workspace-only token scope
   cannot upload. A billing-manager grant remains visible for workspace discovery
   but cannot upload or read artifacts even with artifact scopes on the token.

The separately replayed 24 producer tests retain all eighteen role/binding
combinations, organization-only empty project pages, inactive ancestry, full
Scope IDs, canonical multistep pages, nullable/invalid names, identity revocation
fences, both selected-reader/revoker orderings, witness fallback loss, expiration,
context corruption, real read/commit failures and connection cleanup.

## Reproduction, retained attempts and cleanup

```sh
python3 verification/hosted-customer-workspace-storage-review/run.py \
  --output verification/hosted-customer-workspace-storage-review/run-N \
  --source-revision 6ed7df4f147b3a3254dab91dd3224b9513f586a8 \
  --storage-correction-sha256 3ca97ed522b3d088dd098829d27dbd9c81bfb52c399dcf4efd3e377d121c5e34
```

The collector contains fixed ordinary source and dependency allowlists. It copies
and verifies the frozen producer packet plus the exact root-coordinated one-line
correction, adds only the listed ordinary artifact sources and signed fixture,
checks formatting, requires the structured zero-diagnostic compiler result,
and runs baseline and independent suites in separate Elixir processes. Run-4
uses a fresh second disposable database for the independent controls, applying
003/004/005/006 in their production order. The baseline separately observes 006
apply/down/reapply. No new dependency is installed.

**Passing run-4** binds executed input tree
`fbc8d75c48454b4d5251fcdb08fbdcf23dc2c8ac3c00b45fa9c8bc8c1772e6c1` and pinned
dependency manifest
`c544378354d431a88740973b97517211c514bcad9a51616cb6188cf6ee502645`.
The post-run `closure-verification.json` checks all 303 pinned dependency files
again with no changes; all live selected inputs also remain unchanged.
Environment: Darwin arm64, Elixir 1.20.4, OTP 29/ERTS 17.1, PostgreSQL 17.11,
Python 3.14.8, `ERL_FLAGS='+S 2:2'`. Both owned databases were inside the same
owned cluster, which stopped successfully; all scratch was removed. The
expected Postgrex 23505 output comes from the intentional deferred COMMIT
failure probe and is preserved in the logs.

**Runs 1/2 are retained as earlier behavioral passes** (24+9 each). Their
legacy compiler command accepted the original unused-argument warning. Run-1
also added migration 005 to the baseline's 003/004/006 schema and produced an
Ecto ordering warning, plus two unused review-helper warnings. Run-2 moved the
independent controls into a separate clean database with ordered migrations and
removed those two review-helper declarations.

**Run-3 is retained as a failed review-fixture attempt.** The corrected product
source compiled with zero structured diagnostics and the baseline passed 24/24.
Independent controls passed 8/9: a negative token-issued-at value created at
`now + 31` before a twenty-case matrix crossed a second boundary into the allowed
30-second skew. The review fixture now uses `now + 60`, remaining invalid across
that short matrix. No product change was made for this fixture failure. Run-4
passes 24+9. Every attempt stopped its owned cluster and removed scratch.

## Remaining limits

The trusted application owns SQL/GUC configuration. These policies and internal
structs do not authenticate a compromised API login or form a hostile-SQL or
malicious-BEAM sandbox. Deployed database/topology review remains necessary.

This review does not qualify HTTP/HEAD wire behavior, request parsing, the
SolidJS console, real issuer/SSO, controlled provisioning/revocation writers,
Neon/Cloudflare deployment or operations, customer acceptance, immutable
published FieldLog consumption, or G22/G24. Those are separate required evidence.
The reviewer changed no product files, trackers, Git index/history, production
service, credentials, signing, store submission or customer communications. The frozen catalog-
inspector/authority-driver and rejected Worker transport sources were never
read, imported, compiled, executed, wrapped or retried; the shared main harness
was not invoked. Computer use, capture, native simulator/emulator and physical
phone tests remain paused/pending; this review started none.
