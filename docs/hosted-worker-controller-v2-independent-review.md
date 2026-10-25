# Independent review of the frozen per-operation controller V2

Status: **local development slice recommended; no new correctness finding**.
This review accepts neither a live controller nor any provider, OTA release,
customer workload or GA gate. Root owns integration and its separate validation.
The reviewed candidate remains the separately frozen V2 tree, rather than the
original V1 source or a later integrated tree.

The independent verifier reproduced all 72 frozen groups and added 17 distinct
adversarial groups using actual workerd Durable Objects and SQLite. All pass on
V2. The original source independently reproduces the same three failing cases
and four passing controls; its failed receipt and outputs remain failed evidence.
No producer code, assertion, frozen packet or original failure was repaired by
this review.

## Bound inputs and environment

Before copying or executing candidate code, the reviewer independently verified:

| Binding | Verified value |
| --- | --- |
| Producer receipt SHA-256 | `143295674a760138c358ce5d9ab749724d00848e7fe6eaae312228f6782c8a39` |
| Candidate source tree | `c5848761151f9accfd81eff8292e756cff427e90092d9b7b309b010eb5feb736` |
| Candidate archive SHA-256 | `17a5b38cbc7460d935b0b173ddc45ee8b9c4ef0da25587aa4a2746b3108909c2` |
| Complete 172-record input tree | `ca309000071a7ef5608fe1925664e145bd5f6f7a7bce3fdb06373925728e2d6c` |

Verification covered all 352 producer artifacts, all 60 candidate source/compiled/
contract records, the exact source and input archive members and bytes, 1,180
installed dependency records, 29 bound Jason files and four runtime inputs.
Source-tree digest domains retain their original record shapes. The reviewer
copied the explicit complete closure only after verification and checked copied
dependency bytes again before each run. Original transport vectors were data only.
A final recheck confirms that every bound original input remains unchanged.

Observed tools are Node 22.23.3, npm 10.9.9, TypeScript 5.9.3, Miniflare
4.20260730.0, workerd 1.20260730.1 (`workerd 2026-07-30`) and workers-types
5.20260730.1 on macOS 27.0.1 arm64, compatibility date 2026-07-30. All 58 locked
entries exactly match inventory versions, licenses, resolved URLs, integrities,
nonempty purposes and development-only scope. The 31 installed package versions
also match their locked entries; uninstalled optional platform packages remain
lock/inventory bindings. No dependency was installed and no install script ran.
The bound Jason executable/files were hashed, not executed by this review.

## R1: grant authority, identity and response boundary

The prospective claim now captures operation ID, exact immutable bytes and hash,
epoch, revision, owner, expiry, provider kind/key, instance, boot and claim ID in
`candidate/hosted-worker-controller/src/engine.ts:225–234`. Immutable bytes retain
the record/ref/spec/deadline binding. Consumption and its clock sample persist
before the explicit sync and verification barrier at line 235.

The last transaction at lines 241–247 compares all captured fields with the
current row, requires the permanent consumed state and run intent, rejects
quarantine/terminal state, and checks an actual qualified interval against expiry
and immutable deadline. It saves that exact accepted time with the decision.
There is no await or hook after this decision. Independent AST inspection finds
zero awaits in that final transaction and ten synchronous engine transaction
callbacks overall.

Unchanged regressions now deny the old callback after higher epoch/new owner or
higher revision commits. Focused cases deny changes to all eight independently
mutated identity fields and deny forward expiry renewal, stop, expiry, rollback,
unqualified time and state-version exhaustion without resetting consumption.
Independent additions deny higher epoch with unchanged owner and higher revision
with changed expiry. The same-authority fresh-nonce query and rejected equal-pair
expiry shrink are positive controls: neither wrongly cancels a valid grant.

The implementation uses the default Durable Object outgoing-message gate and
never selects `allowUnconfirmed`. The sealed official storage documentation
supports that boundary; this review does not claim a newly measured deployed
durability guarantee. Actual local fetch/response tests receive a granted result,
SIGKILL only the identified direct-child owned workerd, restart on the same
SQLite storage, and verify the retained claim ID, permanent consumption and final
accepted time. The independent overlap case additionally proves that a returned
final interval whose lower bound moved backward retains its exact endpoints and
old historical floor across that response/restart boundary. The final time write
is therefore exercised through a real runtime response, rather than only an
in-memory model.

## R2: interval history, migration and retained stop

`engine.ts:14–30` compares actual sample upper bounds with the persisted historical
floor. `acceptTime` retains exact latest lower/upper/qualification fields and only
raises `clock_floor`; live authorization uses the actual interval. The seven
accepted-time sites are command admission (69), effect preparation (106), final
dispatch check (124), provider observation decision (144), claim consumption (229),
final grant (245) and result acceptance (262). Each write belongs to its enclosing
synchronous transaction and preserves state-version/CAS behavior.

