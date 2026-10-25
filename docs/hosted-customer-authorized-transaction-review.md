# Ordinary customer authorization transaction review

The corrected transaction facade is accepted as a selected local PostgreSQL
prerequisite. This review does not accept customer domain storage, artifact
metadata resolution, HTTP routes, audit/idempotency/Oban integration, deployment,
provider effects, immutable dogfood publication, or any GA gate.

The reviewer owned only this document and
`verification/hosted-customer-authorized-transaction-review/`. Product code,
producer tests, shared harness, CI fixtures, migrations and Git operations remained
with their owning lanes. The reviewer did not read, import, execute or wrap the
frozen hosted catalog/authority-driver or rejected outbound Worker V2 lanes.
No native, device, browser, provider or production action occurred.

## Independent method and environment

The collector compiles only the explicitly listed identity, scope, policy,
PostgreSQL session/evidence, snapshot, context and facade sources, plus ordinary
migrations 003/004. It uses the existing pinned dependency BEAM directories and
records every dependency file hash. It does not fetch dependencies, invoke the
shared test harness, start the full Mix application, or precompile unrelated
product modules. Independently written Repo modules and fixture rows exercise an
actual disposable loopback PostgreSQL database with separate no-login owner,
restricted login runtime and administrator roles. SQL writes target only the
independent fixture's `review_effects` table, not a product domain table.

Observed tools are Elixir 1.20.4, Erlang/OTP 29 (ERTS 17.1), and Homebrew PostgreSQL
17.11 on macOS. This is PostgreSQL 17 local evidence; PostgreSQL 16 CI, Neon,
Cloudflare, production connection topology and infrastructure qualification are
separate. The base revision `d385adf3dd110da44ba290a7221278c48e39b882` was supplied by
root. The collector did not invoke Git. Captured source hashes identify the actual
working-tree candidate and take precedence over that base revision for this run.

The final collector command is:

```sh
python3 verification/hosted-customer-authorized-transaction-review/run.py --output run-5-final --source-revision d385adf3dd110da44ba290a7221278c48e39b882
```

Receipts preserve commands, tool output, source snapshots, dependency hashes,
source-tree digest and cleanup. Every owned PostgreSQL instance was stopped and
its disposable scratch directory removed. Other projects' processes were not
touched.

## Findings and corrections

1. **Post-validation time boundary.** Initial source review found that a checkpoint
   checked time before policy/snapshot validation but did not refresh it after
   validation. The producer added a fresh monotonic deadline and wall-time check,
   with at most one fresh reevaluation if the wall second advances. A second
   instability fails closed. The independent scheduling probe uses official BEAM
   tracing to suspend the owner during actual policy evaluation of 64 SQL-backed
   membership rows until its five-second deadline has passed. The captured timeout
   stack is inside `Policy.memberships/1`; the corrected checkpoint returns
   unavailable without entering the effect callback. This does not inject a
   caller-supplied clock or claim an OS wall-clock change.

2. **Caught effect failures could commit earlier SQL.** Independent run 2 reproduced
   this against the producer's frozen context digest
   `7c4c03cc13eef789d9176ef5c5f26733ea4d4f5ddf824497a10389ca0fa2dc36`.
   Run `run-3-prefix-repro` strengthened the evidence using that immutable ordinary
   source snapshot: effect callbacks inserted a real SQL row, then raised, threw,
   exited, returned a bounded error, or returned an unknown error. The outer
   callback caught the failure and returned success. All five cases returned
   `{:ok, :rescued}` and persisted exactly one row. The producer corrected
   `effect!/5` to latch escaped failures and explicit `{:error, _}` returns.
   Recognized errors remain bounded; unknown errors become unavailable. Other SQL
   and snapshot return values still pass through. The corrected tests require all
   five rescued cases to return unavailable and persist zero rows; a direct
   bounded error retains `:conflict` and rolls back.

The corrected frozen context digest is
`237e5a9c8bcc529619e68db67d166e4dd185e70bbe125592a8c14b83a259be54`.
Facade digest is
`54cfdb6c4a105e1ea3551b6f687d3ced1fecf6e621baed026f521ea82f1d9d88`;
snapshot digest is
`39bae74a8022ea9884874f8e457568a073fd798fa87ebf901e9b896062528599`.

