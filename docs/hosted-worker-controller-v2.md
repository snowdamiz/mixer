# Per-operation controller V2 repair candidate

Status: **frozen for fresh independent review; not accepted**. This isolated
candidate repairs R1 and R2 from the rejected
[controller review](hosted-worker-controller-implementation-independent-review.md).
The original `hosted-worker-controller/` and its producer/rejected-review packets
remain unchanged. The replacement source is only in
`verification/hosted-worker-controller-v2/candidate/hosted-worker-controller/`.
Root owns integration, commits, pushes and acceptance.

## Bound starting point and scope

Before copying source, this lane independently verified producer receipt
`fb71bcb1cc076b121a26e075c8e1bf8c2703bc5a659686e4a6ae861b855dc68a`,
source tree `6f47612d9bf3118fb50be51f36dc05bbd724bd60416a5cdec0b1fa6299042e95`
and archive `d6894fdae991b51485e7bec04a86027f87d84261ddc527e292e072c8b8dd55b7`,
plus rejected review receipt
`7e146e6f341afc93dca4f108bbee7ee50f7c4a406eb329bd5fa96405463f5b7e`.
Verification covered all 60 producer source records/archive members, 1,180
installed dependency files, 29 Jason files, 54 producer artifacts, four runtime
inputs, 17 command-output pairs, 48 review artifacts and 12 archived review
fixtures. All 58 dependency lock entries match the existing inventory.

The baseline copy reproduces the same three failures: a higher epoch/new owner
and a higher revision commit while a consumed claim callback is paused, and an
accepted later reconciliation clock sample is forgotten before a rollback claim.
The matching four independent controls still pass. These failures and all prior
rejected evidence are retained without rewriting assertions or producer bytes.

Only the isolated `engine.ts`, `ledger.ts`, `schema.sql`, excluded verification
Worker and their compiled outputs change. Existing suite, acceptance driver,
frozen acceptance assertions and exact independent regression assertion bodies
remain byte-identical. The independent noncooperative test uses its complete
unchanged archived fixture Worker in an ephemeral runtime copy. Exact diffs and
assertion/fixture hashes are included in this packet.

## R1: final grant linearization and identity

The consumption transaction retains the exact prospective grant's operation ID,
immutable binding bytes/hash, epoch, revision, owner, expiry, provider kind/key,
instance, boot and claim ID. Consumption and its accepted clock interval commit
before `storage.sync()` and the existing verification barrier. Consumption is
permanent even when no grant is returned.

After every asynchronous boundary, one final synchronous transaction reads the
current row and compares every retained field, permanent consumed state, run
intent, phase, quarantine and terminal state. It samples the actual qualified
clock, checks the actual upper bound against expiry and immutable deadline,
and writes the accepted interval/history with the grant decision. A renewal
that changes expiry also denies the older prospective grant. No await or hook
follows the final decision, and a denied grant never resets/transfers/reissues
consumption.

That synchronous transaction is the grant's linearization point. Explicit sync
has already protected consumption; the final clock write uses the default DO
output gate before the response can become externally visible. Cloudflare's
[storage documentation](https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/)
describes automatic outgoing-message gating until writes succeed, synchronous
transaction rollback and `sync()` persistence. This candidate never opts out
with `allowUnconfirmed`. The exact retrieved documentation/tool output is sealed.
A direct Python retrieval initially returned HTTP 403; its failure is recorded
and the official contract was retrieved through the web tool.

The tests exercise the real workerd request/response path, then SIGKILL the exact
owned child and restart against the same SQLite storage. They confirm that a
returned grant's final accepted time survives and a second grant remains denied.
They do not measure deployed distributed durability, actual ingress, a real
runner, sandbox execution or physical machine failure. A future authenticated
runner adapter must preserve this decision/output-gate boundary.

## R2: exact time plus nondecreasing history

Root selected schema 2 with one added decimal-TEXT field, `clock_floor`.
`clock_lower`, `clock_upper` and `clock_qualification` retain the **exact latest
accepted qualified interval**, even if uncertainty makes its lower bound move
backward. `clock_floor` is the maximum lower bound of every accepted interval.
All comparisons use BigInt. A sample with `upper_us < clock_floor` durably
quarantines the operation; equality is compatible with the known interval.
Changing qualification IDs does not reset history. Neither the floor nor a
clamped wall time is substituted for the actual sample in expiry authorization.

