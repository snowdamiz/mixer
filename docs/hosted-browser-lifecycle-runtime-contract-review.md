# Browser lifecycle runtime contract independent review

Status: passes bounded documentation/source review on 2026-10-25 after the
corrections below. No implementation-blocking contradiction remains in the
reviewed document. This selects no production implementation, provider, grant,
credential, migration, browser route or GA gate. Runtime implementation and its
adversity cases remain pending.

The reviewed [contract](hosted-browser-lifecycle-runtime-contract.md) has SHA-256
`9f58a7656c6bb8ddf95d4a8e97e611a6b8d05c2a64f3557d46143a345b5aaff4`, against
HEAD `7e434330cad8e3566a4a21a6d7ff996da3bc4967`. The complete selected source
manifest and commands are in the [immutable review attempt](../verification/hosted-browser-lifecycle-runtime-contract-review/attempts/20261025T163534.676836Z/receipt.json).
Its selected tree digest is
`14e51da8b5ef46f80a09233543e8a77bb115d8264be5986e99a4da1949c4beee`.

## Corrections confirmed

1. Runtime construction now receives the actual validated hosted runtime
   configuration carrying role, identity startup and ordinary Repo settings.
   Browser Config is loaded with that role and identity startup. The production
   startup must use those same values; neither an arbitrary struct nor unrelated
   startup/connection lists establish provenance. Configured processor mode
   remains denied. These are proposed runtime joins, not existing functionality.
2. Existing ordinary `scoped_read`, `scoped_lock` and `directory_read` policies
   omit `TO` and therefore target PostgreSQL PUBLIC. Catalog admission explicitly
   preserves their exact baseline predicates and targets while rejecting added
   or widened policies. New writer-only policies and narrow grants remain
   separate expectations. Blanket PUBLIC-policy rejection would have rejected
   the accepted ordinary migrations.
3. Existing KeyOwner can replace its manifest generation without changing PID.
   The document no longer implies a process monitor observes that change or an
   existing generation-read/notification API. Its stated guarantee is fresh
   default `authenticate/2`, current verifier finish checks, exact Config fields
   and registered PID continuity. It does not promise atomic trust-generation
   fencing with a later PostgreSQL commit.
4. The first bootstrap/load implementation slice explicitly rejects an active
   snapshot for authentication/workspace use until its current verifier and
   ordinary protected pipeline exist. It can still prove useful preauth encrypted
   storage, admission, bounded checkout, rollback and redaction without enabling
   a browser route.

## Source and contract conclusions

The accepted StorageSchema still exposes eighteen functions, nine public
EXECUTEs and the original three composite types. Its exact nine public signatures
match the contract. The proposed activation-preparation helper and composite are
additive future work, with nineteen functions and ten EXECUTEs only after a
separate reviewed implementation. No accepted SQL behavior is inferred from the
proposal, and initial provisioning cannot be silently replayed for its upgrade.

ConfiguredVerifier returns bounded token evidence with no principal ID or
database revisions. The preparation proposal supplies those provisional values
from a single statement snapshot bound to a current claimed attempt. The
unchanged activation revalidates them under its canonical authz-before-browser
lock order. The new preparation response has exactly six top-level fields;
its nested snapshot uses the existing closed three-field StoredSnapshot format.
Claimed attempts retain claim metadata and erase their attempt ciphertext.

The claim path retains and compares its full discovery snapshot before durable
claim consumption; copied/foreign process handles and uncertain claim commits
cannot authorize provider exchange. Activation avoids a browser SHARE pre-lock
before requesting authz locks. Existing Vault contexts remain authoritative for
AEAD, with token size limited to 4089 bytes and encryption/decryption outside the
mutating transaction. Returned counters, linkage and sealed bytes require exact
comparison before publication. No opaque struct or successful decryption is
treated as provider, identity or authorization proof.

Catalog expectations distinguish granted table/column rights, PUBLIC/default
rights, role reachability, policies, function source/settings, type shapes and
integrity triggers. The compiled baseline manifest does not itself implement
those comparisons. The full expected matrix and current transaction-local
Catalog implementation remain prerequisites. Restricted non-login ownership is
an explicit target for new fixtures and deployment; historical fixture shortcuts
do not become accepted runtime topology.

Custody accepts externally supplied synthetic material for tests and makes no
claim to validate its source. Production injection, provider credentials and
provider/OIDC transport remain separately unqualified. No raw key or token is
authorized in public responses, digest metadata, database settings or receipts.

## Evidence limits

The [independent runner](../verification/hosted-browser-lifecycle-runtime-contract-review/check_review.py)
passes twelve structural controls and obtains its own inventory by loading only
ordinary standalone StorageSchema into a terminated Elixir subprocess. Python
3.14.8, Elixir 1.20.4 / Erlang OTP 29 and Git 2.56.0 are recorded with exact
commands, output and unchanged source hashes. The review did not execute the
producer checker or a broad hosted harness. Textual checks are documentation
evidence only; they do not authorize runtime security or an OTA release.

No PostgreSQL instance, provider exchange, native simulator/emulator, phone,
capture or UI automation was started. Frozen catalog-inspector/authority-driver
and rejected outbound Worker V2 sources were not read, imported or executed.
Runtime catalog drift, pool limits, SQL/AEAD roundtrips, commit uncertainty,
new migration rollback/mixed versions, owner lifecycle, provider/OIDC/Neon/key
custody and protected HTTP/console composition remain unrun here. Browser,
native and phone checks remain paused. Customer/FieldLog and GA acceptance remain
pending; no gate was promoted.