Runtime tests cover accepted clock history at every site, rollback after process
restart, changing qualification IDs, equality with the old floor, overlapping
intervals, maximum int64 TEXT precision, invalid intervals, actual expiry upper
bounds, and both transaction and final-grant version overflow. Stale/expired
requests retain their specified zero-write behavior. New independent cases show
that rollback at final effect dispatch produces no provider call, rollback at
provider return retains occupancy, a rejected provider observation still retains
its qualified decision history, and late result verification cannot accept under
expired, rolled-back or unavailable time. Result CAS, exact retained digest retry,
conflicting reports and stop-winning races pass.

`candidate/hosted-worker-controller/src/ledger.ts:20–40` implements the selected
schema-2 migration. Existing schema-1 rows preserve identity, claims, tombstones,
provider and result fields, initialize the floor from retained history and
quarantine; an empty schema-1 operation upgrades normally. Unknown metadata fails
before writes. Focused tests verify active/consumed/permanent-stop/terminal rows.
The independent migration overflow control forces an exhausted state version:
constructor migration fails unavailable and rolls back the entire ALTER, leaving
the original row and absent floor column intact. This is an actual failed
migration with retained identity, rather than an asserted successful upgrade.

Quarantine blocks new launch/claim/result acceptance. `engine.ts:89–96,120–121,
140–154` still permits enforcement of an already committed exact retained stop
and acceptance of definitive drain evidence without a qualified clock. Independent
revoked-claim and retained accepted-result cases both migrate, remain quarantined,
and settle that preexisting stop with unqualified time. The pending accepted
result remains unchanged; quarantine does not accept a new result. Terminal
identity and one-shot claim state remain permanent.

## Executed evidence and cleanup

| Check | Result |
| --- | --- |
| Original source baseline | Expected exit 1; exact original three failures, four controls pass. |
| Clean V2 rebuild | Exit 0; every compiled/data output matches the frozen candidate bytes. |
| Original suite | All 28 reported groups pass, including unchanged frozen scenarios/fixtures, original 36 vectors, additional 24 Jason/Unicode vectors, concurrency, alarm, timeout, stop, results and four SIGKILL cases. |
| Unchanged independent regressions | All seven groups pass. Assertion sources are byte-identical. |
| Frozen focused suite | All 36 groups pass, including four SIGKILL cases. |
| Unchanged noncooperative timeout | Pass. One occupied provider call remains after abort/timeout until its promise settles; no relaunch or terminal release is inferred. |
| Added independent probes | All 17 distinct groups pass. The first 16-case run and final 17-case run are both retained. |
| Production AST closure | Both replayed and separately written AST checks reach exactly nine compiled/data files, only `cloudflare:workers` external; no test routes, selectors, schema, dynamic import, require, eval, Function loader or unconfirmed-write opt-out. Static closure is not OTA authority. |
| Dependency/tool inventory | Exact 58-entry metadata and selected tool versions pass; zero installs/scripts. |
| Cleanup | All 194 recorded owned storage paths and 11 per-command source/dependency scratch trees removed; 24 specifically identified owned-process SIGKILL/restart observations retained, including repeated verification runs. Shared dependency-copy scratch and expanded frozen scratch removed; immutable archives retained. No owned workerd remains. |

Every runtime uses a new copy of the frozen candidate and already verified
pinned dependency bytes. At most one test runtime is active in this lane. The
noncooperative run substitutes the complete unchanged archived excluded fixture
Worker and rebuilds only in its scratch; production source/output bytes are
checked unchanged. Original and independent assertion bodies remain unchanged.
The new independent fixtures change no product source or candidate test Worker.
Commands, exact executable/source/input/output hashes, actual owned process IDs,
provider observations, storage paths and cleanup are bound in the review receipt.
The complete consulted frozen input closure and all executed fixture variants
are retained in archives, including original failed controls.

## Recommendation and limits

Root may integrate this exact bounded R1/R2 development slice and validate the
integrated tree. No remaining correctness defect was observed within this frozen
scope. The review does not erase the rejected V1 packet, qualify real providers,
select an operational clock, or accept any later change automatically.

Registry/scheduler integration, missed wakes/exhausted retries, independent
nonrollbackable restore/namespace authority, actual edge TLS/header/framing/EOF,
measured live clocks, Linux/macOS images and resource/egress/isolation, trusted
runner/source/private-object/result authorization, descendant disposal,
whole-domain limits, Neon/Oban zero-traffic operation, SLOs, public authorization,
key custody/signing, stores, immutable published FieldLog dogfood, customer and
all GA qualification remain pending. Local SQLite/process-kill tests are not
distributed machine-failure or production qualification. Physical phones remain
disconnected and deferred.

This lane did not read/import/execute the frozen catalog/authority lane or the
separately interrupted outbound transport V2 review. It made no Git, shared
tracker/inventory, cloud/provider/deployment, customer, credential, native,
simulator/emulator, phone or UI changes. Other projects' processes and data were
preserved. Only this report and its owned verification directory were written.
