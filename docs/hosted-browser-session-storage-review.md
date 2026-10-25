# Independent browser storage review

The paused SQL candidate required correction. Its original 18 selected methods
pass, but five independent adversarial cases exposed four defects. The corrected
candidate passes all 23 methods on disposable loopback PostgreSQL 17.11. Because
this reviewer authored the corrections, separate correction review and root
acceptance remain pending. This is development storage evidence; it enables no
login route and passes no deployment, customer or GA gate.

## Inputs and authority

The review first compared all six live candidate files with the October 25 pause
manifest and backup. Every hash matched; no backup was restored. The exact
[comparison](../verification/hosted-browser-session-storage-review/pause-source-comparison.json)
and the original pause source/evidence remain preserved. The binding product
plan, AGENTS, execution plan, pause handoff and selected storage contract were
read before reviewing the SQL implementation, role provisioning and focused
fixture. No external implementation or new dependency was used.

The SQL capability still has nine public operations and three input composites.
Signatures, migration, operator provisioning, fixture infrastructure and runner
are unchanged. The migration remains inert until separately reviewed operator
provisioning. It creates no role, credential, application process or production
state. Function-local statement/idle limits remain five seconds, lock timeout
500 ms, search path `pg_catalog` and bytea output hexadecimal. The production
owner must enforce the complete connection/transaction/commit budget separately.

## Independent findings and corrections

| Finding | Observed failure before correction | Correction and executable rejection |
| --- | --- | --- |
| R1: scope membership did not deny SQL NULL | Both `[NULL]` and `['other.scope',NULL]` completed activation and created an active family/credential. `NOT (required = ANY(scopes))` evaluated to NULL and the PL/pgSQL IF did not deny it. | Require workspace membership `IS NOT TRUE` in the denial condition. Both cases now fail with no family/credential insertion; browser revision/audit sequence and claimed attempt remain unchanged. |
| R2: bootstrap returned after exclusive expiry | A proposed browser ID waited on an uncommitted identical primary key. When that transaction rolled back after the deadline, bootstrap returned a new expired preauth browser/vault. | Recheck fresh time after inserts and before audit/result. The operation now raises and leaves no browser, vault, attempt or event rows. |
| R3: begin returned an expired pending attempt | The attempt state digest waited on an uncommitted identical state for another browser. Releasing that claim after expiry produced a successful expired begin result. | Recheck attempt and browser absolute/idle deadlines after the attempt insertion. Failure preserves the prior browser/vault/audit state and inserts no attempt. |
| R4: activation missed the later unique cookie wait | The existing post-family/credential-insert check passed, then cookie rotation waited on another transaction's uncommitted cookie digest. Releasing it after claim expiry still activated the session. | Recheck all attempt/claim/browser/token/session deadlines and the retained old-family expiry after the cookie UPDATE. Failure rolls back family/credential insertion, cookie rotation, vault and attempt/audit transition. |

Each timing case asserts the actual test backend's `Lock/transactionid` wait,
holds it across the exclusive deadline, rolls back the blocker, and asserts the
complete prior state. These are successful waits shorter than the 500-ms lock
timeout; a timeout is not treated as proof of the expiry correction. Synthetic
digest collisions deliberately exercise the SQL boundary without claiming such
collisions have occurred in production. Root independently identified the R4
boundary while this review was auditing later uniqueness claims.

The final product correction is limited to the three fresh-time checks and the
NULL-safe scope predicate. The five new methods are independent additions to
the selected `storage_spec.exs`; the original 18 methods were rerun, not relabeled
as newly independent tests. The exact [patch and reviewed source
snapshot](../verification/hosted-browser-session-storage-review/reviewed-source-manifest.json)
bind the changes. `StorageSchema` SHA-256 is
`676bb977bbe4c322caf63c1a5f40d86e7861847636029948b55cb01f6dedb6dd`;
the tested `storage_spec.exs` is
`2d7202653bff248341c94f33d00dbc67fe5a91c137057695578a1bbc5ba52736`.
Root formatting subsequently identified one extra trailing newline in that
specification. Removing exactly that one byte leaves all nontrailing bytes
unchanged; its current SHA-256 is
`dfffb543660d713a833b241f09d172e3576b0613051cd45e2657ceaa2bf706cc`.
The immutable test receipts retain their original tested hash. Root's PostgreSQL
16 validation and the second reviewer were notified to bind the current bytes.