## Executable coverage

The 21 independent methods exercise:

- Real successful SQL commit and complete raw profile/binding/principal/family/
  credential/head/membership revisions, separate windows, subject digest and token
  issued/expiry times. Distinct seeded values prevent collapsed revisions or
  windows from passing unnoticed.
- Every Context field plus an extra field, a forged pure Decision, foreign owner
  PID, stale contexts, foreign Repo/dynamic Repo, a real current-role switch,
  each of the sixteen authorization GUCs, and an actual SQL transaction replacement
  with restored GUCs but changed xid. Complete bound connection equality includes
  backend PID, xid, current/session roles and all settings. The tests probe actual
  changed xid and role; direct backend-PID comparison is also reviewed in source.
- A bounded single Context process-dictionary key while active, and absence of
  that key in the same owner PID after each fresh facade call. Connection-local
  marker cleanup and RLS-hidden credentials are separately checked after each
  method. Recursive calls preserve the valid outer context and are rejected;
  calls from an existing external transaction are rejected before the callback.
- Actual local INSERT rollback for outer callback errors, malformed callback
  returns, raise/throw/exit, caught failed checkpoints and caught effect failures.
  Invalid contexts cannot be caught and converted into a successful final commit.
- Exact role/action ceilings and token-scope intersection, invalid action-target
  shape, service identity rejection, inactive profile/binding/family/credential,
  credential/family window rejection and mismatched identity linkage.
- An observed PostgreSQL lock wait followed by token expiry before callback,
  pre-effect expiry, final expiry rolling back an earlier SQL write, a live token
  crossing the transaction's five-second monotonic deadline, and the scheduling
  probe described above. Runtime timeout disconnects in the two deadline tests
  are expected negative controls; no effect or committed row is accepted.
- Profile revision locking against a concurrent blocked writer; after commit the
  next facade observes the increment. A selected membership expiring while an
  independent surviving grant remains produces the newly selected full row,
  preserving its revision/role and leaving the Context's initial snapshot intact.
- Strict snapshot shape, raw revision/window bounds, identity linkage, nested
  extensions, unknown roles, extra/missing fields and oversized membership data.
  Snapshot validation is reviewed as data validation, never independent authority.
- New migration 004 baseline one and invalid revision constraints, plus runtime
  column DML, owner-role reachability and indirect predefined-role reachability
  rejection. Migration 004 only adds profile state/binding revisions; it neither
  reconstructs history nor implements controlled lifecycle writers. Root's separate
  all-migration helper receipt owns wider apply/down/up CI coverage.

The wall-regression negative control deliberately advances the request-local
previous-time state and verifies rollback/latching. It exercises the guarded
branch; it is not an OS clock-regression receipt. Internal structs and the process
dictionary are trusted BEAM discipline, not a hostile-code sandbox. Likewise,
manual SQL transaction replacement is tested only to reject reuse of context;
applications must not issue SQL transaction-control commands, change dynamic
repositories, spawn asynchronous work, or run remote effects inside callbacks.
A malicious caller issuing `COMMIT` can independently violate transaction
ownership before a later checkpoint; no struct API can undo an already committed
external/manual effect. Those actions remain outside this local trusted API.

## Receipt interpretation

- `run-1`: independent fixture setup failure (migration pool too small), zero
  executed tests. Preserved as a failed attempt; corrected only in reviewer-owned
  fixture code.
- `run-2`: 19/20 methods pass; confirmed escaped effect failure on the old source.
- `run-3-prefix-repro`: 19/20 pass; all five old-source cases explicitly show one
  committed row each. This intentionally failing historical receipt is not a
  corrected-source result.
- `run-4-corrected`: all 21 methods pass on the corrected frozen source, including
  actual evaluator suspension across the deadline.
- `run-5-final`: final source freeze and same-owner cleanup verification. Its exact
  result, digest and source-stability comparison are sealed in `review.json`.

No unresolved blocker remains for this narrow local prerequisite once the final
receipt passes. Pure permission lookup remains insufficient for domain actions;
future domain, audit, idempotency and job writes must consume this live transaction
contract and supply their own executable locking/atomicity evidence. The proposed
customer artifact transaction contract is not an implemented or accepted domain
feature. Physical phones remain disconnected and their final checks pending.