Successful command, effect preparation/final dispatch check, provider observation,
claim consumption/final grant and report acceptance decisions retain their
qualified intervals in their own SQLite transactions. Rejected or stale commands
retain the existing zero-write behavior; an observed rollback durably quarantines.
A valid but expired sample that authorizes no effect/claim is not accepted into
history. In particular, it cannot create authority or rewrite an expired request.
Missing/unqualified time authorizes no new work. Clock writes preserve the normal
state-version increment/CAS and bounded 32-slot audit behavior; overflow throws
and rolls back the whole transaction instead of wrapping or issuing a grant.

Root explicitly selected a conservative, non-destructive schema-1 migration:
empty schema 1 upgrades normally; existing operation rows retain all identity,
authority, provider, consumed/revoked claim, permanent stop, result and terminal
fields, gain a floor initialized from the retained interval, and are quarantined.
V1 forgot historical samples, so the initialized floor cannot justify resumed
execution. Migration advances the state version and records bounded audit evidence.
Only the schema metadata table is replaced to change its version CHECK constraint;
operation/audit rows are preserved. Unknown schemas fail unavailable before writes.
No API to clear quarantine or infer a new restore authority is implemented.

Quarantine blocks launch, claim and result acceptance. It still permits exact
retained-provider enforcement of an already committed permanent stop and accepts
definitive drain evidence for that stop. Unqualified time does not reopen work.
A quarantined terminal identity remains retained; no ensure can restart it.

## Observed verification

All final test commands use Node 22.23.3/npm 10.9.9, TypeScript 5.9.3,
Miniflare 4.20260730.0, workerd 1.20260730.1 and workers-types 5.20260730.1,
compatibility date 2026-07-30, on macOS 27.0.1 arm64. Each command runs in a
fresh owned copy of the sealed source and already installed dependency bytes.
No package installation or dependency script ran; any reinstall must use
`npm ci --ignore-scripts --no-audit --no-fund` with the existing lockfile.

| Check | Observed result |
| --- | --- |
| Baseline failure reproduction | Exact seven review groups: same three fail, four controls pass; expected exit 1 retained. |
| Clean V2 rebuild | Pass; newly generated compiled outputs match the tested candidate. |
| Original suite | All 28 groups pass with unchanged assertions, including 20 frozen scenarios plus five fixtures, 36 original vectors, 24 additional Jason/control vectors and four SIGKILL/restart cases. |
| Exact independent regressions | All seven groups pass, including the three formerly failing cases and stop/drain/precision/quarantine controls. |
| Added focused suite | All 36 groups pass on actual workerd/SQLite; four SIGKILL/restart checks, full claim identity races, expiry/renewal/rollback/unqualified time, effect/report history, result CAS, overlap ratchet, exact int64/overflow, migration/quarantine and committed stop enforcement. |
| Exact noncooperative timeout fixture | Pass; an ignored abort retains the occupied provider slot until completion, then stop/drain can settle without relaunch. |
| Production AST closure | Pass: nine production compiled/data files, only `cloudflare:workers` external, no test routes/selectors/loaders/schema. Static closure is not OTA authorization. |
| Dependency verification | All 58 exact entries match versions, licenses, integrities, resolved URLs, purposes and development-only scope. |
| Cleanup | Every owned runtime disposed or specifically killed/restarted; every recorded test storage path and per-command scratch removed; no exact owned workerd executable remains. Other projects untouched. |

The final packet's receipt gives exact command/source/tool/output hashes, all
intermediate source snapshots and cleanup counts. It preserves baseline failures,
intermediate passing attempts and the documentation retrieval failure. No tests
were skipped or rewritten to obtain the stated passes. The production clock,
provider and object verifier remain unavailable, with no runner HTTP or test
control ingress in the production module closure.

## Handoff and pending boundaries

The receipt status is `frozen-v2-repair-awaiting-independent-review`. A fresh
reviewer must verify the complete source/input closure, rebuild, replay the exact
original and independent assertions, inspect the focused cases and review the
transaction/output-gate reasoning. This lane does not independently accept the
slice or mark any GA gate verified.

Pending registry/scheduler integration, missed wakes/exhausted alarm retries,
independent nonrollbackable restore/namespace authority, actual Cloudflare edge
TLS/header/framing/EOF, qualified live clocks, provider/image/resource/egress and
hostile-source isolation, authenticated runner/source/private-R2/object/results,
descendant termination, whole-domain limits, Neon/Oban zero-traffic operation,
operational SLOs, public authorization, signing/key custody, stores, immutable
published FieldLog dogfood, customer qualification and all relevant GA gates
remain pending. Physical phones remain disconnected and deferred.

No frozen catalog-inspector/authority-driver or separately interrupted outbound
transport V2 review was read/imported/executed. Original transport vectors were
used as data only. No live provider/cloud/deployment, credentials, customer
messages/data, native runtimes, simulator/emulator/UI, shared status/inventory,
Git or other active lane was changed.