## Retained execution

All runs used the same selected runner command from the repository root:

```sh
python3 hosted/test/mixer_hosted/browser_auth/run_storage_fixture.py
```

| Immutable attempt | Product source phase | Observed result |
| --- | --- | --- |
| [160002](../verification/hosted-browser-session-storage/attempts/20261025T160002.675098Z-29683a7f/receipt.json) | Exact paused SQL | 18/20; both independent scope cases failed. |
| [160109](../verification/hosted-browser-session-storage/attempts/20261025T160109.739494Z-453eb466/receipt.json) | Exact paused SQL | 18/21; scope and begin unique-wait cases failed. |
| [160209](../verification/hosted-browser-session-storage/attempts/20261025T160209.324733Z-41247e1a/receipt.json) | Exact paused SQL | 18/22; scope, begin and bootstrap unique-wait cases failed. |
| [160254](../verification/hosted-browser-session-storage/attempts/20261025T160254.029794Z-ec7334d2/receipt.json) | Initial scope/bootstrap/begin corrections | 22 passed. |
| [160421](../verification/hosted-browser-session-storage/attempts/20261025T160421.633580Z-6c469d43/receipt.json) | Initial corrections, new R4 case | 22/23; activation cookie-wait case failed. |
| [160530](../verification/hosted-browser-session-storage/attempts/20261025T160530.884605Z-9652e649/receipt.json) | All four findings corrected | 23 passed. |

The runs bind HEAD `1257cbf83f973d3ad05a3a279f94007476f7ce2b`, exact
before/after source/dependency hashes, commands, tool versions, output and cleanup.
Every run reports unchanged inputs during execution and owned PostgreSQL stopped
and scratch removed, including all failing runs. The final run used PostgreSQL
17.11 Homebrew, Erlang/OTP 29 and Elixir 1.20.4. Its expected synthetic owner
fault-injection errors are retained in the successful log. After that run,
documentation changed to describe the findings/evidence and the single trailing
newline was removed from the test source as recorded above. Product executable
source has not changed since the successful run.

The review read and reran the candidate's selected role/RLS, catalog, immutable
audit, exact binding/revisions, one-use claims, family/jti tombstones, rotation,
logout, bounded expiry, AEAD custody and local rollback/reapply checks. Existing
ordinary scoped directory reads and direct DML/column-DML/SET ROLE/lifecycle
execution denials remain passing. Existing canonical authz lock order and
initial-discovery CAS remain intact. After cookie rotation, the remaining
vault/attempt/audit writes use records protected by the held browser, attempt and
vault locks; normal lifecycle callers have no later independent unique claim.

## Pending boundaries

This lane ran no broad hosted harness, whole application compile, frozen hosted
lane, provider call, browser, capture, native runtime, physical phone, production
migration, deployment or credential operation. Only one owned local PostgreSQL
process ran at a time, and every process/scratch directory was cleaned. Other
projects' processes/data were preserved.

Second correction review, root's full nine-migration controls and PostgreSQL 16
CI remain pending in this receipt. Production lifecycle pool/catalog admission,
current default verifier provenance, independent OIDC/provider relation, owner
claim/PKCE custody, Neon roles/ownership transfer/TLS/key custody, ingress/cookie/
cache/logging, commit/response uncertainty, retention scheduling, customer and GA
review remain separate required evidence. The fixed SQL helpers do not establish
provider identity or withstand a compromised lifecycle process/database owner.
